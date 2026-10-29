# Windows FAQ

## 1. 为什么控制台里没有“使用助手”或 AI 助手 B 卡片？

从 v3.3.0 同步版本开始：

- 旧离线“使用助手”A 面板已删除；
- 内嵌 AI 助手 B 卡片已删除；
- 控制台顶部保留 **“AI 助手”** 链接，点击进入独立页面 `/assistant`。

Windows EXE 可直接打开该页面：

```powershell
.\QQBotStudioWindows.exe --assistant --data-dir "$env:LOCALAPPDATA\QQBotStudio\data"
```

如果管理服务已经在运行，也可以直接访问：

```text
http://127.0.0.1:8765/assistant
```

## 2. /assistant 页面能做什么？

- 检查 AI 助手 B 是否已安装；
- 确认后从固定官方仓库安装或更新；
- 配置独立 DeepSeek API Key，或复用某个 bot 实例的 Key（页面不显示 Key）；
- 设置端口（默认 8766）；
- 选择仅本机 `127.0.0.1` 或所有网卡 `0.0.0.0`；
- 公网/所有网卡模式必须填写 `public_host`（IP 或域名）；
- 启动、停止和打开 B；
- B 未安装/后端旧版本时显示可恢复提示，不阻塞控制台。

## 3. AI 助手 B 用 0.0.0.0 安全吗？

默认应使用 `127.0.0.1`。B **没有内置登录认证**，`0.0.0.0` 会使其监听所有网卡。
如必须公网访问：

1. 在 Windows Defender 防火墙/云安全组中只允许固定来源 IP 或 VPN 网段；
2. B 的端口默认 8766，实际端口以页面为准；
3. 不要把会话页面、API Key 或访问地址随意公开；
4. 更推荐本机使用，或 SSH 隧道/反向代理加认证。

`public_host` 只用于生成可点击 URL，不会自动创建防火墙规则。绑定 `0.0.0.0` 后，
回环地址仍用于启动器的健康检查。

## 4. 控制台多久刷新一次？

v3.3.0 起默认自动刷新 **30 分钟**（`30 * 60 * 1000` 毫秒），并保留“手动刷新”
按钮。手动刷新会立即更新并重新计时。不要把旧版 8 秒轮询当作当前行为。

## 5. EXE 首次运行卡住或 Docker 未就绪

先确认 Docker Desktop 已启动，托盘状态正常，并完成首次登录/许可提示：

```powershell
docker version
docker info --format "{{.OSType}}"
docker compose version
```

`OSType` 必须为 `linux`。再检查：

```powershell
.\QQBotStudioWindows.exe --status
.\QQBotStudioWindows.exe --logs 200
```

## 6. 管理页面或 /assistant 打不开

```powershell
Invoke-RestMethod http://127.0.0.1:8765/healthz
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

- 如果绑定 `127.0.0.1`，其他设备无法访问；需要局域网访问时重新配置 `--ip 0.0.0.0`，
  并检查 Windows Defender 防火墙；
- 云 Windows 主机还需要在云安全组放行；
- 修改 `public_host` 只影响打印 URL，不会改变监听或防火墙。

## 7. 插件 1.4.1 有哪些新命令？

- `/找图 关键词`、`/搜图 关键词`，以及插件支持的自然语言找图意图；
- 图片会先安全下载到本地临时文件，再通过 AstrBot 官方本地图片组件发送；
- `/唱歌`、`/点歌`：发送 `songs/` 中用户自行提供的授权音频，不调用 LLM；
- `/option`：查看/进入插件配置说明；
- `memory_mode=direct/astrbot`：选择省 token 直连或 AstrBot 会话记忆。

详见 [`plugin-qqbot-enhancer.md`](plugin-qqbot-enhancer.md)。

## 8. 为什么每个新实例都必须扫码？

新实例有独立 SnowLuma 数据目录和登录态。首次部署必须在 noVNC 中打开 QQ 官方登录
窗口扫码；设备验证、短信/邮箱验证、滑块等都需要用户手动完成。工具不会保存或代填
QQ 密码，也不会绕过验证。

## 9. Windows 如何升级？

**不要**使用 Linux 主项目的自动更新，也不要直接共用数据目录：

1. 下载新的 Windows artifact/EXE；
2. `QQBotStudioWindows.exe --stop`；
3. 备份 `%LOCALAPPDATA%\QQBotStudio\data`；
4. 替换 EXE 和发行文件；
5. `QQBotStudioWindows.exe --status`；
6. 重新验证容器、插件和 AI 助手 B。

## 10. 能否把 Linux 数据复制到 Windows？

不建议。Windows/Linux 的 Docker 宿主、路径、容器发布端口、登录态和程序版本边界不同。
迁移实例前必须停机、备份并逐项复验容器、插件、QQ 登录和 AI 助手 B。
