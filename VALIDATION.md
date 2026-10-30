# Validation record

## v0.7.1 / Native Windows POC (latest development)

This is a development/POC addition, not a new tagged Release. Bundled core remains
`3.9.0` / plugin `1.15.0`; Windows VERSION is `0.7.1`.

### Native process manager implemented

- `windows/native_runtime.py` single-instance runtime manager:
  - native root `%LOCALAPPDATA%\QQBotStudio\data\native` (override with `--data-dir`);
  - `native.json` config, `run/*.json` PID/runtime records, `logs/*.log`;
  - AstrBot `ASTRBOT_ROOT` and command, SnowLuma working directory/launcher,
    NTQQ path, loopback WebUI/OneBot ports;
  - `--start/--restart/--stop/--status/--health/--logs`;
  - port conflict checks and loopback-only default;
  - SnowLuma `config/onebot.json` writer with `ws://127.0.0.1:<port>/ws`, shared
    token, and `statusCommand.enabled=false` (`#sl` disabled);
  - `--open-qq` only opens the official local NTQQ; no password/captcha
    automation and no noVNC.
- Missing AstrBot/SnowLuma/NTQQ prerequisites produce explicit
  `NATIVE_START=BLOCKED`; the old bootstrap-only behavior is removed.

### Tests and smoke

- Linux and Windows Python: **90 tests OK** (Linux skips 1 Windows-only test).
- Real-component validation summary: `docs/native-e2e-validation.md`.
- Native POC process smoke on Windows using the built Native EXE and two real
  local fake Python service processes:
  - configure with fake NTQQ path and explicit AstrBot/SnowLuma commands;
  - strict prerequisite check exit 0;
  - SnowLuma OneBot config written with URL `ws://127.0.0.1:19899/ws` and
    `statusCommand.enabled=false`;
  - `--start` exit 0, both processes reported running with real PIDs;
  - logs contained the service marker;
  - `--stop` exit 0 and both PIDs/processes disappeared;
  - status after stop showed both services not running.
- Additional Native EXE health smoke with two real local fake HTTP services:
  - fake AstrBot returned HTTP 200 on its WebUI port and listened on the
    OneBot TCP port; fake SnowLuma returned HTTP 200 on its WebUI port;
  - `--health` exit 0 and printed `NATIVE_HEALTH_OK=True`;
  - status showed both processes running and `onebot.listening=true`;
  - logs contained both service-ready markers;
  - after `--stop`, no managed process remained.
- Real-component validation in a temporary Windows data directory:
  - installed AstrBot 4.29.3 via uv/Python 3.12.14 and official SnowLuma 2.2.1
    win-x64-lite + official Node 26.13.0;
  - configured NTQQ `D:\Program Files\Tencent\QQ.exe` (9.9.19.35469);
  - `--check --strict-check` exit 0 and `--write-onebot-config` exit 0;
  - `--start` exit 0 with real AstrBot/SnowLuma PIDs;
  - AstrBot WebUI HTTP 200 at 16185; SnowLuma WebUI HTTP 200 at 5099
    (effective port read from SnowLuma `config/runtime.json`);
  - OneBot `ws://127.0.0.1:16199/ws` TCP listener=true; health
    `NATIVE_HEALTH_OK=True`;
  - `--logs` exit 0 with AstrBot started/SnowLuma listening markers;
  - `--stop` exit 0 and all three ports closed.
- Real-component blockers: SnowLuma EULA/PRIVACY consent and QQ
  scan/device/SMS/slider verification were not automated; no QQ login,
  SnowLuma→AstrBot handshake or QQ message E2E is claimed.
- Native EXE build after the Native POC fixes:
  - Docker `QQBotStudioWindows.exe`: `8,567,126` bytes, SHA256
    `7478d9581fa9963e92b58b3cf5e4db7e37a810562e0384fd8bcef0407fdae76f`;
  - Native `QQBotStudioWindowsNative.exe`: `6,965,919` bytes, SHA256
    `53950b2a57498523a1076e47ad47d7f76c8959718055b3b9cd58c78eac340fea`.
- `--version`: `QQ Bot Studio Windows Native POC 0.7.1 (bundled core 3.9.0)`.

### Native POC limitations / blockers

- Real AstrBot/SnowLuma were installed in a temporary directory, not into the
  user's persistent profile or a formal instance. The 90-test suite was run
  against the Windows repo, but this is not a production install.
- SnowLuma EULA/PRIVACY consent and QQ scan/device/SMS/slider verification were
  not automated. No real QQ login, SnowLuma hook compatibility or
  SnowLuma→AstrBot OneBot handshake is claimed; only AstrBot's OneBot TCP
  listener was verified.
- AstrBot needs a user/WebUI-provided `cmd_config.json`; the Native POC does not
  generate the complete AstrBot config. SnowLuma WebUI port is taken from its
  own `config/runtime.json`.
- Single-instance only. Multi-instance, NTQQ multi-open, desktop isolation,
  QQ version compatibility and long-running stability are not supported/claimed.
- `--open-qq` was not invoked in automation to avoid disturbing the user's real
  QQ session; NTQQ discovery was tested read-only.
- Native POC is not part of v0.7.0 Release assets; it is a development build.

---

## v0.7.0 / core 3.9.0 / plugin 1.15.0 dual-edition release (previous)

This development version adds:

- Windows file-location documentation and safe `--move-data <NEW_DIR>`;
- allowlisted Linux-upstream synchronization (`sync-upstream`) with
  `.upstream-commit` and `UPSTREAM.md` recording;
- Docker and Native bootstrap one-file EXE builds in one release workflow.

Committed upstream snapshot used for this validation:
`6ed41b9b281e01b48e3f58e4ad088f3afdebe2df` (Linux `main`, v3.9.0).
Bundled versions: core `3.9.0`, qqbot_enhancer `1.15.0`. Windows version
`0.7.0`.

### Upstream sync workflow and local verification

Implemented:

- `.github/workflows/sync-upstream.yml`: `workflow_dispatch` with dry-run input,
  daily schedule, `contents: write`, checkout of public
  `Stevehim2007/qqbot-studio@main`, tests before commit, and no empty commit;
  workflow URL:
  https://github.com/Stevehim2007/qqbot-studio-windows/actions/workflows/sync-upstream.yml;
- `scripts/sync_upstream.py`: allowlist mirrors `qqbot_studio/` (including
  static), `plugins/qqbot_enhancer/`, `assets/`; copies only allowlisted docs;
  preserves Windows launcher/PowerShell/build/spec/VERSION/release workflows
  and Windows-specific `docs/README.md` + `docs/FAQ.md`;
- `.upstream-commit` stores the full upstream SHA; `UPSTREAM.md` is updated with
  snapshot date, core/plugin versions, and Linux commit.

Local verification (actual script, clean upstream worktree at the committed
SHA):

- dry-run reported the expected allowlisted changes without writing;
- actual sync copied core `3.9.0`, plugin `1.15.0`, assets, and the upstream
  Windows-editions research doc;
- `.upstream-commit` = `6ed41b9b281e01b48e3f58e4ad088f3afdebe2df`;
- second run reported `no changes` and did not modify files;
- Windows-owned launcher/build/spec/VERSION/release workflow files were
  preserved;
- local tests passed after sync.

The GitHub Actions `workflow_dispatch`/schedule run itself was **not executed**
in this task (workflow files and local script were validated; no authenticated
remote dispatch was available). Manual trigger:
`Actions -> Sync upstream Linux snapshot -> Run workflow`.

### Dual EXE build

`windows/build.ps1 -Clean` on Windows Python 3.10.9 + PyInstaller 6.10.0 built
and smoke-tested both EXEs:

- Docker edition `QQBotStudioWindows.exe`:
  - size `8,567,120` bytes;
  - SHA256 `e277c8428751204fd7d39296c444aade16370a3b6a513d7cea16c90d24344154`;
  - `--version`: `QQBot Studio Windows launcher 0.7.0 (core 3.9.0)`;
  - `--help` exit 0.
- Native bootstrap/guide `QQBotStudioWindowsNative.exe`:
  - size `6,405,952` bytes;
  - SHA256 `5d6dd0f12adb531edf174d871d229cadba84f63744de2f9c9399648a43ce3da4`;
  - `--version`: `QQ Bot Studio Windows Native bootstrap 0.7.0 (bundled core 3.9.0)`;
  - `--help`, `--guide`, `--check` exit 0; guide/check explicitly report
    `NATIVE_E2E=NOT_VERIFIED` and `NATIVE_INTEGRATION=NOT_IMPLEMENTED_IN_BOOTSTRAP`.

`dist/SHA256SUMS.txt` contains both local v0.7.0 builds. Local and CI one-file
EXEs are not byte-identical; the official Release sizes and SHA256 digests are
recorded in the dual release section below.

### Migration behavior and tests

Implemented behavior:

- target must be an absolute path on a local fixed NTFS drive;
- target must be absent or empty; no implicit merge is performed;
- WSL/Docker Desktop filesystem paths, UNC/network shares, mapped/remote drives,
  OneDrive paths, removable/unknown drives, drive roots, non-writable ACLs and
  source/target nesting are rejected;
- management service is stopped before copying;
- every instance with a `compose.yml` in the old data directory gets
  `docker compose down --remove-orphans`;
- data is copied to a staging directory in the target parent, then published
  with `os.replace`; the old data directory is retained;
- `windows-data-move.json` and `studio.json` migration fields are written;
- `%LOCALAPPDATA%\QQBotStudio\data-location.json` is updated atomically;
- CLI `--move-data` deliberately does not auto-restart services/containers;
- failure cleans staging/published target and keeps the old directory;
- PowerShell fallback `Resolve-StudioDataDir` reads the same pointer file;
- the console uses a Windows-owned token-protected extension
  (`windows/console_move_ext.py`) and a detached same-EXE helper:
  - `POST /api/system/move-data` with `{target, confirm:true}` validates the
    path without shell interpolation and schedules the helper;
  - `GET /api/system/move-data/status` is token-protected;
  - helper stops the server with `taskkill` without `/T` so the detached helper
    survives, then stops Compose projects, copies/rolls back data, updates the
    pointer, and restarts the management service from the new directory;
  - the UI is injected at runtime by `/windows-console-move.js` and
    `/windows-console-move.css`, so upstream static sync does not erase it.

Tests:

- Linux Python: `python3 -m unittest discover -s tests -v` -> **82 tests OK
  (1 Windows-drive test skipped)**.
- Windows Python 3.10.9: same suite -> **82 tests OK**.
- New tests cover migration copy/pointer/record/conflict/failure rollback,
  WSL/UNC/OneDrive drive-type validation, stop ordering, sync allowlist and
  preserve rules, upstream snapshot guard failures, dry-run/no-op behavior,
  dual workflow assets, and Native spec/build files.
- `python scripts/check_upstream_state.py --root .` passes on the final synced
  tree and fails when vendored core/plugin metadata does not match UPSTREAM.md.
- Windows `compileall`, PowerShell AST, static UI and YAML checks passed.
- Docker Desktop 4.93.0 / Engine 29.8.1 / Compose v5.5.1: busybox
  `config/up/down` all exit 0; container printed
  `qqbot-windows-v070-compose-smoke`, then container/network were removed.

### Real Docker-edition EXE smoke (current build)

Executed with the locally built `QQBotStudioWindows.exe` and isolated
`%LOCALAPPDATA%`:

- start with `--assistant` + new instance; `/healthz` returned
  `{"ok":true,"version":"3.9.0"}`;
- `/console` and `/assistant` both HTTP 200;
- `/console` contains the plugin editor and `/assistant` link;
- `--move-data` to a new empty local target exited 0;
- old data directory retained; target contains `studio.json`,
  `instances\bot-1\instance.json`, and `windows-data-move.json`;
- pointer file points at target; restarting with no `--data-dir` through the
  pointer succeeds; target `/healthz` is `3.9.0`; `--stop` makes health
  unreachable;
- token-protected plugin config API using the real 169-field bundled-schema fallback:
  - GET HTTP 200, defaults `reply_probability=0.12`,
    `user_sticker_reaction_enabled=true`;
  - POST `reply_probability=0.57`,
    `user_sticker_reaction_probability=0.72` returns `ok=true`,
    `restart_required=true`;
  - second GET reads `0.57`/`0.72`.
- An earlier current-launcher migration run also used a real busybox Compose
  project and confirmed `compose down` removed the container before publish.

### Console storage-folder migration smoke (current EXE)

Executed against the final v0.7.0/core 3.9.0 Docker EXE with isolated
`%LOCALAPPDATA%` and a real HTTP server:

- `/console` contained `/windows-console-move.js` and
  `/windows-console-move.css`; both asset endpoints returned HTTP 200;
- status API without token returned HTTP 403; with token returned `status=idle`;
- relative path POST returned HTTP 400;
- valid empty local target POST returned HTTP 200 / `scheduled`;
- helper stopped/restarted the management service; polling observed
  `scheduled` then `completed`; the restarted `/console` returned HTTP 200;
- target contained `studio.json` and `windows-data-move.json`; target request
  marker was removed; source/old directory was retained; pointer pointed at
  target; `--stop` after the move made health unreachable;
- no instance-local `_conf_schema.json` was created: GET returned
  `schema_source=bundled` and the bundled `_MEI.../plugins/qqbot_enhancer/_conf_schema.json`
  path with 169 fields; `food_enabled`, `group_persona_enabled`,
  `group_personas`, `ai_unified_tool_protocol_enabled` and safe-tool
  permission fields were present;
- POST set `reply_probability=0.58`, `user_sticker_reaction_probability=0.73`,
  `safe_tools_allow_search_images=false`, and a two-group `group_personas`
  JSON; `restart_required=true`; after migration and service restart the new
  server GET still returned 169 bundled-schema fields and persisted values,
  including the group persona JSON;
- console/static: AI 工具权限/AI 自动表情 UI, `/components/instance-settings.js`,
  `/services/plugin-config.js`, `/windows-console-move.js` returned HTTP 200;
- partial stats: `ok=true`, `partial=true`; B diagnostics returned HTTP 200
  with `healthy=false`, `error_code=not_installed` and listener/local_health/
  public_probe fields;
- plugin list returned the local offline fallback; plugin toggle returned HTTP
  400 for the undeployed instance (expected offline behavior);
- console storage UI assets and token migration were verified in the same run.
- The test did not run a real browser click flow; UI static/asset and HTTP API
  behavior were verified. Browser automation remains a limitation.

### Dual release workflow status (actual)

- Dual build CI run `41078163641` for commit
  `ba3100108280f54c8004a7ef33f7abf3a6a18baa`: success; artifact
  `QQBotStudioWindows-dual-ba3100...` size `19,070,883` bytes.
- `v0.7.0` tag was pushed at `ba3100108280f54c8004a7ef33f7abf3a6a18baa`.
- Dual release workflow run `41078425027`: success, all release steps passed
  including tag/VERSION, upstream snapshot gate, 82 tests, compileall,
  PowerShell AST, dual PyInstaller build, both EXE smokes, artifact upload and
  Create GitHub Release.
- Release URL:
  https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.7.0
- Public GitHub API confirms these assets:
  - `QQBotStudioWindows.exe`: `10,926,947` bytes, digest
    `sha256:eeb96134806c92356033590d71fc9a8af977cbbc8be4dd5600079acab32a664e`;
  - `QQBotStudioWindowsNative.exe`: `8,350,397` bytes, digest
    `sha256:f16284efa7fe933e3852359b4602b0e560ca4c59e0c45a367a6d305a8c1c2206`;
  - `SHA256SUMS.txt` downloaded and its two SHA256 lines matched the API
    digests;
  - `README.md` and `VALIDATION.md`.
- No Native AstrBot/SnowLuma/NTQQ E2E claim is made.

### Not verified for v0.7.0

- GitHub Actions `sync-upstream` dispatch/schedule run was not executed; only
  local script and workflow-file validation.
- No real AstrBot/SnowLuma deployment, QQ login, noVNC verification, DeepSeek
  call, or AI assistant B install/start.
- Native edition is a bootstrap/guide placeholder: no real NTQQ/SnowLuma hook,
  no AstrBot process management, no native OneBot connection, no multi-instance
  or noVNC implementation.
- Migration was tested with a synthetic busybox Compose project, not a full QQ
  bot; no real OneDrive/UNC/WSL mount or second physical disk was used.
- Browser auto-open and real browser DOM click automation for the console
  storage panel were not tested (API/assets/static JS were tested).
- Windows Defender/firewall/cloud security-group access, long-running
  multi-instance migration and actual user ACLs were not tested.
- Console migration smoke did not have a full AstrBot/SnowLuma Compose project;
  the `compose down` path was covered by the earlier synthetic-container test.

---

## v0.4.0 / core 3.5.0 / plugin 1.5.0 (previous)

Sync source: Linux main `d87f96561cd9167a0279584fffee7cc366564208`, clean
working tree, core `3.5.0`, plugin `1.5.0`, Windows launcher `0.4.0`.

New in this sync:

- qqbot_enhancer 1.5.0;
- pure Image/Face user reaction with `user_sticker_reaction_*` settings;
- `/收藏表情 [分类]`, `/表情分类`, `/表情列表 [分类]`, `/发表情 [分类]`;
- collected stickers participate in normal replies alongside built-in stickers;
- plugin schema expanded to 88 fields and remains editable through the Windows
  console/API.

### Test and static checks

- Linux Python: `python3 -m unittest discover -s tests -v` -> **45 tests OK**.
- Windows Python 3.10.9: same suite -> **45 tests OK**.
- Windows `python -m compileall -q qqbot_studio windows` -> OK.
- Windows PowerShell 5.1 AST parser: all `.ps1` files -> OK.
- `node --check` for `app.js`, `console.js`, and both `assistant.html` inline
  scripts -> OK.
- Both Windows workflow YAML files parsed successfully.
- Static checks verified plugin 1.5.0 metadata, new sticker commands, schema
  fields, docs, version `0.4.0`, and the release workflow `v*`/EXE/SHA256 path.

### Local Windows PyInstaller build

Command:

```powershell
.\windows\build.ps1 -Python C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe -Clean
```

Result:

- Build exited 0.
- Local pre-release EXE: `8,461,717` bytes
- SHA256: `2d44225206473101ca2a3a03f462afef86b5a0b2e47b8d6cddcbee4fe4d240db`
- `--version`: `QQBot Studio Windows launcher 0.4.0 (core 3.5.0)`
- `--help` exited 0.
- Local pre-release EXE is not expected to be byte-identical to the CI release
  EXE; the release SHA256 is authoritative.

### Real EXE / Windows Docker Desktop / API smoke

Executed with the locally built EXE on Windows 10/11 host:

- Docker Desktop 4.93.0, Engine 29.8.1, `OSType=linux`, Compose `v5.5.1`.
- `docker version`, `docker info`, `docker compose version` all exit 0.
- Minimal Compose fixture:
  - `config` exit 0;
  - `up --abort-on-container-exit --exit-code-from smoke` exit 0 and printed
    `qqbot-windows-v040-compose-smoke`;
  - `down --remove-orphans` exit 0; test container/network removed.
- EXE `--assistant` start:
  - start output selected `/assistant`;
  - `/healthz` -> `{"ok":true,"version":"3.5.0"}`;
  - `/console` and `/assistant` both HTTP 200;
  - `/console` has the plugin editor and `/assistant` link, and none of the old
    A/B DOM markers;
  - `/assistant` has public-host controls.
- Token-protected API:
  - `POST /api/instances` created `bot-1`;
  - GET `/api/instances/bot-1/plugins/qqbot_enhancer/config` returned HTTP 200,
    `ok=true`, 88 fields, defaults `reply_probability=0.12`,
    `user_sticker_reaction_enabled=true`, `collected_sticker_enabled=true`;
  - POST values `reply_probability=0.55`,
    `user_sticker_reaction_probability=0.7` returned HTTP 200, `ok=true`,
    `restart_required=true`;
  - a second GET returned `0.55` and `0.7`;
  - local plugin config JSON was written.
- EXE `--status` returned healthy and `--stop` exited 0; health became
  unreachable afterward.

### GitHub Release v0.4.0 (actual)

- Release tag: `v0.4.0`
- Tagged code commit: `6ef56ec6b1185a438f4451fb0066f113c7e697fe`
- Release workflow run: `40997401439`
- Run URL: https://github.com/Stevehim2007/qqbot-studio-windows/actions/runs/40997401439
- Conclusion: `success`
- All workflow steps succeeded, including tag/VERSION verification, 45 tests,
  compileall, PowerShell AST, PyInstaller build, EXE smoke, artifact upload, and
  Create GitHub Release.
- Release URL: https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.4.0
- Public GitHub API reported these release assets:
  - `QQBotStudioWindows.exe`: `10,803,066` bytes,
    digest `sha256:9bd92a299839fd3ec4a4c0c089356c98505fb17995edfee8d279e2b831e53f3b`;
  - `SHA256SUMS.txt`: downloaded, containing the same SHA256;
  - `README.md`;
  - `VALIDATION.md`.
- The local pre-release EXE differs by design from the CI release EXE:
  `8,461,717` bytes / `2d44225206473101ca2a3a03f462afef86b5a0b2e47b8d6cddcbee4fe4d240db`.
  The Release digest is authoritative for the published binary.
- An Actions-only artifact is not the release deliverable; the GitHub Release
  assets were confirmed.

### Not verified for v0.4.0

- No actual AstrBot + SnowLuma deployment through the wizard.
- No real DeepSeek API or QQ account login.
- No noVNC QR scan, device/SMS/email/slider verification.
- No AI assistant B installation/update/start beyond the status/page path.
- No browser auto-open test (`--no-open` was used).
- No Windows Defender firewall/cloud security-group remote-access test.
- No long-duration multi-instance or bind-mount ownership test.
- The new sticker reaction/collection commands were validated by static tests
  and plugin tests/schema, not against a live QQ/AstrBot session.

---

## v0.3.0 / core 3.4.0 sync (previous)

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

### GitHub Actions and Release (actual)

The release workflow was executed on tag `v0.3.0` and succeeded.

- Release tag: `v0.3.0`
- Tagged release commit: `5b540f08d1a8d4d7f6833c8a82d310eb305f9cf4`
- Release workflow run: `40995684732`
- Run URL: https://github.com/Stevehim2007/qqbot-studio-windows/actions/runs/40995684732
- Conclusion: `success`
- All steps succeeded:
  - checkout tagged source;
  - Python 3.12 setup;
  - tag/VERSION validation;
  - independent test suite;
  - Python compileall;
  - PowerShell AST validation;
  - PyInstaller one-file EXE build;
  - EXE `--version`/`--help` smoke;
  - workflow artifact upload;
  - Create GitHub Release and EXE assets upload.
- Release URL: https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.3.0
- Release assets confirmed through the public GitHub API:
  - `QQBotStudioWindows.exe` size `10,795,114` bytes;
  - GitHub API asset digest:
    `sha256:e676ded2bc78ca5b65ac45a11f98e9c1bbb11cd325d39791592242385aca08d0`;
  - `SHA256SUMS.txt` downloaded and contained the same digest;
  - `README.md`;
  - `VALIDATION.md`.
- GitHub's release asset CDN download of the EXE timed out from this WSL
  environment after the API metadata and SHA256SUMS download succeeded; the
  release EXE itself was built and smoke-tested by the successful Windows CI
  job. The digest was verified against the downloadable `SHA256SUMS.txt`.
- The local independently built EXE is intentionally listed above with a
  different digest; one-file artifacts are not guaranteed byte-identical across
  build hosts.

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
