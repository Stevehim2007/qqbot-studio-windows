# Windows PowerShell 备用入口

本文件说明独立 Windows 仓库中的 PowerShell 备用脚本。推荐日常入口是根目录 README
所述的 `QQBotStudioWindows.exe`。

> **项目边界：** 本仓库是 Windows 10/11 + Docker Desktop + WSL2 独立发行项目；
> `qqbot-studio` 是 Ubuntu/Linux 主项目。两者数据目录、版本和升级边界不同，不能
> 直接共用。完整说明见根目录 [`README.md`](../README.md) 和
> [`UPSTREAM.md`](../UPSTREAM.md)。
>
> **状态：Windows v0.8.0 发布候选（最新正式 Release 为 v0.7.0），已同步 upstream core 3.12.0。** Docker edition 稳定；Native edition 为单实例 POC 进程管理器。已包含独立
> `/assistant` 页面、AI 助手 B 本机/公网配置、30 分钟刷新、控制台插件参数编辑和
> qqbot_enhancer 1.21.0。发布由 `v*` tag 触发 GitHub Release，上传 EXE 和 SHA256。
> 基础 Docker Desktop/Linux engine、Compose、EXE 构建和管理服务生命周期已实际测试；
> 完整 AstrBot/SnowLuma 部署、noVNC 扫码和 QQ 验证仍未测试。详见根目录
> [`VALIDATION.md`](../VALIDATION.md) 和 [`docs/FAQ.md`](../docs/FAQ.md)。

---

## 1. 脚本

| 文件 | 作用 |
|---|---|
| `install.ps1` | 检查 Windows/Python 3.10+/WSL2/Docker Desktop/Compose/daemon，创建数据目录并持久化 `studio.json`，可选用 winget 安装 Python/Docker Desktop，可选添加管理端口防火墙规则，最后启动首个实例 |
| `start.ps1` | 检查 Docker，启动/复用隐藏管理服务，创建一个全新实例并打印部署向导 URL |
| `console.ps1` | 启动/复用隐藏管理服务，修复已有容器并打开多实例控制台，不创建新实例 |
| `common.ps1` | Start-Process 隐藏窗口、PID、双日志、`/healthz`、Docker Desktop 检查等共享函数 |
| `studio_helper.py` | 复用 vendored Python 核心做配置、实例创建和容器修复的 JSON 桥 |
| `launcher.py` | 独立 EXE 启动器源码；同样使用隐藏管理子进程、PID/日志/health check |
| `build.ps1` | 创建构建 venv、安装 PyInstaller、生成 one-file EXE 和 SHA256 |
| `qqbot-studio-windows.spec` | PyInstaller 配置；打包核心、static UI、插件和 assets |

EXE 构建与使用见根 README。

---

## 2. 安装与启动

普通 PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows\install.ps1
```

新建第二个实例：

```powershell
.\windows\start.ps1
```

管理已有实例：

```powershell
.\windows\console.ps1
```

只重启后台管理服务：

```powershell
.\windows\console.ps1 -RestartService
```

常用参数：

```powershell
.\windows\install.ps1 `
  -DataDir "$env:LOCALAPPDATA\QQBotStudio\data" `
  -Ip 0.0.0.0 `
  -Port 8765 `
  -PublicHost 192.168.1.20
```

- `-AddFirewallRule`：管理员 PowerShell 中创建 Private + LocalSubnet 的管理端口规则。
- `-NoStart`：只检查和配置，不创建实例。
- `-NoOpen`：不自动打开浏览器。
- `-NonInteractive`：首次配置使用参数/默认值。
- `-InstallMissing`：允许 winget 在无提示情况下安装缺失的 Python/Docker Desktop；
  WSL 仍涉及管理员权限和重启，由用户手动完成。

默认管理服务监听 `0.0.0.0:8765`。首次运行会提示并持久化监听 IP、端口和 public_host。
数据写入 `%LOCALAPPDATA%\QQBotStudio\data\studio.json`。

如果只想本机访问：

```powershell
.\windows\console.ps1 -Ip 127.0.0.1 -Port 8765 -PublicHost 127.0.0.1 -RestartService
```

`public_host` 只决定打印/打开的 URL，不改变监听地址；绑定回环地址时两者必须匹配。

---

## 3. Windows 10/11、Docker Desktop、WSL2

- Windows 10 22H2 x64 或 Windows 11；
- BIOS/UEFI 开启虚拟化；
- WSL2：

```powershell
wsl --install --no-distribution
wsl --update
wsl --status
```

- Docker Desktop 4.x，必须启用 WSL2 backend 并使用 **Linux containers**；
- 验证：

```powershell
docker version
docker compose version
docker info --format "{{.OSType}}"
```

最后一项必须输出 `linux`。PowerShell 脚本会启动 Docker Desktop 并等待 Linux engine；
EXE 也会检查 registry 安装位置、`docker compose version` 和 OSType。

Docker Desktop 必须运行，退出后容器会停止。本项目没有注册 Windows 服务或开机自启。

---

## 4. 后台管理服务

PowerShell 脚本和 EXE 都使用：

- 隐藏管理子进程；
- `server.pid`；
- `studio-server.log` 和 `studio-server.err.log`；
- `server-runtime.json`；
- HTTP `/healthz` 健康检查；
- 读取并核对 PID/runtime 后才自动停止旧服务；
- 不使用 screen/systemd/sudo。

默认文件：

```text
%LOCALAPPDATA%\QQBotStudio\data\
├── studio.json
├── server.pid
├── server-runtime.json
├── studio-server.log
├── studio-server.err.log
└── instances\
```

状态与日志：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/healthz
Get-Content "$env:LOCALAPPDATA\QQBotStudio\data\server.pid"
Get-Content "$env:LOCALAPPDATA\QQBotStudio\data\studio-server.log" -Encoding UTF8 -Tail 100
Get-Content "$env:LOCALAPPDATA\QQBotStudio\data\studio-server.err.log" -Encoding UTF8 -Tail 100
```

Python 子进程使用 `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`，避免旧 ANSI 代码页
造成日志中的中文诊断异常。停止管理服务不会自动停止 Docker 容器。

---

## 5. 新实例、扫码和 noVNC

每次 `start.ps1` 或 `QQBotStudioWindows.exe --new-instance` 都会创建一个全新隔离实例。
启动器会打印 wizard URL。

1. 在向导中填写 QQ 号、DeepSeek API Key、提示词和风险确认并部署；
2. 打开完成页的 noVNC；
3. 输入 VNC 密码；
4. 用手机 QQ 扫描 QQ 官方登录窗口中的二维码；
5. 设备验证、短信/邮箱验证、滑块等只能在 noVNC 内按 QQ 官方提示手动完成。

**每个新实例首次必须扫码登录。** 工具不收集、不保存、不代填 QQ 密码，也不绕过任何
QQ 验证或风控。

---

## 6. 端口、Windows Defender 防火墙与云安全组

管理端口默认 `0.0.0.0:8765`。AstrBot WebUI、SnowLuma WebUI 和 noVNC 的宿主端口由
实例自动选择（常见起点 6185 / 5099 / 6081），实际值以向导和 `docker ps` 为准。
实例 Compose 使用同一 `BIND_ADDRESS`（默认 `0.0.0.0`），因此机器人 WebUI/noVNC 也
可能对网络可达。

只本机使用建议绑定 `127.0.0.1`。需要局域网访问时：

```powershell
New-NetFirewallRule `
  -DisplayName 'QQ Bot Studio Management Console (TCP 8765)' `
  -Direction Inbound -Action Allow -Protocol TCP `
  -LocalPort 8765 -Profile Private -RemoteAddress LocalSubnet
```

- **Windows Defender 防火墙**位于 Windows 内部；
- **云安全组/云防火墙**位于云 Windows 虚拟机外部；
- 云主机通常两层都要放行，且来源最好限制为固定 IP/VPN 网段；
- 不要只改 WSL 内的 `ufw` 就认为 Windows 端口已放行；
- noVNC 中有 QQ 登录界面，禁止长期公开到互联网。

---

## 6.1 v3.12.0 同步后的新入口

- core 3.12.0、qqbot_enhancer 1.21.0；
- 提示词 profiles/active/新会话、按名会话、AstrBot 每群 Persona/记忆；
- ambient 全群上下文/@ 回复/私聊边界、群身份、多分类语义收藏、`/food`；
- prompt API/UI、stale/pending restart、容量上限、E2E/QA 文档；
- Windows launcher、Native POC、console_move_ext、双 EXE、sync workflow 保留。

## 6.2 v3.9.0 同步后的历史入口

- core 3.9.0、qqbot_enhancer 1.15.0；
- `/food`、按群 direct persona、统一 AI tool marker、schema fallback；
- `#sl` 关闭行为、提示词换行保留、最新 backend/UI。

## 6.3 v3.8.0 同步后的历史入口

- core 3.8.0、qqbot_enhancer 1.12.0；
- 收藏语义 tags/meaning/tone、多分类、全局收藏池；
- 自然语言重分类/发表情、AI 工具权限/AI 自动表情 UI；
- 配置并发重试、partial stats/permission_denied 降级。

## 6.4 v3.7.0 同步后的历史入口

- core 3.7.0、qqbot_enhancer 1.7.0；插件/核心模块化；
- 控制台实例设置 modal、services/components、`/assistant` 公网诊断；
- 插件安全工具 marker、AI 自动收藏（默认关闭）、Bing-only 相关性搜索；
- Windows launcher、console_move_ext、同步/双 EXE 流程保留。

## 6.5 v3.6.0 同步后的历史入口

- core 3.6.0、qqbot_enhancer 1.5.2（历史）；
- `/收藏表情` 支持引用消息和会话最近图片缓存，收藏流程更可靠；
- AI 语境选表情（`sticker_ai_select_enabled`）：direct 模式私有标记，memory 模式本地匹配；
- 自动收藏用户表情默认关闭；
- 平台感知部署向导和 Windows 双发行版/同步规则文档继续保留。

- 主控制台不再有离线“使用助手”A 面板或内嵌 AI 助手 B 卡片；
- 点击控制台顶部 **AI 助手**，或运行 `QQBotStudioWindows.exe --assistant`，进入
  `/assistant`；
- 在 `/assistant` 中安装/更新/配置/启动/停止 B；B 默认只监听 `127.0.0.1`；
- 显式使用 `0.0.0.0 + public_host` 时才生成公网 URL，且 B 没有认证，必须由
  Windows 防火墙、云安全组、VPN 或带认证的反向代理保护；
- 控制台自动刷新为 30 分钟，手动刷新会立即生效并重新计时；
- 插件 1.21.0 支持提示词 profiles、按名会话、ambient、群身份、`/food`、多分类语义收藏、图片/歌唱等功能。

详细操作见 [`../docs/FAQ.md`](../docs/FAQ.md) 与
[`../docs/ui-api-contract-v2.md`](../docs/ui-api-contract-v2.md)。

### v3.4.0 插件参数编辑

控制台插件行中的 **“编辑参数”** 打开 schema 驱动面板。`reply_probability` 等
`qqbot_enhancer` 参数可读取/编辑并保存；离线时提示 `restart_required`，在线时尽量
通过 AstrBot 热重载。Key/token/password 类字段不会返回或提交。

### v3.5.0 表情功能

qqbot_enhancer 1.5.0 新增（v3.5.0 历史）：

- 用户 @/私聊发送纯 Image/Face 时按概率自然短句反应，不调用 LLM；
- `/收藏表情 [分类]`、`/表情分类`、`/表情列表 [分类]`、`/发表情 [分类]`；
- 收藏表情参与正常回复，和内置 8 张表情包可混合使用；
- WebUI/API 可编辑 `user_sticker_reaction_*`、`collected_sticker_*` schema 参数。

### 文件位置与数据迁移

- EXE/发行文件：你下载/解压的位置；本工具不创建系统级安装目录。
- 默认数据根：`%LOCALAPPDATA%\QQBotStudio\data`。
- 迁移指针：`%LOCALAPPDATA%\QQBotStudio\data-location.json`（执行 `--move-data` 后）。
- 全局配置：数据根下的 `studio.json`。
- 实例：`instances\bot-N\`，含 `instance.json`、`config.json`、`secrets.json`、
  `compose.yml`、`.env`、`jobs\` 和 `data\astrbot\...`、`data\snowluma\...`。
- 管理日志：`studio-server.log`、`studio-server.err.log`；状态：`server.pid`、
  `server-runtime.json`。
- AI 助手 B：代码在 `extensions\ai-assistant\`，配置/日志/PID 在
  `ai-assistant\config.json`、`assistant.log`、`assistant.pid`。
- 插件：实例内 `data\astrbot\plugins\qqbot_enhancer\`；配置在
  `data\astrbot\config\qqbot_enhancer_config.json`；收藏表情在
  `data\astrbot\plugin_data\qqbot_enhancer\collected_stickers\`；点歌音频在插件目录
  `songs\`。

控制台入口（推荐）：管理控制台顶部 **存储文件夹** → 输入本机绝对路径 → 勾选备份/
停止确认 → **开始安全迁移**。后台 helper 停止服务和旧实例容器，复用同一套安全
复制/回滚/pointer 逻辑，从新目录自动重启同端口服务；页面检测到重启后提示刷新。
浏览器因安全限制不能读取本地绝对路径，所以使用安全文本输入而不是文件选择器。
API 均要求 `X-QB-Token`：`POST /api/system/move-data`（`{target, confirm:true}`）和
`GET /api/system/move-data/status`。

CLI 高级入口：

```powershell
.\QQBotStudioWindows.exe --move-data "D:\QQBotStudioData"
```

目标必须是本机固定 NTFS 磁盘上的不存在或空目录；拒绝 WSL、OneDrive、UNC/网络共享、
可移动盘/未知盘和不可写路径。迁移会先停止管理服务并对其旧数据目录中已有
`compose.yml` 的实例执行 Compose `down --remove-orphans`，再复制数据、写迁移记录和
`data-location.json`。旧目录会保留，服务/容器不会自动重启；迁移后执行
`QQBotStudioWindows.exe --status`，并让核心在新目录下重新生成/启动 Compose。
失败时旧目录不变；回滚可继续显式使用旧目录 `--data-dir <旧目录>`。

详细目录树见根 README。

### Docker/Native 双发行版与上游同步

当前构建产出两个 EXE，同版本、同一 Release：

| 文件 | 用途 | 状态 |
|---|---|---|
| `QQBotStudioWindows.exe` | Docker Desktop + WSL2，QQBotStudio 管理控制台 | 稳定推荐 |
| `QQBotStudioWindowsNative.exe` | Native Windows 单实例 POC：官方 SnowLuma Windows + 本机 NTQQ | 真实 AstrBot 4.29.3/SnowLuma 2.2.1 启动、HTTP 200、OneBot listener、PID/log/stop 已验证；QQ EULA/登录 ENV_BLOCKED |

Native 版官方推荐路径是本机安装桌面 QQ、官方 AstrBot Windows 运行时和官方
SnowLuma Windows x64 包，直接在本机 QQ 窗口扫码；noVNC 仅是可选高级增强，需要
Windows VNC Server + websockify 并共享整个交互桌面，不承诺每实例独立屏幕。
Native POC 管理本地 AstrBot/SnowLuma 进程，但不下载、不安装、不注入、不登录第三方组件。
临时 Windows 数据目录真实安装验证已通过：AstrBot 4.29.3 + SnowLuma 2.2.1
win-x64-lite + Node 26.13.0 + NTQQ 9.9.19.35469；AstrBot/SnowLuma HTTP 200、
OneBot `ws://127.0.0.1:16199/ws` listener=true、health OK、stop 后端口关闭。
SnowLuma EULA/PRIVACY 和 QQ 扫码/设备验证是人工步骤，未完成，因此
SnowLuma→AstrBot 握手和 QQ 消息 E2E 标记 ENV_BLOCKED。QQ 登录只使用官方本机
NTQQ 窗口，不使用 noVNC，也不自动输入密码/验证码。详细记录见
[`../docs/native-e2e-validation.md`](../docs/native-e2e-validation.md)。

```powershell
.\QQBotStudioWindowsNative.exe --configure --non-interactive --ntqq-path "D:\Program Files\Tencent\QQ.exe" --astrbot-command "astrbot run" --snowluma-dir "D:\SnowLuma"
.\QQBotStudioWindowsNative.exe --check --strict-check
.\QQBotStudioWindowsNative.exe --write-onebot-config
.\QQBotStudioWindowsNative.exe --start
.\QQBotStudioWindowsNative.exe --status
.\QQBotStudioWindowsNative.exe --health
.\QQBotStudioWindowsNative.exe --logs --log-service all --lines 100
.\QQBotStudioWindowsNative.exe --stop
```

Native v0.8.0 本地候选构建：Docker `8,594,242` bytes / SHA256
`4e5cf67e733cd4eee63c81d414e2aee9be9454ac53d0979ac3795bcf72b9fab0`；
Native POC `6,965,992` bytes / SHA256
`235b44cefcd32fbd0231474e27bd53194b0dc99d685e8403c6c60d82c96d6362`。
Linux/Windows 各 91 tests OK。真实 AstrBot/SnowLuma 启动和 health 已验证；
QQ EULA/扫码人工步骤仍为 ENV_BLOCKED。


#### 每次上游更新必须同步双版本

- `.github/workflows/sync-upstream.yml` 支持 `workflow_dispatch` 和每日 schedule，
  从公开 `Stevehim2007/qqbot-studio` main 同步 allowlist：
  `qqbot_studio/`（含 static）、`plugins/qqbot_enhancer/`、`assets/` 和必要 docs；
- 保留 Windows launcher、PowerShell、build/spec、`VERSION`、release workflow 和
  Windows 专属 README/FAQ；
- 更新 `.upstream-commit` 与 `UPSTREAM.md`，有变化才自动 commit/push；
- 发布 tag 前必须让两个 EXE 同批构建、smoke 和校验 `VERSION`，同一 Release 上传
  Docker/Native 两个 EXE + `SHA256SUMS.txt` + README/VALIDATION；
- 本地预演：

```powershell
python scripts\sync_upstream.py --upstream-dir ..\qqbot-studio --target-dir . --dry-run
python -m unittest discover -s tests -v
```

### 正式 EXE Release

`v0.7.0` 的双 EXE Release 已实际成功（run `41078425027`）：

- Release: <https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.7.0>
- `QQBotStudioWindows.exe`（Docker edition）：`10,926,947` bytes，
  SHA256 `eeb96134806c92356033590d71fc9a8af977cbbc8be4dd5600079acab32a664e`
- `QQBotStudioWindowsNative.exe`（Native bootstrap/guide）：`8,350,397` bytes，
  SHA256 `f16284efa7fe933e3852359b4602b0e560ca4c59e0c45a367a6d305a8c1c2206`
- `SHA256SUMS.txt`、`README.md`、`VALIDATION.md`

Release workflow 校验 tag/VERSION 和 upstream snapshot metadata 后构建、smoke、
上传两个 EXE；只上传 Actions artifact 不算正式发布。

## 7. 已知限制与未验证项

- 本独立仓库未做真实 QQ 扫码和完整部署联调前，不宣称生产可用。
- 真实 Windows/Docker Desktop 上的 `Start-Process`、隐藏子进程、PID 竞态、日志
  文件锁和防火墙行为仍需实机测试。
- Windows ACL 不等于 Linux `0600`；本机管理员可能读取数据文件。
- Docker Desktop 必须运行；容器不是 Windows 原生服务。
- 网页内一键自动更新在 Windows core 中禁用。升级方式见根 README。
- 动态实例 WebUI/noVNC 端口不自动添加防火墙规则。
- 共享静态 UI 的部分帮助文案可能仍使用 Linux 命令；Windows 命令以本仓库 README
  和 windows 脚本为准。
