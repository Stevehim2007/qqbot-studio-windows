"""v1.0.0 Windows Desktop App + Linux 4.0.1 sync contracts."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "windows"


class V1ReleaseContractTests(unittest.TestCase):
    def test_versions_and_upstream_snapshot(self) -> None:
        self.assertEqual((ROOT / "VERSION").read_text(encoding="ascii").strip(), "1.0.0")
        self.assertEqual((ROOT / ".upstream-commit").read_text(encoding="ascii").strip(), "790d6c0bfc1aa1019934fa348ab9ad847ae8685b")
        init = (ROOT / "qqbot_studio" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn('__version__ = "4.0.1"', init)
        upstream = (ROOT / "UPSTREAM.md").read_text(encoding="utf-8")
        for marker in ("790d6c0bfc1aa1019934fa348ab9ad847ae8685b", "v4.0.1", "4.0.1", "2.1.0"):
            self.assertIn(marker, upstream)
        metadata = (ROOT / "plugins" / "qqbot_enhancer" / "metadata.yaml").read_text(encoding="utf-8")
        self.assertIn("version: 2.1.0", metadata)
        self.assertIn('LAUNCHER_VERSION = "1.0.0"', (WINDOWS / "launcher.py").read_text(encoding="utf-8"))
        native_launcher = (WINDOWS / "native_launcher.py").read_text(encoding="utf-8")
        self.assertIn('NATIVE_LAUNCHER_VERSION = "1.0.0"', native_launcher)
        self.assertIn("if args.guide:", native_launcher)
        self.assertLess(native_launcher.index("if args.guide:"), native_launcher.index("from windows import native_app"))

    def test_desktop_app_navigation_and_no_external_browser(self) -> None:
        launcher = (WINDOWS / "launcher.py").read_text(encoding="utf-8")
        self.assertNotIn("import webbrowser", launcher)
        self.assertNotIn("webbrowser.open", launcher)
        self.assertIn("app_shell.run_app_window", launcher)
        self.assertIn("http://127.0.0.1:{port}", launcher)
        shell = (WINDOWS / "app_shell.py").read_text(encoding="utf-8")
        for marker in (
            "QQ Bot Studio App 导航",
            "控制台",
            "向导",
            "data-qb-nav=\"console\"",
            "data-qb-nav=\"wizard\"",
            "window.location.assign",
            "diagnostics panel injected",
            "show_error_window",
        ):
            self.assertIn(marker, shell)
        self.assertIn("webview.start(gui=\"edgechromium\"", shell)

    def test_task96_wizard_dropdown_and_lock_are_bundled(self) -> None:
        html = (ROOT / "qqbot_studio" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "qqbot_studio" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "qqbot_studio" / "static" / "styles.css").read_text(encoding="utf-8")
        for marker in ("wizard-step-select", "wizard-step-lock-note", "1. 检查环境", "4. 完成与运行"):
            self.assertIn(marker, html)
        for marker in ("deploymentStepsLocked", "return step === 'done'", "app.jobCompleted", "wizard-step-select"):
            self.assertIn(marker, js)
        self.assertIn(".wizard-step-select", css)

    def test_schema_and_prompt_template_contract(self) -> None:
        schema = json.loads((ROOT / "plugins" / "qqbot_enhancer" / "_conf_schema.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(schema), 191)
        for marker in ("prompt_profiles", "prompt_profile_active_id", "group_personas", "food_enabled"):
            self.assertIn(marker, schema)
        console = (ROOT / "qqbot_studio" / "static" / "console.js").read_text(encoding="utf-8")
        for marker in ("提示词模板库", "pinned"):
            self.assertIn(marker, console)
        api_doc = (ROOT / "docs" / "ui-api-contract-v2.md").read_text(encoding="utf-8")
        for marker in ("default_prompt_id", "default_profile"):
            self.assertIn(marker, api_doc)

    def test_native_one_click_install_core_is_preserved(self) -> None:
        setup = (WINDOWS / "native_setup.py").read_text(encoding="utf-8")
        for marker in (
            "ASTRBOT_WHEEL_URL",
            "SNOWLUMA_URL",
            "NODE_URL",
            "UV_URL",
            "expected_sha256",
            "find_ntqq_path",
            "install_all",
            "EULA",
        ):
            self.assertIn(marker, setup)
        native_app = (WINDOWS / "native_app.py").read_text(encoding="utf-8")
        for marker in ("native-app-nav", "native-wizard-step-select", "一键安装/修复", "QQ 扫码"):
            self.assertIn(marker, native_app)


if __name__ == "__main__":
    unittest.main()
