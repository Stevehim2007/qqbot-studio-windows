"""Tests for the allowlisted Linux -> Windows upstream sync automation."""

import tempfile
import unittest
from pathlib import Path

from scripts import sync_upstream

ROOT = Path(__file__).resolve().parents[1]


class SyncWorkflowStaticTests(unittest.TestCase):
    def test_workflow_has_dispatch_schedule_write_and_guardrails(self):
        text = (ROOT / ".github/workflows/sync-upstream.yml").read_text(encoding="utf-8")
        for expected in (
            "workflow_dispatch:",
            "schedule:",
            "cron:",
            "permissions:",
            "contents: write",
            "repository: Stevehim2007/qqbot-studio",
            "ref: main",
            "python scripts/sync_upstream.py",
            "--dry-run",
            "python scripts/check_upstream_state.py --root .",
            "git diff --quiet",
            "git push origin HEAD:main",
            "python -m unittest discover -s tests -v",
        ):
            self.assertIn(expected, text, expected)

    def test_sync_script_uses_allowlist_and_records_commit(self):
        text = (ROOT / "scripts/sync_upstream.py").read_text(encoding="utf-8")
        for expected in (
            '("qqbot_studio", "qqbot_studio")',
            '("plugins/qqbot_enhancer", "plugins/qqbot_enhancer")',
            '("assets", "assets")',
            "DOC_ALLOWLIST",
            ".upstream-commit",
            "UPSTREAM.md",
            '"--dry-run"',
            "VERSION",
        ):
            self.assertIn(expected, text, expected)


class UpstreamStateGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.commit = "b" * 40
        (self.root / ".upstream-commit").write_text(self.commit + "\n", encoding="ascii")
        (self.root / "qqbot_studio").mkdir()
        (self.root / "qqbot_studio" / "__init__.py").write_text(
            '__version__ = "7.8.9"\n', encoding="utf-8"
        )
        (self.root / "plugins" / "qqbot_enhancer").mkdir(parents=True)
        (self.root / "plugins" / "qqbot_enhancer" / "metadata.yaml").write_text(
            "name: qqbot_enhancer\nversion: 4.5.6\n", encoding="utf-8"
        )
        self._write_upstream()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_upstream(self):
        (self.root / "UPSTREAM.md").write_text(
            "# Snapshot\n\n"
            f"- Upstream snapshot commit: `{self.commit}`\n"
            "- Snapshot date: 2026-10-30\n"
            "- Upstream release line: v7.8.9\n"
            "- Bundled core version: `qqbot_studio.__version__ == 7.8.9`\n"
            "- Windows launcher version: `0.4.2`\n"
            "- Plugin snapshot: `qqbot_enhancer` 4.5.6\n",
            encoding="utf-8",
        )

    def test_consistent_metadata_passes(self):
        from scripts import check_upstream_state

        self.assertEqual(check_upstream_state.check_upstream_state(self.root), [])

    def test_stale_metadata_blocks_release(self):
        (self.root / "qqbot_studio" / "__init__.py").write_text(
            '__version__ = "7.9.0"\n', encoding="utf-8"
        )
        from scripts import check_upstream_state

        errors = check_upstream_state.check_upstream_state(self.root)
        self.assertTrue(any("bundled core version" in error for error in errors), errors)


class SyncUpstreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.upstream = self.root / "upstream"
        self.target = self.root / "windows"
        self.upstream.mkdir()
        self.target.mkdir()

        core = self.upstream / "qqbot_studio"
        (core / "static").mkdir(parents=True)
        (core / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
        (core / "static" / "app.js").write_text("// upstream app\n", encoding="utf-8")
        plugin = self.upstream / "plugins" / "qqbot_enhancer"
        plugin.mkdir(parents=True)
        (plugin / "metadata.yaml").write_text("name: qqbot_enhancer\nversion: 2.3.4\n", encoding="utf-8")
        (plugin / "main.py").write_text("# upstream plugin\n", encoding="utf-8")
        assets = self.upstream / "assets"
        assets.mkdir()
        (assets / "logo.svg").write_text("<svg/>\n", encoding="utf-8")
        docs = self.upstream / "docs"
        docs.mkdir()
        (docs / "ui-api-contract-v2.md").write_text("api 9.9.9\n", encoding="utf-8")
        (docs / "windows-editions-research.md").write_text("upstream research\n", encoding="utf-8")
        (docs / "README.md").write_text("upstream docs index must not win\n", encoding="utf-8")
        (docs / "FAQ.md").write_text("upstream FAQ must not win\n", encoding="utf-8")

        # Windows-owned files that the sync must preserve.
        (self.target / "VERSION").write_text("0.4.1\n", encoding="ascii")
        windows = self.target / "windows"
        windows.mkdir()
        (windows / "launcher.py").write_text("# windows launcher sentinel\n", encoding="utf-8")
        (windows / "build.ps1").write_text("# windows build sentinel\n", encoding="utf-8")
        workflows = self.target / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "windows-release.yml").write_text("sentinel release\n", encoding="utf-8")
        target_docs = self.target / "docs"
        target_docs.mkdir()
        (target_docs / "README.md").write_text("windows docs index\n", encoding="utf-8")
        (target_docs / "FAQ.md").write_text("windows FAQ\n", encoding="utf-8")
        (self.target / "UPSTREAM.md").write_text(
            "# Upstream snapshot\n\n"
            "- Upstream snapshot commit: `0000000000000000000000000000000000000000`\n"
            "- Snapshot date: 2000-01-01\n"
            "- Upstream release line: v0.0.0\n"
            "- Bundled core version: `qqbot_studio.__version__ == 0.0.0`\n"
            "- Windows launcher version: `0.4.1`\n"
            "- Plugin snapshot: `qqbot_enhancer` 0.0.0\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _sync(self, **kwargs):
        return sync_upstream.sync_upstream(
            self.upstream,
            self.target,
            source_sha="a" * 40,
            snapshot_date="2026-10-30",
            **kwargs,
        )

    def test_sync_copies_allowlist_preserves_windows_owned_files_and_records_sha(self):
        changed = self._sync()
        self.assertIn(".upstream-commit", changed)
        self.assertEqual((self.target / "qqbot_studio/__init__.py").read_text(encoding="utf-8"), '__version__ = "9.9.9"\n')
        self.assertTrue((self.target / "qqbot_studio/static/app.js").is_file())
        self.assertTrue((self.target / "plugins/qqbot_enhancer/main.py").is_file())
        self.assertTrue((self.target / "assets/logo.svg").is_file())
        self.assertTrue((self.target / "docs/ui-api-contract-v2.md").is_file())
        self.assertTrue((self.target / "docs/windows-editions-research.md").is_file())
        # Windows-owned paths and docs must not be replaced.
        self.assertEqual((self.target / "VERSION").read_text(encoding="ascii"), "0.4.1\n")
        self.assertEqual((self.target / "windows/launcher.py").read_text(encoding="utf-8"), "# windows launcher sentinel\n")
        self.assertEqual((self.target / "windows/build.ps1").read_text(encoding="utf-8"), "# windows build sentinel\n")
        self.assertEqual((self.target / "docs/README.md").read_text(encoding="utf-8"), "windows docs index\n")
        self.assertEqual((self.target / "docs/FAQ.md").read_text(encoding="utf-8"), "windows FAQ\n")
        # Upstream metadata is updated from copied core/plugin files.
        self.assertEqual((self.target / ".upstream-commit").read_text(encoding="ascii"), "a" * 40 + "\n")
        upstream = (self.target / "UPSTREAM.md").read_text(encoding="utf-8")
        self.assertIn("a" * 40, upstream)
        self.assertIn("v9.9.9", upstream)
        self.assertIn("qqbot_studio.__version__ == 9.9.9", upstream)
        self.assertIn("qqbot_enhancer` 2.3.4", upstream)
        self.assertIn("Windows launcher version: `0.4.1`", upstream)
        # Existing upstream README/FAQ are not in the copied docs allowlist.
        self.assertFalse((self.target / "docs/upstream-only.txt").exists())

    def test_second_sync_is_a_noop(self):
        self._sync()
        changed = self._sync()
        self.assertEqual(changed, [])

    def test_dry_run_reports_change_without_writing(self):
        (self.upstream / "qqbot_studio" / "__init__.py").write_text('__version__ = "9.9.10"\n', encoding="utf-8")
        changed = self._sync(dry_run=True)
        self.assertTrue(changed)
        self.assertFalse((self.target / "qqbot_studio/__init__.py").exists())
        self.assertFalse((self.target / ".upstream-commit").exists())

    def test_missing_upstream_core_fails_closed(self):
        (self.upstream / "qqbot_studio" / "__init__.py").unlink()
        with self.assertRaises((FileNotFoundError, ValueError)):
            self._sync()


if __name__ == "__main__":
    unittest.main()
