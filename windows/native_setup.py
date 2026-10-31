"""One-click installer helpers for the Windows Native POC.

Only official project release sources are used. Every downloaded archive or
wheel is size/SHA256 checked before use. NTQQ is detected only; QQ scan,
SnowLuma EULA and all device verification remain manual.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

from windows import app_shell, native_runtime

Progress = Callable[[str, int, str], None]
INSTALL_LOG = "native-install.log"
_LOGGER = logging.getLogger("qqbot.windows.native_setup")

UV_VERSION = "0.13.6"
UV_URL = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip"
UV_SHA256 = "a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f"
ASTRBOT_VERSION = "4.29.3"
ASTRBOT_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/d3/ca/"
    "cbaa6d5c6dfcc6b84264f9612bc1fa88af40d44628fc0a60e06c26bcd0cb/"
    "astrbot-4.29.3-py3-none-any.whl"
)
ASTRBOT_WHEEL_SHA256 = "b78d8ab2d6f153c18be7162799b8589c9f5284233d557c93364c22193fe6be8e"
ASTRBOT_WHEEL_SIZE = 7202340
SNOWLUMA_VERSION = "2.2.1"
SNOWLUMA_URL = (
    "https://github.com/SnowLuma/SnowLuma/releases/download/"
    "v2.2.1/SnowLuma-v2.2.1-win-x64-lite.zip"
)
SNOWLUMA_SHA256 = "29e11c07978f2e970ad918a574650573b74f8ee796e6fa39747dbfb5f74c08f6"
SNOWLUMA_SIZE = 6851206
NODE_VERSION = "26.13.0"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-win-x64.zip"
NODE_SHA256 = "dcc60d59a0746999f99064a01c020445d54d84228c691cdbf25b49ac3b59150a"
NODE_SIZE = 41157375


class InstallError(RuntimeError):
    pass


def official_plan() -> list[dict[str, Any]]:
    return [
        {
            "name": "uv",
            "version": UV_VERSION,
            "url": UV_URL,
            "sha256": UV_SHA256,
            "official": "astral-sh/uv GitHub Release",
        },
        {
            "name": "AstrBot",
            "version": ASTRBOT_VERSION,
            "url": ASTRBOT_WHEEL_URL,
            "sha256": ASTRBOT_WHEEL_SHA256,
            "size": ASTRBOT_WHEEL_SIZE,
            "official": "PyPI astrbot 4.29.3 wheel",
        },
        {
            "name": "SnowLuma",
            "version": SNOWLUMA_VERSION,
            "url": SNOWLUMA_URL,
            "sha256": SNOWLUMA_SHA256,
            "size": SNOWLUMA_SIZE,
            "official": "SnowLuma/SnowLuma GitHub Release (win-x64-lite)",
        },
        {
            "name": "Node.js",
            "version": NODE_VERSION,
            "url": NODE_URL,
            "sha256": NODE_SHA256,
            "size": NODE_SIZE,
            "official": "nodejs.org official Windows x64 zip",
        },
    ]


def configure_logger(root: Path) -> logging.Logger:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "logs" / INSTALL_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    _LOGGER.setLevel(logging.INFO)
    if not any(
        getattr(handler, "baseFilename", "") == str(path.resolve())
        for handler in _LOGGER.handlers
    ):
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        _LOGGER.addHandler(handler)
        _LOGGER.propagate = False
    return _LOGGER


def _emit(progress: Progress | None, phase: str, pct: int, message: str) -> None:
    _LOGGER.info("%s %s%% %s", phase, pct, message)
    if progress:
        try:
            progress(phase, max(0, min(100, int(pct))), message)
        except Exception:
            _LOGGER.exception("progress callback failed")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(
    url: str,
    target: Path,
    *,
    expected_sha256: str,
    expected_size: int | None = None,
    progress: Progress | None = None,
    phase: str = "下载",
    start_pct: int = 0,
    end_pct: int = 40,
) -> Path:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise InstallError(f"拒绝非 HTTPS 下载源: {url}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size > 0:
        try:
            if _sha256(target).lower() == expected_sha256.lower() and (
                expected_size is None or target.stat().st_size == int(expected_size)
            ):
                _emit(progress, phase, end_pct, f"复用已校验缓存 {target.name}")
                return target
        except OSError:
            pass
    temp = target.with_name(target.name + ".part")
    if temp.exists():
        temp.unlink(missing_ok=True)
    _emit(progress, phase, start_pct, f"下载 {url}")
    request = urllib.request.Request(
        url, headers={"User-Agent": "QQBotStudioWindowsNativeInstaller/1.0.3"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            read = 0
            started = time.monotonic()
            with temp.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    handle.write(chunk)
                    read += len(chunk)
                    span = max(1, int(end_pct) - int(start_pct))
                    pct = int(start_pct) + (span * read // total if total else 0)
                    if read % (1024 * 1024) < len(chunk):
                        _emit(progress, phase, pct, f"已下载 {read // 1024 // 1024} MiB")
            _LOGGER.info("download complete bytes=%s seconds=%.2f", read, time.monotonic() - started)
        if expected_size is not None and temp.stat().st_size != int(expected_size):
            raise InstallError(
                f"大小校验失败: {target.name} expected={expected_size} actual={temp.stat().st_size}"
            )
        actual = _sha256(temp)
        if actual.lower() != expected_sha256.lower():
            raise InstallError(
                f"SHA256 校验失败: {target.name} expected={expected_sha256} actual={actual}"
            )
        os.replace(temp, target)
        _emit(progress, phase, end_pct, f"校验通过 {target.name}")
        return target
    except Exception:
        _LOGGER.exception("download failed url=%s", url)
        temp.unlink(missing_ok=True)
        raise


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 1800,
    progress: Progress | None = None,
    phase: str = "安装",
    pct: int = 0,
) -> subprocess.CompletedProcess[str]:
    _emit(progress, phase, pct, "执行: " + " ".join(command))
    _LOGGER.info("RUN cwd=%s command=%s", cwd, command)
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    _LOGGER.info("EXIT %s stdout=%s stderr=%s", result.returncode, result.stdout[-4000:], result.stderr[-4000:])
    if result.returncode != 0:
        raise InstallError(
            f"命令失败 ({result.returncode}): {' '.join(command)}\n{result.stderr[-2000:]}"
        )
    return result


def _extract_zip(zip_path: Path, target: Path, progress: Progress | None, phase: str) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _emit(progress, phase, 50, f"解压 {zip_path.name}")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target)
    _emit(progress, phase, 60, f"已解压到 {target}")


def find_uv(root: Path) -> Path | None:
    candidates = [
        shutil.which("uv.exe"),
        shutil.which("uv"),
        str(Path.home() / ".local" / "bin" / "uv.exe"),
        str(root / "tools" / "uv" / "uv.exe"),
    ]
    for value in candidates:
        if value and Path(value).is_file():
            return Path(value)
    return None


def find_node(root: Path) -> Path | None:
    candidates = [
        shutil.which("node.exe"),
        shutil.which("node"),
        str(root / "tools" / "node" / "node.exe"),
    ]
    # The official node zip extracts into a versioned directory.
    candidates.extend(str(path) for path in (root / "tools" / "node").glob("node-v*-win-x64/node.exe"))
    for value in candidates:
        if value and Path(value).is_file():
            return Path(value)
    return None


def detect_environment(root: Path) -> dict[str, Any]:
    cfg = native_runtime.load_config(root)
    ntqq = native_runtime.find_ntqq_path()
    uv = find_uv(root)
    node = find_node(root)
    snowluma_dir = Path(str(cfg.get("snowluma_dir") or (root / "snowluma")))
    astrbot_root = Path(str(cfg.get("astrbot_root") or (root / "astrbot")))
    venv_python = root / "astrbot-venv" / "Scripts" / "python.exe"
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "windows": os.name == "nt" and platform.machine().lower() in {"amd64", "x86_64"},
        "ntqq": ntqq,
        "ntqq_present": bool(ntqq),
        "uv": str(uv) if uv else "",
        "node": str(node) if node else "",
        "astrbot_venv_python": str(venv_python) if venv_python.is_file() else "",
        "astrbot_installed": venv_python.is_file(),
        "snowluma_dir": str(snowluma_dir),
        "snowluma_installed": (snowluma_dir / "index.mjs").is_file(),
        "onebot_url": str(cfg.get("onebot_url") or ""),
        "bind_host": str(cfg.get("bind_host") or "127.0.0.1"),
        "plan": official_plan(),
        "blockers": [] if ntqq else ["NTQQ 未检测到；请先安装官方 Windows 桌面 QQ，安装器不会自动登录"],
    }


def _choose_ports() -> dict[str, int]:
    candidates = {"astrbot_webui_port": 6185, "astrbot_onebot_port": 6199, "snowluma_webui_port": 5099}
    used: set[int] = set()
    result: dict[str, int] = {}
    for key, start in candidates.items():
        port = int(start)
        while port <= 65535 and (port in used or not native_runtime.is_port_free(port, "127.0.0.1")):
            port += 1
        if port > 65535:
            raise InstallError(f"无法为 {key} 找到空闲本地端口")
        result[key] = port
        used.add(port)
    return result


def _write_astrbot_setup_script(root: Path) -> Path:
    path = root / "astrbot_setup_config.py"
    path.write_text(
        '''import json, os, sys
from pathlib import Path
from astrbot.core.config.astrbot_config import AstrBotConfig
native = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
astrbot_root = Path(native["astrbot_root"])
config_path = astrbot_root / "data" / "cmd_config.json"
config_path.parent.mkdir(parents=True, exist_ok=True)
cfg = AstrBotConfig(config_path=str(config_path))
cfg["dashboard"]["host"] = "127.0.0.1"
cfg["dashboard"]["port"] = int(native["astrbot_webui_port"])
cfg["platform"] = [{
  "id": "qqbot-onebot",
  "type": "aiocqhttp",
  "enable": True,
  "ws_reverse_host": "127.0.0.1",
  "ws_reverse_port": int(native["astrbot_onebot_port"]),
  "ws_reverse_token": native["onebot_token"],
}]
cfg.save_config()
print("ASTRBOT_NATIVE_CONFIG_OK")
''',
        encoding="utf-8",
    )
    return path


def install_all(root: Path | None = None, progress: Progress | None = None) -> dict[str, Any]:
    root = native_runtime.native_root(str(root) if root else None)
    root.mkdir(parents=True, exist_ok=True)
    configure_logger(root)
    _emit(progress, "检测", 0, f"安装数据目录 {root}")
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise InstallError("Native 一键安装仅支持 Windows 10/11 x64")
    ntqq = native_runtime.find_ntqq_path()
    if ntqq:
        _emit(progress, "检测", 3, f"NTQQ 已找到: {ntqq}")
    else:
        _emit(progress, "检测", 3, "NTQQ 未找到；继续安装 AstrBot/SnowLuma/Node，QQ 登录前需先安装 NTQQ")

    tools = root / "tools"
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    uv = find_uv(root)
    if not uv:
        _emit(progress, "下载", 5, "下载官方 uv 独立安装器")
        uv_zip = _download(
            UV_URL,
            cache / f"uv-{UV_VERSION}-win-x64.zip",
            expected_sha256=UV_SHA256,
            progress=progress,
            phase="下载 uv",
            start_pct=5,
            end_pct=16,
        )
        _extract_zip(uv_zip, tools / "uv", progress, "解压 uv")
        uv_candidates = list((tools / "uv").rglob("uv.exe"))
        if not uv_candidates:
            raise InstallError("uv 解压后未找到 uv.exe")
        uv = uv_candidates[0]
    else:
        _emit(progress, "下载", 16, f"复用已有 uv: {uv}")
    uv = Path(uv).resolve()

    python_install = root / "python"
    env = os.environ.copy()
    env.update(
        {
            "UV_CACHE_DIR": str(cache / "uv"),
            "UV_PYTHON_INSTALL_DIR": str(python_install),
            "UV_NO_PROGRESS": "1",
            "PYTHONUTF8": "1",
        }
    )
    _emit(progress, "安装 Python", 18, "使用 uv 安装 Python 3.12")
    _run([str(uv), "python", "install", "3.12"], cwd=root, env=env, progress=progress, phase="安装 Python", pct=20)
    venv = root / "astrbot-venv"
    if not (venv / "Scripts" / "python.exe").is_file():
        _emit(progress, "安装 AstrBot", 24, "创建 AstrBot 虚拟环境")
        _run([str(uv), "venv", str(venv), "--python", "3.12"], cwd=root, env=env, progress=progress, phase="安装 AstrBot", pct=26)
    wheel = _download(
        ASTRBOT_WHEEL_URL,
        cache / "astrbot-4.29.3-py3-none-any.whl",
        expected_sha256=ASTRBOT_WHEEL_SHA256,
        expected_size=ASTRBOT_WHEEL_SIZE,
        progress=progress,
        phase="下载 AstrBot",
        start_pct=28,
        end_pct=38,
    )
    venv_python = venv / "Scripts" / "python.exe"
    _emit(progress, "安装 AstrBot", 40, "安装 AstrBot wheel 及依赖")
    _run([str(uv), "pip", "install", "--python", str(venv_python), str(wheel)], cwd=root, env=env, timeout=1800, progress=progress, phase="安装 AstrBot", pct=42)
    astrbot_exe = venv / "Scripts" / "astrbot.exe"
    if not astrbot_exe.is_file():
        raise InstallError("AstrBot 安装后未找到 astrbot.exe")
    astrbot_root = root / "astrbot"
    astrbot_root.mkdir(parents=True, exist_ok=True)
    _run([str(astrbot_exe), "init", "-y"], cwd=astrbot_root, env={**env, "ASTRBOT_ROOT": str(astrbot_root)}, progress=progress, phase="初始化 AstrBot", pct=50)

    snowluma_dir = root / "snowluma"
    snow_zip = _download(
        SNOWLUMA_URL,
        cache / f"SnowLuma-{SNOWLUMA_VERSION}-win-x64-lite.zip",
        expected_sha256=SNOWLUMA_SHA256,
        expected_size=SNOWLUMA_SIZE,
        progress=progress,
        phase="下载 SnowLuma",
        start_pct=52,
        end_pct=66,
    )
    _extract_zip(snow_zip, snowluma_dir, progress, "解压 SnowLuma")

    node_dir = root / "tools" / "node"
    node_zip = _download(
        NODE_URL,
        cache / f"node-v{NODE_VERSION}-win-x64.zip",
        expected_sha256=NODE_SHA256,
        expected_size=NODE_SIZE,
        progress=progress,
        phase="下载 Node.js",
        start_pct=68,
        end_pct=82,
    )
    _extract_zip(node_zip, node_dir, progress, "解压 Node.js")
    node_candidates = list(node_dir.glob("node-v*-win-x64/node.exe"))
    if not node_candidates:
        raise InstallError("Node.js 解压后未找到 node.exe")
    node_exe = node_candidates[0].resolve()
    snow_index = snowluma_dir / "index.mjs"
    if not snow_index.is_file():
        raise InstallError("SnowLuma 解压后未找到 index.mjs")

    ports = _choose_ports()
    cfg = native_runtime.load_config(root)
    cfg.update(
        {
            "astrbot_command": [str(astrbot_exe), "run", "--port", str(ports["astrbot_webui_port"])],
            "astrbot_root": str(astrbot_root),
            "snowluma_dir": str(snowluma_dir),
            "snowluma_command": [str(node_exe), str(snow_index)],
            "ntqq_path": ntqq or "",
            **ports,
            "bind_host": "127.0.0.1",
            "onebot_url": f"ws://127.0.0.1:{ports['astrbot_onebot_port']}/ws",
        }
    )
    native_runtime.save_config(root, cfg)
    setup_script = _write_astrbot_setup_script(root)
    _emit(progress, "配置 AstrBot", 86, "写入 AstrBot dashboard/OneBot 配置")
    _run(
        [str(venv_python), str(setup_script), str(native_runtime.config_path(root))],
        cwd=astrbot_root,
        env={**os.environ.copy(), "ASTRBOT_ROOT": str(astrbot_root), "PYTHONUTF8": "1"},
        progress=progress,
        phase="配置 AstrBot",
        pct=88,
    )
    _emit(progress, "配置 OneBot", 92, "写入 SnowLuma OneBot 配置")
    native_runtime.write_snowluma_onebot_config(root, cfg)
    _emit(progress, "完成", 100, "官方组件安装/校验/配置完成；QQ 登录与 SnowLuma EULA 仍需人工")
    return {
        "ok": True,
        "root": str(root),
        "ntqq": ntqq,
        "astrbot": {"version": ASTRBOT_VERSION, "venv": str(venv), "root": str(astrbot_root)},
        "snowluma": {"version": SNOWLUMA_VERSION, "dir": str(snowluma_dir)},
        "node": {"version": NODE_VERSION, "exe": str(node_exe)},
        "ports": ports,
        "manual_steps": [
            "打开官方 NTQQ 窗口，由用户本人完成扫码/设备/短信/滑块验证",
            "在 SnowLuma WebUI 中接受 EULA/PRIVACY 并完成官方 QQ hook 登录",
            "不要把 QQ 密码或 API Key 写入日志",
        ],
    }
