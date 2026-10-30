# QQ Bot Studio Windows

[![Windows EXE build](https://github.com/Stevehim2007/qqbot-studio-windows/actions/workflows/windows-build.yml/badge.svg)](https://github.com/Stevehim2007/qqbot-studio-windows/actions/workflows/windows-build.yml)

QQ Bot Studio 的**独立 Windows 10/11 双发行版项目**：

- **Docker edition（稳定）**：Docker Desktop + WSL2 + Linux containers；
- **Native edition（POC/bootstrap）**：官方 SnowLuma Windows + 本机 NTQQ 单实例路线；
  当前 Native EXE 是安装/检查/指南占位，不是已完成的原生 AstrBot/SnowLuma 管理器，
  也未做真机 E2E。

本仓库不是 Linux 项目的打包目录，也不是它的自动更新分支。它拥有自己的启动器、
Windows 服务生命周期实现、版本号、数据目录约定、测试和发布流水线。

> **状态：Windows v0.7.0 发布候选（最新正式 Release 为 v0.6.0），已同步主项目 core 3.9.0。**
>
> 已包含独立 `/assistant` AI 助手页面、控制台 30 分钟刷新 + 手动刷新、
> AI 助手 B 本机/公网配置、控制台插件参数编辑（`reply_probability` 等）、
> qqbot_enhancer 1.15.0 `/food`、按群 persona、统一 AI tool marker、schema fallback 和最新 API/FAQ 文档；
> v0.4.1 新增 Windows 文件位置说明和 CLI 安全迁移；v0.4.2 新增
> token 保护的控制台“存储文件夹”迁移入口、后台 helper 自动停服/复制/重启，
> 以及 Docker/Native 双 EXE 构建与 `sync-upstream` 同步流水线。
> v0.5.0 同步 Linux 3.7.0：模块化 core/static/services/components、实例设置
> modal、B 公网诊断、qqbot_enhancer 1.7.0 安全工具/AI 自动收藏/Bing-only 相关性过滤。
> v0.6.0 同步 Linux 3.8.0：收藏表情 tags/meaning/tone 语义、多分类与全局池、
> 自然语言重分类/发表情、AI 工具权限 UI、配置并发重试与 partial stats。
> v0.7.0 同步 Linux 3.9.0：`/food`、按群 direct persona、schema fallback、
> 统一 AI tool marker、#sl 关闭、提示词换行保留和最新 UI/backend。
> Docker EXE、隐藏管理服务、Docker Desktop/Linux engine 和本机 smoke 已做部分
> 真实验证；发布使用 `v*` tag 触发的 GitHub Release。
> **Native EXE 当前是 bootstrap/guide 占位，不包含完整 AstrBot/SnowLuma/NTQQ 集成。**
> 真实 Windows 上完整 AstrBot/SnowLuma 部署、noVNC 扫码和 QQ 验证仍未测试，
> 不能把本仓库当作已完成完整 Windows QQ 扫码生产联调的版本。

---

## 1. 与 Linux 主项目的关系

| 项目 | 定位 |
|---|---|
| `qqbot-studio` | **Ubuntu/Linux 主项目**，使用 `install.sh`、`start.sh`、`console.sh`、screen/systemd 和 Linux 自动更新 |
| `qqbot-studio-windows`（本仓库） | **Windows 10/11 独立发行项目**，使用 Windows EXE/PowerShell、Docker Desktop + WSL2，不依赖 screen/systemd |

### 两个 Windows 发行版

| 发行版 | EXE | 运行时 | 当前状态 |
|---|---|---|---|
| Docker edition | `QQBotStudioWindows.exe` | Docker Desktop + WSL2 + Linux containers | **稳定推荐**；EXE/API/Compose smoke 已验证，真实 QQ/noVNC E2E 未验证 |
| Native edition | `QQBotStudioWindowsNative.exe` | 官方 SnowLuma Windows + 本机桌面 NTQQ | **POC/bootstrap 占位**；支持官网指南和只读依赖检查，未集成 AstrBot/SnowLuma 进程，未做 native E2E |

Native 版优先使用官方 SnowLuma Windows 发行包和本机 NTQQ 桌面扫码；官方路径不要求
Docker/WSL，也不要求 noVNC。noVNC 仅作为可选高级增强：需要 Windows VNC Server +
websockify，共享整个交互式 Windows 桌面，不承诺每实例独立屏幕，也不是 SnowLuma
自带 QQ 登录二维码。需要简单稳定部署时继续使用 Docker edition。

本仓库 vendor 了主项目的 `qqbot_studio/` Python 核心、静态 UI、`assets/` 和
`plugins/qqbot_enhancer/`。这不是符号链接，也不会在运行时从 Linux 主项目拉取代码。
快照来源与更新方法见 [`UPSTREAM.md`](UPSTREAM.md)。

### v3.9.0 同步内容

- core `3.9.0`、qqbot_enhancer `1.15.0`；
- `/food`（`/吃什么`、`/饭店`）固定 HTTPS 餐厅查询，带超时/大小/冷却/中文降级；
- 实例级 `group_personas` 按群 direct persona，未知群/私聊安全 fallback；
- 插件 schema 缺失时只读回退 bundled schema，并在 API 返回 `schema_source`；
- 统一 AI tool marker 协议；`#sl` 关闭行为、提示词换行保留；
- 保留 Windows launcher/console_move_ext/双 EXE/sync workflow。

### v3.8.0 同步内容

- core `3.8.0`、qqbot_enhancer `1.12.0`；
- 收藏表情支持 tags/meaning/tone 语义元数据、全局收藏池、一个文件多分类；
- 显式 @/私聊自然语言重分类最近收藏、自然语言发表情；AI 工具权限边界更明确；
- 控制台实例设置新增 AI 工具权限/AI 自动表情 UI；
- backend 配置读取并发重试、partial resource stats/permission_denied 降级；
- 保留 Windows console_move_ext、双 EXE 和 sync workflow。

### v3.7.0 同步内容

- core `3.7.0`、qqbot_enhancer `1.7.0`；
- 核心/插件模块化：`contracts.py`、`resource_stats.py`，插件拆分 config/image_search/
  media/llm/safe_tools/songs/sticker_store 等模块；
- 控制台实例设置 modal、`static/services` 与 `static/components`；
- `/assistant` 公网访问诊断 UI 与服务端诊断 API；
- 插件受限安全工具 marker（白名单图片搜索/发/收藏/分类），不提供 shell/路径/URL 工具；
- AI 自动收藏默认关闭；图片搜索默认 Bing-only，并增加结果相关性过滤；
- 保留 Windows launcher、PowerShell、build/spec、console_move_ext 和 sync workflow。

### v3.6.0 同步内容

- core `3.6.0`、qqbot_enhancer `1.5.2`；
- `/收藏表情` 支持引用消息与最近图片缓存，收藏流程更可靠；
- 新增 AI 语境选表情：direct 模式使用私有 `[[sticker:标签]]` 标记，memory 模式
  使用本地关键词/情绪/收藏分类匹配；
- 自动收藏用户表情默认关闭，需显式开启；
- 同步最新插件 README/schema/docs；
- Windows 双 EXE/上游同步流程继续保留。

### v3.5.1 同步内容

- core `3.5.1`、qqbot_enhancer `1.5.0`；
- 平台感知部署向导：识别 Windows / Ubuntu / 其它 Linux，并给出各自可复制的检查/安装命令；
- 同步主项目 Windows 双发行版可行性调研文档；
- 通过 `sync-upstream` 自动化记录 Linux commit 并更新 `.upstream-commit` / `UPSTREAM.md`。

### v3.5.0 同步内容

- qqbot_enhancer 1.15.0；
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

- 本仓库独立维护版本：当前开发版 `VERSION = 0.4.1`，bundled core 版本为
  `qqbot_studio.__version__ = 3.9.0`。
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
- Native edition 另需官方 Windows 桌面 QQ（NTQQ）和 SnowLuma Windows x64 发行包；
  当前 bootstrap 不会自动下载、注入或登录这些组件。原生单实例 POC 要求 QQ 与
  SnowLuma 使用同一 Windows 用户/权限级别，QQ 版本必须与 SnowLuma hook 匹配。

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
- 最新正式 Release: `v0.6.0`
- Release URL: <https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.6.0>
- 发布 workflow: `windows-release.yml` run `41008090389`，conclusion `success`
- Release assets 已确认（双 EXE）：
  - `QQBotStudioWindows.exe`（Docker edition）：`10,914,001` bytes，
    SHA256 `269b71b18d94950684b99b9b14fea314a739397d55f41e2ea71c63e417c2dbdb`
  - `QQBotStudioWindowsNative.exe`（Native bootstrap/guide）：`8,350,396` bytes，
    SHA256 `f2deb9cc7e6ede11345f4e587f7f7023513d944f5beb4ee79067a171e2c0277c`
  - `SHA256SUMS.txt`（已下载核对，与上述 GitHub API digest 一致）
  - `README.md`、`VALIDATION.md`
- 正式 Release 由 same-tag `v0.6.0` workflow 构建，和本地开发构建不保证逐字节一致。

本地 v0.6.0 双 EXE 开发构建（Windows Python 3.10 + PyInstaller 6.10.0）：

- Docker `QQBotStudioWindows.exe`：`8,567,120` bytes，SHA256
  `e277c8428751204fd7d39296c444aade16370a3b6a513d7cea16c90d24344154`；
- Native `QQBotStudioWindowsNative.exe`：`6,405,952` bytes，SHA256
  `5d6dd0f12adb531edf174d871d229cadba84f63744de2f9c9399648a43ce3da4`。

正式用户应使用上面的 Release 资产和 `SHA256SUMS.txt`；不要用本地开发 hash 替代。

下载与校验示例：

```powershell
$release = 'https://github.com/Stevehim2007/qqbot-studio-windows/releases/download/v0.6.0'
Invoke-WebRequest "$release/QQBotStudioWindows.exe" -OutFile .\QQBotStudioWindows.exe
Invoke-WebRequest "$release/QQBotStudioWindowsNative.exe" -OutFile .\QQBotStudioWindowsNative.exe
Invoke-WebRequest "$release/SHA256SUMS.txt" -OutFile .\SHA256SUMS.txt
Get-FileHash .\QQBotStudioWindows.exe -Algorithm SHA256
Get-FileHash .\QQBotStudioWindowsNative.exe -Algorithm SHA256
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

### Windows 文件位置与安全迁移数据目录

#### 文件位置

Windows 版没有系统级安装目录：`QQBotStudioWindows.exe`、README、VERSION 等就是发行包
文件，放在你下载/解压的位置；EXE 解包运行的临时目录不是数据目录。正式安装/升级建议
先停止管理服务，再整体替换 EXE 发行文件。

默认根目录：

```text
%LOCALAPPDATA%\QQBotStudio\
├── data\                         # 默认数据目录
│   ├── studio.json               # 监听 IP/端口/public_host、镜像节点
│   ├── windows-data-move.json    # 迁移后生成的迁移记录
│   ├── server.pid
│   ├── server-runtime.json
│   ├── studio-server.log
│   ├── studio-server.err.log
│   ├── instances\bot-N\
│   │   ├── instance.json
│   │   ├── config.json           # QQ 号、模型、端口等
│   │   ├── secrets.json          # 敏感凭据，勿分享
│   │   ├── deploy-state.json
│   │   ├── compose.yml
│   │   ├── .env                  # 敏感凭据，勿分享
│   │   ├── jobs\                 # 部署任务日志
│   │   └── data\
│   │       ├── astrbot\
│   │       │   ├── plugins\qqbot_enhancer\
│   │       │   ├── config\qqbot_enhancer_config.json
│   │       │   └── plugin_data\qqbot_enhancer\collected_stickers\
│   │       └── snowluma\
│   ├── extensions\ai-assistant\  # 可选 AI 助手 B 代码
│   └── ai-assistant\
│       ├── config.json           # B 的配置；不要分享
│       ├── assistant.log
│       └── assistant.pid
└── data-location.json            # 仅在 --move-data 后出现，指向新数据目录
```

- 内置插件/表情包随 EXE 打包；实际安装到实例的插件在
  `instances\bot-N\data\astrbot\plugins\qqbot_enhancer`。
- 本地点歌音频放在该实例的
  `data\astrbot\plugins\qqbot_enhancer\songs\`（仅使用你有权使用的音频）。
- `config.json`、`secrets.json`、`.env`、AI 助手 `config.json` 均可能含敏感信息，请使用
  Windows ACL 限制访问，不要上传到公开仓库/issue。
- 移动数据目录后，启动器会读取 `%LOCALAPPDATA%\QQBotStudio\data-location.json`；
  也可以始终显式传 `--data-dir <目录>`。

#### 控制台入口（推荐）

管理控制台的顶部有 **存储文件夹** 按钮，页面内也有同名设置卡片：

1. 打开控制台，点击“存储文件夹”；
2. 输入/粘贴新的 Windows 绝对路径（例如 `D:\QQBotStudioData`）；浏览器因安全限制
   不能直接获取本地绝对路径，因此这里采用安全文本输入，不调用系统文件选择器；
3. 勾选“我已备份/确认停止服务和容器”，点击“开始安全迁移”；
4. 页面调用 token 保护的 `POST /api/system/move-data`。后台 helper（同一个 EXE 的
   受控子进程）停止管理服务、对旧目录的 Compose 实例执行 `down`，再复用 CLI 的
   安全复制/回滚/pointer 逻辑；
5. 迁移完成后 helper 从新目录自动重启同端口管理服务，页面检测到服务恢复后提示刷新；
   刷新后状态接口会显示 completed 或 failed 的可操作信息。

如果 helper 失败，会尝试从旧目录重启服务，旧目录始终保留；可以继续用
`--data-dir <旧目录>` 或 CLI 回滚。控制台 API：

- `GET /api/system/move-data/status`：token 保护，查看 idle/scheduled/running/completed/failed；
- `POST /api/system/move-data`：token 保护，JSON `{target, confirm:true}`，不会把路径拼接成
  shell 命令。

CLI 仍作为高级入口：

#### 安全迁移命令

```powershell
# 先备份整个默认数据目录，然后运行；交互模式会要求输入 MOVE 确认
.\QQBotStudioWindows.exe --move-data "D:\QQBotStudioData"

# 已确认备份且需要脚本自动化时
.\QQBotStudioWindows.exe --move-data "D:\QQBotStudioData" --non-interactive
```

迁移会自动：

1. 校验目标必须是本机固定 NTFS 磁盘上的**不存在或空目录**；拒绝 WSL/Docker Desktop
   WSL 路径、OneDrive、UNC/网络共享、可移动盘、未知盘和不可写 ACL；
2. 停止管理服务；对旧数据目录中已有 `compose.yml` 的实例执行
   Compose `down --remove-orphans`，避免旧 bind mount 继续运行；
3. 复制整个数据目录到目标目录（暂存 + 原子发布），写入
   `windows-data-move.json` 和 `studio.json` 的迁移字段；
4. 原子更新 `%LOCALAPPDATA%\QQBotStudio\data-location.json`；
5. **保留旧目录**作为备份，不自动删除，也不自动重启管理服务/容器。

迁移后：

```powershell
.\QQBotStudioWindows.exe --status
.\QQBotStudioWindows.exe --assistant
```

Compose bind mount 必须由 Windows 核心在新数据目录下重新执行/重建，不能只修改
`compose.yml` 字符串。若新目录不可用：

1. 以 `--data-dir <旧目录>` 运行 `--status`/`--stop`；
2. 不要把 `data-location.json` 指向不存在/不可写的位置；
3. 旧目录仍完整保留，可继续用 `--data-dir <旧目录>` 启动；确认新目录验证完成后再人工
   删除旧备份。

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
- 执行 `windows\qqbot-studio-windows.spec` 生成 Docker edition；
- 执行 `windows\qqbot-studio-windows-native.spec` 生成 Native bootstrap edition；
- 生成 `dist\QQBotStudioWindows.exe`、`dist\QQBotStudioWindowsNative.exe` 和
  `dist\SHA256SUMS.txt`（两个 EXE 都记录 SHA256）；
- 用 `--version` / `--help` 对两个 EXE 做无需 Docker 的冒烟测试。

可选参数：

```powershell
.\windows\build.ps1 -Python "C:\Path\python.exe" -SkipInstall -NoClean
```

构建产物是两个 console EXE：Docker 启动器显示配置/启动/错误信息，后台管理子进程隐藏
运行；Native bootstrap 显示官方原生部署指南和只读依赖检查。日志保留在数据目录中，
不依赖父控制台存活。

### GitHub Actions

[`.github/workflows/windows-build.yml`](.github/workflows/windows-build.yml) 会在
push/PR 时构建并上传测试 artifact。正式发布由
[`.github/workflows/windows-release.yml`](.github/workflows/windows-release.yml)
在 `v*` tag 上执行。v0.4.0 的 Release run `40997401439` 是单 EXE 历史结果；
v0.7.0 的 release workflow 已扩展为同一 Release 构建、smoke 并上传 Docker/Native
两个 EXE。构建 workflow 会：

1. 安装 Python 3.12；
2. 跑独立测试；
3. 用 PowerShell AST parser 检查脚本语法；
4. 构建 Docker 和 Native 两个 one-file EXE；
5. 执行两个 EXE 的 `--version` / `--help` smoke test，并对 Native 执行
   `--guide` / `--check`；
6. 上传 artifact `QQBotStudioWindows-dual-<sha>`。

Artifact 包括两个 EXE、SHA256、README、VERSION、LICENSE、UPSTREAM、VALIDATION、
`docs/**` 和备用 PowerShell 脚本。真实 Docker Desktop/QQ 扫码测试不在 CI runner
上执行；Native 实机 NTQQ/SnowLuma E2E 也不在 CI 中执行。

### GitHub Release workflow

[`.github/workflows/windows-release.yml`](.github/workflows/windows-release.yml) 在
推送 `v*` tag 时：

1. 校验 `VERSION` 与 tag 一致（例如 `VERSION=0.7.0` 必须对应 `v0.7.0`）；
2. 重新跑独立测试、compileall、PowerShell AST、PyInstaller 构建和 EXE smoke；
3. 上传 Actions artifact；
4. 通过 `softprops/action-gh-release@v2` 创建真实 GitHub Release；
5. 把 `QQBotStudioWindows.exe`、`QQBotStudioWindowsNative.exe`、
   `SHA256SUMS.txt`、`README.md`、`VALIDATION.md` 作为 Release assets 上传。

只上传 Actions artifact 不算发布；Release assets 必须存在。Native EXE 是
bootstrap/guide 占位，不得在 Release notes 中宣称已完成 AstrBot/SnowLuma/NTQQ E2E。

v0.4.0 实际结果：

- Run: <https://github.com/Stevehim2007/qqbot-studio-windows/actions/runs/40997401439>
- Release: <https://github.com/Stevehim2007/qqbot-studio-windows/releases/tag/v0.4.0>
- Release assets：`QQBotStudioWindows.exe`（`10,803,066` bytes，
  SHA256 `9bd92a299839fd3ec4a4c0c089356c98505fb17995edfee8d279e2b831e53f3b`）、
  `SHA256SUMS.txt`、`README.md`、`VALIDATION.md`。
- 本地执行过的核心验证、Docker compose 结果和限制见 `VALIDATION.md`。

### 主项目更新同步与双 EXE 发布规则

每次 Linux 主项目 major/minor 发布或合入需要进入 Windows 版的核心/插件/UI 变更时：

1. 必须同步 Windows 两个发行版，不允许只更新 Docker 版或只更新 Native 版；
2. `.github/workflows/sync-upstream.yml` 可由 `workflow_dispatch` 手动触发，也可按每日
   schedule 检查公开 Linux 主仓库 `Stevehim2007/qqbot-studio` 的 `main`；
3. 同步 allowlist 仅包含 `qqbot_studio/`（含 static）、`plugins/qqbot_enhancer/`、
   `assets/` 和 `docs/` 中允许的上游文档；Windows launcher、PowerShell、build/spec、
   `VERSION`、release workflow 和 Windows 专属 README/FAQ 不被覆盖；
4. 同步脚本写入 `.upstream-commit` 并更新 `UPSTREAM.md` 的 Linux commit、bundled
   core 版本和插件版本；有变化才 commit/push，无变化不产生空提交；
5. 同步后的测试必须通过，否则 workflow 不提交；版本号升级和发布 tag 仍由发布任务
   显式处理；
6. tag `v*` 发布前必须校验 `VERSION`，并同批构建/上传 Docker 与 Native 两个 EXE。
   Release workflow 还会运行 `scripts/check_upstream_state.py`，校验
   `.upstream-commit`、UPSTREAM.md、vendored core/plugin 版本一致；未同步或元数据
   不一致时直接失败、阻止发布，且不得只上传 Actions artifact。

本地 dry-run：

```powershell
python scripts\sync_upstream.py --upstream-dir ..\qqbot-studio --target-dir . --dry-run
```

Windows 文档同步规则与 Linux 主项目 `docs/windows-editions-research.md` 保持一致。

---

## 7. 已验证与未验证

### 已实际通过

本仓库已在同一台 Windows 主机上通过 WSL interop 使用 Windows PowerShell 5.1、
Windows Python 3.10.9 和 Docker Desktop 4.93.0 做了本地验证：

- 独立测试套件 **82 tests** 在 Linux Python 和 Windows Python 下均通过（Linux 仅跳过 1 个 Windows drive-type 测试）；
- Windows Python `compileall`、PowerShell 5.1 AST、Node JS 检查通过；
- Docker Desktop 4.93.0 / Engine 29.8.1 / `OSType=linux` / Compose v5.5.1；
- 最小 busybox Compose `config/up/down` 全部 exit 0，容器实际输出
  `qqbot-windows-v040-compose-smoke` 后清理；
- PyInstaller 6.10.0 实际构建出 Docker/Native 两个 one-file EXE：
  - Docker：`8,567,120` bytes，SHA256
    `e277c8428751204fd7d39296c444aade16370a3b6a513d7cea16c90d24344154`；
  - Native bootstrap：`6,405,952` bytes，SHA256
    `5d6dd0f12adb531edf174d871d229cadba84f63744de2f9c9399648a43ce3da4`；
- Docker EXE `--assistant` 启动后 `/healthz` 返回 version `3.9.0`，`/console` 与
  `/assistant` 均 HTTP 200；
- Native bootstrap `--version`/`--help`/`--guide`/`--check` 实际退出 0，但明确
  `NATIVE_E2E=NOT_VERIFIED`、`NATIVE_INTEGRATION=NOT_IMPLEMENTED_IN_BOOTSTRAP`；
- `--move-data` 最终 EXE smoke 通过：旧目录保留、目标数据/迁移记录/pointer 写入，
  可通过 pointer 在目标目录重启 `/healthz` 3.9.0，`--stop` 后 health 不可达；
- 最终插件配置 API 实测 **169 字段**；`safe_tools_marker_enabled`、
  `sticker_semantic_tags_enabled`、`collected_sticker_multi_category_enabled`、
  `sticker_ai_auto_collect_enabled` 存在，`image_search_second_source_enabled=false`
  （默认 Bing-only）；POST `reply_probability=0.57` /
  `user_sticker_reaction_probability=0.72` / `safe_tools_allow_search_images=false`
  后读取持久化值，`restart_required=true`；
- 控制台 `/console.js` 和实例设置 modal 含 **AI 工具权限 / AI 自动表情** UI；
  `/components/instance-settings.js`、`/services/plugin-config.js`、存储迁移 UI
  均 HTTP 200；partial stats 返回 `ok=true, partial=true`；
- 插件 schema 缺失时实测回退 bundled schema：`schema_source=bundled`、
  `schema_path=C:\...\_MEI...\plugins\qqbot_enhancer\_conf_schema.json`，
  169 字段；`/food` 相关字段（`food_enabled` 等）、`group_persona_enabled`、
  `group_personas`、`ai_unified_tool_protocol_enabled` 均存在；
- 通过插件配置 API 设置 `group_personas` 两群 JSON 和
  `safe_tools_allow_search_images=false`，迁移后仍读取到群 ID/默认 persona 和设置；
- 控制台实例设置 modal、`/components/instance-settings.js`、
  `/services/plugin-config.js` 实际 HTTP 200；插件列表 API 返回本地降级列表；
  未部署实例的插件开关 API 返回可操作的 400（没有 AstrBot 运行）；
- B 诊断 API `/api/assistant/diagnose` 实际 200，`healthy=false`、
  `error_code=not_installed`，并返回 listener/local_health/public_probe 字段；
- `sync-upstream` 本地 dry-run + 实际同步通过；上游记录为
  `6ed41b9b281e01b48e3f58e4ad088f3afdebe2df`（core 3.9.0/plugin 1.15.0），
  第二次 dry-run 为 no changes；GitHub workflow_dispatch 因无 token/gh 未实际触发；
- 通过 token API 创建实例 `bot-1`，并使用插件 schema 实测插件参数配置：
  - GET 返回 169 个 schema 字段；`reply_probability=0.12`，
    `user_sticker_reaction_enabled=true`；
  - POST 保存 `reply_probability=0.57` 和
    `user_sticker_reaction_probability=0.72`，离线返回
    `restart_required=true`；
  - 再次 GET 读取为 `0.57` / `0.72`；
- `/console` 含插件编辑器和 `/assistant` 链接，不含旧 A/B DOM；
- `--status` 和 `--stop` 实测通过，停止后 health 不可达。

详细命令、环境和输出见 [`VALIDATION.md`](VALIDATION.md)。

### 仍未验证

- v0.7.0 的 dual build / Release workflow 将在本次发布中实际执行；v0.6.0 Release 保留不重复 tag。
- 浏览器自动打开未测试，服务生命周期测试均使用 `--no-open`。
- `install.ps1` 全流程、winget 安装、WSL2 初始化/重启未测试。
- Windows Defender 防火墙、云安全组、局域网/VPN 远程访问未测试。
- GitHub Actions `sync-upstream` 实际 dispatch/schedule 未执行（环境没有
  gh/GH_TOKEN/GITHUB_TOKEN）；当前 v0.7.0 是本地执行同一 sync 脚本手动同步。
  请在 Actions 页面手动点一次 `Sync upstream Linux snapshot` 做远端流程验证。
- 双 EXE `v*` Release workflow 已实际执行并成功；Release URL 和两个资产 SHA 见上。
- Native EXE 仅为 bootstrap/guide 占位，不包含 AstrBot/SnowLuma/NTQQ 进程管理，
  未做真实 NTQQ 扫码、SnowLuma hook 或 native OneBot E2E；noVNC 仅是可选高级
  增强，不是 SnowLuma 自带登录二维码。
- 真实 AstrBot + SnowLuma 向导部署、DeepSeek API 和 QQ 账号登录未测试。
- noVNC 扫码、设备验证、短信/邮箱验证和滑块验证未测试。
- 长时间多实例稳定性、bind mount 属主和容器写权限未测试。

**基础 Windows 启动器、Docker Desktop 和最小 Compose 已验证；完整 QQ 部署/扫码
链路未验证，因此不能宣称 Windows 生产可用。**

## 8. 文档与 FAQ

- [`docs/README.md`](docs/README.md)：Windows 文档索引；
- [`docs/FAQ.md`](docs/FAQ.md)：`/assistant`、AI 助手 B 公网、30 分钟刷新、插件 1.15.0、
  EXE、端口和升级问题；
- [`docs/ui-api-contract-v2.md`](docs/ui-api-contract-v2.md)：最新管理 API 契约；
- [`docs/plugin-qqbot-enhancer.md`](docs/plugin-qqbot-enhancer.md)：qqbot_enhancer 1.15.0；
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
