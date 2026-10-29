"""Regression checks for the upstream v3.3.0 feature sync."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "qqbot_studio" / "static"


class V3SyncFeatureTests(unittest.TestCase):
    def test_core_version_is_synced(self):
        init_text = (ROOT / "qqbot_studio" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn('__version__ = "3.4.0"', init_text)

    def test_assistant_page_exists_and_has_token_placeholder(self):
        path = STATIC / "assistant.html"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn('window.QB_TOKEN = "{{TOKEN}}"', text)
        self.assertIn('id="host-public"', text)
        self.assertIn('id="public-host"', text)
        self.assertIn('id="instance-select"', text)
        self.assertIn("0.0.0.0", text)
        self.assertIn("/api/assistant/config", text)
        self.assertIn("/api/assistant/start", text)
        self.assertIn("/api/assistant/stop", text)
        self.assertNotIn("localStorage", text)
        self.assertNotIn("sessionStorage", text)

    def test_console_links_to_standalone_assistant_and_removed_old_panels(self):
        html = (STATIC / "console.html").read_text(encoding="utf-8")
        js = (STATIC / "console.js").read_text(encoding="utf-8")
        css = (STATIC / "console.css").read_text(encoding="utf-8")
        combined = "\n".join((html, js, css))
        self.assertIn('href="/assistant"', html)
        for old_marker in (
            "assistant-open",
            "assistant-panel",
            "assistant-b-card",
            "使用助手",
        ):
            self.assertNotIn(old_marker, combined)

    def test_console_auto_refresh_is_thirty_minutes(self):
        js = (STATIC / "console.js").read_text(encoding="utf-8")
        self.assertIn("AUTO_REFRESH_INTERVAL_MS = 30 * 60 * 1000", js)
        self.assertNotIn("AUTO_REFRESH_INTERVAL_MS = 8", js)

    def test_server_has_assistant_route_and_graceful_page_loading(self):
        server = (ROOT / "qqbot_studio" / "server.py").read_text(encoding="utf-8")
        self.assertIn('path in ("/assistant", "/assistant.html")', server)
        self.assertIn("self.assistant_html", server)
        self.assertIn("assistant_path = static_dir / \"assistant.html\"", server)

    def test_assistant_extension_supports_public_mode_safely(self):
        text = (ROOT / "qqbot_studio" / "assistant_ext.py").read_text(encoding="utf-8")
        self.assertIn('ASSISTANT_ALLOWED_HOSTS = ("127.0.0.1", "localhost", "::1", "0.0.0.0")', text)
        self.assertIn("_validate_public_host", text)
        self.assertIn("public_host", text)
        self.assertIn("没有可点击的浏览器 URL", text)

    def test_plugin_is_1_4_x(self):
        metadata = (ROOT / "plugins" / "qqbot_enhancer" / "metadata.yaml").read_text(
            encoding="utf-8"
        )
        match = re.search(r"^version:\s*(\S+)", metadata, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertTrue(match.group(1).startswith("1.4."), match.group(1))
        main = (ROOT / "plugins" / "qqbot_enhancer" / "main.py").read_text(
            encoding="utf-8"
        )
        for marker in ("/找图", "/唱歌", "/点歌", "/option", "memory_mode"):
            self.assertIn(marker, main)

    def test_synced_api_and_plugin_docs_cover_new_features(self):
        api = (ROOT / "docs" / "ui-api-contract-v2.md").read_text(encoding="utf-8")
        for marker in (
            "/assistant",
            "/api/assistant/config",
            "/api/assistant/start",
            "public_host",
            "0.0.0.0",
        ):
            self.assertIn(marker, api)
        plugin_doc = (ROOT / "docs" / "plugin-qqbot-enhancer.md").read_text(
            encoding="utf-8"
        )
        for marker in ("自然语言", "本地唱歌", "/option", "memory_mode"):
            self.assertIn(marker, plugin_doc)

    def test_plugin_parameter_config_api_and_ui_are_synced(self):
        server = (ROOT / "qqbot_studio" / "server.py").read_text(encoding="utf-8")
        console_html = (STATIC / "console.html").read_text(encoding="utf-8")
        console_js = (STATIC / "console.js").read_text(encoding="utf-8")
        deployer = (ROOT / "qqbot_studio" / "deployer.py").read_text(encoding="utf-8")
        api_doc = (ROOT / "docs" / "ui-api-contract-v2.md").read_text(encoding="utf-8")

        self.assertIn("get_plugin_config", server)
        self.assertIn("set_plugin_config", server)
        self.assertIn("get_plugin_config", deployer)
        self.assertIn("set_plugin_config", deployer)
        for marker in (
            'id="plugin-config-panel"',
            'id="plugin-config-save"',
            'id="plugin-config-search"',
        ):
            self.assertIn(marker, console_html)
        for marker in (
            "/api/instances/${encodeURIComponent(instance.id)}/plugins/${encodeURIComponent(plugin.id)}/config",
            "reply_probability",
            "编辑参数",
        ):
            self.assertIn(marker, console_js)
        self.assertIn("/api/instances/<instance_id>/plugins/<plugin_id>/config", api_doc)
        self.assertIn("reply_probability", api_doc)

    def test_upstream_metadata_is_updated(self):
        upstream = (ROOT / "UPSTREAM.md").read_text(encoding="utf-8")
        self.assertIn("1e9d4a46b0aba7f89519066693f95b5939c7732e", upstream)
        self.assertIn("3.4.0", upstream)


if __name__ == "__main__":
    unittest.main()
