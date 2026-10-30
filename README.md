# QQ Bot Studio Windows

[![Windows EXE build](https://github.com/Stevehim2007/qqbot-studio-windows/actions/workflows/windows-build.yml/badge.svg)](https://github.com/Stevehim2007/qqbot-studio-windows/actions/workflows/windows-build.yml)

QQ Bot Studio 的**独立 Windows 10/11 发行项目**，面向 Docker Desktop + WSL2
的 Linux 容器环境。

本仓库不是 Linux 项目的打包目录，也不是它的自动更新分支。它拥有自己的启动器、
Windows 服务生命周期实现、版本号、数据目录约定、测试和发布流水线。

> **状态：Windows 独立发行版 v0.4.0，已同步主项目 core 3.5.0。**
>
> 已包含独立 `/assistant` AI 助手页面、控制台 30 分钟刷新 + 手动刷新、
> AI 助手 B 本机/公网配置、控制台插件参数编辑（`reply_probability` 等）、
> qqbot_enhancer 1.5.0 用户表情自动反应/收藏分类/发表情和最新 API/FAQ 文档。
> Windows EXE 构建、隐藏管理服务、Docker Desktop/Linux engine 和本机 smoke
> 已做部分真实验证；发布使用 `v*` tag 触发的 GitHub Release。
> 但真实 Windows 上完整 AstrBot/SnowLuma 部署、noVNC 扫码和 QQ 验证仍未测试。
> **不能把本仓库当作已完成完整 Windows QQ 扫码生产联调的版本。**

---

## 1. 与 Linux 主项目的关系

| 项目 | 定位 |
|---|---|
| `qqbot-studio` | **Ubuntu/Linux 主项目**，使用 `install.sh`、`start.sh`、`console.sh`、screen/systemd 和 Linux 自动更新 |
| `qqbot-studio-windows`（本仓库） | **Windows 10/11 独立发行项目**，使用 Windows EXE/PowerShell、Docker Desktop + WSL2，不依赖 screen/systemd |

本仓库 vendor 了主项目的 `qqbot_studio/` Python 核心、静态 UI、`assets/` 和
`plugins/qqbot_enhancer/`。这不是符号链接，也不会在运行时从 Linux 主项目拉取代码。
快照来源与更新方法见 [`UPSTREAM.md`](UPSTREAM.md)。

### v3.5.0 同步内容

- qqbot_enhancer 1.5.0；
- 用户 @/私聊发送纯 Image/Face 时按概率自然短句反应，不调用 LLM；
- `/收藏表情 [分类]`、`/表情分类`、`/表情列表 [分类]`、`/发表情 [分类]`；
- 收藏表情参与正常回复，可与内置表情包混合使用；
- 新增 `user_sticker_reaction_*`、`collected_sticker_*` 等 schema 参数；
- 独立 Windows 版本升至 `0.4.0`。

### v3.4.0 同步内容

- 控制台插件面板新增 **编辑参数**：读取 schema、生成表单、保存并提示热重载/重启；
- `qqbot_enhancer` 的 `reply_probability` 等 61 项参数可通过 UI 编辑；
- 新增 token 保护的 GET/POST `/api/instances/<id>/plugins/<plugin_id>/config`；
- 敏感 Key/token/password 类字段不会返回或提交；
- 支持 bool/int/float/string/text/list 类型、范围、选项和默认值；
- Windows 独立版本升至 `0.3.0`，新增 tag 驱动的真实 GitHub Release。

### v3.3.0 同步内容

- 控制台顶部新增 **“AI 助手”** 链接，进入独立页面 `/assistant`；
- 删除控制台内旧离线“使用助手”A 面板和内嵌 AI 助手 B 卡片；
- `/assistant` 支持 B 的安装、更新、配置、启动、停止和打开；
- B 默认仅本机 `127.0.0.1`，也支持显式 `0.0.0.0 + public_host` 高风险公网模式；
- 控制台自动刷新为 **30 分钟**，并保留手动刷新；
- qqbot_enhancer **1.4.1**：自然语言找图、图片本地下载、本地唱歌/点歌、
  `/option` 和 `direct/astrbot` 记忆模式；
- 同步最新 README/FAQ/API 契约到 [`docs/`](docs/README.md)。

### 数据目录不能直接共用

- Windows 默认数据目录：`%LOCALAPPDATA%\QQBotStudio\data`
- Linux 主项目默认数据目录：`~/.local/share/qqbot-studio`

**不能直接共用、复制后混用，或把两套程序同时指向同一个数据目录。** 两者的路径
语义、Docker 宿主、install/serve 生命周期和升级节奏不同。需要迁移时，应停机备份，
只迁移 `instances/` 中确认需要的实例数据，并重新完成容器/登录验证。

### 升级边界

- 本仓库独立维护版本：当前 `VERSION = 0.4.0`，bundled core 版本为
  `qqbot_studio.__version__ = 3.5.0`。
- Linux 主项目的自动更新、`scripts/auto-update.sh` 和网页内“更新并重启”不适用于
  本仓库。
- Windows 版升级方式是：下载新的 EXE / PowerShell 发行包，停止旧管理服务，保留
  数据目录，替换程序文件，再用新 EXE 执行 `--status` 和健康检查。
- 从 Linux 主项目同步核心时需要重新 vendor、重跑测试、重新构建 EXE，并更新
  `UPSTREAM.md`。不要把 Linux 主项目的 `install.sh`、screen/systemd 片段直接搬入。

### 问题仓库

- Windows 启动器、PowerShell、Docker Desktop、EXE 打包问题：本仓库。
- 通用部署逻辑问题：先在主项目确认是否仍存在，再在对应仓库报告。
- 不要用同一个 GitHub issue 把两个发行版的日志混在一起；请附发行版版本、
  Windows 版本、Docker Desktop 版本和 `--status` 输出。

---

## 2. 系统要求

- Windows 10 22H2 x64 或 Windows 11
- Docker Desktop 4.x
- Docker Desktop 的 **Linux containers** 模式
- WSL2；在 BIOS/UEFI 中开启 CPU 虚拟化
- 预构建 EXE 不要求系统安装 Python
- 从源码构建 EXE 需要 Python 3.10+ x64 和 PowerShell 5.1+
- 建议至少 8 GB 内存；多实例建议 16 GB
- 普通桌面用户运行；管理员权限只用于 WSL、Windows 防火墙等一次性操作

### WSL2

管理员 PowerShell：

```powershell
wsl --install --no-distribution
wsl --update
```

按提示重启。Docker Desktop 设置中启用 WSL2 based engine 和需要的 WSL integration。
再验证：

```powershell
wsl --status
docker version
docker compose version
docker info
```

`docker info` 的 `OSType` 必须是 `linux`。启动器也会主动检查；Windows containers
模式会直接报错并要求切换。

### Docker Desktop

安装并启动 Docker Desktop，完成首次登录/许可/教程，然后：

```powershell
docker context ls
docker context use desktop-linux
docker version
docker compose version
docker info --format "{{.OSType}}"
```

如果 `docker` 不在 PATH，启动器会尝试从 Docker Desktop 的 registry 安装位置和常见
目录定位 `docker.exe`。定位失败时应安装 Docker Desktop 或手工修复 PATH。

---

## 3. 预构建 EXE / GitHub Release 使用

正式发布从 GitHub Releases 下载，而不是只依赖 Actions artifact：

- Releases: <https://github.com/Stevehim2007/qqbot-studio-windows/releases>
- Tag: `v0.4.0`
- Release URL: <https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.4.0>
- 发布 workflow: `windows-release.yml` run `40997401439`，conclusion `success`
- Release assets 已确认：
  - `QQBotStudioWindows.exe`：`10,803,066` bytes，
    SHA256 `9bd92a299839fd3ec4a4c0c089356c98505fb17995edfee8d279e2b831e53f3b`
  - `SHA256SUMS.txt`（内容与上述 digest 一致）
  - `README.md`
  - `VALIDATION.md`

本地预发布构建（Windows Python 3.10 + PyInstaller 6.10.0）为
`8,461,717` bytes，SHA256
`2d44225206473101ca2a3a03f462afef86b5a0b2e47b8d6cddcbee4fe4d240db`；它与 CI
Release EXE 不保证逐字节一致，正式 SHA 以 Release 的
`9bd92a299839fd3ec4a4c0c089356c98505fb17995edfee8d279e2b831e53f3b` 为准。

下载与校验示例：

```powershell
$release = 'https://github.com/Stevehim2007/qqbot-studio-windows/releases/download/v0.4.0'
Invoke-WebRequest "$release/QQBotStudioWindows.exe" -OutFile .\QQBotStudioWindows.exe
Invoke-WebRequest "$release/SHA256SUMS.txt" -OutFile .\SHA256SUMS.txt
Get-FileHash .\QQBotStudioWindows.exe -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

CI 分支构建也会上传 Actions artifact，便于测试，但正式用户应优先使用 Release
中的 EXE 和 SHA256。

从 Actions `windows-build` workflow 下载测试 artifact：

```text
QQBotStudioWindows.exe
SHA256SUMS.txt
README.md
VERSION
UPSTREAM.md
VALIDATION.md
docs\
windows\...
```

校验 SHA256 后，在文件所在目录打开 PowerShell：

```powershell
Get-FileHash .\QQBotStudioWindows.exe -Algorithm SHA256
.\QQBotStudioWindows.exe --version
```

### 第一次运行

```powershell
.\QQBotStudioWindows.exe
```

首次运行会询问并持久化：

```text
管理服务监听 IP（默认 0.0.0.0）
管理控制台端口（默认 8765）
对外访问 IP/域名（用于浏览器链接）
```

设置保存到 `%LOCALAPPDATA%\QQBotStudio\data\studio.json`。程序会：

1. 检查/启动 Docker Desktop Linux engine；
2. 检查 Compose v2；
3. 通过隐藏子进程启动管理服务；
4. 写入 PID、日志和 runtime 文件；
5. 轮询 `/healthz`；
6. 打开多实例控制台；
7. 父进程退出，后台管理服务继续运行。

控制台点击顶部 **“AI 助手”** 可进入独立 `/assistant` 页面。也可以直接启动到该页面：

```powershell
.\QQBotStudioWindows.exe --assistant
```

`/assistant` 页面负责可选 AI 助手 B 的安装、配置、启动、停止和打开。B 默认只监听
`127.0.0.1`；只有显式选择“公网/所有网卡”并填写 `public_host` 时才生成公网 URL。
**B 没有内置登录认证**，公网模式必须使用 Windows 防火墙/云安全组/VPN 或带认证的
反向代理限制来源，不能裸奔到互联网。

新建机器人实例并直接打开部署向导：

```powershell
.\QQBotStudioWindows.exe --new-instance "我的第一个机器人"
```

> **重要：每个新实例首次部署都必须在 noVNC 中扫码登录 QQ。** 设备验证、短信/
> 邮箱验证、滑块等只能在 QQ 官方登录界面手动完成。工具不收集、不代填、不保存
> QQ 密码，也不绕过 QQ 验证。

### 常用命令

| 命令 | 作用 |
|---|---|
| `QQBotStudioWindows.exe` | 启动/复用管理服务并打开控制台 |
| `QQBotStudioWindows.exe --new-instance [NAME]` | 新建实例并打开 wizard |
| `QQBotStudioWindows.exe --assistant` | 启动/复用服务并打开独立 AI 助手页面 `/assistant` |
| `QQBotStudioWindows.exe --status` | 查看监听、健康、PID/runtime 和日志路径 |
| `QQBotStudioWindows.exe --stop` | 停止管理服务；Docker 容器继续运行 |
| `QQBotStudioWindows.exe --logs` | 输出最近 80 行服务日志 |
| `QQBotStudioWindows.exe --logs 300` | 输出最近 300 行服务日志 |
| `QQBotStudioWindows.exe --restart` | 安全停止由本数据目录管理的服务后重启 |
| `QQBotStudioWindows.exe --configure` | 强制重新配置 IP/端口/public_host |
| `QQBotStudioWindows.exe --no-open` | 不自动打开浏览器 |
| `QQBotStudioWindows.exe --data-dir D:\QQBotStudioData` | 使用独立数据目录 |
| `QQBotStudioWindows.exe --ip 127.0.0.1 --public-host 127.0.0.1` | 只允许本机访问 |
| `QQBotStudioWindows.exe --help` | 完整参数 |

默认管理服务绑定 **`0.0.0.0:8765`**。如果只在本机使用，建议：

```powershell
.\QQBotStudioWindows.exe --ip 127.0.0.1 --port 8765 --public-host 127.0.0.1 --restart
```

修改 `--public-host` 只改变打印/打开的 URL，不改变实际监听地址。

### 数据目录、PID 和日志

默认：

```text
%LOCALAPPDATA%\QQBotStudio\data\
├── studio.json
├── server.pid
├── server-runtime.json
├── studio-server.log
├── studio-server.err.log
└── instances\
```

也可通过 `--data-dir` 或环境变量 `QQBOT_STUDIO_DATA_DIR` 指定。不同数据目录
代表完全独立的实例集合，不能同时混用。

查看服务：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/healthz
Get-Content "$env:LOCALAPPDATA\QQBotStudio\data\server.pid"
Get-Content "$env:LOCALAPPDATA\QQBotStudio\data\studio-server.log" -Encoding UTF8 -Tail 100
Get-Content "$env:LOCALAPPDATA\QQBotStudio\data\studio-server.err.log" -Encoding UTF8 -Tail 100
```

---

## 4. PowerShell 安装/启动脚本（备用）

仓库仍保留原有 PowerShell 入口，供需要检查/安装依赖或习惯脚本的用户使用：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows\install.ps1
.\windows\start.ps1
.\windows\console.ps1
```

它们使用 `Start-Process -WindowStyle Hidden` + PID/日志 + health check，不使用
screen/systemd。详细参数、防火墙示例和排错见 [`windows/README.md`](windows/README.md)。
EXE 是推荐入口；PowerShell 脚本是便于审计/安装的备用入口。

---

## 5. Docker Desktop/WSL2 端口与数据边界

- 容器为 **Linux containers**，不是 Windows containers。
- Docker Desktop 必须运行；退出 Docker Desktop 后容器会停止。
- Docker Desktop 把发布端口代理到 Windows 宿主。Windows 防火墙需要放行实际
  宿主端口；只改 WSL 发行版内的 `ufw` 不够。
- 管理端口默认 `8765`；AstrBot WebUI、SnowLuma WebUI、noVNC 的宿主端口由实例
  自动选择（常见起点 6185 / 5099 / 6081），以向导和 `docker ps` 为准。
- 机器人 Compose 使用同一个 `BIND_ADDRESS`（默认 `0.0.0.0`），因此 per-instance
  WebUI/noVNC 也可能对网络可达。不要把它当作默认安全。
- 建议把数据目录放在本机 NTFS 的 `%LOCALAPPDATA%` 或 `C:` / `D:` 路径；不要用
  OneDrive 同步目录、只读网络共享或 WSL 内部路径作为共享数据根。
- Windows ACL 不等同 Linux `0600`；本机管理员可能读取敏感配置文件。不要把本工具
  当多租户密钥保险箱。

### Windows Defender 防火墙 vs 云安全组

两者是不同层：

1. 云服务器（CVM/ECS 等）的**安全组/云防火墙**在虚拟机外；
2. **Windows Defender 防火墙**在 Windows 内；
3. 云 Windows 主机通常两层都要放行，来源限制到固定 IP/VPN 网段。

只开放管理端口且仅私有网络的示例（管理员 PowerShell）：

```powershell
New-NetFirewallRule `
  -DisplayName 'QQ Bot Studio Management Console (TCP 8765)' `
  -Direction Inbound -Action Allow -Protocol TCP `
  -LocalPort 8765 -Profile Private -RemoteAddress LocalSubnet
```

noVNC 内有 QQ 登录界面，绝不能长期向公网开放。优先使用 VPN、Tailscale/WireGuard、
固定来源 IP 或临时隧道；用完即关规则。

AI 助手 B 默认端口为 `8766`，但实际值以 `/assistant` 页面配置为准。B 未内置认证；
如果配置 `0.0.0.0` + `public_host`，同样必须同时配置 Windows Defender 防火墙、
云安全组或 VPN，并建议使用带认证的反向代理。

---

## 6. 从源码构建 EXE

构建命令（在仓库根目录打开 PowerShell）：

```powershell
.\windows\build.ps1 -Clean
```

脚本会：

- 检查 Python 3.10+；
- 创建 `.venv-build`；
- 安装 `requirements-build.txt` 中固定的 PyInstaller；
- 执行 `windows\qqbot-studio-windows.spec`；
- 生成 `dist\QQBotStudioWindows.exe` 和 `dist\SHA256SUMS.txt`；
- 用 `--version` / `--help` 做无需 Docker 的冒烟测试。

可选参数：

```powershell
.\windows\build.ps1 -Python "C:\Path\python.exe" -SkipInstall -NoClean
```

构建产物是 console EXE：启动器本身显示配置/启动/错误信息，后台管理子进程隐藏运行。
日志保留在数据目录中，不依赖父控制台存活。

### GitHub Actions

[`.github/workflows/windows-build.yml`](.github/workflows/windows-build.yml) 会在
push/PR 时构建并上传测试 artifact。正式发布由
[`.github/workflows/windows-release.yml`](.github/workflows/windows-release.yml)
在 `v*` tag 上执行。v0.4.0 的 Release run `40997401439` 已实际成功；全部
steps（tag/VERSION 校验、45 tests、compileall、PowerShell AST、PyInstaller
构建、EXE smoke、artifact upload、Release 创建）均通过。构建 workflow 会：

1. 安装 Python 3.12；
2. 跑独立测试；
3. 用 PowerShell AST parser 检查脚本语法；
4. 构建 one-file EXE；
5. 执行 EXE `--version` / `--help` smoke test；
6. 上传 artifact `QQBotStudioWindows-<sha>`。

Artifact 包括 EXE、SHA256、README、VERSION、LICENSE、UPSTREAM、VALIDATION、
`docs/**` 和备用 PowerShell 脚本。真实 Docker Desktop/QQ 扫码测试不在 CI runner
上执行。

### GitHub Release workflow

[`.github/workflows/windows-release.yml`](.github/workflows/windows-release.yml) 在
推送 `v*` tag 时：

1. 校验 `VERSION` 与 tag 一致（`VERSION=0.4.0` 必须对应 `v0.4.0`）；
2. 重新跑独立测试、compileall、PowerShell AST、PyInstaller 构建和 EXE smoke；
3. 上传 Actions artifact；
4. 通过 `softprops/action-gh-release@v2` 创建真实 GitHub Release；
5. 把 `QQBotStudioWindows.exe` 和 `SHA256SUMS.txt` 作为 Release assets 上传。

只上传 Actions artifact 不算发布；Release assets 必须存在。

v0.4.0 实际结果：

- Run: <https://github.com/Stevehim2007/qqbot-studio-windows/actions/runs/40997401439>
- Release: <https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.4.0>
- Release assets：`QQBotStudioWindows.exe`（`10,803,066` bytes，
  SHA256 `9bd92a299839fd3ec4a4c0c089356c98505fb17995edfee8d279e2b831e53f3b`）、
  `SHA256SUMS.txt`、`README.md`、`VALIDATION.md`。
- 本地执行过的核心验证、Docker compose 结果和限制见 `VALIDATION.md`。

---

## 7. 已验证与未验证

### 已实际通过

本仓库已在同一台 Windows 主机上通过 WSL interop 使用 Windows PowerShell 5.1、
Windows Python 3.10.9 和 Docker Desktop 4.93.0 做了本地验证：

- 独立测试套件 **45 tests** 在 Linux Python 和 Windows Python 下均通过；
- Windows Python `compileall`、PowerShell 5.1 AST、Node JS 检查通过；
- Docker Desktop 4.93.0 / Engine 29.8.1 / `OSType=linux` / Compose v5.5.1；
- 最小 busybox Compose `config/up/down` 全部 exit 0，容器实际输出
  `qqbot-windows-v040-compose-smoke` 后清理；
- PyInstaller 6.10.0 在 Windows 上实际构建出 one-file EXE：
  `8,461,717` bytes，SHA256
  `2d44225206473101ca2a3a03f462afef86b5a0b2e47b8d6cddcbee4fe4d240db`；
- EXE `--assistant` 启动后 `/healthz` 返回 version `3.5.0`，`/console` 与
  `/assistant` 均 HTTP 200；
- 通过 token API 创建实例 `bot-1`，并使用插件 schema 实测插件参数配置：
  - GET 返回 88 个 schema 字段；`reply_probability=0.12`，
    `user_sticker_reaction_enabled=true`，`collected_sticker_enabled=true`；
  - POST 保存 `reply_probability=0.55` 和
    `user_sticker_reaction_probability=0.7`，离线返回
    `restart_required=true`；
  - 再次 GET 读取为 `0.55` / `0.7`，本地配置 json 写入成功；
- `/console` 含插件编辑器和 `/assistant` 链接，不含旧 A/B DOM；
- `--status` 和 `--stop` 实测通过，停止后 health 不可达。

详细命令、环境和输出见 [`VALIDATION.md`](VALIDATION.md)。

### 仍未验证

- v0.2.0 的 `windows-latest` 构建与 artifact upload 已成功；后续 docs-only 提交仍
  需保持 workflow 绿色。
- 浏览器自动打开未测试，服务生命周期测试均使用 `--no-open`。
- `install.ps1` 全流程、winget 安装、WSL2 初始化/重启未测试。
- Windows Defender 防火墙、云安全组、局域网/VPN 远程访问未测试。
- 真实 AstrBot + SnowLuma 向导部署、DeepSeek API 和 QQ 账号登录未测试。
- noVNC 扫码、设备验证、短信/邮箱验证和滑块验证未测试。
- 长时间多实例稳定性、bind mount 属主和容器写权限未测试。

**基础 Windows 启动器、Docker Desktop 和最小 Compose 已验证；完整 QQ 部署/扫码
链路未验证，因此不能宣称 Windows 生产可用。**

## 8. 文档与 FAQ

- [`docs/README.md`](docs/README.md)：Windows 文档索引；
- [`docs/FAQ.md`](docs/FAQ.md)：`/assistant`、AI 助手 B 公网、30 分钟刷新、插件 1.5.0、
  EXE、端口和升级问题；
- [`docs/ui-api-contract-v2.md`](docs/ui-api-contract-v2.md)：最新管理 API 契约；
- [`docs/plugin-qqbot-enhancer.md`](docs/plugin-qqbot-enhancer.md)：qqbot_enhancer 1.5.0；
- [`VALIDATION.md`](VALIDATION.md)：真实执行和未验证项；
- [`UPSTREAM.md`](UPSTREAM.md)：vendor 来源与下次同步步骤；
- [Linux 主项目 README](https://github.com/Stevehim2007/qqbot-studio/blob/main/README.md)：
  Ubuntu/Linux 安装说明，不要与 Windows 数据目录混用。

## 9. 常见问题

### EXE 一启动就退出或没打开浏览器

先运行：

```powershell
.\QQBotStudioWindows.exe --status
.\QQBotStudioWindows.exe --logs 200
```

确认 Docker Desktop 正在运行并处于 Linux containers。首次启动 Docker Desktop 可能
需要登录/接受许可；启动器无法代替用户完成 GUI 首次引导。

### 端口已占用

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
.\QQBotStudioWindows.exe --port 18765 --public-host 127.0.0.1 --restart
```

管理服务只会在确认 PID/runtime 属于当前数据目录后自动停止旧服务。

### 页面只能本机访问

检查 `studio.json` 的 `bind_host` 是否为 `0.0.0.0`，以及 Windows 防火墙/云安全组。
如果使用 `--ip 127.0.0.1`，其他设备无法访问，同时 `public_host` 也必须匹配。

### 旧数据或 Linux 数据

不要把 Linux `~/.local/share/qqbot-studio` 直接复制到
`%LOCALAPPDATA%\QQBotStudio\data` 后继续运行。容器名、Compose 路径、Docker 宿主和
保存的登录态都需要重新验证。先备份，再新建 Windows 实例并扫码。

---

## 10. 安全与许可

- 不收集或保存 QQ 密码；不会绕过验证码、滑块、设备验证或风控。
- 使用 QQ 小号，遵守腾讯 QQ 用户协议。
- Docker Desktop 许可由用户自行确认。
- 本项目代码沿用主项目 MIT License，见 [`LICENSE`](LICENSE)。
- Windows 数据目录的 ACL 由 Windows 用户配置控制；默认 LocalAppData 仅建议作为
  单用户数据位置，不是多租户安全隔离。
