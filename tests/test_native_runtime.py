"""Tests for the Windows Native POC runtime/process manager."""

import json
import os
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

from windows import native_runtime


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class NativeRuntimeConfigTests(unittest.TestCase):
    def test_defaults_are_loopback_and_native_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "native"
            cfg = native_runtime.load_config(root)
            self.assertEqual(cfg["bind_host"], "127.0.0.1")
            self.assertTrue(cfg["onebot_url"].startswith("ws://127.0.0.1:"))
            self.assertEqual(cfg["astrbot_root"], str(root.resolve() / "astrbot"))
            self.assertEqual(cfg["mode"], "native-poc")
            self.assertTrue(cfg["onebot_token"])

    def test_config_round_trip_and_command_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "native"
            cfg = native_runtime.load_config(root)
            cfg["astrbot_command"] = [sys.executable, "-c", "import time; time.sleep(1)"]
            cfg["snowluma_dir"] = str((root / "snowluma").resolve())
            native_runtime.save_config(root, cfg)
            loaded = native_runtime.load_config(root)
            self.assertEqual(loaded["astrbot_command"], cfg["astrbot_command"])
            self.assertEqual(loaded["onebot_token"], cfg["onebot_token"])
            self.assertEqual(native_runtime.parse_command('"C:\\Program Files\\x.exe" run'), ["C:\\Program Files\\x.exe", "run"])

    def test_port_probe_detects_bound_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            port = int(sock.getsockname()[1])
            self.assertFalse(native_runtime.is_port_free(port))

    def test_environment_blockers_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "native"
            cfg = native_runtime.load_config(root)
            checks = native_runtime.check_prerequisites(root, cfg)
            missing = native_runtime.blockers(checks)
            self.assertTrue(any(item.startswith("astrbot:") for item in missing))
            self.assertTrue(any(item.startswith("snowluma:") for item in missing))


class NativeOneBotConfigTests(unittest.TestCase):
    def test_snowluma_runtime_port_overrides_configured_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "native"
            snowluma = Path(tmp) / "snowluma"
            (snowluma / "config").mkdir(parents=True)
            (snowluma / "config" / "runtime.json").write_text(
                json.dumps({"webuiPort": 5099}), encoding="utf-8"
            )
            cfg = native_runtime.load_config(root)
            cfg["snowluma_dir"] = str(snowluma)
            cfg["snowluma_webui_port"] = 5099
            self.assertEqual(native_runtime.snowluma_effective_webui_port(cfg), 5099)
            cfg["snowluma_webui_port"] = 15099
            self.assertEqual(native_runtime.snowluma_effective_webui_port(cfg), 5099)

    def test_writer_uses_loopback_and_disables_sl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "native"
            snowluma = Path(tmp) / "snowluma"
            (snowluma / "config").mkdir(parents=True)
            existing = snowluma / "config" / "onebot.json"
            existing.write_text(
                json.dumps({"custom": {"keep": True}, "networks": {}, "statusCommand": {"trigger": "#sl"}}),
                encoding="utf-8",
            )
            cfg = native_runtime.load_config(root)
            cfg["snowluma_dir"] = str(snowluma)
            cfg["onebot_url"] = "ws://127.0.0.1:6199/ws"
            cfg["onebot_token"] = "test-token"
            result = native_runtime.write_snowluma_onebot_config(root, cfg)
            payload = json.loads(existing.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertEqual(payload["custom"], {"keep": True})
            client = payload["networks"]["wsClients"][0]
            self.assertEqual(client["url"], "ws://127.0.0.1:6199/ws")
            self.assertEqual(client["accessToken"], "test-token")
            self.assertEqual(client["role"], "Universal")
            self.assertFalse(payload["statusCommand"]["enabled"])
            self.assertEqual(payload["statusCommand"]["trigger"], "#sl")


class NativeProcessLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "native"
        self.snowluma = Path(self.tmp.name) / "snowluma"
        self.snowluma.mkdir()
        self.ntqq = Path(self.tmp.name) / "QQ.exe"
        self.ntqq.write_text("fake NTQQ test placeholder", encoding="utf-8")
        self.cfg = native_runtime.load_config(self.root)
        self.cfg.update(
            {
                "ntqq_path": str(self.ntqq),
                "astrbot_command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "snowluma_command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "snowluma_dir": str(self.snowluma),
                "astrbot_webui_port": _free_port(),
                "astrbot_onebot_port": _free_port(),
                "snowluma_webui_port": _free_port(),
            }
        )
        # Ensure three distinct free ports.
        used = set()
        for field in ("astrbot_webui_port", "astrbot_onebot_port", "snowluma_webui_port"):
            while self.cfg[field] in used:
                self.cfg[field] = _free_port()
            used.add(self.cfg[field])
        native_runtime.save_config(self.root, self.cfg)

    def tearDown(self):
        try:
            native_runtime.stop_native(self.root)
        except Exception:
            pass
        self.tmp.cleanup()

    def test_start_status_logs_and_stop_real_fake_processes(self):
        cfg = native_runtime.load_config(self.root)
        result = native_runtime.start_native(self.root, cfg, enforce_windows=False)
        self.assertTrue(result["ok"])
        self.assertTrue(native_runtime.service_alive(self.root, "astrbot"))
        self.assertTrue(native_runtime.service_alive(self.root, "snowluma"))
        onebot = Path(result["onebot_config"]["path"])
        self.assertTrue(onebot.is_file())
        self.assertIn("ws://127.0.0.1:", onebot.read_text(encoding="utf-8"))
        status = native_runtime.status_payload(self.root, native_runtime.load_config(self.root))
        self.assertTrue(status["services"]["astrbot"]["running"])
        self.assertTrue(status["services"]["snowluma"]["running"])
        self.assertTrue(status["no_vnc_used"])
        logs = native_runtime.native_logs(self.root, "all", 20)
        self.assertEqual(set(logs), {"astrbot", "snowluma"})
        stopped = native_runtime.stop_native(self.root)
        self.assertTrue(stopped["ok"])
        self.assertFalse(native_runtime.service_alive(self.root, "astrbot"))
        self.assertFalse(native_runtime.service_alive(self.root, "snowluma"))

    def test_missing_component_blocks_start_without_partial_launch(self):
        cfg = native_runtime.load_config(self.root)
        cfg["astrbot_command"] = []
        cfg["snowluma_command"] = []
        cfg["snowluma_dir"] = str(Path(self.tmp.name) / "missing-snowluma")
        native_runtime.save_config(self.root, cfg)
        with self.assertRaises(native_runtime.NativeBlocked) as raised:
            native_runtime.start_native(self.root, native_runtime.load_config(self.root))
        self.assertTrue(any("astrbot:" in item for item in raised.exception.blockers))
        self.assertFalse(native_runtime.service_alive(self.root, "astrbot"))
        self.assertFalse(native_runtime.service_alive(self.root, "snowluma"))


if __name__ == "__main__":
    unittest.main()
