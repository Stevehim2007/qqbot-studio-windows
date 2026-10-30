#!/usr/bin/env python3
"""Standalone Windows launcher for QQ Bot Studio.

The launcher starts a detached copy of itself in ``--serve-management`` mode.
That child runs the vendored ``qqbot_studio`` HTTP server. Keeping the server
inside the same executable means the PyInstaller one-file build does not need a
system Python installation at runtime.

The parent only performs first-run configuration, Docker checks, PID/log/health
management, optional instance creation, and browser opening. It then exits so
the management server keeps running after the console window closes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

LAUNCHER_VERSION = "0.6.0"
DEFAULT_SERVER_WAIT_SECONDS = 90

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    APPLICATION_DIR = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    APPLICATION_DIR = PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qqbot_studio import __version__ as CORE_VERSION  # noqa: E402
from qqbot_studio.dockerctl import DockerController, DockerError  # noqa: E402
from qqbot_studio.studio import (  # noqa: E402
    DEFAULT_BIND_HOST,
    DEFAULT_BIND_PORT,
    StudioManager,
    detect_public_host,
)
from qqbot_studio.store import default_data_dir  # noqa: E402
from windows.move_data_core import (  # noqa: E402
    DATA_LOCATION_POINTER_FILENAME,
    MOVE_RECORD_FILENAME,
    _read_json,
    _read_data_location_pointer,
    _write_data_location_pointer,
    _write_json_atomic,
    data_location_pointer_path,
    resolve_data_dir,
    validate_move_target,
)

PrintFunc = Callable[[str], None]


# ---------------------------------------------------------------------------
# Console and file helpers
# ---------------------------------------------------------------------------


def _configure_parent_streams() -> None:
    """Avoid UnicodeEncodeError when core/Docker errors contain Chinese text."""

    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is None:
                continue
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _say(message: str) -> None:
    print(message)


def _warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def _write_text_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def _read_int_file(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return value if value > 0 else None


def _write_pid(data_dir: Path, pid: int) -> None:
    _write_text_atomic(data_dir / "server.pid", f"{int(pid)}\n")


def _remove_quietly(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink()
        except OSError:
            pass


def _normalized_path(value: str | Path) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(str(value))))


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                process_query_limited_information, False, int(pid)
            )
            if not handle:
                return False
            try:
                return True
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="QQBotStudioWindows",
        description=(
            "QQ Bot Studio Windows launcher: configure, start/stop the local "
            "management service, inspect logs, and open the browser."
        ),
    )
    parser.add_argument("--data-dir", default=None, help="Data directory (default: %%LOCALAPPDATA%%\\QQBotStudio\\data).")
    parser.add_argument("--ip", default=None, help="Management bind IP (default: 0.0.0.0).")
    parser.add_argument("--port", type=int, default=None, help="Management TCP port (default: 8765).")
    parser.add_argument("--public-host", default=None, help="Browser-facing IP/DNS name; no scheme, path or port.")
    parser.add_argument(
        "--new-instance",
        nargs="?",
        const="",
        default=None,
        metavar="NAME",
        help="Create a new bot instance and open its wizard instead of only opening the console.",
    )
    parser.add_argument(
        "--assistant",
        action="store_true",
        help="Open the standalone AI Assistant B page (/assistant) instead of the console.",
    )
    parser.add_argument(
        "--move-data",
        default=None,
        metavar="NEW_DIR",
        help=(
            "Safely copy the data directory to NEW_DIR, update the data-location pointer, "
            "and stop the management service and deployed instance containers."
        ),
    )
    parser.add_argument("--configure", action="store_true", help="Force the first-run IP/port/public-host prompts.")
    parser.add_argument("--non-interactive", action="store_true", help="Use defaults/arguments without prompts.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the default browser.")
    parser.add_argument("--restart", action="store_true", help="Restart the management service before opening the UI.")
    parser.add_argument("--status", action="store_true", help="Print service/settings status and exit.")
    parser.add_argument("--stop", action="store_true", help="Stop the management service and exit. Containers keep running.")
    parser.add_argument("--logs", nargs="?", const=80, type=int, metavar="LINES", help="Print recent service logs and exit (default 80 lines).")
    parser.add_argument(
        "--version",
        action="version",
        version=f"QQBot Studio Windows launcher {LAUNCHER_VERSION} (core {CORE_VERSION})",
    )
    parser.add_argument("--serve-management", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--apply-data-move", default=None, metavar="REQUEST_FILE", help=argparse.SUPPRESS)
    return parser


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _stop_instance_containers(data_dir: Path, *, print_func: PrintFunc = _say) -> list[str]:
    """Bring down Compose projects whose files live in this data directory."""

    studio = StudioManager(data_dir)
    candidates: list[tuple[dict[str, Any], Path]] = []
    for meta in studio.list_instance_metas():
        instance_dir = data_dir / "instances" / str(meta.get("id") or "")
        if instance_dir.is_dir() and (instance_dir / "compose.yml").is_file():
            candidates.append((meta, instance_dir))
    if not candidates:
        return []

    probe = DockerController(data_dir)
    status = probe.detect(force=True)
    if not status.ready:
        raise RuntimeError(
            "Existing deployed instances have Docker Compose files, but Docker Desktop is not ready. "
            "Start Docker Desktop and retry --move-data before migration."
        )

    stopped: list[str] = []
    for meta, instance_dir in candidates:
        instance_id = str(meta.get("id") or "unknown")
        controller = DockerController(
            instance_dir,
            project_name=str(meta.get("project_name") or f"qqbot-studio-{instance_id}"),
            astrbot_container=str(meta.get("astrbot_container") or f"qqbot-{instance_id}-astrbot"),
            snowluma_container=str(meta.get("snowluma_container") or f"qqbot-{instance_id}-snowluma"),
        )
        print_func(f"Stopping containers for instance {instance_id} (compose down)...")
        result = controller.compose(
            ["down", "--remove-orphans"],
            timeout=300,
            check=False,
            what=f"停止实例 {instance_id} 的容器",
        )
        if not result.ok:
            raise RuntimeError(
                f"Could not stop containers for instance {instance_id}; migration aborted. "
                f"{result.output or 'Docker Compose down failed'}"
            )
        stopped.append(instance_id)
    return stopped


def move_data(
    current_data_dir: Path,
    new_data_dir: Path,
    *,
    non_interactive: bool = False,
    pointer_path: Path | None = None,
    stop_service_func: Callable[..., Any] | None = None,
    kill_tree: bool = True,
    stop_containers_func: Callable[..., list[str]] | None = None,
    input_func: Callable[[str], str] = input,
    print_func: PrintFunc = _say,
) -> int:
    """Copy data to an empty local target and persist the new location pointer.

    The old directory is never deleted. Deployed Compose projects are brought
    down before copying; they are not silently restarted because the caller must
    verify the new data directory and let the deployer recreate bind mounts from
    the new path.
    """

    source = Path(current_data_dir).expanduser().resolve()
    target = Path(new_data_dir).expanduser().resolve()
    validate_move_target(source, target)

    if not source.is_dir():
        raise ValueError(f"Current data directory does not exist: {source}")
    if not (source / "studio.json").is_file() and not (source / "instances").is_dir():
        raise ValueError(f"Current directory does not look like a QQ Bot Studio data directory: {source}")

    settings = _read_json(source / "studio.json") or {}
    bind_host = str(settings.get("bind_host") or DEFAULT_BIND_HOST)
    try:
        bind_port = int(settings.get("bind_port") or DEFAULT_BIND_PORT)
    except (TypeError, ValueError):
        bind_port = DEFAULT_BIND_PORT

    print_func("")
    print_func("Data-directory migration safety notice:")
    print_func("  - The old directory will be retained as a backup.")
    print_func("  - The management service and deployed instance containers will be stopped.")
    print_func("  - The target must be empty/absent; no merge is performed.")
    print_func("  - Back up sensitive data before continuing.")
    print_func("  - WSL, OneDrive, UNC/network, removable and unknown drives are rejected.")
    if not non_interactive:
        try:
            answer = input_func("Type MOVE to continue: ").strip()
        except EOFError:
            answer = ""
        if answer.upper() != "MOVE":
            print_func("Migration cancelled; nothing was changed.")
            return 1

    # Stop the management service before touching instance containers/data.
    if stop_service_func is None:
        stop_management_server(
            source,
            bind_host=bind_host,
            port=bind_port,
            print_func=print_func,
            kill_tree=kill_tree,
        )
    else:
        stop_service_func(
            source, bind_host=bind_host, port=bind_port, print_func=print_func
        )

    # Stop Compose projects whose files live under the old data directory.
    if stop_containers_func is None:
        stopped_instances = _stop_instance_containers(source, print_func=print_func)
    else:
        stopped_instances = stop_containers_func(source, print_func=print_func)

    staging: Path | None = None
    published = False
    try:
        staging = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.qqbot-move-", dir=str(target.parent))
        )
        print_func(f"Copying data to staging directory: {staging}")
        shutil.copytree(
            source,
            staging,
            dirs_exist_ok=True,
            copy_function=shutil.copy2,
        )
        moved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        record = {
            "schema_version": 1,
            "from": str(source),
            "to": str(target),
            "moved_at": moved_at,
            "status": "copied",
            "old_directory_retained": True,
            "containers_stopped": list(stopped_instances),
        }
        _write_json_atomic(staging / MOVE_RECORD_FILENAME, record)
        copied_settings = _read_json(staging / "studio.json") or {}
        copied_settings["windows_data_dir"] = str(target)
        copied_settings["windows_data_moved_at"] = moved_at
        _write_json_atomic(staging / "studio.json", copied_settings)

        if target.exists():
            if any(target.iterdir()):
                raise RuntimeError(
                    f"Target became non-empty during migration; refusing to overwrite: {target}"
                )
            target.rmdir()
        os.replace(staging, target)
        staging = None
        published = True
        pointer = _write_data_location_pointer(target, pointer_path)
    except Exception as exc:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if published:
            shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(
            "Data migration failed. The old data directory was retained unchanged. "
            f"Target: {target}. Original error: {exc}"
        ) from exc

    print_func("")
    print_func("Data migration completed.")
    print_func(f"  Old data (retained as backup): {source}")
    print_func(f"  New data: {target}")
    print_func(f"  Location pointer: {pointer}")
    print_func(f"  Migration record: {target / MOVE_RECORD_FILENAME}")
    if stopped_instances:
        print_func("  Containers brought down: " + ", ".join(stopped_instances))
    else:
        print_func("  Containers brought down: none found")
    print_func("  The management service was not automatically restarted.")
    print_func("  Verify with: QQBotStudioWindows.exe --status")
    print_func("  Start the UI with: QQBotStudioWindows.exe")
    print_func("  If the new location is unusable, keep using the old directory directly:")
    print_func(f"    QQBotStudioWindows.exe --data-dir \"{source}\"")
    print_func("  Do not delete the old directory until the new service and containers are verified.")
    print_func("  Existing Compose projects were brought down; let the deployer recreate them from the new data path.")
    return 0


def _prompt_value(default: str, prompt: str, input_func: Callable[[str], str]) -> str:
    try:
        answer = input_func(f"{prompt} [{default}]: ").strip()
    except EOFError:
        return default
    return answer or default


def _prompt_port(default: int, input_func: Callable[[str], str]) -> int:
    while True:
        raw = _prompt_value(str(default), "Management console port", input_func)
        try:
            value = int(raw)
        except ValueError:
            print("Port must be a number between 1 and 65535.", file=sys.stderr)
            continue
        if 1 <= value <= 65535:
            return value
        print("Port must be between 1 and 65535.", file=sys.stderr)


def _normalize_public_host(value: str) -> str:
    host = str(value or "").strip()
    if not host:
        raise ValueError("Public host cannot be empty.")
    if "://" in host:
        raise ValueError("Public host must not include http:// or https://.")
    if "/" in host or any(ch.isspace() for ch in host):
        raise ValueError("Public host must be a host name or IP address without a path or spaces.")
    if host in {"0.0.0.0", "::"}:
        raise ValueError("Public host must be a reachable address, not an all-interfaces bind address.")
    if host.startswith("[") and "]:" in host:
        raise ValueError("Public host must not include a port; use --port separately.")
    if not host.startswith("[") and host.count(":") == 1:
        raise ValueError("Public host must not include a port; use --port separately.")
    if host.startswith("[") and not host.endswith("]"):
        raise ValueError("Malformed bracketed IPv6 public host.")
    return host


def _default_public_for_bind(bind_host: str) -> str:
    value = bind_host.strip().lower()
    if value in {"", "0.0.0.0", "::"}:
        return detect_public_host()
    if value in {"127.0.0.1", "localhost"}:
        return "127.0.0.1"
    if value in {"::1", "[::1]"}:
        return "[::1]"
    return bind_host.strip()


def configure_studio(
    studio: StudioManager,
    *,
    ip: str | None = None,
    port: int | None = None,
    public_host: str | None = None,
    non_interactive: bool = False,
    force: bool = False,
    input_func: Callable[[str], str] = input,
    print_func: PrintFunc = _say,
) -> dict[str, Any]:
    """Prompt on first run and persist bind_host/bind_port/public_host."""

    existing = studio.load_settings()
    first_run = force or not studio.settings_path.exists() or not bool(existing.get("first_run_complete"))
    bind_host = ip or str(existing.get("bind_host") or DEFAULT_BIND_HOST)
    bind_port = int(port if port is not None else existing.get("bind_port") or DEFAULT_BIND_PORT)
    saved_public = public_host if public_host is not None else str(existing.get("public_host") or "")

    if not 1 <= bind_port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    if not str(bind_host).strip():
        raise ValueError("Management bind IP cannot be empty.")

    if first_run and not non_interactive:
        print_func("")
        print_func("First-run network configuration (saved to studio.json):")
        print_func("0.0.0.0 listens on every interface; use 127.0.0.1 for local-only access.")
        bind_host = _prompt_value(str(bind_host), "Management listen IP", input_func)
        bind_port = _prompt_port(bind_port, input_func)
        if not saved_public:
            saved_public = _default_public_for_bind(bind_host)
        saved_public = _prompt_value(saved_public, "Public IP/DNS name used in browser links", input_func)

    bind_host = str(bind_host).strip()
    if not saved_public:
        saved_public = _default_public_for_bind(bind_host)
    saved_public = _normalize_public_host(saved_public)

    settings = studio.update_network(
        bind_host=bind_host,
        bind_port=int(bind_port),
        public_host=saved_public,
    )
    if first_run:
        print_func(f"Saved first-run settings: {studio.settings_path}")
    return settings


# ---------------------------------------------------------------------------
# Docker Desktop discovery and checks
# ---------------------------------------------------------------------------


def _windows_registry_docker_roots() -> list[Path]:
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []

    roots: list[Path] = []
    access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
    uninstall = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, uninstall, 0, access) as key:
                count = winreg.QueryInfoKey(key)[0]
                for index in range(count):
                    try:
                        sub_name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, sub_name, 0, access) as sub:
                            try:
                                display_name = str(winreg.QueryValueEx(sub, "DisplayName")[0])
                            except OSError:
                                continue
                            if "docker desktop" not in display_name.lower():
                                continue
                            try:
                                location = str(winreg.QueryValueEx(sub, "InstallLocation")[0]).strip()
                            except OSError:
                                location = ""
                            if location:
                                roots.append(Path(location))
                    except OSError:
                        continue
        except OSError:
            continue
    return roots


def _docker_install_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name, suffix in (
        ("ProgramFiles", r"Docker\Docker"),
        ("LOCALAPPDATA", r"Docker\Docker"),
        ("LOCALAPPDATA", r"Programs\Docker\Docker"),
    ):
        base = os.environ.get(env_name, "").strip()
        if base:
            roots.append(Path(base) / suffix)
    roots.extend(_windows_registry_docker_roots())
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = _normalized_path(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def update_docker_path() -> None:
    """Prepend known Docker Desktop CLI directories to PATH."""

    path_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    seen = {_normalized_path(entry) for entry in path_entries}
    additions: list[str] = []
    for root in _docker_install_roots():
        cli_dir = root / "resources" / "bin"
        if cli_dir.is_dir():
            key = _normalized_path(cli_dir)
            if key not in seen:
                seen.add(key)
                additions.append(str(cli_dir))
    if additions:
        os.environ["PATH"] = os.pathsep.join(additions + path_entries)


def find_docker_desktop() -> Path | None:
    if os.name != "nt":
        return None
    for root in _docker_install_roots():
        candidate = root / "Docker Desktop.exe"
        if candidate.is_file():
            return candidate
    return None


def find_docker_cli() -> Path | None:
    update_docker_path()
    found = shutil.which("docker.exe") or shutil.which("docker")
    if found:
        return Path(found)
    for root in _docker_install_roots():
        candidate = root / "resources" / "bin" / "docker.exe"
        if candidate.is_file():
            return candidate
    return None


def _docker_process_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Docker Desktop.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "Docker Desktop.exe" in (result.stdout or "")


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # When a PyInstaller one-file EXE launches another copy of itself, make
    # the child extract a clean runtime instead of inheriting the parent's
    # temporary _MEI directory. This avoids the bootloader warning
    # "Failed to remove temporary directory" when the parent exits.
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def _run_docker(cli: Path, args: Sequence[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(cli), *[str(item) for item in args]],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=_subprocess_env(),
    )


def ensure_docker_ready(
    data_dir: Path,
    *,
    timeout_seconds: int = 180,
    print_func: PrintFunc = _say,
) -> DockerController:
    """Start Docker Desktop if needed, then verify Linux engine + Compose v2."""

    update_docker_path()
    controller = DockerController(data_dir)
    desktop = find_docker_desktop()
    cli = find_docker_cli()
    if cli is None and desktop is None:
        raise RuntimeError(
            "Docker Desktop and the docker CLI were not found. Install Docker Desktop "
            "for Windows with the WSL2 backend and start it once."
        )

    status = controller.detect(force=True)
    if not status.ready and desktop is not None and not _docker_process_running():
        print_func(f"Starting Docker Desktop: {desktop}")
        try:
            subprocess.Popen(
                [str(desktop)],
                cwd=str(desktop.parent),
                close_fds=True,
                env=_subprocess_env(),
            )
        except OSError as exc:
            raise RuntimeError(f"Could not start Docker Desktop: {exc}") from exc
    elif not status.ready and desktop is not None:
        print_func("Docker Desktop is running but its Linux engine is not ready yet; waiting...")

    if not status.ready:
        print_func(f"Waiting up to {timeout_seconds}s for Docker Desktop's Linux engine...")
        deadline = time.monotonic() + max(10, int(timeout_seconds))
        while time.monotonic() < deadline:
            time.sleep(2)
            update_docker_path()
            status = controller.detect(force=True)
            if status.ready:
                break
        if not status.ready:
            detail = status.detail or "Docker Desktop did not become ready."
            raise RuntimeError(
                "Docker Desktop is unavailable. Start it, finish login/license prompts, "
                "and confirm it uses Linux containers.\n"
                f"Details: {detail}"
            )

    cli = find_docker_cli()
    if cli is None:
        raise RuntimeError("The docker CLI is still unavailable after starting Docker Desktop.")

    compose = _run_docker(cli, ["compose", "version"], timeout=20)
    if compose.returncode != 0:
        detail = "\n".join(part for part in (compose.stdout, compose.stderr) if part).strip()
        raise RuntimeError(f"Docker Compose v2 is unavailable: {detail or 'command failed'}")

    os_type = _run_docker(cli, ["info", "--format", "{{.OSType}}"], timeout=20)
    os_type_value = (os_type.stdout or "").strip().lower()
    if os_type.returncode != 0 or os_type_value != "linux":
        detail = "\n".join(part for part in (os_type.stdout, os_type.stderr) if part).strip()
        raise RuntimeError(
            "QQ Bot Studio requires Docker Desktop Linux containers; "
            f"detected OSType={os_type_value or 'unknown'}.\n{detail}"
        )
    print_func("Docker Desktop, Compose v2 and the Linux engine are ready.")
    return controller


# ---------------------------------------------------------------------------
# Management service lifecycle
# ---------------------------------------------------------------------------


def _probe_host(bind_host: str) -> str:
    value = str(bind_host or "").strip()
    if value in {"", "0.0.0.0"}:
        return "127.0.0.1"
    if value == "::":
        return "::1"
    return value


def _url_host(host: str) -> str:
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def _health_url(bind_host: str, port: int) -> str:
    return f"http://{_url_host(_probe_host(bind_host))}:{int(port)}/healthz"


def health_ok(bind_host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(_health_url(bind_host, port), timeout=timeout) as response:
            if int(getattr(response, "status", 200)) != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return bool(payload.get("ok"))
    except Exception:
        return False


def _port_in_use(bind_host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((_probe_host(bind_host), int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _server_runtime(data_dir: Path) -> dict[str, Any] | None:
    return _read_json(data_dir / "server-runtime.json")


def _runtime_matches(runtime: dict[str, Any] | None, *, data_dir: Path, bind_host: str, port: int) -> bool:
    if not isinstance(runtime, dict):
        return False
    try:
        runtime_port = int(runtime.get("port") or 0)
    except (TypeError, ValueError):
        runtime_port = 0
    return (
        str(runtime.get("host") or "") == str(bind_host)
        and runtime_port == int(port)
        and _normalized_path(str(runtime.get("data_dir") or "")) == _normalized_path(data_dir)
    )


def _verified_server_pid(data_dir: Path, *, bind_host: str, port: int) -> int | None:
    runtime = _server_runtime(data_dir)
    pid: int | None = None
    if isinstance(runtime, dict):
        try:
            runtime_pid = int(runtime.get("pid") or 0)
        except (TypeError, ValueError):
            runtime_pid = 0
        if runtime_pid > 0 and _runtime_matches(
            runtime, data_dir=data_dir, bind_host=bind_host, port=port
        ):
            pid = runtime_pid
    if pid is None:
        candidate = _read_int_file(data_dir / "server.pid")
        if candidate and health_ok(bind_host, port):
            pid = candidate
    if pid is not None and _pid_alive(pid):
        return pid
    return None


def _kill_pid_tree(pid: int, *, tree: bool = True) -> None:
    if os.name == "nt":
        command = ["taskkill", "/PID", str(int(pid)), "/F"]
        if tree:
            command.insert(3, "/T")
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(int(pid), 15)
    except OSError:
        return


def stop_management_server(
    data_dir: Path,
    *,
    bind_host: str,
    port: int,
    print_func: PrintFunc = _say,
    kill_tree: bool = True,
) -> bool:
    pid = _verified_server_pid(data_dir, bind_host=bind_host, port=port)
    pid_file = data_dir / "server.pid"
    runtime_file = data_dir / "server-runtime.json"
    if pid is None:
        _remove_quietly(pid_file, runtime_file)
        print_func("Management service is not running.")
        return False

    print_func(f"Stopping management service (PID {pid}); Docker containers keep running.")
    _kill_pid_tree(pid, tree=kill_tree)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            break
        time.sleep(0.25)
    _remove_quietly(pid_file, runtime_file)
    if _pid_alive(pid):
        raise RuntimeError(f"PID {pid} is still alive after stop request.")
    print_func("Management service stopped.")
    return True


def _rotate_log_if_large(path: Path, limit: int = 5 * 1024 * 1024) -> None:
    try:
        if path.is_file() and path.stat().st_size > limit:
            target = path.with_name(path.name + ".1")
            if target.exists():
                target.unlink()
            path.replace(target)
    except OSError:
        pass


def _server_command(data_dir: Path, bind_host: str, port: int) -> list[str]:
    if getattr(sys, "frozen", False):
        base = [sys.executable]
    else:
        base = [sys.executable, str(Path(__file__).resolve())]
    return [
        *base,
        "--serve-management",
        "--data-dir",
        str(data_dir),
        "--ip",
        str(bind_host),
        "--port",
        str(int(port)),
        "--no-open",
    ]


def _server_creationflags() -> int:
    if os.name != "nt":
        return 0
    flags = 0
    for name in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP"):
        flags |= int(getattr(subprocess, name, 0))
    return flags


def _tail_text(path: Path, lines: int) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 64 * 1024))
            data = handle.read()
        text = data.decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-max(1, lines):])
    except OSError:
        return ""


def _log_tail(data_dir: Path, lines: int = 40) -> str:
    chunks: list[str] = []
    for name in ("studio-server.log", "studio-server.err.log"):
        text = _tail_text(data_dir / name, lines)
        if text:
            chunks.append(f"--- {name} ---\n{text}")
    return "\n".join(chunks) or "(no server log content)"


def start_management_server(
    data_dir: Path,
    *,
    bind_host: str,
    port: int,
    wait_seconds: int = DEFAULT_SERVER_WAIT_SECONDS,
    print_func: PrintFunc = _say,
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = data_dir / "studio-server.log"
    stderr_log = data_dir / "studio-server.err.log"
    _rotate_log_if_large(stdout_log)
    _rotate_log_if_large(stderr_log)

    command = _server_command(data_dir, bind_host, port)
    env = _subprocess_env()
    print_func("Starting the hidden management service...")
    with stdout_log.open("ab", buffering=0) as log_handle:
        kwargs: dict[str, Any] = {
            "cwd": str(APPLICATION_DIR),
            "stdin": subprocess.DEVNULL,
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "close_fds": True,
            "env": env,
        }
        if os.name == "nt":
            kwargs["creationflags"] = _server_creationflags()
        else:
            kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(command, **kwargs)
        except OSError as exc:
            raise RuntimeError(f"Could not start the management service: {exc}") from exc

    _write_pid(data_dir, process.pid)
    deadline = time.monotonic() + max(10, int(wait_seconds))
    while time.monotonic() < deadline:
        if health_ok(bind_host, port):
            runtime = _server_runtime(data_dir)
            if isinstance(runtime, dict):
                try:
                    runtime_pid = int(runtime.get("pid") or 0)
                except (TypeError, ValueError):
                    runtime_pid = 0
                if runtime_pid > 0:
                    _write_pid(data_dir, runtime_pid)
            pid = _read_int_file(data_dir / "server.pid")
            print_func(f"Management service healthy (PID {pid or process.pid}).")
            print_func(f"Logs: {stdout_log}")
            print_func(f"      {stderr_log}")
            return
        if process.poll() is not None:
            break
        time.sleep(0.5)

    tail = _log_tail(data_dir)
    if process.poll() is None:
        _kill_pid_tree(process.pid)
    _remove_quietly(data_dir / "server.pid", data_dir / "server-runtime.json")
    raise RuntimeError(
        f"The management service did not become healthy within {wait_seconds}s.\n{tail}"
    )


def ensure_management_server(
    data_dir: Path,
    *,
    bind_host: str,
    port: int,
    force_restart: bool = False,
    print_func: PrintFunc = _say,
) -> None:
    if force_restart:
        stop_management_server(data_dir, bind_host=bind_host, port=port, print_func=print_func)

    healthy = health_ok(bind_host, port)
    if healthy:
        runtime = _server_runtime(data_dir)
        if _runtime_matches(runtime, data_dir=data_dir, bind_host=bind_host, port=port):
            pid: int | None = None
            if isinstance(runtime, dict):
                try:
                    pid = int(runtime.get("pid") or 0)
                except (TypeError, ValueError):
                    pid = None
            if pid and pid > 0:
                _write_pid(data_dir, pid)
            print_func("Management service is already healthy with matching settings.")
            return
        verified_pid = _verified_server_pid(data_dir, bind_host=bind_host, port=port)
        if verified_pid is None:
            raise RuntimeError(
                f"Port {port} answers /healthz, but it is not verifiably managed by {data_dir}. "
                "Stop the other process or choose another port."
            )
        stop_management_server(data_dir, bind_host=bind_host, port=port, print_func=print_func)

    if _verified_server_pid(data_dir, bind_host=bind_host, port=port) is not None:
        stop_management_server(data_dir, bind_host=bind_host, port=port, print_func=print_func)
    else:
        _remove_quietly(data_dir / "server.pid")

    if _port_in_use(bind_host, port):
        raise RuntimeError(
            f"Port {port} is already in use by another process. Stop it or choose another port with --port."
        )

    start_management_server(data_dir, bind_host=bind_host, port=port, print_func=print_func)


# ---------------------------------------------------------------------------
# Status, logs and instances
# ---------------------------------------------------------------------------


def print_status(studio: StudioManager, settings: dict[str, Any]) -> int:
    bind_host = str(settings.get("bind_host") or DEFAULT_BIND_HOST)
    try:
        port = int(settings.get("bind_port") or DEFAULT_BIND_PORT)
    except (TypeError, ValueError):
        port = DEFAULT_BIND_PORT
    data_dir = studio.root
    pid = _read_int_file(data_dir / "server.pid")
    runtime = _server_runtime(data_dir)
    running = health_ok(bind_host, port)
    print(f"Data directory : {data_dir}")
    print(f"Bind address   : {bind_host}:{port}")
    print(f"Public URL     : {studio.public_base_url()}/console")
    print(f"Health URL     : {_health_url(bind_host, port)}")
    print(f"Healthy        : {'yes' if running else 'no'}")
    print(f"PID file       : {data_dir / 'server.pid'} ({pid or 'missing'})")
    print(f"Runtime file   : {data_dir / 'server-runtime.json'}")
    if isinstance(runtime, dict):
        print(f"Runtime        : host={runtime.get('host')} port={runtime.get('port')} pid={runtime.get('pid')}")
    print(f"Service log    : {data_dir / 'studio-server.log'}")
    print(f"Error log      : {data_dir / 'studio-server.err.log'}")
    return 0 if running else 1


def print_logs(data_dir: Path, lines: int) -> int:
    requested = max(1, min(2000, int(lines)))
    any_file = False
    for name in ("studio-server.log", "studio-server.err.log"):
        path = data_dir / name
        print(f"--- {path} ---")
        if path.is_file():
            any_file = True
            text = _tail_text(path, requested)
            print(text if text else "(empty)")
        else:
            print("(missing)")
    return 0 if any_file else 1


def create_instance(studio: StudioManager, name: str | None = None, print_func: PrintFunc = _say) -> dict[str, Any]:
    controller = DockerController(studio.root)
    controller.require_ready()
    if studio.list_instance_metas():
        print_func("Checking existing containers...")
        for repair in studio.repair_instances():
            if not repair.get("ok"):
                print_func(
                    "WARNING: repair failed for "
                    f"{repair.get('name') or repair.get('instance_id') or 'instance'}: "
                    f"{repair.get('message') or repair.get('action')}"
                )
    meta = studio.create_instance(name or None)
    print_func(f"Created instance: {meta['name']} ({meta['id']})")
    return meta


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def _run_management_server(args: argparse.Namespace) -> int:
    from qqbot_studio import server as server_module
    from qqbot_studio.server import main as server_main

    try:
        from windows.console_move_ext import install_windows_console_extension

        install_windows_console_extension(server_module)
    except Exception as exc:  # noqa: BLE001 - optional Windows feature isolation
        print(
            f"WARNING: Windows console storage-migration extension disabled: {exc}",
            file=sys.stderr,
        )

    data_dir = resolve_data_dir(args.data_dir)
    host = str(args.ip or DEFAULT_BIND_HOST)
    port = int(args.port if args.port is not None else DEFAULT_BIND_PORT)
    try:
        return int(
            server_main(
                [
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--data-dir",
                    str(data_dir),
                    "--no-browser",
                ]
            )
        )
    except Exception:
        traceback.print_exc()
        return 1


def _validate_action_combination(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.move_data is not None:
        if (
            args.status
            or args.stop
            or args.logs is not None
            or args.new_instance is not None
            or args.assistant
            or args.configure
            or args.restart
        ):
            parser.error("--move-data must be used alone (apart from --data-dir/--non-interactive).")
        return
    terminal = [bool(args.status), bool(args.stop), args.logs is not None]
    if sum(1 for item in terminal if item) > 1:
        parser.error("--status, --stop and --logs are mutually exclusive.")
    if any(terminal) and (args.new_instance is not None or args.assistant or args.configure or args.restart):
        parser.error("--status/--stop/--logs cannot be combined with start/configure/restart actions.")
    if args.assistant and args.new_instance is not None:
        parser.error("--assistant and --new-instance select different browser targets; use only one.")


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    _validate_action_combination(parser, args)
    data_dir = resolve_data_dir(args.data_dir)

    if args.move_data is not None:
        return move_data(
            data_dir,
            Path(args.move_data),
            non_interactive=args.non_interactive,
            print_func=_say,
        )
    if args.logs is not None:
        return print_logs(data_dir, int(args.logs))

    studio = StudioManager(data_dir)
    existing = studio.load_settings()
    bind_host = str(existing.get("bind_host") or DEFAULT_BIND_HOST)
    port = int(existing.get("bind_port") or DEFAULT_BIND_PORT)

    if args.stop:
        stop_management_server(data_dir, bind_host=bind_host, port=port)
        return 0
    if args.status:
        return print_status(studio, existing)

    settings = configure_studio(
        studio,
        ip=args.ip,
        port=args.port,
        public_host=args.public_host,
        non_interactive=args.non_interactive,
        force=args.configure,
        print_func=_say,
    )
    bind_host = str(settings.get("bind_host") or DEFAULT_BIND_HOST)
    port = int(settings.get("bind_port") or DEFAULT_BIND_PORT)

    ensure_docker_ready(data_dir, print_func=_say)
    ensure_management_server(
        data_dir,
        bind_host=bind_host,
        port=port,
        force_restart=args.restart,
        print_func=_say,
    )

    base_url = studio.public_base_url()
    if args.new_instance is not None:
        meta = create_instance(studio, args.new_instance or None, print_func=_say)
        target_url = f"{base_url}/wizard?instance={meta['id']}"
        print("")
        print("IMPORTANT: a new instance must scan the QQ login QR code in noVNC.")
        print("Complete device/SMS/slider verification manually in the official QQ window.")
        print("The tool never asks for or stores the QQ password.")
    elif args.assistant:
        target_url = f"{base_url}/assistant"
        print("")
        print("Opening the standalone AI Assistant B page. Optional installation/configuration is handled there.")
        print("B has no built-in authentication; keep loopback/VPN or restrict 0.0.0.0 exposure with a firewall.")
    else:
        target_url = f"{base_url}/console"

    print("")
    print(f"Management console: {base_url}/console")
    print(f"Open URL          : {target_url}")
    print(f"Data directory    : {data_dir}")
    print("The launcher exits now; the management service keeps running in the background.")
    print("Use --status, --logs, or --stop to manage it.")
    if not args.no_open:
        try:
            webbrowser.open_new_tab(target_url)
        except Exception as exc:
            _warn(f"Could not open the browser ({exc}); open the URL manually.")
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    _configure_parent_streams()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if getattr(args, "apply_data_move", None):
        from windows.console_move_ext import apply_move_request

        return int(
            apply_move_request(
                Path(args.apply_data_move),
                move_data_func=move_data,
                ensure_server_func=ensure_management_server,
                print_func=_say,
            )
        )
    if args.serve_management:
        return _run_management_server(args)
    try:
        return int(run(args, parser))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except (DockerError, RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
