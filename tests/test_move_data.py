"""Tests for safe Windows data-directory migration helpers."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from windows import launcher


class DataMoveValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "studio.json").write_text('{"bind_host":"127.0.0.1"}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_empty_target_is_accepted(self):
        target = self.root / "target"
        self.assertEqual(
            launcher.validate_move_target(self.source, target),
            target.resolve(),
        )

    def test_non_empty_target_is_rejected_without_merge(self):
        target = self.root / "target"
        target.mkdir()
        (target / "existing.txt").write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be empty"):
            launcher.validate_move_target(self.source, target)

    def test_source_inside_or_containing_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "nested"):
            launcher.validate_move_target(self.source, self.source / "nested")
        # The parent is always non-empty; the nesting check must happen first.
        with self.assertRaisesRegex(ValueError, "contain"):
            launcher.validate_move_target(self.source, self.root)

    def test_wsl_unc_and_onedrive_paths_are_rejected(self):
        for target in (
            Path(r"\\wsl.localhost\Ubuntu\qqbot-data"),
            Path(r"\\server\share\qqbot-data"),
            self.root / "OneDrive" / "qqbot-data",
        ):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    launcher.validate_move_target(self.source, target)

    def test_removable_or_remote_drive_type_is_rejected(self):
        # This test is meaningful only on Windows, where the drive-type branch
        # runs. The path-level UNC/network checks are covered above on all OSes.
        if __import__("os").name != "nt":
            self.skipTest("drive type is Windows-only")
        target = self.root / "drive-check"
        for drive_type in (0, 1, 2, 4, 5, 6):
            with self.subTest(drive_type=drive_type):
                with self.assertRaisesRegex(ValueError, "fixed"):
                    launcher.validate_move_target(
                        self.source, target, drive_type_func=lambda _path, kind=drive_type: kind
                    )


class DataPointerTests(unittest.TestCase):
    def test_resolve_data_dir_reads_atomic_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "moved-data"
            target.mkdir()
            pointer = root / "data-location.json"
            launcher._write_json_atomic(pointer, {"data_dir": str(target)})
            with mock.patch.dict("os.environ", {"QQBOT_STUDIO_DATA_DIR": ""}, clear=False):
                resolved = launcher.resolve_data_dir(None, pointer_path=pointer)
            self.assertEqual(resolved, target.resolve())

    def test_powershell_fallback_reads_the_same_pointer(self):
        common = (Path(__file__).resolve().parents[1] / "windows" / "common.ps1").read_text(
            encoding="ascii"
        )
        self.assertIn("data-location.json", common)
        self.assertIn("data_dir", common)
        self.assertIn("Pass -DataDir explicitly", common)

    def test_invalid_pointer_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pointer = Path(tmp) / "data-location.json"
            pointer.write_text("{not json", encoding="utf-8")
            with mock.patch.dict("os.environ", {"QQBOT_STUDIO_DATA_DIR": ""}, clear=False):
                with self.assertRaises(ValueError):
                    launcher.resolve_data_dir(None, pointer_path=pointer)


class DataMoveDocumentationTests(unittest.TestCase):
    def test_docs_cover_file_locations_and_safe_move(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        windows_readme = (root / "windows" / "README.md").read_text(encoding="utf-8")
        for text in (readme, windows_readme):
            self.assertIn("--move-data", text)
            self.assertIn("data-location.json", text)
            self.assertIn("studio.json", text)
        for marker in (
            "instances\\bot-N",
            "studio-server.log",
            "extensions\\ai-assistant",
            "qqbot_enhancer",
            "OneDrive",
            "WSL",
            "UNC",
        ):
            self.assertIn(marker, readme, marker)

class DataMoveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "studio.json").write_text(
            json.dumps(
                {
                    "bind_host": "127.0.0.1",
                    "bind_port": 18791,
                    "public_host": "127.0.0.1",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        instances = self.source / "instances" / "bot-1"
        instances.mkdir(parents=True)
        (instances / "instance.json").write_text('{"id":"bot-1"}\n', encoding="utf-8")
        (instances / "deploy-state.json").write_text('{"running":true}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_move_copies_data_updates_pointer_and_retains_old_directory(self):
        target = self.root / "moved-data"
        pointer = self.root / "pointer" / "data-location.json"
        events = []

        def stop_service(source, *, bind_host, port, print_func):
            events.append(("stop-service", str(source), bind_host, port))

        def stop_containers(source, *, print_func):
            events.append(("stop-containers", str(source)))
            return ["bot-1"]

        result = launcher.move_data(
            self.source,
            target,
            non_interactive=True,
            pointer_path=pointer,
            stop_service_func=stop_service,
            stop_containers_func=stop_containers,
            print_func=lambda _message: None,
        )

        self.assertEqual(result, 0)
        self.assertEqual([event[0] for event in events], ["stop-service", "stop-containers"])
        self.assertTrue((self.source / "studio.json").is_file())
        self.assertTrue((target / "studio.json").is_file())
        self.assertTrue((target / "instances" / "bot-1" / "instance.json").is_file())
        copied_settings = json.loads((target / "studio.json").read_text(encoding="utf-8"))
        self.assertEqual(copied_settings["windows_data_dir"], str(target.resolve()))
        record = json.loads((target / launcher.MOVE_RECORD_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(record["from"], str(self.source.resolve()))
        self.assertEqual(record["to"], str(target.resolve()))
        self.assertEqual(record["containers_stopped"], ["bot-1"])
        pointer_payload = json.loads(pointer.read_text(encoding="utf-8"))
        self.assertEqual(pointer_payload["data_dir"], str(target.resolve()))

    def test_failed_copy_keeps_old_data_and_does_not_publish_target(self):
        target = self.root / "failed-target"
        pointer = self.root / "pointer" / "data-location.json"
        with mock.patch.object(launcher.shutil, "copytree", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(RuntimeError, "old data directory was retained"):
                launcher.move_data(
                    self.source,
                    target,
                    non_interactive=True,
                    pointer_path=pointer,
                    stop_service_func=lambda *args, **kwargs: None,
                    stop_containers_func=lambda *args, **kwargs: [],
                    print_func=lambda _message: None,
                )
        self.assertTrue((self.source / "studio.json").is_file())
        self.assertFalse(target.exists())
        self.assertFalse(pointer.exists())

    def test_pointer_update_failure_rolls_back_published_target(self):
        target = self.root / "pointer-failure-target"
        pointer = self.root / "pointer" / "data-location.json"
        with mock.patch.object(
            launcher, "_write_data_location_pointer", side_effect=OSError("acl denied")
        ):
            with self.assertRaisesRegex(RuntimeError, "old data directory was retained"):
                launcher.move_data(
                    self.source,
                    target,
                    non_interactive=True,
                    pointer_path=pointer,
                    stop_service_func=lambda *args, **kwargs: None,
                    stop_containers_func=lambda *args, **kwargs: [],
                    print_func=lambda _message: None,
                )
        self.assertTrue((self.source / "studio.json").is_file())
        self.assertFalse(target.exists())

    def test_noninteractive_false_can_cancel_before_any_stop(self):
        target = self.root / "cancel-target"
        stopped = []

        def stop_service(*args, **kwargs):
            stopped.append("service")

        result = launcher.move_data(
            self.source,
            target,
            non_interactive=False,
            input_func=lambda _prompt: "no",
            stop_service_func=stop_service,
            stop_containers_func=lambda *args, **kwargs: [],
            print_func=lambda _message: None,
        )
        self.assertEqual(result, 1)
        self.assertEqual(stopped, [])
        self.assertTrue((self.source / "studio.json").is_file())
        self.assertFalse(target.exists())


class ParserMoveDataTests(unittest.TestCase):
    def test_move_data_flag_and_combination_validation(self):
        parser = launcher.build_parser()
        args = parser.parse_args(["--move-data", r"D:\QQBotStudioData"])
        self.assertEqual(args.move_data, r"D:\QQBotStudioData")
        conflict = parser.parse_args(["--move-data", "D:\\data", "--status"])
        with self.assertRaises(SystemExit) as raised:
            launcher._validate_action_combination(parser, conflict)
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
