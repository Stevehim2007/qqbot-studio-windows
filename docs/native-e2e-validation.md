# Native Windows 真实组件安装与启动验证

日期：2026-10-31（本机时区）
验证对象：Windows Native POC（真实验证使用 `VERSION=0.7.1`；该 runtime 代码在
v0.8.0 中保留，Native EXE 只做了版本/`--check` smoke，未重复安装真实组件）
Windows repo commit `4860d12` 加本文件所在提交
验证范围：Windows 10/11 x64 原生进程；无 Docker、无 WSL、无 noVNC，
单实例；QQ 登录只在官方本机 NTQQ 窗口中人工完成。

## 结论

| 项目 | 结果 | 说明 |
|---|---|---|
| NTQQ 发现 | PASS | `D:\Program Files\Tencent\QQ.exe`，9.9.19.35469，进程和主窗口存在 |
| AstrBot 4.29.3 安装/启动 | PASS | uv + Python 3.12.14，临时 venv；WebUI HTTP 200 |
| SnowLuma 2.2.1 Windows 包安装/启动 | PASS | 官方 win-x64 lite zip + 官方 Node 26.13.0；WebUI HTTP 200 |
| Native configure/check | PASS | `--configure`、`--check --strict-check` exit 0 |
| OneBot 地址 | PASS（监听层） | `ws://127.0.0.1:16199/ws`，AstrBot TCP 监听=true |
| `--write-onebot-config` | PASS | SnowLuma `config/onebot.json` 写入 loopback URL/token，#sl disabled |
| Native start/status/health/logs/stop | PASS | 两进程真实 PID；health OK=true；stop 后端口全部关闭 |
| SnowLuma EULA/PRIVACY | ENV_BLOCKED（人工） | WebUI 启动后等待用户同意，未自动点击/绕过 |
| QQ 扫码/设备/短信/滑块 | ENV_BLOCKED（人工） | 未操作用户 QQ 登录；未声称已登录 |
| SnowLuma → AstrBot OneBot 实际握手 | ENV_BLOCKED | EULA/QQ 登录未完成，未观察到 SnowLuma ws client 连接日志 |
| QQ 消息收发 | ENV_BLOCKED | 未登录，不能做消息 E2E |

最终标记：

```text
NATIVE_REAL_INSTALL=PASS
NATIVE_REAL_START=PASS
NATIVE_ASTRBOT_WEBUI=PASS
NATIVE_SNOWLUMA_WEBUI=PASS
NATIVE_ONEBOT_LISTENER=PASS
SNOWLUMA_ONEBOT_CONNECTION=ENV_BLOCKED
QQ_LOGIN=ENV_BLOCKED
```

## 环境与官方来源

| 组件 | 版本/路径 | 来源与校验 |
|---|---|---|
| Windows | `Microsoft Windows NT 10.0.26200.0` x64 | 本机 |
| NTQQ | 9.9.19.35469，`D:\Program Files\Tencent\QQ.exe` | 已安装；进程运行，主窗口标题 `QQ`；未自动登录 |
| Python | 3.12.14 | uv 管理的 Python；未改系统默认 Python 3.10 |
| AstrBot | 4.29.3 | PyPI 官方 `astrbot` 4.29.3 wheel，requires-python >=3.12；wheel SHA256 `b78d8ab2d6f153c18be7162799b8589c9f5284233d557c93364c22193fe6be8e` |
| SnowLuma | 2.2.1 win-x64-lite | 官方 GitHub Release asset `SnowLuma-v2.2.1-win-x64-lite.zip`，6,851,206 bytes，SHA256 `29e11c07978f2e970ad918a574650573b74f8ee796e6fa39747dbfb5f74c08f6` |
| Node.js | 26.13.0 win-x64 | 官方 `nodejs.org` zip，41,157,375 bytes，SHA256 `dcc60d59a0746999f99064a01c020445d54d84228c691cdbf25b49ac3b59150a`（与官方 `SHASUMS256.txt` 一致） |

SnowLuma lite 包要求 Node `^24.22.1 || >=26.12.1`；本机原有 Node 22.21.1
不满足，因此使用官方 Node 26.13.0；没有使用第三方镜像或不可信包。

所有安装和运行数据均在临时目录：

```text
C:\Users\33299\AppData\Local\Temp\qqbot-native-real-v071\
├── astrbot-venv\
├── native\                 # Native POC 临时数据根
├── snowluma\               # 官方 SnowLuma 解压目录
├── node-v26.13.0-win-x64\
└── windows-repo\
```

没有写入用户正式 `%LOCALAPPDATA%\QQBotStudio\data`，没有修改 Linux 主项目。

## 执行步骤（实际使用）

1. 用 uv 创建 Python 3.12 venv，并从 PyPI 安装 AstrBot 4.29.3：

```powershell
uv venv C:\...\astrbot-venv --python 3.12
uv pip install --python C:\...\astrbot-venv\Scripts\python.exe astrbot==4.29.3
```

2. 解压官方 SnowLuma win-x64-lite 到临时 `snowluma` 目录，解压官方 Node 26
   到临时 `node-v26.13.0-win-x64`，并设置 PATH 优先级。

3. 运行 AstrBot `init -y`；随后在临时 AstrBot root 的
   `data\cmd_config.json` 中配置：

```json
{
  "dashboard": {"host": "127.0.0.1", "port": 16185},
  "platform": [{
    "id": "qqbot-onebot",
    "type": "aiocqhttp",
    "enable": true,
    "ws_reverse_host": "127.0.0.1",
    "ws_reverse_port": 16199,
    "ws_reverse_token": "<native.json 中同一 token>"
  }]
}
```

说明：AstrBot 的这项目前仍需用户/验证脚本通过官方 WebUI 或
`cmd_config.json` 配置；Native POC 本轮没有内置 AstrBot 全量配置生成器。
本验证的记录中不打印 token/password。

4. Native 配置（临时数据根）：

```powershell
QQBotStudioWindowsNative.exe --configure --non-interactive ^
  --data-dir C:\...\native ^
  --ntqq-path "D:\Program Files\Tencent\QQ.exe" ^
  --astrbot-command "C:\...\astrbot-venv\Scripts\astrbot.exe run --port 16185" ^
  --snowluma-dir C:\...\snowluma ^
  --astrbot-webui-port 16185 ^
  --astrbot-onebot-port 16199 ^
  --snowluma-webui-port 5099
QQBotStudioWindowsNative.exe --check --strict-check --data-dir C:\...\native
QQBotStudioWindowsNative.exe --write-onebot-config --data-dir C:\...\native
QQBotStudioWindowsNative.exe --start --data-dir C:\...\native
```

5. 等待后执行 `--status`、`--health`、`--logs`，最后 `--stop`。

## 实际结果

### Native configure / strict check / OneBot config

- `--configure` exit 0；
- `--check --strict-check` exit 0：
  - windows OK
  - ntqq OK
  - astrbot command OK
  - snowluma dir/launcher OK
  - node OK
  - onebot URL OK
- `--write-onebot-config` exit 0，写入
  `snowluma\config\onebot.json`：
  - `networks.wsClients[0].url = ws://127.0.0.1:16199/ws`
  - `accessToken` 与 Native `native.json` 中的临时 token 相同
  - `role = Universal`、`messageFormat = array`
  - `statusCommand.enabled = false`，`trigger = #sl`（不会注册为聊天命令）

### start/status/health

真实最终 Native EXE 在等待 12 秒后：

```text
NATIVE_HEALTH_OK=True
NATIVE_ASTRBOT_ALIVE=True HTTP=200 DETAIL=HTTP 200
NATIVE_SNOWLUMA_ALIVE=True HTTP=200 DETAIL=HTTP 200
NATIVE_ONEBOT_PORT=16199 LISTENING=True URL=ws://127.0.0.1:16199/ws
NATIVE_NO_VNC_USED=True
```

状态 JSON 摘要：

- AstrBot: running=true, PID 真实，command
  `...\astrbot.exe run --port 16185`
- SnowLuma: running=true, PID 真实，
  command 为官方 `cmd.exe /d /c ...\snowluma\launcher.bat`
- AstrBot WebUI: `http://127.0.0.1:16185/` HTTP 200
- SnowLuma WebUI: 实际端口 `5099`（来自 `snowluma/config/runtime.json`）
  HTTP 200；`snowluma_webui_port_effective=5099`
- OneBot: `ws://127.0.0.1:16199/ws`，TCP listener=true
- QQ: `D:\Program Files\Tencent\QQ.exe`，进程运行且主窗口存在

日志摘要：

- AstrBot log 出现 `AstrBot v4.29.3`、`Loading IM platform adapter
  aiocqhttp(qqbot-onebot)`、`Starting WebUI at http://127.0.0.1:16185`、
  `AstrBot started`；
- SnowLuma log 出现 `SnowLuma starting`、`listening http://127.0.0.1:5099`、
  `awaiting EULA/PRIVACY consent before the panel unlocks`；
- Native `--logs` 能正常退出，包含 AstrBot/SnowLuma 上述日志，不因 emoji 崩溃。

### stop

- `--stop` exit 0；
- 停止后 16185/16199/5099 均无 listener；
- 停止后 `--status --json` 显示 AstrBot/SnowLuma running=false、health=false；
- 没有遗留 Native 管理的 AstrBot/SnowLuma 进程；
- 用户 QQ 进程仍在运行（stop 后重新查询为 true），没有被 Native 管理器停止；
- 没有操作或停止用户 QQ 进程（QQ 进程原本即由用户启动并保持运行）。

## 发现的问题与 Windows repo 小修复

1. **SnowLuma WebUI 端口以自身 runtime.json 为准**：
   SnowLuma 2.2.1 不接受 Native `--snowluma-webui-port` 参数覆盖；实际会监听
   `snowluma/config/runtime.json` 里的 `webuiPort`。已在
   `windows/native_runtime.py` 增加 `snowluma_effective_webui_port()`，health 和
   status 自动读取该文件的端口；用真实 SnowLuma runtime.json 做了单元测试。
2. **Windows GBK 控制台下 `--logs` 遇到日志 emoji 会编码失败**：
   已让 Native launcher 在输出日志前把 stdout/stderr 配置为容错替换，避免
   `--logs` 因日志中的 emoji 抛出 UnicodeEncodeError；真实日志 smoke 通过。
3. **AstrBot cmd_config 目前仍需手工/外部配置**：Native POC 只负责生成
   SnowLuma OneBot 配置和进程/端口/健康管理，不伪造 AstrBot 全量配置。
   在没有 AstrBot 配置时 OneBot 端口不会按预期工作；这是已记录的 GAP，
   不是本轮已自动化能力。
4. **首次 6185 端口尝试出现 WinError 10013（ENV_BLOCKED/瞬时）**：
   首次真实 AstrBot 尝试在 6185 绑定失败；切换临时端口 16185/16199/5099 后
   完整启动通过。已完成 socket 探测和复测，但未把 6185 当作稳定可用端口。

## 人工阻塞步骤（未绕过）

- SnowLuma WebUI 明确等待 EULA/PRIVACY 同意；本验证没有自动点击、伪造同意或
  绕过法律/隐私确认。
- 本机 NTQQ 已运行，但没有扫描二维码、没有输入密码、没有处理设备/短信/邮箱/
  滑块验证；因此：
  - 没有 QQ 登录成功声明；
  - 没有 SnowLuma hook 成功声明；
  - 没有 SnowLuma → AstrBot OneBot 实际握手声明；
  - 没有 QQ 消息收发声明。
- OneBot 16199 的 AstrBot listener 已验证为 TCP listening，但这只是服务器监听，
  不等于 SnowLuma 客户端已连接。

## 清理

验证完成后已停止 Native 管理的两个进程，16185/16199/5099 均无 listener。
随后删除临时数据根、AstrBot venv/SnowLuma/Node 解压目录和临时构建目录；
未触碰用户正式实例，未修改 Linux 主项目。
