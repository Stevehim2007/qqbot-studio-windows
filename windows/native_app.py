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

#native-app-nav{position:fixed;inset:0 auto 0 0;width:190px;z-index:8;display:flex;flex-direction:column;gap:8px;padding:20px 13px;box-sizing:border-box;background:linear-gradient(170deg,#031421,#092b41 62%,#062033);border-right:1px solid #1e4a62;box-shadow:12px 0 34px rgba(0,0,0,.18)}
#native-app-nav .nav-brand{display:flex;align-items:center;gap:9px;padding:2px 5px 16px;border-bottom:1px solid #1d4258;margin-bottom:8px}
#native-app-nav .nav-brand-mark{width:33px;height:33px;border-radius:10px;display:grid;place-items:center;color:#62e8c4;background:linear-gradient(145deg,#0b3454,#0c5b60);border:1px solid #2b6881}
#native-app-nav .nav-brand strong{display:block;font-size:13px;color:#f4fffd}#native-app-nav .nav-brand small{display:block;font-size:9px;color:#81adc1;letter-spacing:.07em;margin-top:1px}
#native-app-nav .nav-label{padding:7px 6px 2px;color:#6f9db3;font-size:9px;font-weight:750;letter-spacing:.13em;text-transform:uppercase}
#native-app-nav .nav-btn{display:flex;align-items:center;gap:9px;width:100%;min-height:42px;padding:8px 10px;border:1px solid transparent;border-radius:10px;background:transparent;color:#c2dce8;font:650 13px "Segoe UI","Microsoft YaHei UI",sans-serif;text-align:left;cursor:pointer}
#native-app-nav .nav-btn:hover{background:rgba(255,255,255,.07);color:#fff;border-color:#28536c}
#native-app-nav .nav-btn[aria-current="page"]{color:#06251f;background:linear-gradient(135deg,#7cf2d5,#29d6a7);border-color:#a2ffe5}
#native-app-nav .nav-icon{width:22px;height:22px;display:grid;place-items:center;border:1px solid currentColor;border-radius:7px;font-size:13px}
#native-app-nav .nav-spacer{flex:1}#native-app-nav .nav-meta{padding:10px 6px 0;border-top:1px solid #1d4258;color:#7198ac;font:10px/1.5 "Cascadia Mono",Consolas,monospace;word-break:break-all}#native-app-nav .nav-meta strong{display:block;color:#a7cad8}
body{padding-left:190px;box-sizing:border-box}.native-view[hidden]{display:none!important}.wizard-head{display:flex;gap:12px;align-items:flex-end;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap}.wizard-picker label{display:block;margin-bottom:6px;color:var(--muted);font-size:11px;font-weight:720;letter-spacing:.05em}.wizard-picker select{min-width:220px;min-height:36px;padding:7px 28px 7px 10px;color:#e7fffa;background:#0d2d4b;border:1px solid #2a5275;border-radius:9px;font:12px "Segoe UI","Microsoft YaHei UI",sans-serif;cursor:pointer}.wizard-picker select:disabled{opacity:.7}.wizard-picker option{color:#edf8ff;background:#0d2d4b}.wizard-picker option:disabled{color:#69859c}.wizard-lock-note{margin:8px 0 0;color:#f2d69a;font-size:11px}.wizard-step-card{display:none}.wizard-step-card.is-active{display:block}.wizard-step-head{display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap}.wizard-step-index{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:#123d54;border:1px solid #2d6a8f;color:#62e8c4;font-weight:700}.wizard-kv{display:grid;grid-template-columns:190px minmax(0,1fr);gap:7px 14px;margin:10px 0;font-size:13px}.wizard-kv dt{color:var(--muted)}.wizard-kv dd{margin:0;word-break:break-all;color:#d9f3ff}.wizard-actions{display:flex;gap:9px;margin-top:16px;flex-wrap:wrap}@media(max-width:900px){body{padding-left:148px}#native-app-nav{width:148px;padding:13px 8px}#native-app-nav .nav-brand small{display:none}#native-app-nav .nav-btn{padding:7px;font-size:11px}.wizard-kv{grid-template-columns:1fr}.wizard-picker select{min-width:170px}}

/* v1.0.4 default light theme */
:root{color-scheme:light;--bg:#f4f8fb;--panel:#ffffff;--panel2:#eef6fb;--line:#d6e4ee;--text:#183247;--muted:#5f788b;--accent:#0b8f72;--warn:#9a6419;--danger:#b23b4a}
html,body{background:#f4f8fb!important;color:#183247!important}
body{background:radial-gradient(circle at 85% 0,rgba(11,143,114,.09),transparent 28rem),linear-gradient(150deg,#f8fbfd,#edf5fa)!important}
header{background:rgba(255,255,255,.94)!important;border-bottom:1px solid #d8e6ef!important;box-shadow:0 5px 18px rgba(31,67,91,.07)}
h1{color:#122e43!important}h1 em{color:#0a9b80!important}.sub,.small,.statusline,.card .label{color:#5f788b!important}.pill{background:#fff!important;border-color:#cddfe9!important;color:#365b71!important}.pill.ok{color:#08755f!important;border-color:#b8e4d8!important;background:#effbf7!important}.pill.warn{color:#85601d!important;border-color:#ebd8ad!important;background:#fffaf0!important}.pill.bad{color:#a43343!important;border-color:#edc6cd!important;background:#fff4f5!important}
#native-app-nav{background:linear-gradient(180deg,#ffffff,#f4fafc)!important;border-right:1px solid #d6e4ee!important;box-shadow:8px 0 24px rgba(31,67,91,.06)!important;color:#183247!important}
#native-app-nav .nav-brand{border-bottom-color:#e1ebf2!important}#native-app-nav .nav-brand strong{color:#173247!important}#native-app-nav .nav-brand small,#native-app-nav .nav-label,#native-app-nav .nav-meta{color:#688295!important}#native-app-nav .nav-meta{border-top-color:#e1ebf2!important}#native-app-nav .nav-meta strong{color:#355a70!important}
#native-app-nav .nav-btn{background:#fff!important;color:#31556b!important;border-color:#dbe8f0!important}#native-app-nav .nav-btn:hover{background:#f1f8fb!important;color:#163247!important;border-color:#bcd4e2!important}#native-app-nav .nav-btn[aria-current="page"]{color:#fff!important;background:linear-gradient(135deg,#0b8f72,#35bf9d)!important;border-color:#0b8f72!important;box-shadow:0 5px 14px rgba(11,143,114,.2)!important}
.panel,.card{background:#fff!important;border-color:#d7e5ee!important;box-shadow:0 8px 24px rgba(28,63,88,.07)!important;color:#183247!important}section h2{color:#163247!important}.value{color:#183247!important}.ok{color:#08755f!important}.warn{color:#9a6419!important}.bad{color:#ad3848!important}
.btn{background:#fff!important;color:#24536c!important;border-color:#c9dce8!important}.btn:hover{background:#eff7fb!important}.btn.primary{background:#0b8f72!important;color:#fff!important;border-color:#0b8f72!important}.btn.primary:hover{background:#087b62!important}.btn.danger{background:#fff4f5!important;color:#a43343!important;border-color:#ecc4cc!important}
.progress-wrap{background:#e8f1f5!important;border-color:#d2e2eb!important}.logbox{background:#f8fbfd!important;border-color:#d6e4ee!important;color:#294c62!important;user-select:text!important}.manual{background:#fff9ec!important;border-left-color:#d6a343!important;color:#77531b!important}
#toast{background:#fff!important;border-color:#cddfe9!important;color:#183247!important;box-shadow:0 10px 30px rgba(28,63,88,.18)!important}.wizard-picker select{background:#fff!important;color:#183247!important;border-color:#c8dbe7!important}.wizard-picker option{background:#fff!important;color:#183247!important}.wizard-lock-note{color:#8a661f!important}.wizard-step-index{background:#eff9f6!important;border-color:#b8e4d8!important;color:#0b8f72!important}.wizard-kv dt{color:#637e91!important}.wizard-kv dd{color:#183247!important}
</style></head>
<body><aside id="native-app-nav" aria-label="QQ Bot Studio Native App 导航"><div class="nav-brand"><div class="nav-brand-mark">◎</div><div><strong>QQ Bot Studio</strong><small>Native 桌面应用</small></div></div><div class="nav-label">工作区</div><button class="nav-btn" type="button" data-native-nav="console" aria-current="page"><span class="nav-icon">▦</span>控制台</button><button class="nav-btn" type="button" data-native-nav="wizard" aria-current="false"><span class="nav-icon">↗</span>向导</button><div class="nav-spacer"></div><div class="nav-meta"><strong>单实例模式</strong>WebView2 · 127.0.0.1</div></aside><header><div class="logo">◎</div><div><h1>QQ Bot <em>Studio</em> · Native</h1><div class="sub">Windows 原生单实例 POC · 无 Docker / 无 WSL / 无 noVNC</div></div><span id="native-connection" class="pill warn">正在连接 Native 服务…</span><span id="mode-pill" class="pill">正在读取状态…</span></header>
<main id="native-view-console" class="native-view">
<section class="grid" id="env-cards">
<div class="card"><div class="label">NTQQ</div><div class="value" id="ntqq">…</div></div>
<div class="card"><div class="label">AstrBot</div><div class="value" id="astrbot">…</div></div>
<div class="card"><div class="label">SnowLuma</div><div class="value" id="snowluma">…</div></div>
<div class="card"><div class="label">Node.js</div><div class="value" id="node">…</div></div>
</section>
<section class="panel"><h2>一键安装/修复官方组件</h2><div class="small" id="install-caption">首次使用请点击一键安装：下载并校验官方 AstrBot wheel、Python 3.12、SnowLuma Windows lite 和 Node.js；NTQQ 只检测，不自动登录。</div><div class="progress-wrap"><div class="progress-bar" id="progress-bar"></div></div><div class="statusline" id="install-status">等待检测…</div><div class="actions" style="margin-top:14px"><button id="install-btn" class="btn primary" type="button">一键安装/修复</button><button id="refresh-btn" class="btn" type="button">刷新状态</button></div></section>
<section class="panel"><h2>运行控制</h2><div class="actions"><button id="start-btn" class="btn primary" type="button">启动 Native 服务</button><button id="stop-btn" class="btn danger" type="button">停止</button><button id="qq-btn" class="btn" type="button">打开本机 NTQQ</button><button id="refresh2-btn" class="btn" type="button">刷新进程</button></div><div class="statusline" id="run-status" style="margin-top:12px">尚未启动</div><div class="manual" style="margin-top:14px">QQ 扫码、设备/短信/邮箱/滑块验证必须在官方本机 NTQQ 窗口完成；SnowLuma EULA/PRIVACY 必须由你本人在其 WebUI 接受。程序不会绕过验证，也不会保存 QQ 密码或 API Key。</div></section>
<section class="panel"><div class="toolbar"><h2 style="margin:0">诊断日志</h2><span class="grow"></span><button class="btn" id="copy-logs-btn" type="button">复制日志</button><button class="btn" id="open-logs-btn" type="button">打开日志目录</button><button class="btn" id="refresh-logs-btn" type="button">刷新</button></div><div class="logbox" id="logbox">正在读取日志…</div></section>

</main>
<main id="native-view-wizard" class="native-view" hidden>
<section class="panel">
<h2>部署向导</h2>
<div class="wizard-head"><div class="wizard-picker"><label for="native-wizard-step-select">快速跳转步骤</label><select id="native-wizard-step-select"><option value="env" selected>1. 检查环境</option><option value="install">2. 安装组件</option><option value="config">3. 配置与启动</option><option value="done">4. 完成与人工验证</option></select><p id="native-wizard-lock-note" class="wizard-lock-note" role="status" hidden>机器人组件已部署，前三步已锁定，只能进入完成与人工验证。</p></div><div class="small" id="native-wizard-progress-text">可随时用下拉菜单切换步骤。</div></div>
<section class="wizard-step-card is-active" data-native-step="env"><div class="wizard-step-head"><span class="wizard-step-index">1</span><h2 style="margin:0">检查环境</h2></div><p class="small">检查 Windows x64、NTQQ、uv、Node、AstrBot/SnowLuma 当前状态。NTQQ 只会检测，不会自动登录。</p><dl class="wizard-kv"><dt>操作系统</dt><dd id="wiz-os">…</dd><dt>NTQQ</dt><dd id="wiz-ntqq">…</dd><dt>AstrBot</dt><dd id="wiz-astrbot">…</dd><dt>SnowLuma</dt><dd id="wiz-snowluma">…</dd><dt>官方来源计划</dt><dd id="wiz-plan">4 项固定 URL/SHA256 校验</dd></dl><div class="wizard-actions"><button class="btn" type="button" data-native-step-action="next">下一步：安装组件</button></div></section>
<section class="wizard-step-card" data-native-step="install"><div class="wizard-step-head"><span class="wizard-step-index">2</span><h2 style="margin:0">安装组件</h2></div><p class="small">下载并校验官方 uv、AstrBot wheel、SnowLuma Windows lite 和 Node.js，然后安装 Python/AstrBot 并生成 OneBot 配置。</p><div class="progress-wrap"><div class="progress-bar" id="wiz-progress-bar"></div></div><div class="statusline" id="wiz-install-status">等待开始。</div><div class="wizard-actions"><button class="btn" type="button" data-native-step-action="prev">上一步</button><button id="wiz-install-btn" class="btn primary" type="button">开始一键安装</button><button class="btn" type="button" data-native-step-action="next">下一步：配置</button></div></section>
<section class="wizard-step-card" data-native-step="config"><div class="wizard-step-head"><span class="wizard-step-index">3</span><h2 style="margin:0">配置与启动</h2></div><p class="small">安装完成后，启动 AstrBot 与 SnowLuma 本地进程，并检查 health/OneBot TCP 监听。</p><dl class="wizard-kv"><dt>Native 数据目录</dt><dd id="wiz-root">…</dd><dt>OneBot URL</dt><dd id="wiz-onebot">…</dd><dt>当前服务</dt><dd id="wiz-runtime">…</dd></dl><div class="wizard-actions"><button class="btn" type="button" data-native-step-action="prev">上一步</button><button id="wiz-start-btn" class="btn primary" type="button">启动 Native 服务</button><button class="btn danger" id="wiz-stop-btn" type="button">停止</button><button class="btn" type="button" data-native-step-action="next">下一步：人工验证</button></div></section>
<section class="wizard-step-card" data-native-step="done"><div class="wizard-step-head"><span class="wizard-step-index">4</span><h2 style="margin:0">完成与人工验证</h2></div><div class="manual">部署完成不等于 QQ 登录完成。请在本机官方 NTQQ 窗口人工完成扫码/设备/短信/滑块验证；在 SnowLuma WebUI 人工接受 EULA/PRIVACY 并完成登录。程序不会伪造这些步骤。</div><dl class="wizard-kv"><dt>NTQQ</dt><dd id="wiz-done-ntqq">…</dd><dt>服务状态</dt><dd id="wiz-done-runtime">…</dd></dl><div class="wizard-actions"><button class="btn" type="button" data-native-step-action="prev">上一步</button><button class="btn" type="button" id="wiz-open-qq-btn">打开本机 NTQQ</button><button class="btn" id="wiz-open-logs-btn" type="button">打开日志目录</button></div></section>
</section>
</main>
<div id="toast"></div>

<script>
let installPoller = null;
let nativeReady = false;
let nativeReadyTimer = null;
function getApi(){
  try {
    const bridge = window.pywebview;
    const candidate = bridge && bridge.api;
    return candidate && typeof candidate === 'object' ? candidate : null;
  } catch (error) { return null; }
}
function setConnection(text, tone='warn'){
  const el = t('native-connection');
  if (!el) return;
  el.textContent = text;
  el.className = 'pill ' + tone;
}
async function callApi(method, ...args){
  const api = getApi();
  if (!api || typeof api[method] !== 'function') {
    setConnection('Native 服务未连接', 'bad');
    const error = new Error('Native API 尚未就绪：' + method);
    error.code = 'NATIVE_API_NOT_READY';
    throw error;
  }
  nativeReady = true;
  if (nativeReadyTimer) { clearTimeout(nativeReadyTimer); nativeReadyTimer = null; }
  setConnection('Native 服务已连接', 'ok');
  try { return await api[method](...args); }
  catch (error) { setConnection('Native 服务调用失败', 'bad'); throw error; }
}
function connectionFailureText(error){
  const suffix = error && error.message ? error.message : String(error || '未知错误');
  return '正在连接 Native 服务…\n\n暂时无法调用本地服务：' + suffix + '\n请保留本窗口，等待 pywebviewready；若持续失败，请点击“打开日志目录”反馈日志。';
}
window.addEventListener('pywebviewready', () => {
  setConnection('Native 服务已连接', 'ok');
  nativeReady = true;
  if (nativeReadyTimer) { clearTimeout(nativeReadyTimer); nativeReadyTimer = null; }
  refreshState().then(refreshLogs);
});
nativeReadyTimer = setTimeout(() => {
  if (getApi()) return;
  setConnection('无法连接 Native 服务', 'bad');
  const box = t('logbox');
  if (box) box.textContent = '正在连接 Native 服务…\n\n超时：window.pywebview.api 尚未注入。\n请保持窗口打开并查看诊断日志；可点击“打开日志目录”。';
}, 5000);

let nativeState = {};
let currentNativeView = 'console';
let currentWizardStep = 'env';
function t(id){return document.getElementById(id)}
function setText(id,text,cls){const e=t(id);e.textContent=text;if(cls)e.className='value '+cls}
function toast(text){const e=t('toast');e.textContent=text;e.style.display='block';clearTimeout(window.__toast);window.__toast=setTimeout(()=>e.style.display='none',4500)}
async function copyLogs(){try{const ok=await callApi('copy_logs');toast(ok?'日志已复制':'复制失败')}catch(e){toast('复制失败: '+e)}}
async function openLogs(){try{await callApi('open_log_folder')}catch(e){toast('打开失败: '+e)}}
async function refreshLogs(){try{t('logbox').textContent=await callApi('get_logs')}catch(e){const box=t('logbox');if(box)box.textContent='读取日志失败: '+(e&&e.message?e.message:e)+'\n请点击“打开日志目录”查看本地日志。';setConnection('日志读取失败，可查看日志目录','bad')}}

function deployedEnv(){const e=(nativeState&&nativeState.environment)||{};return !!(e.astrbot_installed&&e.snowluma_installed&&e.node);}
function updateWizardLock(){const locked=deployedEnv();const select=t('native-wizard-step-select');const note=t('native-wizard-lock-note');if(!select||!note)return;Array.from(select.options||[]).forEach((option)=>{option.disabled=locked&&option.value!=='done'});note.hidden=!locked;if(locked&&currentWizardStep!=='done')currentWizardStep='done';select.value=currentWizardStep;document.querySelectorAll('[data-native-step]').forEach((panel)=>{panel.classList.toggle('is-active',panel.dataset.nativeStep===currentWizardStep)});const e=(nativeState&&nativeState.environment)||{};t('wiz-os').textContent=(e.os||'')+' / '+(e.arch||'');t('wiz-ntqq').textContent=e.ntqq||'未检测到';t('wiz-astrbot').textContent=e.astrbot_installed?'已安装':'未安装';t('wiz-snowluma').textContent=e.snowluma_installed?'已安装':'未安装';t('wiz-root').textContent=(nativeState&&nativeState.root)||'';t('wiz-onebot').textContent=(nativeState&&nativeState.onebot_url)||'';t('wiz-runtime').textContent=(nativeState&&nativeState.runtime_text)||'';t('wiz-done-ntqq').textContent=e.ntqq||'未检测到';t('wiz-done-runtime').textContent=(nativeState&&nativeState.runtime_text)||'';t('native-wizard-progress-text').textContent=locked?'部署完成：前三个步骤已锁定，后续只能查看完成与人工验证。':'可随时用下拉菜单切换步骤。';}
function setWizardStep(step){const locked=deployedEnv();if(locked&&step!=='done'){toast('机器人组件已部署，前三步已锁定，只能进入完成与人工验证。');step='done';}currentWizardStep=step;updateWizardLock();}
function switchNativeView(view){currentNativeView=view;t('native-view-console').hidden=view!=='console';t('native-view-wizard').hidden=view!=='wizard';document.querySelectorAll('[data-native-nav]').forEach((button)=>{button.setAttribute('aria-current',button.dataset.nativeNav===view?'page':'false')});if(view==='wizard')setWizardStep(deployedEnv()?'done':'env');}
async function refreshState(){try{const s=await callApi('get_state'); nativeState=s; const e=s.environment||{}; setText('ntqq',e.ntqq?'已找到':'未找到',e.ntqq?'ok':'bad'); setText('astrbot',e.astrbot_installed?'已安装':'未安装',e.astrbot_installed?'ok':'warn'); setText('snowluma',e.snowluma_installed?'已安装':'未安装',e.snowluma_installed?'ok':'warn'); setText('node',e.node||'未找到',e.node?'ok':'warn'); t('mode-pill').textContent=s.bind_host||'127.0.0.1'; t('run-status').textContent=s.runtime_text||'AstrBot/SnowLuma 未启动'; updateWizardLock();}catch(e){toast('状态读取失败: '+e)}}
function showInstall(s){const p=Number(s.percent||0);t('progress-bar').style.width=p+'%';t('install-status').textContent=(s.message||'')+(s.error?' · '+s.error:'');if(t('wiz-progress-bar'))t('wiz-progress-bar').style.width=p+'%';if(t('wiz-install-status'))t('wiz-install-status').textContent=(s.message||'')+(s.error?' · '+s.error:'');if(s.active){t('install-btn').disabled=true;if(t('wiz-install-btn'))t('wiz-install-btn').disabled=true}else{t('install-btn').disabled=false;if(t('wiz-install-btn'))t('wiz-install-btn').disabled=false;if(installPoller){clearInterval(installPoller);installPoller=null}}}
async function pollInstall(){try{const s=await callApi('get_install_status');showInstall(s);if(!s.active){await refreshState();await refreshLogs()}}catch(e){t('install-status').textContent='读取安装状态失败: '+e}}
async function install(){try{const r=await callApi('one_click_install');if(!r.started){toast(r.message||'无法开始安装');return}t('install-btn').disabled=true;if(t('wiz-install-btn'))t('wiz-install-btn').disabled=true;t('install-status').textContent='正在安装，请保持窗口打开…';if(t('wiz-install-status'))t('wiz-install-status').textContent='正在安装，请保持窗口打开…';if(!installPoller)installPoller=setInterval(pollInstall,900)}catch(e){toast('安装启动失败: '+e)}}
async function startServices(){try{const r=await callApi('start_services');toast(r.message||'启动请求已提交');setTimeout(refreshState,1200)}catch(e){toast('启动失败: '+e)}}
async function stopServices(){try{const r=await callApi('stop_services');toast(r.message||'停止请求已提交');setTimeout(refreshState,500)}catch(e){toast('停止失败: '+e)}}
async function openQQ(){try{const r=await callApi('open_qq');toast(r.message||'已打开 NTQQ')}catch(e){toast('打开 NTQQ 失败: '+e)}}
document.querySelectorAll('[data-native-nav]').forEach((button)=>{button.addEventListener('click',()=>switchNativeView(button.dataset.nativeNav))});t('native-wizard-step-select').addEventListener('change',()=>setWizardStep(t('native-wizard-step-select').value));t('wiz-install-btn').addEventListener('click',install);t('wiz-start-btn').addEventListener('click',startServices);t('wiz-stop-btn').addEventListener('click',stopServices);t('wiz-open-qq-btn').addEventListener('click',openQQ);t('wiz-open-logs-btn').addEventListener('click',openLogs);document.querySelectorAll('[data-native-step-action]').forEach((button)=>{button.addEventListener('click',()=>{const order=['env','install','config','done'];let index=order.indexOf(currentWizardStep);index+=(button.dataset.nativeStepAction==='next'?1:-1);index=Math.max(0,Math.min(order.length-1,index));setWizardStep(order[index])})});t('install-btn').addEventListener('click',install);t('refresh-btn').addEventListener('click',refreshState);t('refresh2-btn').addEventListener('click',refreshState);t('start-btn').addEventListener('click',startServices);t('stop-btn').addEventListener('click',stopServices);t('qq-btn').addEventListener('click',openQQ);t('copy-logs-btn').addEventListener('click',copyLogs);t('open-logs-btn').addEventListener('click',openLogs);t('refresh-logs-btn').addEventListener('click',refreshLogs);
window.__nativeTest = {getApi, callApi, refreshState, refreshLogs, install};
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
            "onebot_url": str(cfg.get("onebot_url") or ""),
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
