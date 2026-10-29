"""Unit tests for the standalone Windows launcher (runnable on any OS)."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from qqbot_studio.studio import StudioManager
from windows import launcher


class WindowsLauncherArgumentTests(unittest.TestCase):
    def setUp(self):
        self.parser = launcher.build_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.data_dir)
        self.assertIsNone(args.new_instance)
        self.assertFalse(args.status)
        self.assertFalse(args.stop)
        self.assertIsNone(args.logs)

    def test_new_instance_optional_name(self):
        self.assertEqual(self.parser.parse_args(["--new-instance"]).new_instance, "")
        self.assertEqual(
            self.parser.parse_args(["--new-instance", "测试 机器人"]).new_instance,
            "测试 机器人",
        )

    def test_logs_optional_line_count(self):
        self.assertEqual(self.parser.parse_args(["--logs"]).logs, 80)
        self.assertEqual(self.parser.parse_args(["--logs", "250"]).logs, 250)

    def test_assistant_flag_opens_standalone_page(self):
        args = self.parser.parse_args(["--assistant"])
        self.assertTrue(args.assistant)
        self.assertIsNone(args.new_instance)

    def test_assistant_and_new_instance_targets_conflict(self):
        args = self.parser.parse_args(["--assistant", "--new-instance", "bot"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            launcher._validate_action_combination(self.parser, args)
        self.assertEqual(raised.exception.code, 2)

    def test_terminal_actions_are_mutually_exclusive(self):
        args = self.parser.parse_args(["--status", "--stop"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            launcher._validate_action_combination(self.parser, args)
        self.assertEqual(raised.exception.code, 2)


class WindowsLauncherConfigTests(unittest.TestCase):
    def test_noninteractive_first_run_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio = StudioManager(tmp)
            settings = launcher.configure_studio(
                studio,
                ip="127.0.0.1",
                port=9123,
                public_host="127.0.0.1",
                non_interactive=True,
                print_func=lambda _: None,
            )
            self.assertEqual(settings["bind_host"], "127.0.0.1")
            self.assertEqual(settings["bind_port"], 9123)
            self.assertEqual(settings["public_host"], "127.0.0.1")
            raw = json.loads((Path(tmp) / "studio.json").read_text(encoding="utf-8"))
            self.assertTrue(raw["first_run_complete"])

    def test_interactive_first_run_uses_prompt_answers(self):
        answers = iter(["0.0.0.0", "9876", "bot.example.test"])
        with tempfile.TemporaryDirectory() as tmp:
            studio = StudioManager(tmp)
            settings = launcher.configure_studio(
                studio,
                non_interactive=False,
                input_func=lambda _: next(answers),
                print_func=lambda _: None,
            )
            self.assertEqual(settings["bind_host"], "0.0.0.0")
            self.assertEqual(settings["bind_port"], 9876)
            self.assertEqual(settings["public_host"], "bot.example.test")

    def test_loopback_bind_defaults_public_host_to_loopback(self):
        self.assertEqual(launcher._default_public_for_bind("127.0.0.1"), "127.0.0.1")
        self.assertEqual(launcher._default_public_for_bind("localhost"), "127.0.0.1")

    def test_public_host_validation(self):
        self.assertEqual(launcher._normalize_public_host("bot.example.test"), "bot.example.test")
        self.assertEqual(launcher._normalize_public_host("[::1]"), "[::1]")
        for bad in ("http://bot.example.test", "0.0.0.0", "bot.example.test:8765", "a b"):
            with self.assertRaises(ValueError):
                launcher._normalize_public_host(bad)


class WindowsLauncherServiceContractTests(unittest.TestCase):
    def test_server_command_uses_hidden_management_mode(self):
        command = launcher._server_command(Path("C:/data"), "0.0.0.0", 8765)
        self.assertIn("--serve-management", command)
        self.assertIn("--data-dir", command)
        self.assertIn("--ip", command)
        self.assertIn("--port", command)
        self.assertIn("--no-open", command)

    def test_health_url_handles_wildcard_and_ipv6(self):
        self.assertEqual(
            launcher._health_url("0.0.0.0", 8765),
            "http://127.0.0.1:8765/healthz",
        )
        self.assertEqual(
            launcher._health_url("::", 8765),
            "http://[::1]:8765/healthz",
        )

    def test_status_without_service_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio = StudioManager(tmp)
            settings = studio.update_network(
                bind_host="127.0.0.1", bind_port=18999, public_host="127.0.0.1"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = launcher.print_status(studio, settings)
            self.assertEqual(result, 1)
            self.assertIn("Healthy        : no", output.getvalue())

    def test_logs_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output):
                result = launcher.print_logs(Path(tmp), 10)
            self.assertEqual(result, 1)
            self.assertIn("(missing)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
