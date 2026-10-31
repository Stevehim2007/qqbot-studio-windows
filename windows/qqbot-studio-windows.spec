# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file build for the standalone Windows launcher."""

from pathlib import Path

try:
    ROOT = Path(SPECPATH).resolve().parent
except NameError:
    # Fallback for syntax checks. Builds should invoke this through build.ps1.
    ROOT = Path.cwd()

windows_dir = ROOT / "windows"
if not (windows_dir / "launcher.py").is_file():
    raise RuntimeError(
        f"Repository root could not be resolved from {ROOT!s}; "
        "run windows/build.ps1 from the checkout root."
    )

datas = [
    (str(ROOT / "qqbot_studio" / "static"), "qqbot_studio/static"),
    (str(ROOT / "plugins" / "qqbot_enhancer"), "plugins/qqbot_enhancer"),
    (str(ROOT / "assets"), "assets"),
    (str(windows_dir / "console_move.js"), "windows"),
    (str(windows_dir / "console_move.css"), "windows"),
]

hiddenimports = [
    "qqbot_studio",
    "qqbot_studio.__main__",
    "qqbot_studio.assistant_ext",
    "qqbot_studio.astrbot_api",
    "qqbot_studio.configgen",
    "qqbot_studio.deployer",
    "qqbot_studio.dockerctl",
    "qqbot_studio.launcher",
    "qqbot_studio.server",
    "qqbot_studio.store",
    "qqbot_studio.studio",
    "qqbot_studio.contracts",
    "qqbot_studio.gitutil",
    "qqbot_studio.resource_stats",
    "qqbot_studio.updater",
    "windows.move_data_core",
    "windows.console_move_ext",
]

a = Analysis(
    [str(windows_dir / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="QQBotStudioWindows",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
