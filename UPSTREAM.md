# Upstream snapshot

This repository is an independent Windows distribution. It vendors the
reusable Python/UI core from the Linux project instead of fetching code at
runtime or build time.

- Upstream project: `git@github.com:Stevehim2007/qqbot-studio.git`
- Upstream snapshot commit: `51238d33e5aebd4e7148aaba0bf45c6c71415567`
- Snapshot date: 2026-10-30
- Upstream release line: v3.8.0
- Bundled core version: `qqbot_studio.__version__ == 3.8.0`
- Windows launcher version: `0.6.0`
- Plugin snapshot: `qqbot_enhancer` 1.12.0

The upstream working tree was clean at the snapshot commit. This repository is
now the source of truth for the Windows distribution; do not point it at a
Linux data directory or the Linux auto-update pipeline.

## What this snapshot includes

- `/assistant` standalone page and server route;
- removal of the old offline assistant-A panel and embedded assistant-B card
  from the Windows console;
- 30-minute console auto-refresh and manual refresh;
- AI assistant B loopback and explicit `0.0.0.0 + public_host` public mode;
- **plugin parameter read/edit API and console panel**:
  - GET/POST `/api/instances/<instance_id>/plugins/<plugin_id>/config`;
  - schema-driven bool/int/float/string/text/list validation;
  - `reply_probability` highlighted editor and offline restart guidance;
  - sensitive Key/token/password fields excluded;
- `qqbot_enhancer` 1.12.0 with natural-language image search, downloaded image
  sending, local song playback, `/option`, memory-mode support, pure Image/Face
  automatic reactions, collected-sticker categories, and
  `/收藏表情`, `/表情分类`, `/表情列表`, `/发表情` commands;
- latest API contract, plugin documentation, troubleshooting and QA references
  under `docs/`;
- Windows launcher/services/PowerShell/PyInstaller/CI files maintained here,
  plus tag-driven GitHub Release publishing of the EXE and SHA256.

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
- `.github/workflows/windows-release.yml`
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
   with Docker Desktop) `--assistant`, plugin-config API, service health,
   `--status`, and `--stop`.
7. Push main and confirm `windows-build.yml` succeeds.
8. Push a `v<version>` tag and confirm `windows-release.yml` creates a real
   GitHub Release with `QQBotStudioWindows.exe` and `SHA256SUMS.txt` assets.
9. Only then announce the Windows release. Never claim unexecuted AstrBot,
   SnowLuma, QQ, noVNC or DeepSeek end-to-end tests.

Do not copy the Linux project's `install.sh`, `start.sh`, `console.sh`, screen
sessions, systemd units or Linux auto-update script into this repository as the
runtime mechanism. The Windows release continues to use its own EXE/PowerShell
service lifecycle.
