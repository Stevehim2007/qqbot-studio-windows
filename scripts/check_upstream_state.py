#!/usr/bin/env python3
"""Fail a Release/build when Windows upstream metadata is stale or broken."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
CORE_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
PLUGIN_RE = re.compile(r"^version:\s*(\S+)", re.MULTILINE)


def check_upstream_state(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    commit_path = root / ".upstream-commit"
    upstream_path = root / "UPSTREAM.md"
    core_path = root / "qqbot_studio" / "__init__.py"
    plugin_path = root / "plugins" / "qqbot_enhancer" / "metadata.yaml"

    if not commit_path.is_file():
        errors.append(".upstream-commit is missing")
        commit = ""
    else:
        commit = commit_path.read_text(encoding="ascii", errors="replace").strip()
        if not COMMIT_RE.fullmatch(commit):
            errors.append(".upstream-commit must contain a 40-character git SHA")

    if not upstream_path.is_file():
        errors.append("UPSTREAM.md is missing")
        upstream = ""
    else:
        upstream = upstream_path.read_text(encoding="utf-8", errors="replace")

    if not core_path.is_file():
        errors.append("qqbot_studio/__init__.py is missing")
        core_version = ""
    else:
        match = CORE_RE.search(core_path.read_text(encoding="utf-8", errors="replace"))
        core_version = match.group(1) if match else ""
        if not core_version:
            errors.append("qqbot_studio.__version__ is missing")

    if not plugin_path.is_file():
        errors.append("plugins/qqbot_enhancer/metadata.yaml is missing")
        plugin_version = ""
    else:
        match = PLUGIN_RE.search(plugin_path.read_text(encoding="utf-8", errors="replace"))
        plugin_version = match.group(1) if match else ""
        if not plugin_version:
            errors.append("qqbot_enhancer metadata version is missing")

    if commit and commit not in upstream:
        errors.append("UPSTREAM.md does not record the .upstream-commit snapshot")
    if core_version and f"qqbot_studio.__version__ == {core_version}" not in upstream:
        errors.append("UPSTREAM.md bundled core version does not match the vendored core")
    if plugin_version and f"`qqbot_enhancer` {plugin_version}" not in upstream:
        errors.append("UPSTREAM.md plugin version does not match the vendored plugin")
    if core_version and f"v{core_version}" not in upstream:
        errors.append("UPSTREAM.md upstream release line does not match the vendored core")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = check_upstream_state(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            "Release blocked: run sync-upstream and commit the resulting "
            ".upstream-commit/UPSTREAM.md/code before tagging.",
            file=sys.stderr,
        )
        return 1
    print("Upstream snapshot metadata is consistent; release/build may proceed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
