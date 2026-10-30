# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file build for the Windows Native POC process-manager EXE."""

from pathlib import Path

try:
    ROOT = Path(SPECPATH).resolve().parent
except NameError:
    ROOT = Path.cwd()

windows_dir = ROOT / "windows"
if not (windows_dir / "native_launcher.py").is_file():
    raise RuntimeError(
        f"Repository root could not be resolved from {ROOT!s}; "
        "run windows/build.ps1 from the checkout root."
    )

datas = [
    (str(ROOT / "VERSION"), "."),
    (str(ROOT / "UPSTREAM.md"), "."),
    (str(ROOT / "LICENSE"), "."),
]

a = Analysis(
    [str(windows_dir / "native_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["windows.native_runtime", "qqbot_studio.store"],
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
    name="QQBotStudioWindowsNative",
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
