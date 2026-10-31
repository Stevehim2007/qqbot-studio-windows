# Windows 文档索引

本目录保存从 Linux 主项目 v3.13.0 同步的功能/API/FAQ 文档，并补充 Windows 独立发行
项目自己的说明。

## 先读

| 文档 | 内容 |
|---|---|
| [`../README.md`](../README.md) | Windows 独立项目安装、EXE 使用、Docker Desktop/WSL2、数据与升级边界 |
| [`../VALIDATION.md`](../VALIDATION.md) | 真实执行过的测试、构建和 EXE smoke；Native POC 进程/health/PID 结果和未验证项 |
| [`native-e2e-validation.md`](native-e2e-validation.md) | 真实 AstrBot 4.29.3 + SnowLuma 2.2.1 + NTQQ 临时目录安装/启动/health/OneBot/stop 验证及人工阻塞 |
| [`FAQ.md`](FAQ.md) | Windows 常见问题：Docker Desktop、端口、AI 助手 B、EXE、扫码与更新 |
| [`../UPSTREAM.md`](../UPSTREAM.md) | vendor 来源、上游 commit、同步和升级流程 |

## 功能与 API

| 文档 | 内容 |
|---|---|
| [`ui-api-contract-v2.md`](ui-api-contract-v2.md) | v3.13.0 管理 API，包括 `/assistant`、AI 助手 B 配置/启停、提示词 profiles、插件、记忆、统计 |
| [`plugin-qqbot-enhancer.md`](plugin-qqbot-enhancer.md) | qqbot_enhancer 1.22.0：会话级提示词模板/pinned、按名会话、ambient、群身份、`/表情状态`、多分类语义收藏 |
| [`server-troubleshooting.md`](server-troubleshooting.md) | Linux/云服务器排错资料；Windows 场景请同时阅读本目录 FAQ 和根 README |
| [`integration-research.md`](integration-research.md) | AstrBot / SnowLuma / OneBot / DeepSeek 集成调研 |
| [`qa-report-v2.md`](qa-report-v2.md) | 主项目 v3.13.0 条件验收、P0/P1 和真实 E2E 待测清单 |
| [`windows-editions-research.md`](windows-editions-research.md) | 双发行版（Native/Docker）可行性、限制和同步发布规则 |
| [`ui-api-contract.md`](ui-api-contract.md) | 旧版单实例 API，历史兼容参考 |
| [`qa-report.md`](qa-report.md) | 旧版 QA 快照，历史参考 |

## v3.13.0 同步重点

- core 3.13.0、qqbot_enhancer 1.22.0；
- 提示词 profile 作为会话模板库，pinned/default_profile 排序；
- activate 只更新默认模板，不 pending/新建会话；`/新会话` 可选模板；
- `/会话` 仅切换已有；旧 system_prompt UI 去重、配置 backup 恢复；
- `/表情状态` 收藏存储诊断；
- Windows Native POC 与真实启动验证文档保留。

## v3.12.1 同步重点（历史）

- core 3.12.1、qqbot_enhancer 1.21.0；
- Ponytail phase 2：共享 `qqbot_studio/gitutil.py`、`static/services/api.js`；
- HTML 显式加载共享 API；同步 `tests/e2e/` harness，排除 artifacts；
- prompts/ambient/persona、多分类语义收藏和 `/food` 功能保留；
- Windows Native POC 与真实启动验证文档保留。

## v3.12.0 同步重点（历史）

- core 3.12.0、qqbot_enhancer 1.21.0；
- 提示词 profiles/active/新会话、按名会话、AstrBot 每群 Persona/记忆；
- ambient 全群短期上下文、低频参与、@ 发言人/私聊边界、群身份；
- 多分类/语义收藏、`/food`、统一 tool marker；
- prompt API/UI、stale/pending restart、容量上限、E2E/QA 文档；
- Windows Native POC 及真实启动验证记录继续保留。

## 平台边界

Windows 版本不是 Linux 主项目的运行时分支。不要把 Linux 数据目录直接复制过来，
也不要使用 Linux 主项目的 screen/systemd/自动更新流程。版本升级按根 README 的
“升级边界”执行。
