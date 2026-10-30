# Windows 文档索引

本目录保存从 Linux 主项目 v3.9.0 同步的功能/API/FAQ 文档，并补充 Windows 独立发行
项目自己的说明。

## 先读

| 文档 | 内容 |
|---|---|
| [`../README.md`](../README.md) | Windows 独立项目安装、EXE 使用、Docker Desktop/WSL2、数据与升级边界 |
| [`../VALIDATION.md`](../VALIDATION.md) | 真实执行过的测试、构建和 EXE smoke；明确未验证项 |
| [`FAQ.md`](FAQ.md) | Windows 常见问题：Docker Desktop、端口、AI 助手 B、EXE、扫码与更新 |
| [`../UPSTREAM.md`](../UPSTREAM.md) | vendor 来源、上游 commit、同步和升级流程 |

## 功能与 API

| 文档 | 内容 |
|---|---|
| [`ui-api-contract-v2.md`](ui-api-contract-v2.md) | v3.9.0 管理 API，包括 `/assistant`、AI 助手 B 配置/启停、插件、记忆、统计 |
| [`plugin-qqbot-enhancer.md`](plugin-qqbot-enhancer.md) | qqbot_enhancer 1.15.0：自然语言找图、图片下载、本地唱歌、`/option`、记忆模式 |
| [`server-troubleshooting.md`](server-troubleshooting.md) | Linux/云服务器排错资料；Windows 场景请同时阅读本目录 FAQ 和根 README |
| [`integration-research.md`](integration-research.md) | AstrBot / SnowLuma / OneBot / DeepSeek 集成调研 |
| [`qa-report-v2.md`](qa-report-v2.md) | 主项目 v3.9.0 条件验收和真实 E2E 待测清单 |
| [`windows-editions-research.md`](windows-editions-research.md) | 双发行版（Native/Docker）可行性、限制和同步发布规则 |
| [`ui-api-contract.md`](ui-api-contract.md) | 旧版单实例 API，历史兼容参考 |
| [`qa-report.md`](qa-report.md) | 旧版 QA 快照，历史参考 |

## v3.9.0 同步重点

- core 3.8.0、qqbot_enhancer 1.15.0；
- 平台感知部署向导（Windows/Ubuntu/其它 Linux）；
- 双发行版调研与同步规则 docs。

## v3.5.0 同步重点

- 控制台顶部 **“AI 助手”** 链接跳转独立 `/assistant` 页面。
- 主控制台不再内置离线“使用助手”A 面板，也不再内嵌 AI 助手 B 卡片。
- AI 助手 B 的安装、更新、配置、启动、停止和打开均在 `/assistant` 完成。
- B 支持默认回环安全模式和显式 `0.0.0.0 + public_host` 高风险公网模式。
- 控制台自动刷新改为 30 分钟，并保留手动刷新。
- qqbot_enhancer 1.15.0 增加自然语言找图、图片本地下载、唱歌/点歌、`/option` 和记忆模式。
- 用户纯 Image/Face 自动短句反应；`/收藏表情`、`/表情分类`、`/表情列表`、`/发表情`
  收藏分类/发送功能；收藏表情参与正常回复。

## 平台边界

Windows 版本不是 Linux 主项目的运行时分支。不要把 Linux 数据目录直接复制过来，
也不要使用 Linux 主项目的 screen/systemd/自动更新流程。版本升级按根 README 的
“升级边界”执行。
