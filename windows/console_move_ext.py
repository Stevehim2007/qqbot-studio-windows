"""Token-protected console API for Windows data-directory migration.

The management server cannot copy its own live data directory in-process. The
HTTP request therefore validates the target and schedules a detached copy of
the same EXE (``--apply-data-move``). That helper stops the server/containers,
performs the existing safe migration, updates the pointer, and starts a fresh
management server from the new directory. The browser polls the status API
and reloads when the restarted service is reachable.

This module is Windows-owned. It is not part of the Linux upstream allowlist.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from qqbot_studio.store import default_data_dir
from qqbot_studio.studio import StudioManager

from windows.move_data_core import (
    MOVE_REQUEST_FILENAME,
    MOVE_STATUS_FILENAME,
    _read_json,
    _write_json_atomic,
    data_location_pointer_path,
    validate_move_target,
)

WORKER_LOG_FILENAME = "windows-console-move-worker.log"
_HERE = Path(__file__).resolve().parent
_RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", _HERE))


def _resource_path(name: str) -> Path:
    candidates = (
        _RESOURCE_ROOT / "windows" / name,
        _HERE / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Windows console resource is missing: {name}")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_move_status(data_dir: Path, **fields: Any) -> dict[str, Any]:
    path = Path(data_dir).resolve() / MOVE_STATUS_FILENAME
    payload = {
        "schema_version": 1,
        "updated_at": _utc_stamp(),
        **fields,
    }
    _write_json_atomic(path, payload)
    return payload


def read_move_status(data_dir: Path) -> dict[str, Any]:
    root = Path(data_dir).resolve()
    status = _read_json(root / MOVE_STATUS_FILENAME)
    pointer = data_location_pointer_path()
    pointer_payload = _read_json(pointer) if pointer.is_file() else None
    if status is None:
        status = {
            "ok": True,
            "status": "idle",
            "message": "尚未从控制台发起存储文件夹迁移。",
        }
    status = dict(status)
    status.setdefault("ok", status.get("status") not in {"failed", "restart_failed"})
    status["current_data_dir"] = str(root)
    status["pointer_path"] = str(pointer)
    status["pointer_data_dir"] = (
        str(pointer_payload.get("data_dir") or "") if isinstance(pointer_payload, dict) else ""
    )
    status["request_path"] = str(root / MOVE_REQUEST_FILENAME)
    status["status_path"] = str(root / MOVE_STATUS_FILENAME)
    status["worker_log_path"] = str(root / WORKER_LOG_FILENAME)
    return status


def validate_console_target(data_dir: Path, target_value: Any) -> Path:
    if not isinstance(target_value, str):
        raise ValueError("请输入新的本机目录绝对路径。")
    value = target_value.strip()
    if not value:
        raise ValueError("新目录不能为空。")
    if len(value) > 1024 or any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError("目录路径包含不支持的字符或长度过长。")
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise ValueError("新目录必须是绝对路径，例如 D:\\QQBotStudioData。")
    return validate_move_target(Path(data_dir).resolve(), raw.resolve())


def _helper_command(request_path: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        base = [sys.executable]
    else:
        base = [sys.executable, str(_HERE / "launcher.py")]
    return [*base, "--apply-data-move", str(request_path)]


def _spawn_worker(request_path: Path, data_dir: Path) -> int:
    log_path = Path(data_dir) / WORKER_LOG_FILENAME
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = 0
    if os.name == "nt":
        for name in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
            creationflags |= int(getattr(subprocess, name, 0))
    with log_path.open("ab", buffering=0) as log_handle:
        process = subprocess.Popen(
            _helper_command(request_path),
            cwd=str(_HERE.parent),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=creationflags,
        )
    return int(process.pid)


def schedule_move(
    data_dir: Path,
    payload: dict[str, Any],
    *,
    spawn_func: Callable[[Path, Path], int] | None = None,
) -> dict[str, Any]:
    """Validate and enqueue a migration from a token-protected console request."""

    root = Path(data_dir).resolve()
    if payload.get("confirm") is not True:
        raise ValueError("必须勾选“我已备份并确认停止服务/容器”。")
    target = validate_console_target(root, payload.get("target"))

    request_path = root / MOVE_REQUEST_FILENAME
    status_path = root / MOVE_STATUS_FILENAME
    previous_status = _read_json(status_path) or {}
    previous_state = str(previous_status.get("status") or "")
    if request_path.exists() or previous_state in {"scheduled", "running"}:
        raise RuntimeError("已有存储迁移任务正在进行或等待启动；请等待完成后再试。")
    if previous_state in {"failed", "restart_failed", "completed"}:
        try:
            request_path.unlink()
        except OSError:
            pass

    try:
        studio = StudioManager(root)
        if studio.has_active_deployments():
            raise ValueError("有部署任务正在运行；请等待部署完成后再迁移数据目录。")
        settings = _read_json(root / "studio.json") or {}
        bind_host = str(settings.get("bind_host") or "0.0.0.0")
        bind_port = int(settings.get("bind_port") or 8765)
    except (TypeError, ValueError):
        raise
    except Exception as exc:  # noqa: BLE001 - return an actionable API error
        raise RuntimeError(f"无法读取当前实例状态：{exc}") from exc

    request = {
        "schema_version": 1,
        "source": str(root),
        "target": str(target),
        "requested_at": _utc_stamp(),
        "bind_host": bind_host,
        "bind_port": bind_port,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(request_path, flags, 0o600)
    except FileExistsError:
        raise RuntimeError("已有存储迁移任务正在进行或等待启动；请等待完成后再试。")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(request, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except Exception:
        try:
            request_path.unlink()
        except OSError:
            pass
        raise

    write_move_status(
        root,
        ok=True,
        status="scheduled",
        source=str(root),
        target=str(target),
        message="迁移任务已排队；管理服务和容器将短暂停止。",
    )
    try:
        pid = (spawn_func or _spawn_worker)(request_path, root)
    except Exception as exc:  # noqa: BLE001
        try:
            request_path.unlink()
        except OSError:
            pass
        write_move_status(
            root,
            ok=False,
            status="failed",
            source=str(root),
            target=str(target),
            message="无法启动迁移 helper；旧数据目录未改动。",
            error=str(exc),
        )
        raise RuntimeError(f"无法启动迁移 helper：{exc}") from exc

    write_move_status(
        root,
        ok=True,
        status="scheduled",
        source=str(root),
        target=str(target),
        pid=pid,
        message="迁移 helper 已启动；页面会在服务重启后自动刷新。",
    )
    return {
        "ok": True,
        "status": "scheduled",
        "source": str(root),
        "target": str(target),
        "message": "迁移任务已启动。管理服务会短暂停止，完成后自动从新目录重启。",
        "poll_url": "/api/system/move-data/status",
        "safety_note": "旧目录会保留；若迁移失败，helper 会尝试恢复旧目录服务。",
    }


def apply_move_request(
    request_path: Path,
    *,
    move_data_func: Callable[..., int],
    ensure_server_func: Callable[..., Any],
    print_func: Callable[[str], None] = print,
) -> int:
    """Run in the detached helper: migrate, record status, restart service."""

    request = _read_json(request_path)
    if not isinstance(request, dict):
        print_func(f"ERROR: invalid move request: {request_path}")
        return 1
    try:
        source = Path(str(request["source"])).expanduser().resolve()
        target = Path(str(request["target"])).expanduser().resolve()
        bind_host = str(request.get("bind_host") or "0.0.0.0")
        bind_port = int(request.get("bind_port") or 8765)
    except (KeyError, TypeError, ValueError) as exc:
        print_func(f"ERROR: invalid move request fields: {exc}")
        return 1

    # Give the HTTP response time to reach the browser before killing its
    # server process. The helper itself is detached from that server.
    time.sleep(1.2)
    write_move_status(
        source,
        ok=True,
        status="running",
        source=str(source),
        target=str(target),
        message="正在停止管理服务/容器并复制数据；旧目录会保留。",
    )
    try:
        result = int(
            move_data_func(
                source,
                target,
                non_interactive=True,
                kill_tree=False,
                print_func=print_func,
            )
        )
        if result != 0:
            raise RuntimeError(f"迁移命令返回非零退出码：{result}")
    except Exception as exc:  # noqa: BLE001 - preserve old data and report
        write_move_status(
            source,
            ok=False,
            status="failed",
            source=str(source),
            target=str(target),
            message="迁移失败；旧数据目录未删除。正在尝试恢复旧目录服务。",
            error=str(exc),
        )
        try:
            ensure_server_func(
                source,
                bind_host=bind_host,
                port=bind_port,
                force_restart=False,
                print_func=print_func,
            )
        except Exception as restart_exc:  # noqa: BLE001
            print_func(f"ERROR: could not restore old management service: {restart_exc}")
        try:
            request_path.unlink()
        except OSError:
            pass
        return 1

    # The request was copied with the data. Remove the copied request from the
    # new data directory so the new console can schedule another migration.
    try:
        (target / MOVE_REQUEST_FILENAME).unlink()
    except OSError:
        pass

    target_settings = _read_json(target / "studio.json") or {}
    target_host = str(target_settings.get("bind_host") or bind_host)
    try:
        target_port = int(target_settings.get("bind_port") or bind_port)
    except (TypeError, ValueError):
        target_port = bind_port

    write_move_status(
        target,
        ok=True,
        status="completed",
        source=str(source),
        target=str(target),
        message="数据迁移完成；管理服务正在从新目录重启。",
        pointer_path=str(data_location_pointer_path()),
        old_directory_retained=True,
    )
    try:
        ensure_server_func(
            target,
            bind_host=target_host,
            port=target_port,
            force_restart=False,
            print_func=print_func,
        )
    except Exception as exc:  # noqa: BLE001
        write_move_status(
            target,
            ok=False,
            status="restart_failed",
            source=str(source),
            target=str(target),
            message="数据已复制，但管理服务没有自动重启。请手动启动 EXE 并检查日志。",
            error=str(exc),
            old_directory_retained=True,
        )
        try:
            request_path.unlink()
        except OSError:
            pass
        return 1

    write_move_status(
        target,
        ok=True,
        status="completed",
        source=str(source),
        target=str(target),
        message="迁移完成，服务已从新目录启动。刷新页面即可继续。",
        pointer_path=str(data_location_pointer_path()),
        old_directory_retained=True,
    )
    try:
        request_path.unlink()
    except OSError:
        pass
    return 0


def install_windows_console_extension(server_module: Any) -> None:
    """Patch the vendored server with Windows-only API and static assets."""

    if getattr(server_module.QQBotRequestHandler, "_windows_console_migration_patch", False):
        return

    try:
        console_js = _resource_path("console_move.js").read_bytes()
        console_css = _resource_path("console_move.css").read_bytes()
    except OSError as exc:
        print(f"Windows console migration assets missing; feature disabled: {exc}", file=sys.stderr)
        return

    base_handler = server_module.QQBotRequestHandler
    base_app_context = server_module.AppContext
    if not getattr(base_app_context, "_windows_console_migration_patch", False):
        original_init = base_app_context.__init__

        def patched_init(self, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            if "/windows-console-move.js" not in self.console_html:
                injection = (
                    '<link rel="stylesheet" href="/windows-console-move.css">\n'
                    '<script src="/windows-console-move.js" defer></script>\n'
                )
                if "</body>" in self.console_html:
                    self.console_html = self.console_html.replace("</body>", injection + "</body>", 1)
                else:
                    self.console_html += injection

        base_app_context.__init__ = patched_init
        setattr(base_app_context, "_windows_console_migration_patch", True)

    class WindowsConsoleRequestHandler(base_handler):
        _windows_console_migration_patch = True

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/windows-console-move.js":
                self._serve_static(console_js, "text/javascript; charset=utf-8")
                return
            if path == "/windows-console-move.css":
                self._serve_static(console_css, "text/css; charset=utf-8")
                return
            if path == "/api/system/move-data/status":
                if not self._validate_host_header():
                    self._error(HTTPStatus.BAD_REQUEST, "Invalid Host header")
                    return
                if not self._check_token():
                    self._error(HTTPStatus.FORBIDDEN, "本地访问令牌无效或已过期。")
                    return
                self._json(
                    HTTPStatus.OK,
                    read_move_status(self.server.context.studio.root),
                )
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            if urlsplit(self.path).path != "/api/system/move-data":
                super().do_POST()
                return
            if not self._validate_host_header():
                self._error(HTTPStatus.BAD_REQUEST, "Invalid Host header")
                return
            if not self._check_token():
                self._error(HTTPStatus.FORBIDDEN, "本地访问令牌无效或已过期。")
                return
            payload = self._read_json_body()
            if payload is None:
                return
            try:
                result = schedule_move(self.server.context.studio.root, payload)
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except RuntimeError as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"无法启动迁移：{exc}")
                return
            self._json(HTTPStatus.OK, result)

    server_module.QQBotRequestHandler = WindowsConsoleRequestHandler
