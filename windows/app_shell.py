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



_APP_NAV_JS = r"""
(function () {
  if (document.getElementById('qb-app-nav')) return;
  const navWidth = 176;
  const currentPath = String(window.location.pathname || '');
  const isWizard = currentPath.indexOf('/wizard') === 0;
  const style = document.createElement('style');
  style.id = 'qb-app-nav-style';
  style.textContent = `
    :root { --qb-app-nav-width: 176px; }
    #qb-app-nav{position:fixed;inset:0 auto 0 0;width:176px;z-index:2147483644;display:flex;
      flex-direction:column;gap:8px;padding:18px 12px 14px;box-sizing:border-box;
      color:#e7fffa;background:linear-gradient(170deg,#06172a 0%,#0a2944 60%,#082238 100%);
      border-right:1px solid rgba(255,255,255,.1);box-shadow:12px 0 34px rgba(2,12,24,.2);
      font:13px/1.4 'Segoe UI','Microsoft YaHei UI',sans-serif;}
    #qb-app-nav .qb-app-brand{display:flex;align-items:center;gap:9px;padding:2px 6px 16px;
      border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:8px;}
    #qb-app-nav .qb-app-brand-mark{width:31px;height:31px;border-radius:10px;display:grid;place-items:center;
      color:#65efd0;background:linear-gradient(145deg,#0e3556,#0c5b60);border:1px solid #2b6881;font-size:17px;}
    #qb-app-nav .qb-app-brand-copy{display:flex;flex-direction:column;min-width:0;}
    #qb-app-nav .qb-app-brand-copy strong{font-size:13px;color:#f5fffd;letter-spacing:.01em;}
    #qb-app-nav .qb-app-brand-copy small{font-size:9px;color:#87b3c6;letter-spacing:.08em;}
    #qb-app-nav .qb-app-nav-label{padding:7px 7px 2px;color:#6f9db3;font-size:9px;font-weight:750;
      letter-spacing:.14em;text-transform:uppercase;}
    #qb-app-nav .qb-app-nav-button{display:flex;align-items:center;gap:10px;width:100%;min-height:43px;
      padding:9px 11px;border:1px solid transparent;border-radius:10px;color:#c2dce8;background:transparent;
      font:650 13px 'Segoe UI','Microsoft YaHei UI',sans-serif;text-align:left;cursor:pointer;}
    #qb-app-nav .qb-app-nav-button:hover{color:#f4fffd;background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.1);}
    #qb-app-nav .qb-app-nav-button[aria-current="page"]{color:#06251f;
      background:linear-gradient(135deg,#7cf2d5,#29d6a7);border-color:#a2ffe5;box-shadow:0 7px 18px rgba(9,120,91,.22);}
    #qb-app-nav .qb-app-nav-icon{width:22px;height:22px;display:grid;place-items:center;border:1px solid currentColor;
      border-radius:7px;font-size:13px;line-height:1;}
    #qb-app-nav .qb-app-nav-spacer{flex:1;}
    #qb-app-nav .qb-app-nav-meta{padding:10px 7px 0;border-top:1px solid rgba(255,255,255,.1);
      color:#7198ac;font:10px/1.5 'Cascadia Mono','Consolas',monospace;word-break:break-all;}
    #qb-app-nav .qb-app-nav-meta strong{display:block;color:#a7cad8;font-weight:600;}
    @media (max-width: 900px){
      :root { --qb-app-nav-width: 148px; }
      #qb-app-nav{width:148px;padding:12px 8px;}
      #qb-app-nav .qb-app-brand-copy small{display:none;}
      #qb-app-nav .qb-app-nav-button{padding:8px;font-size:12px;}
    }
    /* v1.0.4 light app shell theme */
    #qb-app-nav{color:#183247!important;background:linear-gradient(180deg,#ffffff,#f4fafc)!important;border-right:1px solid #d6e4ee!important;box-shadow:8px 0 24px rgba(31,67,91,.06)!important}
    #qb-app-nav .qb-app-brand{border-bottom-color:#e1ebf2!important}
    #qb-app-nav .qb-app-brand-copy strong{color:#173247!important}
    #qb-app-nav .qb-app-brand-copy small,#qb-app-nav .qb-app-nav-label{color:#688295!important}
    #qb-app-nav .qb-app-brand-mark{color:#0b8f72!important;background:linear-gradient(145deg,#effbf7,#d7f4eb)!important;border-color:#b8e4d8!important}
    #qb-app-nav .qb-app-nav-button{color:#31556b!important;background:#fff!important;border-color:#dbe8f0!important}
    #qb-app-nav .qb-app-nav-button:hover{color:#163247!important;background:#f1f8fb!important;border-color:#bcd4e2!important}
    #qb-app-nav .qb-app-nav-button[aria-current="page"]{color:#fff!important;background:linear-gradient(135deg,#0b8f72,#35bf9d)!important;border-color:#0b8f72!important;box-shadow:0 5px 14px rgba(11,143,114,.2)!important}
    #qb-app-nav .qb-app-nav-meta{border-top-color:#e1ebf2!important;color:#688295!important}
    #qb-app-nav .qb-app-nav-meta strong{color:#355a70!important}
  `;
  document.head.appendChild(style);
  const nav = document.createElement('aside');
  nav.id = 'qb-app-nav';
  nav.setAttribute('aria-label', 'QQ Bot Studio App 导航');
  nav.innerHTML = `
    <div class="qb-app-brand"><div class="qb-app-brand-mark">◎</div><div class="qb-app-brand-copy">
      <strong>QQ Bot Studio</strong><small>桌面应用</small></div></div>
    <div class="qb-app-nav-label">工作区</div>
    <button class="qb-app-nav-button" type="button" data-qb-nav="console" aria-current="${isWizard ? 'false' : 'page'}">
      <span class="qb-app-nav-icon">▦</span><span>控制台</span></button>
    <button class="qb-app-nav-button" type="button" data-qb-nav="wizard" aria-current="${isWizard ? 'page' : 'false'}">
      <span class="qb-app-nav-icon">↗</span><span>向导</span></button>
    <div class="qb-app-nav-spacer"></div>
    <div class="qb-app-nav-meta"><strong>本地回环运行</strong>127.0.0.1 · WebView2</div>
  `;
  document.body.appendChild(nav);
  const existingPadding = window.getComputedStyle(document.body).paddingLeft || '0px';
  document.body.style.setProperty('padding-left', `calc(${navWidth}px + ${existingPadding})`, 'important');
  document.body.style.setProperty('box-sizing', 'border-box', 'important');
  nav.querySelector('[data-qb-nav="console"]').addEventListener('click', () => {
    if (!isWizard) return;
    window.location.assign('/console');
  });
  nav.querySelector('[data-qb-nav="wizard"]').addEventListener('click', async () => {
    if (isWizard) return;
    let target = '/wizard';
    try {
      const token = typeof window.QB_TOKEN === 'string' ? window.QB_TOKEN : '';
      const response = await fetch('/api/instances', {headers: {'X-QB-Token': token}, cache: 'no-store'});
      if (response.ok) {
        const data = await response.json();
        const instances = Array.isArray(data.instances) ? data.instances : [];
        const first = instances.find((item) => item && ((item.id || item.instance_id)));
        const id = first && (first.id || first.instance_id);
        if (id) target = '/wizard?instance=' + encodeURIComponent(String(id));
      }
    } catch (error) { /* wizard without an instance still renders the entry page */ }
    window.location.assign(target);
  });
})();
"""


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
            window.evaluate_js(_APP_NAV_JS + "\n" + _DIAGNOSTICS_JS)
            logger.info("app navigation and diagnostics panel injected")
            test_nav = os.environ.get("QQBOT_APP_TEST_NAV", "").strip().lower()
            if test_nav in {"wizard", "console"}:
                # Deterministic POC smoke hook; never set for normal users.
                window.evaluate_js(
                    "(() => {"
                    "const key='qb-app-test-nav';"
                    "if (sessionStorage.getItem(key)) return;"
                    "sessionStorage.setItem(key, '1');"
                    f"setTimeout(() => document.querySelector('[data-qb-nav={test_nav}]')?.click(), 80);"
                    "})();"
                )
                logger.info("test navigation to %s scheduled", test_nav)
        except Exception:
            logger.exception("app navigation injection failed")
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
