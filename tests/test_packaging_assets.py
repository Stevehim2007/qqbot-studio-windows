"""Static checks for the independent Windows distribution and CI artifact."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "windows"


class PackagingAssetTests(unittest.TestCase):
    def test_independent_project_files_exist(self):
        for relative in (
            "README.md",
            "VERSION",
            "UPSTREAM.md",
            "requirements-build.txt",
            "windows/build.ps1",
            "windows/qqbot-studio-windows.spec",
            "windows/qqbot-studio-windows-native.spec",
            "windows/launcher.py",
            "windows/native_launcher.py",
            ".github/workflows/windows-build.yml",
            ".github/workflows/windows-release.yml",
            ".github/workflows/sync-upstream.yml",
            "scripts/sync_upstream.py",
            ".upstream-commit",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_spec_bundles_server_assets_and_launcher(self):
        path = WINDOWS / "qqbot-studio-windows.spec"
        text = path.read_text(encoding="utf-8")
        compile(text, str(path), "exec")
        for expected in (
            'windows_dir / "launcher.py"',
            "qqbot_studio/static",
            "plugins/qqbot_enhancer",
            "qqbot_studio.assistant_ext",
            "QQBotStudioWindows",
            "console=True",
        ):
            self.assertIn(expected, text, expected)

    def test_native_spec_builds_process_manager_exe(self):
        path = WINDOWS / "qqbot-studio-windows-native.spec"
        text = path.read_text(encoding="utf-8")
        compile(text, str(path), "exec")
        for expected in (
            'windows_dir / "native_launcher.py"',
            'ROOT / "VERSION"',
            'ROOT / "UPSTREAM.md"',
            "QQBotStudioWindowsNative",
            "console=True",
        ):
            self.assertIn(expected, text, expected)

    def test_build_script_uses_pinned_requirements_and_smokes_exe(self):
        text = (WINDOWS / "build.ps1").read_text(encoding="ascii")
        for expected in (
            "#requires -Version 5.1",
            "requirements-build.txt",
            "PyInstaller",
            "QQBotStudioWindows.exe",
            "qqbot-studio-windows-native.spec",
            "QQBotStudioWindowsNative.exe",
            "--version",
            "--help",
            "SHA256SUMS.txt",
        ):
            self.assertIn(expected, text, expected)

    def test_ci_builds_and_uploads_windows_artifact(self):
        text = (ROOT / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
        for expected in (
            "windows-latest",
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "python-version: '3.12'",
            "python -m unittest discover -s tests -v",
            "build.ps1 -Clean",
            "actions/upload-artifact@v4",
            "dist/QQBotStudioWindows.exe",
            "dist/QQBotStudioWindowsNative.exe",
            "build.ps1 -Clean",
        ):
            self.assertIn(expected, text, expected)

    def test_native_poc_has_process_manager_and_honest_blockers(self):
        launcher = (WINDOWS / "native_launcher.py").read_text(encoding="utf-8")
        runtime = (WINDOWS / "native_runtime.py").read_text(encoding="utf-8")
        spec = (WINDOWS / "qqbot-studio-windows-native.spec").read_text(
            encoding="utf-8"
        )
        for expected in (
            "Native single-instance Windows POC",
            "native_runtime.start_native",
            "native_runtime.check_prerequisites",
            "NATIVE_E2E=NOT_VERIFIED",
            "NoVNC was NOT started",
            "official local NTQQ window",
            "snowluma.github.io",
        ):
            self.assertIn(expected, launcher, expected)
        for expected in (
            "def start_process",
            "def stop_process",
            "def start_native",
            "def stop_native",
            "def write_snowluma_onebot_config",
            "ws://127.0.0.1:",
            "no_vnc_used",
        ):
            self.assertIn(expected, runtime, expected)
        self.assertIn("windows.native_runtime", spec)

    def test_release_workflow_publishes_exe_and_sha256(self):
        text = (ROOT / ".github/workflows/windows-release.yml").read_text(
            encoding="utf-8"
        )
        for expected in (
            "tags:",
            "v*",
            "contents: write",
            "windows-latest",
            "softprops/action-gh-release@v2",
            "dist/QQBotStudioWindows.exe",
            "dist/QQBotStudioWindowsNative.exe",
            "dist/SHA256SUMS.txt",
            "fail_on_unmatched_files: true",
        ):
            self.assertIn(expected, text, expected)

    def test_readme_defines_independent_boundaries(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in (
            "Ubuntu/Linux 主项目",
            "Windows 10/11",
            "Docker Desktop",
            "WSL2",
            "%LOCALAPPDATA%\\QQBotStudio\\data",
            "升级边界",
            "不能直接共用",
            "/assistant",
            "30 分钟",
            "1.4",
            "GitHub Release",
            "reply_probability",
            "Native",
            "Docker",
            "sync-upstream",
            "Native POC",
            "未验证",
        ):
            self.assertIn(expected, text, expected)


if __name__ == "__main__":
    unittest.main()
