# T03 Product Facts

> 核验日期：2026-08-13（Asia/Shanghai）
> 用途：Issue #4 视觉方向评审中的具名产品事实，不是长期产品适配文档。
> 事实等级：官方页面观察；未进行账号登录、付费服务调用或真实客户端现场测试。

## OpenAI / Codex

- OpenAI 的官方产品页 [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) 说明 Codex app 是用于管理多个 agent、并行任务和长期协作的产品界面；页面标注 2026-02-02 发布，并在 2026-03-04 更新 Windows 可用性。页面还把 CLI、IDE、app 和 cloud 作为 Codex 的工作表面。
- OpenAI 的官方 [Design Guidelines](https://openai.com/brand/) 说明 OpenAI 名称、logo、ChatGPT/GPT 等属于 OpenAI 商标；使用条件包括只在直接相关服务语境中使用、按原样使用、不暗示背书，并遵守当前 Marks usage terms。官方页面提供 wordmark 图像资源，本项目只把该 CDN URL 作为可选远程 logo 资产，不在仓库中重绘或修改。
- 本课程页面只断言“Codex 是课程的主要 Coding Agent 实例之一”，不在 T03 固定模型、客户端版本、价格、安装命令或当前 UI 布局。上述内容属于后续工具适配层，必须在正式课节当天重新核验。

## Anthropic / Claude Code

- Anthropic 官方 [Claude Code overview](https://code.claude.com/docs/en/overview)（2026-08-13 页面现场打开）描述 Claude Code 为能读取代码库、编辑文件、运行命令并连接开发工具的 agentic coding tool，工作表面包括 terminal、IDE、desktop app 和 browser。
- 同一官方页面当前列出 Windows PowerShell 的安装入口、WinGet、桌面和 web surface，并说明多数表面需要 Claude subscription 或 Anthropic Console account；本项目不复制这些安装命令到方向 demo，也不声称本次完成客户端实验。
- Anthropic 官方 [Newsroom](https://www.anthropic.com/news) 的 Media assets 区提供 “Download press kit” 入口。内存读取 press kit 后确认包含 `Claude Code logo - Slate.svg`、`Claude Code logo - Ivory.svg` 和 `Claude Code logo - One-color.svg` 等官方资产。本分支落盘的是 Slate SVG，路径为 `site/public/brands/claude-code-logo-slate.svg`。
- Anthropic 官方产品页面与 press kit 的商标/资产条款未被本项目重新许可；本 demo 只在直接介绍 Claude Code 的课程语境中展示原始比例 logo，不暗示 Anthropic 对本课程的赞助、合作或背书。

## UI 截图边界

- 官方产品页面确实包含产品说明、界面描述或可见图像，但本次没有取得一份明确允许课程仓库再发布的 Codex 或 Claude Code UI 截图许可。因此三版不下载、裁切、重制或伪造 UI screenshot。
- 需要保留视觉语义时，页面使用真实产品文本 mark、官方产品链接和“官方 UI 截图待许可核准”的文字占位。占位不会被画成像真实终端或 dashboard 的假数据，也不会写用户、任务、token、性能或价格数字。

## 未验证事项

- 未登录 Codex 或 Claude Code，未执行真实仓库任务，未验证客户端版本、模型、价格、权限行为或账号可用性。
- 未对 OpenAI CDN 远程 wordmark 的离线缓存、未来 URL 稳定性或具体分发权作承诺；若生产站需要离线可靠，应重新取得许可并使用官方可分发包。
- 未把 Anthropic press kit 的其他 PNG、Claude app 图标或 UI 画面加入课程包；后续每一项都需要独立来源和许可证记录。
