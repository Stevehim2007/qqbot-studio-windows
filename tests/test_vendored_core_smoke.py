"""Smoke checks for the vendored Python/UI core."""

import tempfile
import unittest
from pathlib import Path

from qqbot_studio import __version__ as core_version
from qqbot_studio.configgen import _compose_yaml
from qqbot_studio.studio import StudioManager

ROOT = Path(__file__).resolve().parents[1]


class VendoredCoreSmokeTests(unittest.TestCase):
    def test_core_version_and_static_ui_are_present(self):
        self.assertTrue(core_version)
        self.assertTrue((ROOT / "qqbot_studio" / "static" / "index.html").is_file())
        self.assertTrue((ROOT / "qqbot_studio" / "static" / "console.html").is_file())
        self.assertTrue((ROOT / "qqbot_studio" / "static" / "assistant.html").is_file())
        self.assertTrue((ROOT / "qqbot_studio" / "assistant_ext.py").is_file())
        self.assertTrue((ROOT / "plugins" / "qqbot_enhancer" / "main.py").is_file())

    def test_instance_creation_uses_independent_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio = StudioManager(tmp)
            studio.update_network(
                bind_host="127.0.0.1", bind_port=8765, public_host="127.0.0.1"
            )
            first = studio.create_instance("独立 Windows 测试实例")
            second = studio.create_instance("second")
            self.assertEqual(first["id"], "bot-1")
            self.assertEqual(second["id"], "bot-2")
            self.assertTrue((Path(tmp) / "instances" / "bot-1" / "instance.json").is_file())

    def test_windows_compose_omits_linux_localtime(self):
        compose = _compose_yaml(include_localtime=False)
        self.assertNotIn("/etc/localtime", compose)
        self.assertIn("TZ: Asia/Shanghai", compose)


if __name__ == "__main__":
    unittest.main()
