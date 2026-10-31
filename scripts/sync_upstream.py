#!/usr/bin/env python3
"""Synchronize the allowlisted Linux upstream snapshot into the Windows repo.

The Windows launcher, PowerShell lifecycle scripts, build specs, tests,
VERSION and release workflows are Windows-owned and are never copied from the
Linux project. Only the allowlisted runtime/docs paths are vendored.

The script is intentionally deterministic and importable so the GitHub Actions
workflow and local dry-runs share exactly the same logic.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPO = "Stevehim2007/qqbot-studio"
UPSTREAM_BRANCH = "main"

# Runtime-owned paths. Windows-owned files outside these paths are preserved.
MIRRORED_PATHS = (
    ("qqbot_studio", "qqbot_studio"),
    ("plugins/qqbot_enhancer", "plugins/qqbot_enhancer"),
    ("assets", "assets"),
    # E2E harness scripts are source artifacts too; generated tests/e2e/artifacts
    # directories are excluded below.
    ("tests/e2e", "tests/e2e"),
)

# Docs are copied file-by-file. docs/README.md and docs/FAQ.md are
# Windows-specific and must never be overwritten by upstream copies.
DOC_ALLOWLIST = (
    "ui-api-contract-v2.md",
    "plugin-qqbot-enhancer.md",
    "server-troubleshooting.md",
    "qa-report-v2.md",
    "integration-research.md",
    "windows-editions-research.md",
    "ui-api-contract.md",
    "qa-report.md",
)

CORE_VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
PLUGIN_VERSION_RE = re.compile(r"^version:\s*(\S+)", re.MULTILINE)
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", "artifacts"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_state(root: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    if not root.is_dir():
        return state
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_NAMES for part in path.parts):
            continue
        state[path.relative_to(root).as_posix()] = _sha256(path)
    return state


def _tree_plan(source: Path, target: Path) -> list[str]:
    source_state = _tree_state(source)
    target_state = _tree_state(target)
    if source_state == target_state:
        return []
    return [f"{target.name}/"]


def _copy_ignore(_directory: str, names: Iterable[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES or name.endswith(".pyc")}


def _mirror_tree(source: Path, target: Path) -> list[str]:
    if not source.is_dir():
        raise FileNotFoundError(f"Required upstream path is missing: {source}")
    changed = _tree_plan(source, target)
    if not changed:
        return []
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=_copy_ignore)
    return [target.as_posix()]


def _copy_docs(upstream_dir: Path, target_dir: Path) -> list[str]:
    source_docs = upstream_dir / "docs"
    target_docs = target_dir / "docs"
    changed: list[str] = []
    for name in DOC_ALLOWLIST:
        source = source_docs / name
        if not source.is_file():
            print(f"WARNING: upstream docs/{name} not found; leaving existing copy untouched")
            continue
        target = target_docs / name
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        target_docs.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        changed.append(f"docs/{name}")
    return changed


def _core_version(upstream_dir: Path) -> str:
    path = upstream_dir / "qqbot_studio" / "__init__.py"
    match = CORE_VERSION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Could not find qqbot_studio.__version__ in {path}")
    return match.group(1)


def _plugin_version(upstream_dir: Path) -> str:
    path = upstream_dir / "plugins" / "qqbot_enhancer" / "metadata.yaml"
    match = PLUGIN_VERSION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Could not find plugin version in {path}")
    return match.group(1)


def _source_sha(upstream_dir: Path, override: str | None) -> str:
    if override:
        value = override.strip()
    else:
        try:
            value = subprocess.check_output(
                ["git", "-C", str(upstream_dir), "rev-parse", "HEAD"], text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "Could not determine upstream git SHA; pass --source-sha for a "
                "non-git test fixture."
            ) from exc
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise ValueError(f"Upstream commit SHA must be 40 hex characters: {value!r}")
    return value.lower()


def _render_upstream_md(
    existing: str,
    *,
    commit: str,
    snapshot_date: str,
    core_version: str,
    plugin_version: str,
) -> str:
    text = existing
    replacements = (
        (r"(?m)^- Upstream snapshot commit: `[^`]+`$", f"- Upstream snapshot commit: `{commit}`"),
        (r"(?m)^- Snapshot date: .*$", f"- Snapshot date: {snapshot_date}"),
        (r"(?m)^- Upstream release line: .*$", f"- Upstream release line: v{core_version}"),
        (
            r"(?m)^- Bundled core version: `qqbot_studio\.__version__ == [^`]+`$",
            f"- Bundled core version: `qqbot_studio.__version__ == {core_version}`",
        ),
        (
            r"(?m)^- Plugin snapshot: `qqbot_enhancer` .*$",
            f"- Plugin snapshot: `qqbot_enhancer` {plugin_version}",
        ),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    if text == existing and "Upstream snapshot commit:" not in text:
        text = (
            "# Upstream snapshot\n\n"
            f"- Upstream snapshot commit: `{commit}`\n"
            f"- Snapshot date: {snapshot_date}\n"
            f"- Upstream release line: v{core_version}\n"
            f"- Bundled core version: `qqbot_studio.__version__ == {core_version}`\n"
            f"- Plugin snapshot: `qqbot_enhancer` {plugin_version}\n"
        )
    return text


def sync_upstream(
    upstream_dir: Path,
    target_dir: Path,
    *,
    dry_run: bool = False,
    source_sha: str | None = None,
    snapshot_date: str | None = None,
) -> list[str]:
    """Copy the upstream allowlist into target_dir and record the source SHA.

    Returns the relative paths that would change / did change. A dry-run only
    reports those paths and never writes to the target tree.
    """

    upstream_dir = Path(upstream_dir).resolve()
    target_dir = Path(target_dir).resolve()
    if not (upstream_dir / "qqbot_studio").is_dir():
        raise FileNotFoundError(
            f"Upstream directory does not look like qqbot-studio: {upstream_dir}"
        )
    commit = _source_sha(upstream_dir, source_sha)
    snapshot_date = snapshot_date or date.today().isoformat()
    core_version = _core_version(upstream_dir)
    plugin_version = _plugin_version(upstream_dir)

    changed: list[str] = []
    for relative_source, relative_target in MIRRORED_PATHS:
        source = upstream_dir / relative_source
        target = target_dir / relative_target
        if dry_run:
            if _tree_plan(source, target):
                changed.append(relative_target)
        else:
            if _mirror_tree(source, target):
                changed.append(relative_target)
    if dry_run:
        source_docs = upstream_dir / "docs"
        target_docs = target_dir / "docs"
        for name in DOC_ALLOWLIST:
            source = source_docs / name
            target = target_docs / name
            if source.is_file() and (
                not target.is_file() or source.read_bytes() != target.read_bytes()
            ):
                changed.append(f"docs/{name}")
    else:
        changed.extend(_copy_docs(upstream_dir, target_dir))

    commit_path = target_dir / ".upstream-commit"
    commit_payload = f"{commit}\n"
    if not commit_path.is_file() or commit_path.read_text(encoding="ascii") != commit_payload:
        changed.append(".upstream-commit")
        if not dry_run:
            commit_path.write_text(commit_payload, encoding="ascii")

    upstream_path = target_dir / "UPSTREAM.md"
    existing = upstream_path.read_text(encoding="utf-8") if upstream_path.is_file() else ""
    rendered = _render_upstream_md(
        existing,
        commit=commit,
        snapshot_date=snapshot_date,
        core_version=core_version,
        plugin_version=plugin_version,
    )
    if rendered != existing:
        changed.append("UPSTREAM.md")
        if not dry_run:
            upstream_path.write_text(rendered, encoding="utf-8")

    mode = "DRY-RUN" if dry_run else "SYNC"
    print(f"{mode}: upstream {UPSTREAM_REPO}@{commit}")
    print(f"  core={core_version} plugin={plugin_version} snapshot={snapshot_date}")
    if changed:
        print("  changed:")
        for path in sorted(set(changed)):
            print(f"    {path}")
    else:
        print("  no changes")
    return sorted(set(changed))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-dir", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source-sha", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--snapshot-date", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        sync_upstream(
            args.upstream_dir,
            args.target_dir,
            dry_run=args.dry_run,
            source_sha=args.source_sha,
            snapshot_date=args.snapshot_date,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
