# Desktop App Shell + Native One-Click Installer POC

状态：`v1.0.2` 正式 Windows Desktop App。bundled core 4.0.3、plugin 2.2.0。

## 1. Docker EXE 闪退根因与证据

结论：在当前测试机上，v0.9.0 Docker EXE **不是 Python/PyInstaller 崩溃**。
它是控制台式外部浏览器启动器：

1. 父进程启动 `--serve-management` 隐藏管理服务；
2. 等待 `/healthz` 成功；
3. 打印说明并调用 `webbrowser.open_new_tab(public_url)`；
4. 父进程按设计立即退出；管理服务留在后台。

证据（隔离 `%LOCALAPPDATA%` + 临时 data dir）：

- `QQBotStudioWindows.exe --version`：stdout
  `QQBot Studio Windows launcher 0.9.0 (core 3.13.0)`，exit 0；
- 空参数首次运行：stdout 显示 Docker ready、`Management service healthy`、
  `The launcher exits now`；stderr 为空；
- 空参数 + 已配置设置：launcher 进程退出（观察约 7 秒），
  `/healthz` 返回 `{"ok":true,"version":"3.13.0"}`；
- `studio-server.log` 显示浏览器确实请求了 `/console`、`/console.js`、
  `/services/api.js` 等资产并全部 HTTP 200；
- Application/System Event Viewer 无匹配 Error；
- `Get-MpThreatDetection` 无记录，Windows Defender 近期 Operational 日志无匹配；
- SmartScreen/Debug 无近期匹配事件；
- 本地构建 EXE 未被标记 Zone.Identifier（无 Mark-of-the-Web），但未签名
  (`Authenticode=NotSigned`)；正式下载资产仍需单独验证 MOTW/SmartScreen；
- 未发现新的 onefile `_MEI*` 解包目录或解包错误。

因此用户看到的“闪退”最可能是：**控制台父进程按设计快速退出，且外部浏览器没有
成为用户可见的应用窗口**。首次运行另一个风险是 `public_host` 自动探测到公网 IP，
启动器打开 `http://<public-ip>:8765/console` 而不是 loopback；本机回环/NAT/防火墙
不允许自访问时浏览器会失败，而控制台此时已关闭，用户只看到闪退感。

POC 修复方向：不再启动外部浏览器；父进程保持到 WebView2 窗口关闭；App 窗口始终
加载 `http://127.0.0.1:<port>/...`。窗口启动失败时显示可复制的错误窗口。

## 2. App Shell 技术选择

- `pywebview==6.2.1` + 系统已安装的 Microsoft Edge WebView2 Runtime；
- 实测 WebView2 Runtime：`156.0.4314.50`，`msedgewebview2.exe` 可启动；
- 不引入 Electron/Tauri，不重写业务 UI；
- Docker 版窗口直接承载现有 `/console`、`/assistant`、`/wizard` HTML；
- Native 版窗口承载新的单实例 Native 仪表盘；
- 共用 `windows/app_shell.py`：
  - WebView2 窗口；
  - 左侧 App 导航分栏：第一行“控制台”，第二行“向导”；
  - 文件日志；
  - 页面内“诊断日志”浮层（复制/打开日志目录）；
  - pywebview/WebView2 失败时退回 Tk 错误窗口，窗口内显示可复制日志，不静默退出；
- Docker App 导航：
  - “控制台”-> `/console`；
  - “向导”-> 读取 `/api/instances` 后打开 `/wizard?instance=<本机实例>`；无实例时打开 `/wizard` 入口；
  - 全程同一 WebView2 窗口内导航，不打开外部浏览器。
- 向导复用 Linux v4.0.1/task-96 的锁定逻辑并移植到 Windows 当前 core 4.0.3 静态页面：
  - 向导侧栏加入“快速跳转步骤”下拉菜单；
  - 步骤 1 环境、2 账号与模型、3 部署进度、4 完成与运行；
  - `deployment.deployed || app.jobCompleted` 后前三步按钮和下拉选项全部禁用，只允许“完成与运行”；
  - 已部署页面显示“环境/账号/部署步骤已锁定”说明。
- `QQBOT_APP_AUTOCLOSE_SECONDS` 仅用于自动化 smoke，正式用户不设置。
- Docker 窗口始终用 loopback URL；`public_host` 只用于显示/远程访问链接。

## 3. Docker App 窗口 POC 实测

构建：`windows/build.ps1`，Windows Python 3.10，PyInstaller 6.10.0。
v1.0.2 EXE：

- Docker：16,155,923 bytes，SHA256
  `188e198590bfa0f3a3a997ecc25f445dac42a0821ffe3c76bf48ef11ffb58c27`
- Native：14,931,831 bytes，SHA256
  `2a533ec63abd74435c40f1cf1efa52cbac29a370124af30bfb1ce84a1c529778`

用隔离环境、预配置 loopback、`QQBOT_APP_AUTOCLOSE_SECONDS=6` 启动 Docker EXE：

- app window 打开现有控制台，左侧 App 导航显示“控制台/向导”；
- app-shell.log：
  - `starting app window ... url=http://127.0.0.1:18830/console`
  - `app navigation and diagnostics panel injected`
  - `app window closed normally`
- 自动化 POC hook 点击“向导”后，server log 实际出现
  `GET /wizard?instance=bot-1 HTTP/1.1 200`，页面显示 Linux v4.0.1
  同源的“快速跳转步骤”下拉菜单；
- server log 显示控制台及 services/api.js 等资产全部 HTTP 200；
- 管理服务在窗口关闭后仍健康，健康检查 3.13.0；
- 不再依赖外部浏览器。

## 4. Native App / 一键安装 POC

- Native 启动器默认打开 Native 仪表盘窗口，不再默认打印 CLI guide；
- 仪表盘同样有左侧“控制台/向导”导航；向导含 4 步下拉菜单
  （环境检查/安装组件/配置与启动/完成与人工验证），组件安装完成后
  前三步锁定，只允许进入完成与人工验证；
- 仪表盘显示 NTQQ/AstrBot/SnowLuma/Node 状态、安装进度、运行控制、
  诊断日志复制/打开目录；
- 一次安装核心在 `windows/native_setup.py`，全部使用固定官方来源并校验大小/SHA256：
  - uv 0.13.6 Windows ZIP；
  - AstrBot 4.29.3 PyPI wheel；
  - SnowLuma 2.2.1 win-x64-lite GitHub Release；
  - Node.js 26.13.0 nodejs.org Windows x64 ZIP；
- 安装流程：下载/校验 → uv 安装 Python 3.12 → AstrBot venv → 生成 AstrBot
  `cmd_config.json` dashboard/OneBot 配置 → 解压 SnowLuma/Node → 写 SnowLuma
  `config/onebot.json` → 选 loopback 空闲端口 → 保存 Native config；
- NTQQ 只检测 `D:\Program Files\Tencent\QQ.exe`（当前环境找到 9.9.19.35469），
  不自动扫码/登录；
- SnowLuma EULA/PRIVACY、QQ 扫码/设备/短信/滑块全部人工。

POC 验证：

- Native EXE `--install-plan --json` 在真实 Windows 上返回：
  NTQQ present、Windows x64 true、uv/node 检测结果、4 个官方来源与 SHA256；
- Native App 窗口启动/自关闭成功，日志记录
  `starting HTML app window` / `HTML app window closed normally`；
- 未重复执行真实组件下载/安装：task-72 已真实验证 AstrBot 4.29.3/SnowLuma 2.2.1/
  Node 26.13 的启动；本轮遵循“不重复 Native 真机安装”的范围限制。
- 一键安装的完整下载→安装→启动 E2E 仍需在有网干净用户目录执行一次后再宣称完成。

## 5. 导航与向导补充验证：导航与向导演进

- 已同步 Linux v4.0.1/task-96 的向导步骤下拉与部署后前三步锁定逻辑到
  Linux v4.0.3 静态页面（Windows v1.0.2 已全量同步）；新增 `wizard-step-select`、`wizard-step-lock-note`，
  `deploymentStepsLocked()/isStepAvailable()` 单元 JS 测试通过。
- Docker App 实际截图/自动化 smoke：左栏“控制台/向导”正常，点击“向导”
  成功进入 `/wizard?instance=bot-1`，页面内下拉菜单可见；无外部浏览器。
- Native 仪表盘增加相同左栏导航；向导 4 步下拉/锁定代码就绪。
- 上游 Linux **450 tests OK**；Windows 独立套件 **108 tests OK**（Linux 1 个
  Windows-only skip）；
  最终 POC 构建哈希：
  - Docker `16,155,923` bytes
    `188e198590bfa0f3a3a997ecc25f445dac42a0821ffe3c76bf48ef11ffb58c27`
  - Native `14,931,831` bytes
    `2a533ec63abd74435c40f1cf1efa52cbac29a370124af30bfb1ce84a1c529778`

## 6. 当前限制与未验证项

- App shell POC 尚未在真实用户干净目录做首次双击/缩放/DPI/托盘体验验收；
- 正式下载的 v0.9.0 EXE 有 MOTW/SmartScreen/未签名下载风险，本轮未能下载 release
  资产（GitHub 网络重置），使用同源本地 v0.9.0 构建复现，结论以实际文件证据为准；
- pywebview/WebView2 打包已实测可用；如果目标机 WebView2 Runtime 缺失，
  当前会显示 Tk 错误窗口，后续可增加 WebView2 Runtime 引导安装；
- Native 一键安装的下载/安装完整 E2E 未执行；官方 URL/SHA/大小、环境检测、
  AstrBot 配置生成代码已实现；
- QQ 扫码/EULA/真实消息 E2E 仍为 ENV_BLOCKED；
- Windows VERSION 1.0.2；正式发布由唯一 `v1.0.2` tag 触发。
- v1.0.2 smoke：config GET schema/values 均 193，`reply_probability=0.12`，
  `ambient_group_reply_probability` 返回弃用兼容说明；`/option` ambient 文案匹配；
  schema 缺失时返回 `schema_source=bundled` + `schema_warning`。
