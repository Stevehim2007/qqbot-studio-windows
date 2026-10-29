# Validation record

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

- GitHub Actions workflow has **not** actually run on a GitHub-hosted
  `windows-latest` runner. The YAML syntax was checked locally and the same
  PyInstaller build path succeeded on the local Windows host.
- No browser auto-open test; all service lifecycle tests used `--no-open`.
- No `install.ps1` end-to-end test, winget install, or WSL setup/reboot test.
- No Windows Defender Firewall rule, cloud security-group, remote LAN, or VPN
  access test.
- No real AstrBot + SnowLuma deployment through the wizard.
- No real DeepSeek API deployment or QQ account login.
- No noVNC QR scan, device verification, SMS/email verification, or slider test.
- No long-duration multi-instance or container bind-mount ownership test.
- No test of the actual user-facing browser console beyond HTTP `/healthz`.
