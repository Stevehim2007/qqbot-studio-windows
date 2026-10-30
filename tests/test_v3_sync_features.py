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
        match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
        self.assertIsNotNone(match)
        commit = (ROOT / ".upstream-commit").read_text(encoding="ascii").strip()
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        upstream = (ROOT / "UPSTREAM.md").read_text(encoding="utf-8")
        self.assertIn(commit, upstream)
        self.assertIn(f"qqbot_studio.__version__ == {match.group(1)}", upstream)

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

    def test_plugin_is_1_5_x_and_has_sticker_features(self):
        metadata = (ROOT / "plugins" / "qqbot_enhancer" / "metadata.yaml").read_text(
            encoding="utf-8"
        )
        match = re.search(r"^version:\s*(\S+)", metadata, re.MULTILINE)
        self.assertIsNotNone(match)
        version_tuple = tuple(int(part) for part in match.group(1).split("."))
        self.assertGreaterEqual(version_tuple, (1, 7, 0), match.group(1))
        main = (ROOT / "plugins" / "qqbot_enhancer" / "main.py").read_text(
            encoding="utf-8"
        )
        for marker in (
            "/找图", "/唱歌", "/点歌", "/option", "memory_mode",
            "/收藏表情", "/表情分类", "/表情列表", "/发表情",
            "sticker_ai_select_enabled", "auto_collect_user_sticker_enabled",
        ):
            self.assertIn(marker, main)
        schema = json.loads(
            (ROOT / "plugins" / "qqbot_enhancer" / "_conf_schema.json").read_text(
                encoding="utf-8"
            )
        )
        for field in (
            "user_sticker_reaction_enabled",
            "user_sticker_reaction_probability",
            "collected_sticker_enabled",
            "collected_sticker_use_probability",
            "sticker_ai_select_enabled",
            "sticker_ai_auto_collect_enabled",
            "safe_tools_marker_enabled",
            "auto_collect_user_sticker_enabled",
        ):
            self.assertIn(field, schema)

    def test_v3_7_modular_static_and_plugin_files_are_present(self):
        for relative in (
            "qqbot_studio/contracts.py",
            "qqbot_studio/resource_stats.py",
            "qqbot_studio/static/components/instance-settings.js",
            "qqbot_studio/static/services/api.js",
            "qqbot_studio/static/services/plugin-config.js",
            "plugins/qqbot_enhancer/config.py",
            "plugins/qqbot_enhancer/image_search.py",
            "plugins/qqbot_enhancer/interfaces.py",
            "plugins/qqbot_enhancer/llm.py",
            "plugins/qqbot_enhancer/media.py",
            "plugins/qqbot_enhancer/safe_tools.py",
            "plugins/qqbot_enhancer/songs.py",
            "plugins/qqbot_enhancer/sticker_store.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        server = (ROOT / "qqbot_studio" / "server.py").read_text(encoding="utf-8")
        self.assertIn('path.startswith(("/services/", "/components/"))', server)
        self.assertIn('if path == "/api/assistant/diagnose":', server)
        assistant = (ROOT / "qqbot_studio" / "static" / "assistant.html").read_text(encoding="utf-8")
        self.assertIn('id="diagnose-button"', assistant)
        console = (ROOT / "qqbot_studio" / "static" / "console.html").read_text(encoding="utf-8")
        self.assertIn("instance-settings-modal", console)
        plugin_doc = (ROOT / "docs" / "plugin-qqbot-enhancer.md").read_text(encoding="utf-8")
        for marker in ("安全工具", "AI 自动", "Bing", "相关性"):
            self.assertIn(marker, plugin_doc)

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
        for marker in (
            "自然语言", "本地唱歌", "/option", "memory_mode",
            "/收藏表情", "/表情分类", "/表情列表", "/发表情",
            "sticker_ai_select_enabled", "auto_collect_user_sticker_enabled",
        ):
            self.assertIn(marker, plugin_doc)

    def test_plugin_parameter_config_api_and_ui_are_synced(self):
        server = (ROOT / "qqbot_studio" / "server.py").read_text(encoding="utf-8")
        console_html = (STATIC / "console.html").read_text(encoding="utf-8")
        console_js = (STATIC / "console.js").read_text(encoding="utf-8")
        plugin_config_js = (STATIC / "services" / "plugin-config.js").read_text(
            encoding="utf-8"
        )
        instance_settings_component = (
            STATIC / "components" / "instance-settings.js"
        ).read_text(encoding="utf-8")
        deployer = (ROOT / "qqbot_studio" / "deployer.py").read_text(encoding="utf-8")
        api_doc = (ROOT / "docs" / "ui-api-contract-v2.md").read_text(encoding="utf-8")
        static_combined = "\n".join(
            (console_js, plugin_config_js, instance_settings_component)
        )

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
            "/api/instances/${encodeURIComponent(instanceId)}/plugins/${encodeURIComponent(pluginId)}/config",
        ):
            self.assertIn(marker, static_combined)
        for marker in ("reply_probability", "编辑参数"):
            self.assertIn(marker, console_js)
        self.assertIn("/api/instances/<instance_id>/plugins/<plugin_id>/config", api_doc)
        self.assertIn("reply_probability", api_doc)

    def test_windows_release_version_is_0_5_0(self):
        self.assertEqual((ROOT / "VERSION").read_text(encoding="ascii").strip(), "0.5.0")
        launcher = (ROOT / "windows" / "launcher.py").read_text(encoding="utf-8")
        self.assertIn('LAUNCHER_VERSION = "0.5.0"', launcher)
        native = (ROOT / "windows" / "native_launcher.py").read_text(encoding="utf-8")
        self.assertIn('NATIVE_LAUNCHER_VERSION = "0.5.0"', native)

    def test_upstream_metadata_is_updated(self):
        upstream = (ROOT / "UPSTREAM.md").read_text(encoding="utf-8")
        commit = (ROOT / ".upstream-commit").read_text(encoding="ascii").strip()
        core_match = re.search(
            r'__version__\s*=\s*"([^"]+)"',
            (ROOT / "qqbot_studio" / "__init__.py").read_text(encoding="utf-8"),
        )
        plugin_match = re.search(
            r"^version:\s*(\S+)",
            (ROOT / "plugins" / "qqbot_enhancer" / "metadata.yaml").read_text(
                encoding="utf-8"
            ),
            re.MULTILINE,
        )
        self.assertIsNotNone(core_match)
        self.assertIsNotNone(plugin_match)
        for expected in (
            commit,
            f"v{core_match.group(1)}",
            f"qqbot_studio.__version__ == {core_match.group(1)}",
            f"qqbot_enhancer` {plugin_match.group(1)}",
        ):
            self.assertIn(expected, upstream)


if __name__ == "__main__":
    unittest.main()
