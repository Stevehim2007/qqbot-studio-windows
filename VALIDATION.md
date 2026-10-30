# Validation record

## v0.3.0 / core 3.4.0 sync (latest)

Sync source: Linux main commit `1e9d4a46b0aba7f89519066693f95b5939c7732e`,
clean working tree, core `3.4.0`, plugin `1.4.1`, launcher `0.3.0`.

New in this sync:

- console plugin parameter editor and GET/POST plugin config API;
- `reply_probability` schema-driven editing and validation;
- sensitive Key/token/password fields excluded;
- tag-driven `windows-release.yml` publishing a real GitHub Release.

### Test and static checks

- Linux Python: `python3 -m unittest discover -s tests -v` -> **44 tests OK**.
- Windows Python 3.10.9: same independent suite -> **44 tests OK**.
- Windows `python -m compileall -q qqbot_studio windows` -> OK.
- Windows PowerShell 5.1 AST parser: all 5 `.ps1` files -> OK.
- `node --check` `app.js`, `console.js`, and both inline `<script>` blocks in
  `assistant.html` -> OK.
- Workflow YAML parsed successfully for both `windows-build.yml` and
  `windows-release.yml`.
- Static feature checks passed:
  - `/assistant` page/token and public-host controls;
  - console `/assistant` link and no old A/B DOM;
  - 30-minute auto-refresh;
  - plugin config panel IDs, `reply_probability` UI, and API URL;
  - plugin config API strings and schema-driven backend methods;
  - synced API contract includes plugin config endpoints;
  - release workflow has `v*` tag trigger, `contents: write`, EXE/SHA256 assets
    and `softprops/action-gh-release@v2`.

### Real Windows PyInstaller build

Command:

```powershell
.\windows\build.ps1 -Python C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe -Clean
```

Result:

- Build exited 0.
- Artifact: `dist\QQBotStudioWindows.exe`
- Version: launcher `0.3.0`, core `3.4.0`
- Size: `8,453,805` bytes
- SHA256: `a3eaa74880d5f64fe954c3842cb986dac782650d83a127422560ac172be144c1`
- EXE `--version` returned
  `QQBot Studio Windows launcher 0.3.0 (core 3.4.0)`; `--help` exited 0.

### Real EXE + Windows Docker Desktop smoke

A single Windows PowerShell smoke run started the built EXE with a temporary
data directory and `127.0.0.1:18781`, created isolated instance `bot-1`, and
then exercised the live service and Docker Desktop.

Verified:

- Docker Desktop 4.93.0, Engine 29.8.1, `OSType=linux`, Compose `v5.5.1`.
- `/healthz` returned `{"ok":true,"version":"3.4.0"}`.
- `/console` and `/assistant` both returned HTTP 200.
- `/console` contains the plugin editor panel and `href="/assistant"`, and does
  not contain old `assistant-open`, `assistant-panel`, `assistant-b-card`, or
  `使用助手` markers.
- `/assistant` contains the public-host mode controls and a real injected token.
- Plugin config API using `qqbot_enhancer` schema (61 fields):
  - GET returned HTTP 200, `ok=true`, source `local`, default
    `reply_probability=0.12`;
  - POST `{"values":{"reply_probability":0.5}}` returned HTTP 200, `ok=true`,
    `restart_required=true`, saved value `0.5`;
  - a second GET returned `0.5`;
  - the local config file was written without an AstrBot online dependency.
- EXE `--status` passed while the service was healthy and `--stop` stopped it;
  health became unreachable afterward.
- Minimal Docker Compose test:
  - `docker compose config` exit 0;
  - `docker compose up --abort-on-container-exit --exit-code-from smoke`
    printed `qqbot-windows-v034-compose-smoke` and exited 0;
  - `docker compose down --remove-orphans` exit 0;
  - no leftover test container.

### GitHub Actions and Release

- `windows-build.yml` is intended to run for push/PR and upload a workflow
  artifact.
- `windows-release.yml` is intended to run for `v*` tags, verify the tag matches
  `VERSION`, rebuild the EXE, and create a real GitHub Release with
  `QQBotStudioWindows.exe` and `SHA256SUMS.txt`.
- Release execution result is recorded after the tag is pushed. This section is
  updated by a follow-up docs commit if needed; it is not a substitute for a
  GitHub Release asset.

### Not verified for v0.3.0

- No actual AstrBot + SnowLuma deployment through the wizard.
- No real DeepSeek API or QQ account login.
- No noVNC QR scan, device/SMS/email/slider verification.
- No AI assistant B installation/update/start (the `/assistant` page and status
  route were exercised only in the not-installed state).
- No browser auto-open test (`--no-open` was used).
- No Windows Defender firewall/cloud-security-group remote-access test.
- No long-duration multi-instance or bind-mount ownership test.

---

## v0.2.0 / core 3.3.0 sync (previous)

Sync source: Linux main commit `7cdeb0ecc60066eb7df7702777289aa03a6f8bd1`,
core `3.3.0`, plugin `1.4.1`.

### Test and static checks

- Linux Python: `python3 -m unittest discover -s tests -v` -> **42 tests OK**.
- Windows Python 3.10.9: same independent suite -> **42 tests OK**.
- Windows `python -m compileall -q qqbot_studio windows` -> OK.
- Windows PowerShell 5.1 AST parser: all 5 `.ps1` files -> OK.
- `node --check` for `app.js` and `console.js` -> OK.
- All two inline `<script>` blocks in `assistant.html` extracted and
  `node --check` -> OK.
- Static regression checks passed:
  - `/assistant` contains `window.QB_TOKEN = "{{TOKEN}}"`;
  - `host-public`, `public-host`, independent/instance key selectors present;
  - console has `href="/assistant"`;
  - console has no `assistant-open`, `assistant-panel`, `assistant-b-card` or
    old offline “使用助手” markers;
  - console refresh interval is `30 * 60 * 1000`;
  - plugin metadata version is `1.4.1`;
  - synced API contract contains `/assistant`, assistant config/start APIs and
    `public_host`.

### Real Windows PyInstaller build

Command:

```powershell
.\windows\build.ps1 -Python C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe -Clean
```

Result:

- Build exited 0.
- Artifact: `dist\QQBotStudioWindows.exe`
- Version: launcher `0.2.0`, core `3.3.0`
- Size: `8,438,864` bytes
- SHA256: `830a7c920d280c2819abdb82da28745b6fac01f72ec1ba8e514a6440fac14fba`
- EXE `--version` returned
  `QQBot Studio Windows launcher 0.2.0 (core 3.3.0)`; `--help` exited 0.

### Real Windows EXE service smoke

Commands used a temporary data directory and `127.0.0.1:18770`:

```powershell
.\QQBotStudioWindows.exe --assistant --configure --non-interactive \
  --data-dir <tmp> --ip 127.0.0.1 --port 18770 \
  --public-host 127.0.0.1 --no-open
Invoke-RestMethod http://127.0.0.1:18770/healthz
.\QQBotStudioWindows.exe --restart --new-instance "V3 Sync Smoke" \
  --non-interactive --data-dir <tmp> --no-open
.\QQBotStudioWindows.exe --status --data-dir <tmp>
.\QQBotStudioWindows.exe --stop --data-dir <tmp>
```

Verified:

- Docker Desktop 4.93.0 / Linux engine 29.8.1 was started and checked
  (`OSType=linux`, Compose v5.5.1).
- `/healthz` returned `{"ok":true,"version":"3.3.0"}`.
- `/assistant` returned HTTP 200 and injected a real token.
- `/api/assistant/status` with `X-QB-Token` returned HTTP 200 for the
  not-installed state and did not expose an `api_key` field.
- `/console` returned HTTP 200, contained `href="/assistant"`, and contained
  none of the old A/B DOM markers.
- `--assistant` selected the `/assistant` browser target.
- `--restart` stopped the old PID and started a new healthy PID.
- `--new-instance "V3 Sync Smoke"` created isolated `instances\bot-1`
  metadata and printed console and wizard URLs.
- `--stop` terminated the service; health became unreachable afterward.
- No PyInstaller temporary-directory warning was observed after the
  `PYINSTALLER_RESET_ENVIRONMENT=1` fix.

### GitHub Actions for v0.2.0

The `windows-latest` workflow ran on the synced repository and succeeded.

- Run id: `40895998356`
- Source commit: `9b4e44ad427dfb6889c4578c75d7e86a0685f639`
- Conclusion: `success`
- URL: https://github.com/Stevehim2007/qqbot-studio-windows/actions/runs/40895998356
- Artifact name: `QQBotStudioWindows-9b4e44ad427dfb6889c4578c75d7e86a0685f639`
- Artifact size: `10,688,179` bytes
- Artifact uploaded, not expired at query time.
- Successful steps: checkout, Python 3.12 setup, 42-test suite, Python
  compileall, PowerShell AST validation, one-file EXE build, EXE
  `--version`/`--help` smoke, and artifact upload.

A docs-only follow-up commit may have its own workflow run and artifact with a
different size; the final task report states the latest result.

### Not verified for v0.2.0

- Actual AI assistant B installation/update from GitHub and its real startup.
- Actual AstrBot + SnowLuma deployment through the wizard.
- Real DeepSeek API requests and QQ account login.
- noVNC QR scan, device/SMS/email/slider verification.
- Windows Defender firewall/cloud security-group remote access.
- Browser auto-open (all service checks used `--no-open`).
- Long-duration multi-instance or container bind-mount ownership behavior.

---

## Historical v0.1.0 validation

Date: 2026-10-29 (local test machine time)
Repository version: `VERSION 0.1.0`, bundled core `2.2.0`

This file records what was actually executed, and what remains unverified. It is
not a claim that the complete QQ login/deployment chain was tested.

## Environment actually used

- Windows processes were reachable through WSL interop on the same host.
- Windows: `Windows-10-10.0.26200-SP0` as reported by PyInstaller.
- Windows PowerShell: `5.1.26100.9444`.
- Windows Python: `3.10.9` x64 at
  `C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe`.
- Docker Desktop: `4.93.0 (240920)`.
- Docker CLI/Engine: `29.8.1`, `OSType=linux`, context `desktop-linux`.
- Docker Compose: `v5.5.1`.
- Build tool: PyInstaller `6.10.0` from `requirements-build.txt`.

## Passed checks

### Python source and unit tests

Commands:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q qqbot_studio windows
```

Results:

- 31 independent tests passed under both Linux Python 3.12 and Windows Python
  3.10.9.
- `compileall` passed for `qqbot_studio` and `windows`.
- Launcher source smoke:
  - `python.exe windows\launcher.py --version` printed
    `QQBot Studio Windows launcher 0.1.0 (core 2.2.0)`.
  - `python.exe windows\launcher.py --help` exited 0.

### PowerShell and workflow static checks

- Windows PowerShell 5.1 AST parser successfully parsed
  `windows\common.ps1`, `install.ps1`, `start.ps1`, `console.ps1`,
  `build.ps1`.
- `.github/workflows/windows-build.yml` parsed as YAML and was normalized with
  PyYAML; `runs-on: windows-latest`, `setup-python`, `build.ps1`, and
  `upload-artifact@v4` are present.
- PyInstaller spec compiles as Python source.

### Docker Desktop on Windows

Commands (Windows Docker CLI at `E:\Docker\resources\bin\docker.exe`):

```powershell
docker version
docker info --format "ServerVersion={{.ServerVersion}} OSType={{.OSType}} OS={{.OperatingSystem}}"
docker compose version
```

Results:

- Client and server both returned successfully.
- Server reported `OSType=linux`, Docker Desktop 4.93.0, Engine 29.8.1.
- Compose reported `v5.5.1`.

A minimal Compose project using `busybox:latest` was created and run:

```powershell
docker compose --project-directory <tmp> -f <tmp>\compose.yml config
docker compose --project-directory <tmp> -f <tmp>\compose.yml up \
  --abort-on-container-exit --exit-code-from smoke
docker compose --project-directory <tmp> -f <tmp>\compose.yml down --remove-orphans
```

Results: config exited 0; image pulled; container printed
`qqbot-windows-compose-smoke`; container exited 0; `down` removed the container
and network.

### GitHub Actions windows-latest run

The repository was pushed and GitHub Actions actually ran the workflow on a
GitHub-hosted Windows runner.

- Workflow: `Windows EXE build`
- Run id: `40862213882`
- Commit: `46f4bee1fb805f05ac6f59e265cc4ca884d6f9ac`
- Conclusion: `success`
- URL: https://github.com/Stevehim2007/qqbot-studio-windows/actions/runs/40862213882

Successful steps included:

- Checkout;
- Set up Python 3.12;
- Run independent test suite;
- Compile Python sources;
- Validate PowerShell syntax;
- Build one-file EXE;
- Smoke-test EXE with `--version`/`--help`;
- Upload Windows artifact.

### Real one-file EXE build

Command:

```powershell
.\windows\build.ps1 -Python C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe -Clean
```

Results:

- Build exited 0.
- Artifact: `dist\QQBotStudioWindows.exe`
- Size: `7,574,666` bytes
- SHA256: `8a8082056ed490e77bba17b93888b94c01b5277313eb9b2a053c0b235d138e4e`
- EXE `--version` and `--help` smoke tests exited 0.

This local artifact intentionally is not committed to the repository.

### Real EXE service lifecycle

The built EXE was invoked with temporary independent data directories on
`127.0.0.1:18767` and `127.0.0.1:18768`:

```powershell
.\QQBotStudioWindows.exe --non-interactive --data-dir <tmp> \
  --ip 127.0.0.1 --port 18767 --public-host 127.0.0.1 --no-open
.\QQBotStudioWindows.exe --status --data-dir <tmp>
Invoke-RestMethod http://127.0.0.1:18767/healthz
.\QQBotStudioWindows.exe --stop --data-dir <tmp>

.\QQBotStudioWindows.exe --configure --non-interactive --restart \
  --new-instance "Final EXE Smoke" --data-dir <tmp2> \
  --ip 127.0.0.1 --port 18768 --public-host 127.0.0.1 --no-open
.\QQBotStudioWindows.exe --status --data-dir <tmp2>
Invoke-RestMethod http://127.0.0.1:18768/healthz
.\QQBotStudioWindows.exe --stop --data-dir <tmp2>
```

Verified:

- Parent exited while hidden management service remained healthy.
- `/healthz` returned `{"ok":true,"version":"2.2.0"}`.
- `server.pid` and `server-runtime.json` matched the running process.
- Process command line included `QQBotStudioWindows.exe --serve-management ...`.
- `--status` returned healthy with matching runtime.
- `--restart` stopped the old PID and started a new healthy PID.
- `--new-instance "EXE Smoke"` and the final rebuilt artifact's
  `--new-instance "Final EXE Smoke"` created isolated `instances\bot-1`
  metadata and printed both console and wizard URLs.
- `--stop` terminated the service and the health endpoint became unreachable.
- After adding `PYINSTALLER_RESET_ENVIRONMENT=1` for self-spawned one-file child
  processes, the prior "Failed to remove temporary directory" bootloader warning
  was no longer observed.

### Instance metadata

The EXE-created `bot-1` had isolated:

```text
project_name: qqbot-studio-bot-1
astrbot_container: qqbot-bot-1-astrbot
snowluma_container: qqbot-bot-1-snowluma
network_name: qqbot-studio-bot-1-net
```

No AstrBot, SnowLuma, DeepSeek or real QQ deployment was started.

## Not verified / still required

- Future workflow runs must still be observed after subsequent pushes; the
  first push/run is confirmed successful. The locally built EXE and the CI-built
  EXE are not byte-identical by design because build timestamps/paths may differ.
- No browser auto-open test; all service lifecycle tests used `--no-open`.
- No `install.ps1` end-to-end test, winget install, or WSL setup/reboot test.
- No Windows Defender Firewall rule, cloud security-group, remote LAN, or VPN
  access test.
- No real AstrBot + SnowLuma deployment through the wizard.
- No real DeepSeek API deployment or QQ account login.
- No noVNC QR scan, device verification, SMS/email verification, or slider test.
- No long-duration multi-instance or container bind-mount ownership test.
- No test of the actual user-facing browser console beyond HTTP `/healthz`.
