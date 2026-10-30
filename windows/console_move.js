(function () {
  'use strict';

  var token = window.QB_TOKEN || '';
  var panel = null;
  var input = null;
  var confirmBox = null;
  var submit = null;
  var statusBox = null;
  var reloadButton = null;
  var polling = false;
  var waitedForRestart = false;

  function apiFetch(path, options) {
    var opts = options || {};
    opts.headers = Object.assign({}, opts.headers || {}, { 'X-QB-Token': token });
    return fetch(path, opts).then(function (response) {
      return response.text().then(function (text) {
        var payload = {};
        try { payload = text ? JSON.parse(text) : {}; } catch (e) { payload = { ok: false, message: text || '响应格式异常' }; }
        if (!response.ok || payload.ok === false) {
          throw new Error(payload.message || ('HTTP ' + response.status));
        }
        return payload;
      });
    });
  }

  function setStatus(message, kind) {
    if (!statusBox) return;
    statusBox.textContent = message || '';
    statusBox.dataset.kind = kind || '';
    statusBox.hidden = !message;
  }

  function setBusy(busy) {
    if (!submit) return;
    submit.disabled = busy;
    submit.textContent = busy ? '迁移中…' : '开始安全迁移';
    if (input) input.disabled = busy;
    if (confirmBox) confirmBox.disabled = busy;
  }

  function showReload() {
    if (!reloadButton) return;
    reloadButton.hidden = false;
    reloadButton.onclick = function () { window.location.reload(); };
  }

  function pollStatus() {
    if (!polling) return;
    var healthUrl = '/healthz?_=' + Date.now();
    fetch(healthUrl, { cache: 'no-store' })
      .then(function (response) { return response.ok; })
      .catch(function () { return false; })
      .then(function (healthy) {
        if (!healthy) {
          waitedForRestart = true;
          setStatus('管理服务正在停止/迁移，等待新服务恢复…', 'busy');
          window.setTimeout(pollStatus, 2000);
          return;
        }
        apiFetch('/api/system/move-data/status', { cache: 'no-store' })
          .then(function (status) {
            if (status.status === 'completed') {
              polling = false;
              setBusy(false);
              setStatus('迁移完成：' + (status.target || '') + '。服务正在从新目录运行。', 'ok');
              showReload();
              return;
            }
            if (status.status === 'failed' || status.status === 'restart_failed') {
              polling = false;
              setBusy(false);
              setStatus((status.message || '迁移失败') + (status.error ? ' ' + status.error : ''), 'error');
              return;
            }
            setStatus(status.message || '迁移任务处理中…', 'busy');
            window.setTimeout(pollStatus, 2000);
          })
          .catch(function () {
            if (waitedForRestart) {
              // A restarted server issues a new random token. Reload once to
              // obtain the new token and read the final status from the new
              // data directory (which is either target on success or source on
              // failed-rollback).
              setStatus('管理服务已恢复；正在刷新状态…', 'busy');
              window.setTimeout(function () { window.location.reload(); }, 1200);
              return;
            }
            setStatus('正在等待管理服务恢复或状态接口就绪…', 'busy');
            window.setTimeout(pollStatus, 2000);
          });
      });
  }

  function refreshCurrentStatus() {
    apiFetch('/api/system/move-data/status', { cache: 'no-store' })
      .then(function (status) {
        var current = document.getElementById('windows-data-current-dir');
        if (current) current.textContent = status.current_data_dir || '未知';
        var pointer = document.getElementById('windows-data-pointer');
        if (pointer) pointer.textContent = status.pointer_data_dir || status.pointer_path || '未设置';
        if (status.status === 'scheduled' || status.status === 'running') {
          setBusy(true);
          polling = true;
          setStatus(status.message || '迁移任务处理中…', 'busy');
          pollStatus();
        } else if (status.status === 'completed') {
          setStatus('最近一次迁移已完成：' + (status.target || ''), 'ok');
          showReload();
        } else if (status.status === 'failed' || status.status === 'restart_failed') {
          setStatus((status.message || '迁移失败') + (status.error ? ' ' + status.error : ''), 'error');
        }
      })
      .catch(function (error) {
        setStatus('无法读取存储迁移状态：' + error.message, 'error');
      });
  }

  function buildPanel() {
    var main = document.getElementById('console-main');
    if (!main || document.getElementById('windows-data-folder-panel')) return;
    var anchor = document.getElementById('create-instance-panel');
    var section = document.createElement('section');
    section.id = 'windows-data-folder-panel';
    section.className = 'create-instance-panel windows-storage-panel';
    section.setAttribute('aria-labelledby', 'windows-data-folder-title');
    section.innerHTML = '' +
      '<div class="create-instance-copy">' +
      '  <span class="create-instance-icon" aria-hidden="true">📁</span>' +
      '  <div>' +
      '    <h2 id="windows-data-folder-title">存储文件夹</h2>' +
      '    <p>把管理服务、实例、日志和 AI 助手数据安全迁移到本机固定 NTFS 磁盘上的另一个目录。' +
      '      浏览器因安全限制不能获取本地绝对路径，请在下面粘贴/输入完整路径；也可以使用高级入口 <code>--move-data</code>。</p>' +
      '    <p class="field-hint">当前数据目录：<code id="windows-data-current-dir">读取中…</code><br>' +
      '      迁移指针：<code id="windows-data-pointer">读取中…</code></p>' +
      '  </div>' +
      '</div>' +
      '<form id="windows-data-folder-form" class="create-instance-form" novalidate>' +
      '  <label for="windows-data-target">新目录绝对路径 <span class="required-mark" aria-hidden="true">*</span></label>' +
      '  <div class="create-instance-input-row">' +
      '    <input id="windows-data-target" name="target" type="text" maxlength="1024" autocomplete="off" spellcheck="false" placeholder="例如：D:\\QQBotStudioData" aria-describedby="windows-data-help">' +
      '    <button id="windows-data-submit" class="btn btn-primary" type="submit">开始安全迁移</button>' +
      '  </div>' +
      '  <p id="windows-data-help" class="field-hint">目标必须不存在或为空；拒绝 WSL、OneDrive、UNC/网络共享、可移动/未知盘。旧目录会保留；迁移期间服务和容器会短暂停止。</p>' +
      '  <label class="field-hint"><input id="windows-data-confirm" type="checkbox"> 我已备份旧数据，并确认停止管理服务和相关 Compose 容器</label>' +
      '  <p id="windows-data-status" class="field-hint" role="status" aria-live="polite" hidden></p>' +
      '  <button id="windows-data-reload" class="btn btn-secondary" type="button" hidden>刷新控制台</button>' +
      '</form>';
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(section, anchor);
    else main.appendChild(section);

    var headerActions = document.querySelector('.console-header-actions');
    if (headerActions && !document.getElementById('windows-data-open')) {
      var button = document.createElement('button');
      button.id = 'windows-data-open';
      button.type = 'button';
      button.className = 'console-header-btn';
      button.textContent = '存储文件夹';
      button.onclick = function () {
        section.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (input) input.focus();
      };
      var before = headerActions.querySelector('.console-create-button');
      headerActions.insertBefore(button, before || null);
    }

    input = document.getElementById('windows-data-target');
    confirmBox = document.getElementById('windows-data-confirm');
    submit = document.getElementById('windows-data-submit');
    statusBox = document.getElementById('windows-data-status');
    reloadButton = document.getElementById('windows-data-reload');
    document.getElementById('windows-data-folder-form').addEventListener('submit', function (event) {
      event.preventDefault();
      var target = (input.value || '').trim();
      if (!target) { setStatus('请输入新的数据目录绝对路径。', 'error'); return; }
      if (!confirmBox.checked) { setStatus('请先勾选备份/停止确认。', 'error'); return; }
      setBusy(true);
      setStatus('正在校验目标并排队迁移…', 'busy');
      apiFetch('/api/system/move-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: target, confirm: true })
      }).then(function (result) {
        polling = true;
        waitedForRestart = false;
        setStatus(result.message || '迁移任务已启动。', 'busy');
        window.setTimeout(pollStatus, 1000);
      }).catch(function (error) {
        setBusy(false);
        setStatus(error.message, 'error');
      });
    });
    refreshCurrentStatus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildPanel);
  } else {
    buildPanel();
  }
})();
