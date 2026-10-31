"""Shared desktop app shell for Docker and Native Windows editions.

The shell uses pywebview/WebView2 to host the existing local HTML UI in a
persistent desktop window. It never opens an external browser. Startup logs are
written to a file and a diagnostics panel is injected into the hosted page.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable, Sequence


APP_LOG_NAME = "app-shell.log"
LOGGER_NAME = "qqbot.windows.app_shell"


def logs_root() -> Path:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "QQBotStudio" / "logs"
    return Path.home() / ".qqbot-studio" / "logs"


def app_log_path() -> Path:
    return logs_root() / APP_LOG_NAME


def configure_logger(log_path: str | Path | None = None) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    path = Path(log_path) if log_path else app_log_path()
    if not any(
        isinstance(handler, RotatingFileHandler)
        and Path(getattr(handler, "baseFilename", "")) == path.resolve()
        for handler in logger.handlers
    ):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            logger.addHandler(handler)
        except OSError:
            if not any(isinstance(item, logging.NullHandler) for item in logger.handlers):
                logger.addHandler(logging.NullHandler())
        logger.propagate = False
    return logger


def _tail(path: Path, lines: int = 200, max_bytes: int = 512 * 1024) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            data = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(data.splitlines()[-max(1, int(lines)) :])


def read_diagnostics(
    log_paths: Sequence[str | Path],
    *,
    lines: int = 200,
    limit: int = 32000,
) -> str:
    sections: list[str] = []
    for raw_path in log_paths:
        path = Path(raw_path)
        sections.append(f"===== {path} =====")
        tail = _tail(path, lines=max(20, lines))
        sections.append(tail if tail else "(empty or not created yet)")
    text = "\n".join(sections)
    return text[-max(1000, int(limit)) :]


def _windows_clipboard(text: str) -> bool:
    if os.name != "nt":
        return False
    try:
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        encoded = (text + "\x00").encode("utf-16-le")
        if not user32.OpenClipboard(None):
            return False
        try:
            user32.EmptyClipboard()
            handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
            if not handle:
                return False
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return False
            try:
                ctypes.memmove(pointer, encoded, len(encoded))
            finally:
                kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                kernel32.GlobalFree(handle)
                return False
            return True
        finally:
            user32.CloseClipboard()
    except Exception:
        return False


class AppDiagnosticsAPI:
    """pywebview JS API exposed to the diagnostics panel."""

    def __init__(
        self,
        *,
        data_dir: str | Path,
        log_paths: Iterable[str | Path],
        title: str = "QQ Bot Studio",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.log_paths = [Path(path) for path in log_paths]
        self.title = title
        self.logger = configure_logger()

    def get_logs(self) -> str:
        self.logger.info("diagnostics panel requested logs")
        return read_diagnostics(self.log_paths)

    def copy_logs(self) -> bool:
        text = read_diagnostics(self.log_paths)
        ok = _windows_clipboard(text)
        self.logger.info("diagnostics copy logs result=%s", ok)
        return ok

    def open_log_folder(self) -> bool:
        try:
            folder = self.log_paths[0].parent if self.log_paths else logs_root()
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]
            self.logger.info("opened log folder %s", folder)
            return True
        except Exception:
            self.logger.exception("could not open log folder")
            return False

    def get_app_info(self) -> dict:
        return {
            "title": self.title,
            "data_dir": str(self.data_dir),
            "log_paths": [str(path) for path in self.log_paths],
            "pid": os.getpid(),
            "python": sys.version,
            "frozen": bool(getattr(sys, "frozen", False)),
        }


_DIAGNOSTICS_JS = r"""
(function () {
  if (document.getElementById('qb-app-diagnostics-button')) return;
  const style = document.createElement('style');
  style.textContent = `
    #qb-app-diagnostics-button{position:fixed;right:18px;bottom:18px;z-index:2147483646;
      border:1px solid #2d6a8f;border-radius:999px;background:#0d2b45;color:#bfe9ff;
      padding:9px 13px;font:12px/1.2 'Segoe UI',sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.35);
      cursor:pointer;}
    #qb-app-diagnostics-overlay{position:fixed;inset:0;z-index:2147483647;background:rgba(2,12,24,.72);
      display:flex;align-items:center;justify-content:center;padding:24px;}
    #qb-app-diagnostics-panel{width:min(980px,96vw);height:min(720px,90vh);background:#071d31;
      color:#e7f4ff;border:1px solid #285777;border-radius:16px;display:flex;flex-direction:column;
      box-shadow:0 24px 80px rgba(0,0,0,.55);font:13px/1.45 'Cascadia Mono','Consolas',monospace;}
    #qb-app-diagnostics-panel header{display:flex;gap:10px;align-items:center;padding:14px 16px;
      border-bottom:1px solid #234963;font:600 14px 'Segoe UI',sans-serif;}
    #qb-app-diagnostics-panel header strong{flex:1;color:#82f2d0;}
    #qb-app-diagnostics-panel button{border:1px solid #326580;border-radius:8px;background:#103a57;
      color:#dff5ff;padding:6px 10px;cursor:pointer;}
    #qb-app-diagnostics-log{white-space:pre-wrap;overflow:auto;flex:1;padding:16px;margin:0;color:#cfe8f7;}
    #qb-app-diagnostics-note{padding:0 16px 12px;color:#8fb3c8;font:12px 'Segoe UI',sans-serif;}
  `;
  document.head.appendChild(style);
  const button = document.createElement('button');
  button.id = 'qb-app-diagnostics-button';
  button.type = 'button';
  button.textContent = '诊断日志';
  button.title = '查看启动/服务日志，可复制或打开日志目录';
  button.addEventListener('click', async () => {
    if (document.getElementById('qb-app-diagnostics-overlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'qb-app-diagnostics-overlay';
    const panel = document.createElement('section');
    panel.id = 'qb-app-diagnostics-panel';
    const header = document.createElement('header');
    const title = document.createElement('strong');
    title.textContent = 'QQ Bot Studio · 诊断日志';
    const copy = document.createElement('button'); copy.type = 'button'; copy.textContent = '复制日志';
    const open = document.createElement('button'); open.type = 'button'; open.textContent = '打开日志目录';
    const close = document.createElement('button'); close.type = 'button'; close.textContent = '关闭';
    const log = document.createElement('pre'); log.id = 'qb-app-diagnostics-log'; log.textContent = '正在读取日志…';
    const note = document.createElement('div'); note.id = 'qb-app-diagnostics-note';
    note.textContent = '日志不包含 API Key 或 QQ 密码。关闭窗口不会停止后台管理服务。';
    header.append(title, copy, open, close); panel.append(header, log, note); overlay.appendChild(panel);
    document.body.appendChild(overlay);
    close.addEventListener('click', () => overlay.remove());
    copy.addEventListener('click', async () => {
      try { await window.pywebview.api.copy_logs(); copy.textContent = '已复制'; setTimeout(() => copy.textContent = '复制日志', 1500); }
      catch (error) { copy.textContent = '复制失败'; }
    });
    open.addEventListener('click', async () => {
      try { await window.pywebview.api.open_log_folder(); } catch (error) { note.textContent = '打开日志目录失败：' + error; }
    });
    try { log.textContent = await window.pywebview.api.get_logs(); }
    catch (error) { log.textContent = '读取日志失败：' + error + '\n\n请使用“打开日志目录”或查看应用日志文件。'; }
  });
  document.body.appendChild(button);
})();
"""


def _auto_close_seconds() -> float:
    try:
        value = float(os.environ.get("QQBOT_APP_AUTOCLOSE_SECONDS", "0") or 0)
    except ValueError:
        return 0.0
    return max(0.0, min(300.0, value))


def _start_auto_close(window, seconds: float) -> None:
    if seconds <= 0:
        return
    def close_later() -> None:
        time.sleep(seconds)
        try:
            window.destroy()
        except Exception:
            pass
    threading.Thread(target=close_later, daemon=True, name="app-shell-autoclose").start()


def _install_diagnostics(window, api: AppDiagnosticsAPI, logger: logging.Logger) -> None:
    def on_loaded() -> None:
        try:
            window.evaluate_js(_DIAGNOSTICS_JS)
            logger.info("diagnostics panel injected")
        except Exception:
            logger.exception("diagnostics panel injection failed")
    try:
        window.events.loaded += on_loaded
    except Exception:
        logger.exception("could not subscribe to webview loaded event")


def run_app_window(
    url: str,
    *,
    title: str,
    data_dir: str | Path,
    log_paths: Sequence[str | Path] | None = None,
    width: int = 1280,
    height: int = 860,
    min_size: tuple[int, int] = (980, 640),
) -> int:
    logger = configure_logger()
    paths = [Path(path) for path in (log_paths or [])]
    if app_log_path() not in paths:
        paths.insert(0, app_log_path())
    logger.info("starting app window title=%r url=%s data_dir=%s", title, url, data_dir)
    logger.info("app shell pid=%s frozen=%s executable=%s", os.getpid(), bool(getattr(sys, "frozen", False)), sys.executable)
    api = AppDiagnosticsAPI(data_dir=data_dir, log_paths=paths, title=title)
    try:
        import webview

        window = webview.create_window(
            title,
            url=url,
            js_api=api,
            width=int(width),
            height=int(height),
            min_size=min_size,
            resizable=True,
        )
        _install_diagnostics(window, api, logger)
        _start_auto_close(window, _auto_close_seconds())
        webview.start(gui="edgechromium", debug=False)
        logger.info("app window closed normally")
        return 0
    except Exception as exc:
        logger.exception("app window failed: %r", exc)
        return show_error_window(
            "QQ Bot Studio 无法启动桌面窗口",
            f"桌面窗口启动失败。应用没有退出，下面是错误和日志路径。\n\n{exc!r}",
            log_paths=paths,
            data_dir=data_dir,
        )


def run_html_app(
    html: str,
    *,
    title: str,
    data_dir: str | Path,
    log_paths: Sequence[str | Path] | None = None,
    js_api: Any = None,
    width: int = 1280,
    height: int = 860,
    min_size: tuple[int, int] = (980, 640),
) -> int:
    """Run a custom local HTML application inside the shared WebView2 shell."""

    logger = configure_logger()
    paths = [Path(path) for path in (log_paths or [])]
    if app_log_path() not in paths:
        paths.insert(0, app_log_path())
    logger.info("starting HTML app window title=%r data_dir=%s", title, data_dir)
    logger.info(
        "app shell pid=%s frozen=%s executable=%s",
        os.getpid(),
        bool(getattr(sys, "frozen", False)),
        sys.executable,
    )
    try:
        import webview

        window = webview.create_window(
            title,
            html=html,
            js_api=js_api,
            width=int(width),
            height=int(height),
            min_size=min_size,
            resizable=True,
        )
        _start_auto_close(window, _auto_close_seconds())
        webview.start(gui="edgechromium", debug=False)
        logger.info("HTML app window closed normally")
        return 0
    except Exception as exc:
        logger.exception("HTML app window failed: %r", exc)
        return show_error_window(
            "QQ Bot Studio 无法启动桌面窗口",
            f"桌面窗口启动失败。应用没有退出，下面是错误和日志路径。\n\n{exc!r}",
            log_paths=paths,
            data_dir=data_dir,
        )


def _tk_error_window(title: str, message: str, log_paths: Sequence[Path], data_dir: Path) -> int:
    try:
        import tkinter as tk
        from tkinter import scrolledtext

        logger = configure_logger()
        root = tk.Tk()
        root.title(title)
        root.geometry("980x680")
        root.minsize(720, 480)
        root.configure(bg="#081a33")
        header = tk.Label(
            root,
            text="QQ Bot Studio 启动失败",
            font=("Segoe UI", 16, "bold"),
            fg="#ffcf7a",
            bg="#081a33",
            anchor="w",
        )
        header.pack(fill="x", padx=18, pady=(18, 6))
        note = tk.Label(
            root,
            text="窗口不会自动消失。可复制日志，或打开日志目录后反馈给支持人员。",
            font=("Segoe UI", 10),
            fg="#b7d9ed",
            bg="#081a33",
            anchor="w",
        )
        note.pack(fill="x", padx=18, pady=(0, 10))
        text = scrolledtext.ScrolledText(
            root, wrap="word", font=("Consolas", 10), bg="#071d31", fg="#e7f4ff",
            insertbackground="#e7f4ff", relief="flat", padx=12, pady=12,
        )
        text.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        text.insert("1.0", message + "\n\n" + read_diagnostics(log_paths))
        text.configure(state="disabled")
        buttons = tk.Frame(root, bg="#081a33")
        buttons.pack(fill="x", padx=18, pady=(0, 16))

        def copy_logs() -> None:
            _windows_clipboard(read_diagnostics(log_paths))

        def open_logs() -> None:
            try:
                folder = log_paths[0].parent if log_paths else logs_root()
                folder.mkdir(parents=True, exist_ok=True)
                os.startfile(str(folder))  # type: ignore[attr-defined]
            except Exception:
                logger.exception("error window could not open log folder")

        tk.Button(buttons, text="复制日志", command=copy_logs).pack(side="left")
        tk.Button(buttons, text="打开日志目录", command=open_logs).pack(side="left", padx=8)
        tk.Button(buttons, text="关闭", command=root.destroy).pack(side="right")
        seconds = _auto_close_seconds()
        if seconds > 0:
            root.after(int(seconds * 1000), root.destroy)
        root.mainloop()
        return 1
    except Exception:
        try:
            _windows_clipboard(message + "\n\n" + read_diagnostics(log_paths))
        except Exception:
            pass
        if os.name == "nt":
            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    message + "\n\n日志：" + "\n".join(str(path) for path in log_paths),
                    title,
                    0x10,
                )
            except Exception:
                pass
        return 1


def show_error_window(
    title: str,
    message: str,
    *,
    log_paths: Sequence[str | Path],
    data_dir: str | Path,
) -> int:
    logger = configure_logger()
    paths = [Path(path) for path in log_paths]
    if app_log_path() not in paths:
        paths.insert(0, app_log_path())
    logger.error("showing startup error window: %s", message.replace("\n", " | ")[:2000])
    return _tk_error_window(title, message, paths, Path(data_dir))


def clipboard_text(text: str) -> bool:
    """Small public helper used by tests and the native dashboard."""
    return _windows_clipboard(text)
