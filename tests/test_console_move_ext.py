"""Tests for the token-protected console storage-migration extension."""

import json
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from unittest import mock

from qqbot_studio import server as server_module
from qqbot_studio.studio import StudioManager
from windows import console_move_ext


class ConsoleMoveTargetTests(unittest.TestCase):
    def test_relative_and_empty_targets_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            with self.assertRaisesRegex(ValueError, "绝对路径"):
                console_move_ext.validate_console_target(source, "relative-data")
            with self.assertRaisesRegex(ValueError, "不能为空"):
                console_move_ext.validate_console_target(source, "   ")
            with self.assertRaisesRegex(ValueError, "绝对路径"):
                console_move_ext.validate_console_target(source, 123)

    def test_absolute_empty_target_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            target = Path(tmp) / "new-data"
            resolved = console_move_ext.validate_console_target(source, str(target))
            self.assertEqual(resolved, target.resolve())


class ConsoleMoveScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "studio.json").write_text(
            json.dumps({"bind_host": "127.0.0.1", "bind_port": 18797}) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_schedule_writes_request_and_status_without_shell(self):
        target = self.root / "new-data"
        result = console_move_ext.schedule_move(
            self.data,
            {"target": str(target), "confirm": True},
            spawn_func=lambda request, data: 4242,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "scheduled")
        request_path = self.data / console_move_ext.MOVE_REQUEST_FILENAME
        self.assertTrue(request_path.is_file())
        request = json.loads(request_path.read_text(encoding="utf-8"))
        self.assertEqual(request["source"], str(self.data.resolve()))
        self.assertEqual(request["target"], str(target.resolve()))
        status = console_move_ext.read_move_status(self.data)
        self.assertEqual(status["status"], "scheduled")
        self.assertEqual(status["pid"], 4242)
        self.assertIn("worker_log_path", status)

        with self.assertRaisesRegex(RuntimeError, "已有存储迁移任务"):
            console_move_ext.schedule_move(
                self.data,
                {"target": str(self.root / "other"), "confirm": True},
                spawn_func=lambda request, data: 1,
            )

    def test_confirmation_and_nonempty_target_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "勾选"):
            console_move_ext.schedule_move(self.data, {"target": str(self.root / "x")})
        target = self.root / "nonempty"
        target.mkdir()
        (target / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be empty|必须为空"):
            console_move_ext.schedule_move(
                self.data,
                {"target": str(target), "confirm": True},
                spawn_func=lambda request, data: 1,
            )

    def test_spawn_failure_removes_request_and_reports_failed(self):
        target = self.root / "spawn-fail"
        with self.assertRaisesRegex(RuntimeError, "无法启动迁移"):
            console_move_ext.schedule_move(
                self.data,
                {"target": str(target), "confirm": True},
                spawn_func=lambda request, data: (_ for _ in ()).throw(OSError("spawn denied")),
            )
        self.assertFalse((self.data / console_move_ext.MOVE_REQUEST_FILENAME).exists())
        status = json.loads(
            (self.data / console_move_ext.MOVE_STATUS_FILENAME).read_text(encoding="utf-8")
        )
        self.assertEqual(status["status"], "failed")
        self.assertIn("旧数据目录未改动", status["message"])


class ConsoleMoveApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "studio.json").write_text(
            json.dumps({"bind_host": "127.0.0.1", "bind_port": 18797}) + "\n",
            encoding="utf-8",
        )
        self.target = self.root / "target"
        self.request = self.source / console_move_ext.MOVE_REQUEST_FILENAME
        self.request.write_text(
            json.dumps(
                {
                    "source": str(self.source.resolve()),
                    "target": str(self.target.resolve()),
                    "bind_host": "127.0.0.1",
                    "bind_port": 18797,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_apply_success_writes_completed_status_and_starts_target(self):
        calls = []

        def fake_move(source, target, **kwargs):
            self.assertEqual(source, self.source.resolve())
            target.mkdir()
            (target / "studio.json").write_text(
                json.dumps({"bind_host": "127.0.0.1", "bind_port": 18798}) + "\n",
                encoding="utf-8",
            )
            calls.append("move")
            return 0

        def fake_ensure(data_dir, **kwargs):
            calls.append(("ensure", Path(data_dir).resolve(), kwargs["port"]))

        with mock.patch.object(console_move_ext.time, "sleep", return_value=None):
            rc = console_move_ext.apply_move_request(
                self.request,
                move_data_func=fake_move,
                ensure_server_func=fake_ensure,
                print_func=lambda _message: None,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(calls[0], "move")
        self.assertEqual(calls[1][0], "ensure")
        self.assertEqual(calls[1][1], self.target.resolve())
        self.assertEqual(calls[1][2], 18798)
        status = json.loads(
            (self.target / console_move_ext.MOVE_STATUS_FILENAME).read_text(encoding="utf-8")
        )
        self.assertEqual(status["status"], "completed")
        self.assertTrue(status["old_directory_retained"])
        self.assertFalse(self.request.exists())

    def test_apply_failure_keeps_source_and_restores_old_service(self):
        calls = []

        def failing_move(source, target, **kwargs):
            raise OSError("simulated copy failure")

        def fake_ensure(data_dir, **kwargs):
            calls.append((Path(data_dir).resolve(), kwargs["port"]))

        with mock.patch.object(console_move_ext.time, "sleep", return_value=None):
            rc = console_move_ext.apply_move_request(
                self.request,
                move_data_func=failing_move,
                ensure_server_func=fake_ensure,
                print_func=lambda _message: None,
            )
        self.assertEqual(rc, 1)
        self.assertEqual(calls, [(self.source.resolve(), 18797)])
        self.assertTrue((self.source / "studio.json").is_file())
        status = json.loads(
            (self.source / console_move_ext.MOVE_STATUS_FILENAME).read_text(encoding="utf-8")
        )
        self.assertEqual(status["status"], "failed")
        self.assertFalse(self.request.exists())


class ConsoleMoveHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "studio.json").write_text(
            json.dumps({"bind_host": "127.0.0.1", "bind_port": 18799, "first_run_complete": True}) + "\n",
            encoding="utf-8",
        )
        console_move_ext.install_windows_console_extension(server_module)
        self.server = server_module.create_server(
            StudioManager(self.data),
            host="127.0.0.1",
            port=0,
            token="test-token",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def _request(self, path, *, method="GET", body=None, token=None):
        headers = {"User-Agent": "console-move-test"}
        if token:
            headers["X-QB-Token"] = token
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read()

    def test_api_token_and_console_assets(self):
        status, body = self._request("/console")
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn("/windows-console-move.js", html)
        self.assertIn("/windows-console-move.css", html)
        status, body = self._request("/windows-console-move.js")
        self.assertEqual(status, 200)
        self.assertIn(b"/api/system/move-data", body)

        with self.assertRaises(urllib.error.HTTPError) as raised:
            self._request("/api/system/move-data/status")
        self.assertEqual(raised.exception.code, 403)
        status, body = self._request("/api/system/move-data/status", token="test-token")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "idle")
        self.assertEqual(payload["current_data_dir"], str(self.data.resolve()))

        target = self.root / "new-data"
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self._request(
                "/api/system/move-data",
                method="POST",
                body={"target": str(target), "confirm": True},
            )
        self.assertEqual(raised.exception.code, 403)

    def test_api_rejects_unconfirmed_and_schedules_valid_request(self):
        target = self.root / "new-data"
        with mock.patch.object(console_move_ext, "_spawn_worker", return_value=777):
            status, body = self._request(
                "/api/system/move-data",
                method="POST",
                body={"target": str(target), "confirm": True},
                token="test-token",
            )
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "scheduled")
        self.assertTrue((self.data / console_move_ext.MOVE_REQUEST_FILENAME).is_file())

        with self.assertRaises(urllib.error.HTTPError) as raised:
            with mock.patch.object(console_move_ext, "_spawn_worker", return_value=778):
                self._request(
                    "/api/system/move-data",
                    method="POST",
                    body={"target": str(self.root / "other"), "confirm": True},
                    token="test-token",
                )
        self.assertEqual(raised.exception.code, 409)

class ConsoleMoveStaticTests(unittest.TestCase):
    def test_ui_and_api_require_token_and_show_migration_states(self):
        root = Path(__file__).resolve().parents[1]
        js = (root / "windows" / "console_move.js").read_text(encoding="utf-8")
        css = (root / "windows" / "console_move.css").read_text(encoding="utf-8")
        ext = (root / "windows" / "console_move_ext.py").read_text(encoding="utf-8")
        spec = (root / "windows" / "qqbot-studio-windows.spec").read_text(encoding="utf-8")
        for marker in (
            "/api/system/move-data",
            "/api/system/move-data/status",
            "X-QB-Token",
            "windows-data-confirm",
            "开始安全迁移",
            "刷新控制台",
        ):
            self.assertIn(marker, js)
        self.assertIn("windows-storage-panel", css)
        for marker in (
            "_check_token",
            "schedule_move",
            "Popen",
            "CREATE_NO_WINDOW",
            "/api/system/move-data/status",
            "apply_move_request",
        ):
            self.assertIn(marker, ext)
        self.assertIn("console_move.js", spec)
        self.assertIn("console_move.css", spec)
        self.assertIn("windows.console_move_ext", spec)


if __name__ == "__main__":
    unittest.main()
