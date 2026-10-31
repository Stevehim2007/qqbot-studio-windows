"""Native edition desktop dashboard and one-click installer UI."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from windows import app_shell, native_runtime, native_setup

LOGGER = logging.getLogger("qqbot.windows.native_app")


def native_dashboard_html() -> str:
    return r'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>QQ Bot Studio Native</title>
<style>
:root{color-scheme:dark;--bg:#061824;--panel:#0c2b40;--panel2:#103750;--line:#245571;--text:#e7f5ff;--muted:#91b8ce;--accent:#62e8c4;--warn:#ffce72;--danger:#ff8d8d}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(140deg,#04121e,#09283b 60%,#0b344a);color:var(--text);font:14px/1.5 "Segoe UI","Microsoft YaHei UI",sans-serif;min-height:100vh}
header{display:flex;align-items:center;gap:16px;padding:22px 28px;border-bottom:1px solid var(--line);background:rgba(4,18,30,.72);position:sticky;top:0;z-index:3}
.logo{width:42px;height:42px;border-radius:13px;background:linear-gradient(145deg,#0e3458,#0b5b68);display:grid;place-items:center;font-size:22px;border:1px solid #2d6a8f}
h1{font-size:21px;margin:0;color:#fff}h1 em{color:var(--accent);font-style:normal}.sub{color:var(--muted);font-size:12px;margin-top:2px;flex:1}.pill{border:1px solid var(--line);border-radius:999px;padding:5px 10px;color:var(--muted);font-size:12px;white-space:nowrap}
main{max-width:1240px;margin:0 auto;padding:24px;display:grid;gap:18px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card{background:rgba(12,43,64,.92);border:1px solid var(--line);border-radius:15px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.18)}.card .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.card .value{font-weight:650;margin-top:5px;word-break:break-all}.ok{color:var(--accent)}.warn{color:var(--warn)}.bad{color:var(--danger)}.mono{font-family:"Cascadia Mono",Consolas,monospace;font-size:12px}
.panel{background:rgba(8,33,49,.94);border:1px solid var(--line);border-radius:16px;padding:18px}section h2{font-size:16px;margin:0 0 12px;color:#fff}.actions{display:flex;gap:10px;flex-wrap:wrap}.btn{border:1px solid #326580;border-radius:9px;background:#103a57;color:#e2f6ff;padding:9px 14px;font:600 13px "Segoe UI",sans-serif;cursor:pointer}.btn:hover{background:#155276}.btn.primary{background:linear-gradient(135deg,#0f735f,#1e9c77);border-color:#2bd7a5;color:#041c1a}.btn.danger{background:#4a202b;border-color:#985363}.btn:disabled{opacity:.45;cursor:not-allowed}.progress-wrap{height:9px;border-radius:999px;background:#051520;border:1px solid #1d4258;overflow:hidden;margin:12px 0}.progress-bar{height:100%;width:0;background:linear-gradient(90deg,#1e9c77,#62e8c4);transition:width .35s}.statusline{min-height:22px;color:var(--muted);font-size:13px}.manual{border-left:3px solid var(--warn);padding:10px 13px;background:rgba(255,206,114,.07);border-radius:8px;color:#ffe8b0;font-size:13px}.logbox{height:230px;overflow:auto;background:#03111b;border:1px solid #1c4055;border-radius:10px;padding:12px;white-space:pre-wrap;color:#b8dceb;font:12px/1.45 "Cascadia Mono",Consolas,monospace}.toolbar{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap}.toolbar .grow{flex:1}.small{font-size:12px;color:var(--muted)}#toast{position:fixed;right:20px;bottom:20px;max-width:460px;padding:12px 15px;border-radius:10px;background:#103750;border:1px solid #326580;color:#e5f8ff;box-shadow:0 12px 36px rgba(0,0,0,.4);display:none}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.grid{grid-template-columns:1fr}main{padding:14px}header{padding:16px}.sub{display:none}}
</style></head>
<body><header><div class="logo">◎</div><div><h1>QQ Bot <em>Studio</em> · Native</h1><div class="sub">Windows 原生单实例 POC · 无 Docker / 无 WSL / 无 noVNC</div></div><span id="mode-pill" class="pill">正在读取状态…</span></header>
<main>
<section class="grid" id="env-cards">
<div class="card"><div class="label">NTQQ</div><div class="value" id="ntqq">…</div></div>
<div class="card"><div class="label">AstrBot</div><div class="value" id="astrbot">…</div></div>
<div class="card"><div class="label">SnowLuma</div><div class="value" id="snowluma">…</div></div>
<div class="card"><div class="label">Node.js</div><div class="value" id="node">…</div></div>
</section>
<section class="panel"><h2>一键安装/修复官方组件</h2><div class="small" id="install-caption">首次使用请点击一键安装：下载并校验官方 AstrBot wheel、Python 3.12、SnowLuma Windows lite 和 Node.js；NTQQ 只检测，不自动登录。</div><div class="progress-wrap"><div class="progress-bar" id="progress-bar"></div></div><div class="statusline" id="install-status">等待检测…</div><div class="actions" style="margin-top:14px"><button id="install-btn" class="btn primary" type="button">一键安装/修复</button><button id="refresh-btn" class="btn" type="button">刷新状态</button></div></section>
<section class="panel"><h2>运行控制</h2><div class="actions"><button id="start-btn" class="btn primary" type="button">启动 Native 服务</button><button id="stop-btn" class="btn danger" type="button">停止</button><button id="qq-btn" class="btn" type="button">打开本机 NTQQ</button><button id="refresh2-btn" class="btn" type="button">刷新进程</button></div><div class="statusline" id="run-status" style="margin-top:12px">尚未启动</div><div class="manual" style="margin-top:14px">QQ 扫码、设备/短信/邮箱/滑块验证必须在官方本机 NTQQ 窗口完成；SnowLuma EULA/PRIVACY 必须由你本人在其 WebUI 接受。程序不会绕过验证，也不会保存 QQ 密码或 API Key。</div></section>
<section class="panel"><div class="toolbar"><h2 style="margin:0">诊断日志</h2><span class="grow"></span><button class="btn" id="copy-logs-btn" type="button">复制日志</button><button class="btn" id="open-logs-btn" type="button">打开日志目录</button><button class="btn" id="refresh-logs-btn" type="button">刷新</button></div><div class="logbox" id="logbox">正在读取日志…</div></section>
</main><div id="toast"></div>
<script>
const api = window.pywebview && window.pywebview.api;
let installPoller = null;
function t(id){return document.getElementById(id)}
function setText(id,text,cls){const e=t(id);e.textContent=text;if(cls)e.className='value '+cls}
function toast(text){const e=t('toast');e.textContent=text;e.style.display='block';clearTimeout(window.__toast);window.__toast=setTimeout(()=>e.style.display='none',4500)}
async function copyLogs(){try{const ok=await api.copy_logs();toast(ok?'日志已复制':'复制失败')}catch(e){toast('复制失败: '+e)}}
async function openLogs(){try{await api.open_log_folder()}catch(e){toast('打开失败: '+e)}}
async function refreshLogs(){try{t('logbox').textContent=await api.get_logs()}catch(e){t('logbox').textContent='读取日志失败: '+e}}
async function refreshState(){try{const s=await api.get_state(); const e=s.environment||{}; setText('ntqq',e.ntqq?'已找到':'未找到',e.ntqq?'ok':'bad'); setText('astrbot',e.astrbot_installed?'已安装':'未安装',e.astrbot_installed?'ok':'warn'); setText('snowluma',e.snowluma_installed?'已安装':'未安装',e.snowluma_installed?'ok':'warn'); setText('node',e.node||'未找到',e.node?'ok':'warn'); t('mode-pill').textContent=s.bind_host||'127.0.0.1'; t('run-status').textContent=s.runtime_text||'AstrBot/SnowLuma 未启动';}catch(e){toast('状态读取失败: '+e)}}
function showInstall(s){const p=Number(s.percent||0);t('progress-bar').style.width=p+'%';t('install-status').textContent=(s.message||'')+(s.error?' · '+s.error:'');if(s.active){t('install-btn').disabled=true}else{t('install-btn').disabled=false;if(installPoller){clearInterval(installPoller);installPoller=null}}}
async function pollInstall(){try{const s=await api.get_install_status();showInstall(s);if(!s.active){await refreshState();await refreshLogs()}}catch(e){t('install-status').textContent='读取安装状态失败: '+e}}
async function install(){try{const r=await api.one_click_install();if(!r.started){toast(r.message||'无法开始安装');return}t('install-btn').disabled=true;t('install-status').textContent='正在安装，请保持窗口打开…';if(!installPoller)installPoller=setInterval(pollInstall,900)}catch(e){toast('安装启动失败: '+e)}}
async function startServices(){try{const r=await api.start_services();toast(r.message||'启动请求已提交');setTimeout(refreshState,1200)}catch(e){toast('启动失败: '+e)}}
async function stopServices(){try{const r=await api.stop_services();toast(r.message||'停止请求已提交');setTimeout(refreshState,500)}catch(e){toast('停止失败: '+e)}}
async function openQQ(){try{const r=await api.open_qq();toast(r.message||'已打开 NTQQ')}catch(e){toast('打开 NTQQ 失败: '+e)}}
t('install-btn').addEventListener('click',install);t('refresh-btn').addEventListener('click',refreshState);t('refresh2-btn').addEventListener('click',refreshState);t('start-btn').addEventListener('click',startServices);t('stop-btn').addEventListener('click',stopServices);t('qq-btn').addEventListener('click',openQQ);t('copy-logs-btn').addEventListener('click',copyLogs);t('open-logs-btn').addEventListener('click',openLogs);t('refresh-logs-btn').addEventListener('click',refreshLogs);
refreshState().then(refreshLogs);setInterval(refreshLogs,5000);
</script></body></html>'''


class NativeAppAPI:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self._lock = threading.Lock()
        self._install_thread: threading.Thread | None = None
        self._install_events: list[str] = []
        self._install_percent = 0
        self._install_message = "等待检测…"
        self._install_active = False
        self._install_error = ""
        self._logger = native_setup.configure_logger(self.root)

    def _log(self, text: str) -> None:
        self._logger.info(text)
        with self._lock:
            self._install_events.append(f"{time.strftime('%H:%M:%S')} {text}")
            self._install_events = self._install_events[-300:]

    def get_state(self) -> dict[str, Any]:
        cfg = native_runtime.load_config(self.root)
        env = native_setup.detect_environment(self.root)
        astrbot = native_runtime.service_alive(self.root, "astrbot")
        snowluma = native_runtime.service_alive(self.root, "snowluma")
        return {
            "ok": True,
            "root": str(self.root),
            "bind_host": "127.0.0.1",
            "environment": env,
            "services": {"astrbot_running": astrbot, "snowluma_running": snowluma},
            "runtime_text": (
                f"AstrBot {'运行中' if astrbot else '未运行'} · SnowLuma {'运行中' if snowluma else '未运行'} · "
                f"OneBot {cfg.get('onebot_url')}"
            ),
        }

    def get_logs(self) -> str:
        paths = [
            app_shell.app_log_path(),
            app_shell.logs_root() / "launcher.log",
            self.root / "logs" / native_setup.INSTALL_LOG,
            self.root / "logs" / "astrbot.log",
            self.root / "logs" / "snowluma.log",
        ]
        text = app_shell.read_diagnostics(paths, lines=240)
        with self._lock:
            if self._install_events:
                text += "\n===== installer events =====\n" + "\n".join(self._install_events[-80:])
        return text

    def copy_logs(self) -> bool:
        return app_shell.clipboard_text(self.get_logs())

    def open_log_folder(self) -> bool:
        try:
            folder = app_shell.logs_root()
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]
            return True
        except Exception:
            return False

    def get_install_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._install_active,
                "percent": self._install_percent,
                "message": self._install_message,
                "error": self._install_error,
                "events": list(self._install_events[-80:]),
            }

    def _progress(self, phase: str, percent: int, message: str) -> None:
        with self._lock:
            self._install_percent = int(percent)
            self._install_message = f"[{phase}] {message}"
        self._log(f"[{phase}] {message}")
        try:
            # Keep the pywebview dashboard responsive during long installs.
            import webview

            for window in webview.windows:
                window.evaluate_js(
                    f"showInstall({json.dumps(self.get_install_status(), ensure_ascii=False)})"
                )
        except Exception:
            pass

    def one_click_install(self) -> dict[str, Any]:
        with self._lock:
            if self._install_active or (self._install_thread and self._install_thread.is_alive()):
                return {"started": False, "message": "安装已在进行中"}
            self._install_active = True
            self._install_percent = 0
            self._install_error = ""
            self._install_message = "准备安装…"
            self._install_events = []

        def worker() -> None:
            try:
                result = native_setup.install_all(self.root, self._progress)
                with self._lock:
                    self._install_percent = 100
                    self._install_message = "一键安装/校验完成"
                self._log(json.dumps(result, ensure_ascii=False)[:4000])
            except Exception as exc:
                with self._lock:
                    self._install_error = f"{type(exc).__name__}: {exc}"
                    self._install_message = "安装失败；请查看诊断日志"
                self._log(self._install_error)
            finally:
                with self._lock:
                    self._install_active = False

        self._install_thread = threading.Thread(target=worker, daemon=True, name="native-one-click-install")
        self._install_thread.start()
        return {"started": True, "message": "后台安装已启动"}

    def start_services(self) -> dict[str, Any]:
        try:
            result = native_runtime.start_native(self.root)
            self._log("native start: " + json.dumps(result.get("runtime", {}), ensure_ascii=False))
            return {"ok": True, "message": "AstrBot/SnowLuma 已启动"}
        except native_runtime.NativeBlocked as exc:
            return {"ok": False, "message": "缺少组件: " + "; ".join(exc.blockers)}
        except Exception as exc:
            self._log(f"start failed: {exc}")
            return {"ok": False, "message": f"启动失败: {exc}"}

    def stop_services(self) -> dict[str, Any]:
        try:
            result = native_runtime.stop_native(self.root)
            self._log("native stop: " + json.dumps(result, ensure_ascii=False))
            return {"ok": True, "message": "已停止 Native 服务"}
        except Exception as exc:
            return {"ok": False, "message": f"停止失败: {exc}"}

    def open_qq(self) -> dict[str, Any]:
        try:
            path = native_runtime.open_qq_window(native_runtime.load_config(self.root))
            return {"ok": True, "message": f"已打开官方 NTQQ: {path}"}
        except Exception as exc:
            return {"ok": False, "message": f"打开 NTQQ 失败: {exc}"}


def run(root: Path) -> int:
    native_setup.configure_logger(root)
    html = native_dashboard_html()
    return app_shell.run_html_app(
        html,
        title="QQ Bot Studio Native",
        data_dir=root,
        log_paths=[
            app_shell.app_log_path(),
            app_shell.logs_root() / "launcher.log",
            root / "logs" / native_setup.INSTALL_LOG,
            root / "logs" / "astrbot.log",
            root / "logs" / "snowluma.log",
        ],
        js_api=NativeAppAPI(root),
    )
