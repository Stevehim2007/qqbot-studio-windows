"""Tests for the Native one-click installer POC."""

import tempfile
import unittest
from pathlib import Path

from windows import native_setup


class NativeSetupPlanTests(unittest.TestCase):
    def test_official_plan_uses_https_and_pinned_sha256(self):
        plan = native_setup.official_plan()
        names = {item["name"] for item in plan}
        self.assertTrue({"uv", "AstrBot", "SnowLuma", "Node.js"} <= names)
        for item in plan:
            self.assertTrue(item["url"].startswith("https://"), item)
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("official", item)

    def test_detect_environment_reports_plan_and_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "native"
            result = native_setup.detect_environment(root)
            self.assertIn("plan", result)
            self.assertEqual(len(result["plan"]), 4)
            self.assertIn("blockers", result)
            self.assertEqual(result["bind_host"], "127.0.0.1")

    def test_download_rejects_non_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(native_setup.InstallError):
                native_setup._download(
                    "http://example.com/x.zip",
                    Path(tmp) / "x.zip",
                    expected_sha256="0" * 64,
                )


if __name__ == "__main__":
    unittest.main()
