#!/usr/bin/env python3
"""Bootstrap/guide EXE for the planned native Windows edition.

This is intentionally NOT a full native AstrBot/SnowLuma manager yet. It
provides an honest, buildable Windows-native entry point while the Edition A
POC is validated against official SnowLuma Windows + desktop NTQQ.

No AstrBot, SnowLuma, NTQQ, VNC server or websockify is bundled. The planner
does not download, install, launch, inject into or authenticate any of them.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

NATIVE_LAUNCHER_VERSION = "0.5.0"
SNOWLUMA_WINDOWS_DOCS = "https://snowluma.github.io/zh/docs/guide/deploy/windows"
SNOWLUMA_RELEASES = "https://github.com/SnowLuma/SnowLuma/releases"
ASTRBOT_WINDOWS_DOCS = "https://docs.astrbot.app/deploy/astrbot/package.html"
NOVNC_REPO = "https://github.com/novnc/noVNC"
WEBSOCKIFY_REPO = "https://github.com/novnc/websockify"


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _read_bundle_text(name: str) -> str:
    try:
        return (_bundle_root() / name).read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _bundled_core_version() -> str:
    upstream = _read_bundle_text("UPSTREAM.md")
    for line in upstream.splitlines():
        if line.startswith("- Bundled core version:"):
            part = line.rsplit("==", 1)[-1].strip().strip("`")
            if part:
                return part
    return "unknown"


def _print_guide() -> None:
    print("QQ Bot Studio Windows - Native Edition bootstrap (preview)")
    print("==========================================================")
    print("This EXE is a native bootstrap/guide placeholder, not a complete")
    print("AstrBot/SnowLuma/NTQQ integration yet. It does not bundle or launch")
    print("those programs, and it makes no native end-to-end claim.")
    print("")
    print("Recommended official path (single instance first):")
    print("  1. Install the official Windows desktop QQ (NTQQ) and sign in there.")
    print("  2. Install AstrBot's official Windows/PowerShell deployment or")
    print("     Python runtime; use a dedicated ASTRBOT_ROOT for one instance.")
    print("  3. Download the official SnowLuma Windows x64 release zip, run")
    print("     launcher.bat in the same Windows user/elevation context as QQ.")
    print("  4. Connect SnowLuma to native AstrBot over loopback OneBot WS.")
    print("  5. Scan the QQ login QR code in the desktop QQ window manually.")
    print("")
    print("Official links:")
    print(f"  SnowLuma Windows guide : {SNOWLUMA_WINDOWS_DOCS}")
    print(f"  SnowLuma releases      : {SNOWLUMA_RELEASES}")
    print(f"  AstrBot Windows docs   : {ASTRBOT_WINDOWS_DOCS}")
    print("")
    print("noVNC is an OPTIONAL advanced enhancement, not SnowLuma's native")
    print("login page. It needs a third-party Windows VNC Server + websockify")
    print("and shares the whole interactive Windows desktop. It is not a")
    print("per-instance private screen. Only use it over loopback/VPN/firewall.")
    print(f"  noVNC: {NOVNC_REPO}")
    print(f"  websockify: {WEBSOCKIFY_REPO}")
    print("")
    print("The Docker Desktop + WSL2 edition remains the simpler stable edition.")
    print("Use --check to inspect local prerequisites; --help for all options.")


def _candidate_qq_paths() -> list[Path]:
    roots = [
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    relative = (
        r"Tencent\QQNT\QQ.exe",
        r"Tencent\QQ\Bin\QQ.exe",
        r"Programs\Tencent\QQNT\QQ.exe",
        r"Programs\Tencent\QQ\Bin\QQ.exe",
    )
    candidates: list[Path] = []
    for root in roots:
        if root:
            candidates.extend(Path(root) / rel for rel in relative)
    return candidates


def _process_present(image_name: str) -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return image_name.lower() in (result.stdout or "").lower()
    except (OSError, subprocess.SubprocessError):
        return False


def _check(snowluma_dir: str | None, astrbot_root: str | None) -> int:
    print("Native edition prerequisite check (read-only; no integration launch)")
    print(f"  platform          : {platform.platform()}")
    print(f"  OS family         : {os.name}")
    print(f"  bundled core      : {_bundled_core_version()}")
    print(f"  native launcher   : {NATIVE_LAUNCHER_VERSION}")
    print("")
    qq_path = next((p for p in _candidate_qq_paths() if p.is_file()), None)
    print(f"  NTQQ executable   : {qq_path if qq_path else 'NOT FOUND (install desktop QQ)'}")
    print(f"  NTQQ process      : {'RUNNING' if _process_present('QQ.exe') else 'not running'}")
    if snowluma_dir:
        snowluma = Path(snowluma_dir).expanduser().resolve()
        launcher = snowluma / "launcher.bat"
        print(f"  SnowLuma launcher : {launcher if launcher.is_file() else 'NOT FOUND at --snowluma-dir'}")
    else:
        print("  SnowLuma launcher : not checked; pass --snowluma-dir to inspect an extracted release")
    if astrbot_root:
        astrbot = Path(astrbot_root).expanduser().resolve()
        print(f"  AstrBot root      : {astrbot if astrbot.is_dir() else 'NOT FOUND at --astrbot-root'}")
    else:
        print("  AstrBot root      : not checked; pass --astrbot-root")
    print(f"  astrbot command   : {shutil.which('astrbot') or 'not found in PATH'}")
    print(f"  node command      : {shutil.which('node') or 'not found in PATH (full SnowLuma bundles Node)'}")
    print(f"  websockify        : {shutil.which('websockify') or 'not found (optional noVNC only)'}")
    print("")
    print("NATIVE_PREREQ_CHECK=COMPLETE")
    print("NATIVE_E2E=NOT_VERIFIED")
    print("NATIVE_INTEGRATION=NOT_IMPLEMENTED_IN_BOOTSTRAP")
    return 0


def _open(url: str) -> None:
    print(f"Opening: {url}")
    try:
        webbrowser.open_new_tab(url)
    except Exception as exc:
        print(f"ERROR: Could not open browser: {exc}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="QQBotStudioWindowsNative",
        description=(
            "Native Windows bootstrap/guide placeholder. It does not bundle or "
            "manage AstrBot/SnowLuma/NTQQ yet; Docker edition remains the stable option."
        ),
    )
    parser.add_argument("--version", action="version", version=f"QQ Bot Studio Windows Native bootstrap {NATIVE_LAUNCHER_VERSION} (bundled core {_bundled_core_version()})")
    parser.add_argument("--guide", action="store_true", help="Print the official native setup guide (default).")
    parser.add_argument("--check", action="store_true", help="Inspect local NTQQ/AstrBot/SnowLuma prerequisites.")
    parser.add_argument("--snowluma-dir", default=None, help="Optional extracted SnowLuma directory to inspect.")
    parser.add_argument("--astrbot-root", default=None, help="Optional native AstrBot root to inspect.")
    parser.add_argument("--open-snowluma", action="store_true", help="Open the official SnowLuma Windows guide.")
    parser.add_argument("--open-snowluma-release", action="store_true", help="Open the official SnowLuma release page.")
    parser.add_argument("--open-astrbot", action="store_true", help="Open the official AstrBot Windows deployment docs.")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    opened = False
    if args.open_snowluma:
        _open(SNOWLUMA_WINDOWS_DOCS)
        opened = True
    if args.open_snowluma_release:
        _open(SNOWLUMA_RELEASES)
        opened = True
    if args.open_astrbot:
        _open(ASTRBOT_WINDOWS_DOCS)
        opened = True
    if args.check:
        return _check(args.snowluma_dir, args.astrbot_root)
    if not opened:
        _print_guide()
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
