# Upstream snapshot

This repository is an independent Windows distribution. It vendors the
reusable Python/UI core from the Linux project instead of fetching code at
runtime or build time.

- Upstream project: `git@github.com:Stevehim2007/qqbot-studio.git`
- Upstream snapshot commit: `7cdeb0ecc60066eb7df7702777289aa03a6f8bd1`
- Snapshot date: 2026-10-29
- Upstream release line: v3.3.0
- Bundled core version: `qqbot_studio.__version__ == 3.3.0`
- Windows launcher version: `0.2.0`
- Plugin snapshot: `qqbot_enhancer` 1.4.1

The upstream working tree was clean at the snapshot commit. This repository is
now the source of truth for the Windows distribution; do not point it at a
Linux data directory or the Linux auto-update pipeline.

## What this snapshot includes

- `/assistant` standalone page and server route;
- removal of the old offline assistant-A panel and embedded assistant-B card
  from the Windows console;
- 30-minute console auto-refresh and manual refresh;
- AI assistant B loopback and explicit `0.0.0.0 + public_host` public mode;
- `qqbot_enhancer` 1.4.1 with natural-language image search, downloaded image
  sending, local song playback, `/option`, and memory-mode support;
- latest API contract, plugin documentation, troubleshooting and QA references
  under `docs/`;
- Windows launcher/services/PowerShell/PyInstaller/CI files maintained here.

## Vendored / synced paths

- `qqbot_studio/` - Python management/deployment core and static UI, including
  `static/assistant.html`;
- `plugins/qqbot_enhancer/` - AstrBot plugin installed by the deployer;
- `assets/qqbot-studio.svg` - console icon;
- `docs/` - synced API/plugin/FAQ/reference documentation plus a Windows index;
- `tests/` - Windows-focused independent test suite;
- `windows/` - standalone Windows launcher, PowerShell fallback scripts,
  PyInstaller spec and build script.

The following Windows-owned files are intentionally preserved across upstream
syncs:

- `windows/launcher.py`
- `windows/build.ps1`
- `windows/qqbot-studio-windows.spec`
- `windows/install.ps1`, `start.ps1`, `console.ps1`, `common.ps1`
- `.github/workflows/windows-build.yml`
- Windows-specific README/UPSTREAM/VALIDATION/tests

## Updating from upstream

1. Fetch/pull the desired clean Linux main commit.
2. Copy upstream `qqbot_studio/`, `plugins/qqbot_enhancer/`, `assets/` and the
   API/plugin/FAQ docs into a branch of this repository.
3. Review Windows compatibility changes and re-apply any Windows launcher/CI
   adjustments that are intentionally local to this repository.
4. Update `VERSION`, this file, the Windows README and `VALIDATION.md`.
5. Run:

   ```powershell
   python -m unittest discover -s tests -v
   python -m compileall -q qqbot_studio windows
   .\windows\build.ps1 -Clean
   ```

6. Confirm `QQBotStudioWindows.exe --version`, `--help`, and (on a Windows host
   with Docker Desktop) `--assistant`, service health, `--status`, `--stop`.
7. Push and confirm the `windows-latest` CI workflow is green and uploads the
   artifact.
8. Only then announce the Windows artifact. Never claim unexecuted AstrBot,
   SnowLuma, QQ, noVNC or DeepSeek end-to-end tests.

Do not copy the Linux project's `install.sh`, `start.sh`, `console.sh`, screen
sessions, systemd units or Linux auto-update script into this repository as the
runtime mechanism. The Windows release continues to use its own EXE/PowerShell
service lifecycle.
