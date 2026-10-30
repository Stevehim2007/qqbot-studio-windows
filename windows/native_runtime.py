"""Native Windows POC runtime for AstrBot + SnowLuma + desktop NTQQ.

Single-instance process manager only. It does not install or authenticate
AstrBot/SnowLuma/NTQQ. Missing prerequisites are surfaced as explicit blockers;
the native launcher refuses to pretend an unverified end-to-end link is ready.
"""

from __future__ import annotations

import json
import os
import secrets
import shlex
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qqbot_studio.store import default_data_dir

NATIVE_MODE = "native-poc"
DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_ASTRBOT_WEBUI_PORT = 6185
DEFAULT_ASTRBOT_ONEBOT_PORT = 6199
DEFAULT_SNOWLUMA_WEBUI_PORT = 5099


class NativePOCError(RuntimeError):
    """Actionable native POC error."""


class NativeBlocked(NativePOCError):
    """Required native components are absent/unusable."""

    def __init__(self, blockers: list[str]):
        super().__init__("; ".join(blockers))
        self.blockers = blockers


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def native_root(value: str | Path | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return (default_data_dir() / "native").resolve()


def config_path(root: Path) -> Path:
    return Path(root).resolve() / "native.json"


def run_dir(root: Path) -> Path:
    return Path(root).resolve() / "run"


def logs_dir(root: Path) -> Path:
    return Path(root).resolve() / "logs"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _write_json_atomic(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def default_config(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    return {
        "schema_version": 1,
        "mode": NATIVE_MODE,
        "bind_host": DEFAULT_BIND_HOST,
        "astrbot_command": [],
        "astrbot_root": str(root / "astrbot"),
        "astrbot_webui_port": DEFAULT_ASTRBOT_WEBUI_PORT,
        "astrbot_onebot_port": DEFAULT_ASTRBOT_ONEBOT_PORT,
        "snowluma_dir": str(root / "snowluma"),
        "snowluma_command": [],
        "snowluma_webui_port": DEFAULT_SNOWLUMA_WEBUI_PORT,
        "onebot_url": f"ws://{DEFAULT_BIND_HOST}:{DEFAULT_ASTRBOT_ONEBOT_PORT}/ws",
        "onebot_token": "",
        "ntqq_path": "",
        "public_host": "",
        "created_at": utc_now(),
    }


def load_config(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    cfg = default_config(root)
    stored = _read_json(config_path(root))
    if stored:
        cfg.update(stored)
    # POC security: keep the management/OneBot side loopback-only. A public
    # host is display-only; it must never silently rebind the service.
    if str(cfg.get("bind_host") or "") not in {"127.0.0.1", "localhost", "::1"}:
        cfg["bind_host"] = DEFAULT_BIND_HOST
    if not str(cfg.get("onebot_url") or "").startswith(("ws://127.0.0.1:", "ws://localhost:")):
        cfg["onebot_url"] = f"ws://{DEFAULT_BIND_HOST}:{int(cfg.get('astrbot_onebot_port') or 6199)}/ws"
    if not str(cfg.get("onebot_token") or "").strip():
        cfg["onebot_token"] = secrets.token_urlsafe(24)
    return cfg


def save_config(root: Path, config: dict[str, Any]) -> Path:
    path = config_path(root)
    _write_json_atomic(path, config)
    return path


def parse_command(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    raw = str(value).strip()
    if not raw:
        return []
    parts = shlex.split(raw, posix=False)
    return [
        part[1:-1] if len(part) >= 2 and part[0] == part[-1] == '"' else part
        for part in parts
    ]


def _pid_alive(pid: int) -> bool:
    if int(pid) <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if not handle:
                return False
            try:
                return True
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        reaped, _status = os.waitpid(int(pid), os.WNOHANG)
        if reaped == int(pid):
            return False
    except (ChildProcessError, OSError):
        pass
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _kill_pid(pid: int) -> None:
    if int(pid) <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(int(pid), 15)
    except OSError:
        try:
            os.kill(int(pid), 15)
        except OSError:
            return


def find_ntqq_path() -> str:
    for env_name in ("QQ_EXE", "NTQQ_PATH"):
        value = os.environ.get(env_name, "").strip()
        if value and Path(value).is_file():
            return str(Path(value).resolve())
    found = shutil.which("QQ.exe") or shutil.which("QQ")
    if found:
        return str(Path(found).resolve())
    candidates: list[Path] = []
    for root in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        if root:
            candidates.extend(
                Path(root) / rel
                for rel in (r"Tencent\QQ.exe", r"Tencent\QQNT\QQ.exe", r"Tencent\QQ\Bin\QQ.exe")
            )
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidates.extend(
            Path(local) / rel
            for rel in (
                r"Tencent\QQ.exe",
                r"Tencent\QQNT\QQ.exe",
                r"Programs\Tencent\QQ.exe",
                r"Programs\Tencent\QQNT\QQ.exe",
            )
        )
    if os.name == "nt":
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            candidates.extend(
                Path(f"{letter}:\\") / rel
                for rel in (
                    r"Program Files\Tencent\QQ.exe",
                    r"Program Files\Tencent\QQNT\QQ.exe",
                    r"Program Files (x86)\Tencent\QQ.exe",
                    r"Program Files (x86)\Tencent\QQNT\QQ.exe",
                )
            )
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "(Get-Process QQ -ErrorAction SilentlyContinue | Where-Object {$_.Path} | Select-Object -First 1).Path",
                ],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            lines = (result.stdout or "").strip().splitlines()
            if lines and lines[0] and Path(lines[0]).is_file():
                return str(Path(lines[0]).resolve())
        except (OSError, subprocess.SubprocessError):
            pass
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return ""


def find_astrbot_command() -> list[str]:
    env = os.environ.get("ASTRBOT_COMMAND", "").strip()
    if env:
        return parse_command(env)
    for name in ("astrbot.exe", "astrbot"):
        found = shutil.which(name)
        if found:
            return [str(Path(found).resolve()), "run"]
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        for version in ("Python312", "Python311", "Python313"):
            candidate = Path(local) / "Programs" / "Python" / version / "Scripts" / "astrbot.exe"
            if candidate.is_file():
                return [str(candidate.resolve()), "run"]
    return []


def find_snowluma_launcher(snowluma_dir: str | Path) -> list[str]:
    directory = Path(snowluma_dir).expanduser()
    for name in ("launcher.bat", "SnowLuma.exe", "snow-luma.exe"):
        candidate = directory / name
        if candidate.is_file():
            if candidate.suffix.lower() == ".bat":
                return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(candidate)]
            return [str(candidate.resolve())]
    return []


def _display_command(command: list[str] | None) -> str:
    return " ".join(str(item) for item in (command or []))


def _service_record_path(root: Path, service: str) -> Path:
    return run_dir(root) / f"{service}.json"


def service_record(root: Path, service: str) -> dict[str, Any] | None:
    return _read_json(_service_record_path(root, service))


def service_alive(root: Path, service: str) -> bool:
    record = service_record(root, service)
    if not record:
        return False
    try:
        return _pid_alive(int(record.get("pid") or 0))
    except (TypeError, ValueError):
        return False


def _tail(path: Path, lines: int) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max(4096, int(lines) * 512)))
            data = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(data.splitlines()[-max(1, int(lines)) :])


def is_port_free(port: int, host: str = DEFAULT_BIND_HOST) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
            if os.name == "nt" and exclusive is not None:
                try:
                    sock.setsockopt(socket.SOL_SOCKET, exclusive, 1)
                except OSError:
                    pass
            else:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(port)))
        return True
    except OSError:
        return False


def port_listening(port: int, host: str = DEFAULT_BIND_HOST) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=0.8):
            return True
    except OSError:
        return False


def probe_http(url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "QQBotStudioNativePOC/0.7"}, method="GET"
        )
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            return {"ok": True, "status": int(response.status), "detail": f"HTTP {int(response.status)}"}
    except urllib.error.HTTPError as exc:
        return {"ok": True, "status": int(exc.code), "detail": f"HTTP {int(exc.code)}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "detail": str(exc)}


def check_prerequisites(
    root: Path, config: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    cfg = dict(config or load_config(root))
    astrbot_command = list(cfg.get("astrbot_command") or find_astrbot_command())
    snowluma_dir = Path(str(cfg.get("snowluma_dir") or (root / "snowluma"))).expanduser()
    snowluma_command = list(cfg.get("snowluma_command") or find_snowluma_launcher(snowluma_dir))
    ntqq_path = str(cfg.get("ntqq_path") or find_ntqq_path())
    return [
        {
            "name": "windows",
            "ok": os.name == "nt",
            "blocking": True,
            "detail": f"os.name={os.name}; Native POC targets Windows 10/11 x64",
        },
        {
            "name": "ntqq",
            "ok": bool(ntqq_path and Path(ntqq_path).is_file()),
            "blocking": True,
            "detail": ntqq_path or "official Windows NTQQ not found (set QQ_EXE or --ntqq-path)",
            "path": ntqq_path,
        },
        {
            "name": "astrbot",
            "ok": bool(astrbot_command),
            "blocking": True,
            "detail": _display_command(astrbot_command) or "AstrBot CLI not found (set ASTRBOT_COMMAND or --astrbot-command)",
            "command": astrbot_command,
        },
        {
            "name": "snowluma",
            "ok": snowluma_dir.is_dir() and bool(snowluma_command),
            "blocking": True,
            "detail": (
                f"dir={snowluma_dir}; command={_display_command(snowluma_command)}"
                if snowluma_dir.is_dir()
                else f"extracted SnowLuma Windows directory not found: {snowluma_dir}"
            ),
            "path": str(snowluma_dir),
            "command": snowluma_command,
        },
        {
            "name": "node",
            "ok": bool(shutil.which("node")),
            "blocking": False,
            "detail": shutil.which("node")
            or "not found (full SnowLuma bundles Node; lite needs Node 22/24)",
        },
        {
            "name": "onebot",
            "ok": str(cfg.get("onebot_url") or "").startswith(("ws://127.0.0.1:", "ws://localhost:")),
            "blocking": True,
            "detail": str(cfg.get("onebot_url") or ""),
        },
    ]


def blockers(results: list[dict[str, Any]]) -> list[str]:
    return [
        f"{item['name']}: {item.get('detail', '')}"
        for item in results
        if item.get("blocking") and not item.get("ok")
    ]


def write_snowluma_onebot_config(
    root: Path, config: dict[str, Any], *, force: bool = False
) -> dict[str, Any]:
    root = Path(root).resolve()
    cfg = dict(config)
    snowluma_dir = Path(str(cfg.get("snowluma_dir") or (root / "snowluma"))).expanduser().resolve()
    if not snowluma_dir.is_dir():
        raise NativePOCError(f"SnowLuma directory does not exist: {snowluma_dir}")
    path = snowluma_dir / "config" / "onebot.json"
    payload: dict[str, Any]
    if path.exists() and not force:
        existing = _read_json(path)
        if existing is None:
            raise NativePOCError(
                f"SnowLuma onebot.json is not a valid JSON object; refusing to overwrite: {path}"
            )
        payload = existing
    else:
        payload = {}
    networks = payload.setdefault("networks", {})
    if not isinstance(networks, dict):
        raise NativePOCError(f"SnowLuma onebot.json networks is not an object: {path}")
    token = str(cfg.get("onebot_token") or "")
    onebot_url = str(
        cfg.get("onebot_url")
        or f"ws://127.0.0.1:{int(cfg.get('astrbot_onebot_port') or 6199)}/ws"
    )
    networks["httpServers"] = []
    networks["httpClients"] = []
    networks["wsServers"] = []
    networks["wsClients"] = [
        {
            "name": "astrbot",
            "enabled": True,
            "url": onebot_url,
            "role": "Universal",
            "accessToken": token,
            "messageFormat": "array",
            "reportSelfMessage": False,
            "reconnectIntervalMs": 5000,
        }
    ]
    status = payload.get("statusCommand")
    if not isinstance(status, dict):
        status = {}
    status.update({"enabled": False, "swallow": False, "cooldownSeconds": 5, "trigger": "#sl"})
    payload["statusCommand"] = status
    history = payload.get("historySync")
    if not isinstance(history, dict):
        history = {}
    history["enabled"] = False
    payload["historySync"] = history
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(path, payload)
    cfg["onebot_config_path"] = str(path)
    save_config(root, cfg)
    return {"ok": True, "path": str(path), "onebot_url": onebot_url}


def onebot_connection_hint(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": str(config.get("onebot_url") or ""),
        "token_present": bool(config.get("onebot_token")),
        "astrbot_fields": {
            "ws_reverse_host": "127.0.0.1",
            "ws_reverse_port": int(config.get("astrbot_onebot_port") or 6199),
            "ws_reverse_token": "<same token stored in native.json>",
        },
        "snowluma_config": "config/onebot.json wsClients[0]",
    }


def health_payload(root: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    cfg = dict(config or load_config(root))
    host = str(cfg.get("bind_host") or DEFAULT_BIND_HOST)
    astrbot_url = f"http://{host}:{int(cfg.get('astrbot_webui_port') or 6185)}/"
    snowluma_url = f"http://{host}:{int(cfg.get('snowluma_webui_port') or 5099)}/"
    astrbot_http = probe_http(astrbot_url)
    snowluma_http = probe_http(snowluma_url)
    onebot_port = int(cfg.get("astrbot_onebot_port") or 6199)
    return {
        "ok": bool(astrbot_http["ok"] and snowluma_http["ok"]),
        "astrbot": {"alive": service_alive(root, "astrbot"), "http": astrbot_http, "url": astrbot_url},
        "snowluma": {"alive": service_alive(root, "snowluma"), "http": snowluma_http, "url": snowluma_url},
        "onebot": {"url": str(cfg.get("onebot_url") or ""), "port": onebot_port, "listening": port_listening(onebot_port, host)},
        "no_vnc_used": True,
        "qq_login": "Use the official local Windows QQ/NTQQ window; noVNC is not used by Native POC.",
    }


def start_process(
    root: Path,
    service: str,
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    log_name: str | None = None,
) -> int:
    root = Path(root).resolve()
    if not command:
        raise NativePOCError(f"{service} command is not configured")
    if service_alive(root, service):
        raise NativePOCError(f"{service} is already running")
    cwd = Path(cwd).expanduser().resolve()
    if not cwd.is_dir():
        raise NativePOCError(f"{service} working directory does not exist: {cwd}")
    log_path = logs_dir(root) / (log_name or f"{service}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) | int(
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        start_new_session = True
    with log_path.open("ab", buffering=0) as log_handle:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
    record = {
        "service": service,
        "pid": int(process.pid),
        "command": [str(item) for item in command],
        "cwd": str(cwd),
        "log_path": str(log_path),
        "started_at": utc_now(),
    }
    _write_json_atomic(_service_record_path(root, service), record)
    time.sleep(0.35)
    if not _pid_alive(int(process.pid)):
        raise NativePOCError(
            f"{service} exited immediately (exit code {process.poll()}); log tail:\n{_tail(log_path, 40)}"
        )
    return int(process.pid)


def stop_process(root: Path, service: str) -> bool:
    root = Path(root).resolve()
    record_path = _service_record_path(root, service)
    record = service_record(root, service)
    if not record:
        return False
    try:
        pid = int(record.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    if pid > 0 and _pid_alive(pid):
        _kill_pid(pid)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and _pid_alive(pid):
            time.sleep(0.2)
    try:
        record_path.unlink()
    except OSError:
        pass
    return True


def start_native(
    root: Path,
    config: dict[str, Any] | None = None,
    *,
    enforce_windows: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    cfg = dict(config or load_config(root))
    checks = check_prerequisites(root, cfg)
    missing = blockers(checks)
    if not enforce_windows:
        missing = [item for item in missing if not item.startswith("windows:")]
    if missing:
        raise NativeBlocked(missing)
    astrbot_dir = Path(str(cfg.get("astrbot_root") or (root / "astrbot"))).expanduser().resolve()
    snowluma_dir = Path(str(cfg.get("snowluma_dir") or (root / "snowluma"))).expanduser().resolve()
    astrbot_dir.mkdir(parents=True, exist_ok=True)
    snowluma_dir.mkdir(parents=True, exist_ok=True)
    written = write_snowluma_onebot_config(root, cfg)
    if not service_alive(root, "astrbot"):
        command = list(cfg.get("astrbot_command") or find_astrbot_command())
        if not command:
            raise NativeBlocked(["astrbot command not configured/discovered"])
        if not is_port_free(int(cfg.get("astrbot_webui_port") or 6185), str(cfg.get("bind_host") or "127.0.0.1")):
            raise NativePOCError("AstrBot WebUI port is already in use")
        if not is_port_free(int(cfg.get("astrbot_onebot_port") or 6199), "127.0.0.1"):
            raise NativePOCError("AstrBot OneBot port is already in use")
        env = os.environ.copy()
        env.update(
            {
                "ASTRBOT_ROOT": str(astrbot_dir),
                "PYTHONUTF8": "1",
                "QQBOT_NATIVE_ONEBOT_URL": str(cfg.get("onebot_url") or ""),
                "QQBOT_NATIVE_ONEBOT_TOKEN": str(cfg.get("onebot_token") or ""),
            }
        )
        start_process(root, "astrbot", command, cwd=astrbot_dir, env=env)
    if not service_alive(root, "snowluma"):
        if not is_port_free(int(cfg.get("snowluma_webui_port") or 5099), str(cfg.get("bind_host") or "127.0.0.1")):
            raise NativePOCError("SnowLuma WebUI port is already in use")
        command = list(cfg.get("snowluma_command") or find_snowluma_launcher(snowluma_dir))
        if not command:
            raise NativeBlocked(["SnowLuma launcher not configured/discovered"])
        env = os.environ.copy()
        env["QQBOT_NATIVE_ONEBOT_URL"] = str(cfg.get("onebot_url") or "")
        start_process(root, "snowluma", command, cwd=snowluma_dir, env=env)
    runtime = {
        "schema_version": 1,
        "mode": NATIVE_MODE,
        "started_at": utc_now(),
        "astrbot_pid": (service_record(root, "astrbot") or {}).get("pid"),
        "snowluma_pid": (service_record(root, "snowluma") or {}).get("pid"),
        "onebot": onebot_connection_hint(cfg),
        "qq_login": "Open the official local NTQQ window and scan/verify there; noVNC is not used.",
    }
    _write_json_atomic(run_dir(root) / "runtime.json", runtime)
    return {
        "ok": True,
        "root": str(root),
        "runtime": runtime,
        "onebot_config": written,
        "checks": checks,
        "note": "Native POC manages local processes only; real AstrBot/SnowLuma/NTQQ E2E and QQ login are not claimed.",
    }


def stop_native(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    snowluma = stop_process(root, "snowluma")
    astrbot = stop_process(root, "astrbot")
    try:
        (run_dir(root) / "runtime.json").unlink()
    except OSError:
        pass
    return {"ok": True, "astrbot_stopped": astrbot, "snowluma_stopped": snowluma}


def status_payload(root: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    cfg = dict(config or load_config(root))
    services: dict[str, Any] = {}
    for service in ("astrbot", "snowluma"):
        record = service_record(root, service)
        default_command = list(cfg.get(f"{service}_command") or [])
        if service == "snowluma" and not default_command:
            default_command = find_snowluma_launcher(cfg.get("snowluma_dir") or "")
        services[service] = {
            "configured": bool(default_command or (record or {}).get("command")),
            "running": service_alive(root, service),
            "pid": (record or {}).get("pid"),
            "log_path": (record or {}).get("log_path", str(logs_dir(root) / f"{service}.log")),
            "command": _display_command(list((record or {}).get("command") or default_command)),
        }
    return {
        "ok": True,
        "mode": NATIVE_MODE,
        "data_root": str(root),
        "bind_host": str(cfg.get("bind_host") or DEFAULT_BIND_HOST),
        "onebot": onebot_connection_hint(cfg),
        "qq": {
            "path": str(cfg.get("ntqq_path") or find_ntqq_path()),
            "login": "official local Windows QQ window; noVNC not used",
        },
        "services": services,
        "health": health_payload(root, cfg),
        "no_vnc_used": True,
    }


def native_logs(root: Path, service: str = "all", lines: int = 80) -> dict[str, str]:
    root = Path(root).resolve()
    result: dict[str, str] = {}
    services = ("astrbot", "snowluma") if service in {"all", "both"} else (service,)
    for name in services:
        record = service_record(root, name)
        path = Path(str((record or {}).get("log_path") or (logs_dir(root) / f"{name}.log")))
        result[name] = _tail(path, max(1, min(2000, int(lines))))
    return result


def open_qq_window(config: dict[str, Any]) -> str:
    qq_path = str(config.get("ntqq_path") or find_ntqq_path())
    if not qq_path or not Path(qq_path).is_file():
        raise NativeBlocked(["official Windows NTQQ not found; set QQ_EXE or --ntqq-path"])
    if os.name == "nt":
        try:
            os.startfile(qq_path)  # type: ignore[attr-defined]
        except OSError as exc:
            raise NativePOCError(f"Could not open NTQQ: {exc}") from exc
    return qq_path
