# Windows PowerShell 备用入口

本文件说明独立 Windows 仓库中的 PowerShell 备用脚本。推荐日常入口是根目录 README
所述的 `QQBotStudioWindows.exe`。

> **项目边界：** 本仓库是 Windows 10/11 + Docker Desktop + WSL2 独立发行项目；
> `qqbot-studio` 是 Ubuntu/Linux 主项目。两者数据目录、版本和升级边界不同，不能
> 直接共用。完整说明见根目录 [`README.md`](../README.md) 和
> [`UPSTREAM.md`](../UPSTREAM.md)。
>
> **状态：Windows 独立发行版 v0.3.0，已同步 upstream core 3.4.0。** 已包含独立
> `/assistant` 页面、AI 助手 B 本机/公网配置、30 分钟刷新、控制台插件参数编辑和
> qqbot_enhancer 1.4.1。发布由 `v*` tag 触发 GitHub Release，上传 EXE 和 SHA256。
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

## 6.1 v3.4.0 同步后的新入口

- 主控制台不再有离线“使用助手”A 面板或内嵌 AI 助手 B 卡片；
- 点击控制台顶部 **AI 助手**，或运行 `QQBotStudioWindows.exe --assistant`，进入
  `/assistant`；
- 在 `/assistant` 中安装/更新/配置/启动/停止 B；B 默认只监听 `127.0.0.1`；
- 显式使用 `0.0.0.0 + public_host` 时才生成公网 URL，且 B 没有认证，必须由
  Windows 防火墙、云安全组、VPN 或带认证的反向代理保护；
- 控制台自动刷新为 30 分钟，手动刷新会立即生效并重新计时；
- 插件 1.4.1 支持自然语言找图、图片下载后本地发送、唱歌/点歌、`/option` 和记忆模式。

详细操作见 [`../docs/FAQ.md`](../docs/FAQ.md) 与
[`../docs/ui-api-contract-v2.md`](../docs/ui-api-contract-v2.md)。

### v3.4.0 插件参数编辑

控制台插件行中的 **“编辑参数”** 打开 schema 驱动面板。`reply_probability` 等
`qqbot_enhancer` 参数可读取/编辑并保存；离线时提示 `restart_required`，在线时尽量
通过 AstrBot 热重载。Key/token/password 类字段不会返回或提交。

### 正式 EXE Release

`v0.3.0` 起推送匹配 `VERSION` 的 tag 会触发
`.github/workflows/windows-release.yml`，创建真实 GitHub Release 并上传：

- `QQBotStudioWindows.exe`
- `SHA256SUMS.txt`

只上传 Actions artifact 不算正式发布。参见根 README 的下载/校验示例。

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
