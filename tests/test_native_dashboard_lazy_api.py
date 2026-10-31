"""Mock/browser-contract tests for the Native dashboard lazy pywebview API."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from windows import native_app

ROOT = Path(__file__).resolve().parents[1]


class NativeDashboardLazyApiTests(unittest.TestCase):
    def test_source_uses_lazy_api_and_light_theme(self) -> None:
        source = (ROOT / "windows" / "native_app.py").read_text(encoding="utf-8")
        self.assertNotIn("const api = window.pywebview && window.pywebview.api", source)
        for marker in (
            "function getApi()",
            "window.addEventListener('pywebviewready'",
            "callApi('one_click_install')",
            "callApi('get_logs')",
            "正在连接 Native 服务",
            "v1.0.4 default light theme",
            "user-select:text",
        ):
            self.assertIn(marker, source)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_delayed_pywebview_api_and_ready_refresh(self) -> None:
        html = native_app.native_dashboard_html()
        match = re.search(r"<script>(.*)</script>", html, re.DOTALL)
        self.assertIsNotNone(match)
        script = match.group(1)
        harness = r'''
        const elements = new Map();
        function element(id) {
          if (!elements.has(id)) {
            elements.set(id, {
              id, textContent: '', className: '', style: {}, disabled: false,
              hidden: false, value: '', options: [],
              classList: { toggle() {} }, dataset: {},
              addEventListener(type, handler) { this[type] = handler; },
            });
          }
          return elements.get(id);
        }
        const readyHandlers = [];
        global.document = {
          getElementById: element,
          querySelectorAll: () => [],
          body: {},
        };
        global.window = {
          addEventListener(type, handler) { if (type === 'pywebviewready') readyHandlers.push(handler); },
          setInterval: () => 0,
          clearInterval: () => {},
        };
        global.setTimeout = setTimeout;
        global.clearTimeout = clearTimeout;
        global.setInterval = () => 0;
        global.calls = [];
        '''
        test = r'''
        eval(SCRIPT);
        (async () => {
          const beforeApi = window.__nativeTest.getApi();
          await window.__nativeTest.refreshState();
          await window.__nativeTest.refreshLogs();
          await window.__nativeTest.install();
          const beforeReadyLog = element('logbox').textContent;
          const beforeReadyConnection = element('native-connection').textContent;
          window.pywebview = {api: {
            get_state: async () => {
              calls.push('get_state');
              return {
                root: 'C:\\mock',
                bind_host: '127.0.0.1',
                onebot_url: 'ws://127.0.0.1:6199/ws',
                runtime_text: 'MOCK_RUNTIME',
                environment: {os: 'Windows', arch: 'AMD64', astrbot_installed: true,
                  snowluma_installed: true, node: 'node.exe', ntqq: 'QQ.exe'}
              };
            },
            get_logs: async () => { calls.push('get_logs'); return 'MOCK_LOGS_OK'; },
            get_install_status: async () => ({active: false, percent: 0, message: ''}),
            one_click_install: async () => { calls.push('one_click_install'); return {started: false, message: 'MOCK_INSTALL'}; },
            copy_logs: async () => true,
            open_log_folder: async () => true,
            start_services: async () => ({message: 'started'}),
            stop_services: async () => ({message: 'stopped'}),
            open_qq: async () => ({message: 'qq'}),
          }};
          for (const handler of readyHandlers) handler();
          await new Promise((resolve) => setTimeout(resolve, 30));
          console.log(JSON.stringify({
            beforeApiNull: beforeApi === null,
            beforeReadyLog,
            beforeReadyConnection,
            afterReadyConnection: element('native-connection').textContent,
            log: element('logbox').textContent,
            calls,
          }));
        })().catch((error) => { console.error(error); process.exit(1); });
        '''
        harness_script = harness + "\nconst SCRIPT = " + json.dumps(script) + ";\n" + test
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "native-dashboard-mock.js"
            path.write_text(harness_script, encoding="utf-8")
            result = subprocess.run(
                ["node", str(path)], check=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=20
            )
        data = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(data["beforeApiNull"])
        self.assertIn("读取日志失败", data["beforeReadyLog"])
        self.assertIn("Native 服务未连接", data["beforeReadyConnection"])
        self.assertIn("Native 服务已连接", data["afterReadyConnection"])
        self.assertEqual(data["log"], "MOCK_LOGS_OK")
        self.assertIn("get_state", data["calls"])
        self.assertIn("get_logs", data["calls"])


if __name__ == "__main__":
    unittest.main()
