# Upstream snapshot

This repository is an independent Windows distribution. It vendors the
reusable Python/UI core from the Linux project instead of fetching code at
runtime or build time.

- Upstream project: `git@github.com:Stevehim2007/qqbot-studio.git`
- Snapshot base commit: `9eeb860f23af8a6f20dbfed4174a268e9b0e058b`
- Snapshot date: 2026-10-29
- Bundled core version: `qqbot_studio.__version__ == 2.2.0`
- Windows launcher version: `0.1.0`

The snapshot includes Windows-compatibility work that was present in the
upstream working tree at snapshot time. The exact source commit alone is not
enough to reproduce that working-tree state; this repository is now the source
of truth for the Windows distribution.

## Vendored paths

- `qqbot_studio/` - Python management/deployment core and static UI
- `plugins/qqbot_enhancer/` - AstrBot plugin installed by the deployer
- `assets/qqbot-studio.svg` - console icon
- `tests/` - a Windows-focused independent test suite
- `windows/` - standalone Windows launcher, PowerShell fallback scripts and
  PyInstaller build configuration

## Updating from upstream

1. Copy the desired upstream `qqbot_studio/`, `plugins/qqbot_enhancer/` and
   `assets/` into a branch of this repository.
2. Re-apply or review Windows compatibility changes.
3. Run `python -m unittest discover -s tests -v` and `python -m py_compile`.
4. Build the EXE with `windows/build.ps1 -Clean`.
5. Update this file with the upstream commit/date and bump `VERSION`.
6. Test first-run configuration, Docker Desktop, service PID/logs/health and
   noVNC QR login on a real Windows 10/11 host before release.

Do not copy the Linux project's `install.sh`, `start.sh`, `console.sh`, screen
sessions, systemd units or Linux auto-update script into this repository.
