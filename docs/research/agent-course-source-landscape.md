# AI Agent 网页课程资料源版图

> 状态：第一轮资料审计完成，覆盖 OpenAI/Codex、Anthropic/Claude Code、两家 API/Agent SDK、Agent Skills、Plugins、MCP 及高影响力课程与模式库。
>
> 快照日期：2026-08-12（GitHub 的 stars、forks 与 pushed_at 通过仓库 REST 元数据核对；数字会持续变化）。

## 1. 结论先行

这门课不应从“工具菜单”开始，而应先建立一个稳定的心智模型：Agent 是“模型在上下文中反复决定下一步，并通过工具改变外部状态”的系统。Memory、Skills、Plugins、MCP 与 API 都是在解决这个循环里的不同问题，不能混为一谈。

建议采用四层资料优先级：

1. 协议规范与产品官方文档：负责定义事实、接口、当前行为和安全边界。
2. 官方 SDK、Cookbook 与 Quickstart：负责提供可运行的最小实战。
3. 高影响力课程：负责借鉴教学顺序、练习设计和案例梯度。
4. 社区插件与工作流仓库：只作为模式库和反例库，不作为产品事实来源。

本轮审计还发现两个必须写进课程维护制度的风险：

- MCP 已于 2026-07-28 发布新的正式规范，并改为无状态核心；初始化握手与会话标识退出核心，Roots、Sampling、Logging 及旧 HTTP+SSE 路径进入弃用周期。教程必须标注规范版本，不能只写“支持 MCP”。
- OpenAI 的 [openai/skills](https://github.com/openai/skills) 已明确标记 deprecated，并把当前 Skill/Plugin 示例导向 [openai/plugins](https://github.com/openai/plugins)；旧仓库只能用于历史比较，不能继续作为 Codex 教学主线。
- [microsoft/autogen](https://github.com/microsoft/autogen) 已进入 maintenance mode，并建议新用户转向 Microsoft Agent Framework。高 star 不能抵消技术路线已退居维护的事实。
- 用户指定的 [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 在快照当天刚把 canonical 主线重构为 17 课，且没有 release 或 tag。它很适合解释 harness 机制，但课程必须固定 commit、重写安全层，并用官方资料校准产品事实。
- 高 star 不代表可以直接复用。Anthropic Skills、Hello-Agents、GenAI_Agents 等仓库存在混合许可、非商业许可或自定义许可；课程内容应以原创讲解和最小必要引用为主。

## 2. 应作为“事实真源”的官方文档

| 官方资料 | 类型 | 最适合支撑的课程模块 | 使用边界与过时风险 |
| --- | --- | --- | --- |
| [Codex documentation](https://learn.chatgpt.com/docs)、[Codex CLI](https://learn.chatgpt.com/docs/codex/cli) 与 [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) | 产品与 SDK 官方文档 | Codex 环境、交互模式、自动化入口；从 CLI 真实仓库任务过渡到程序化调用 | 安装命令、配置键、客户端界面和模型选择都属于易变层；逐课记录客户端版本与核验日期。 |
| [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | Codex 项目指令参考 | 指令发现、作用域、优先级、仓库内可审计约束 | 它是项目指令，不等于长期 Memory；课程应分别测试根目录和嵌套目录的生效边界。 |
| [Memories](https://learn.chatgpt.com/docs/customization/memories) | Codex/ChatGPT Memory 官方说明 | 用户偏好、历史信息、跨会话定制与隐私管理 | Memory 与当前上下文、AGENTS.md、检索知识必须分开；行为和管理入口可能随产品变化。 |
| [Build skills](https://learn.chatgpt.com/docs/build-skills) 与 [Skills and Plugins](https://learn.chatgpt.com/docs/skills-and-plugins) | Codex Skill/Plugin 概念与制作说明 | Skill 渐进披露；Plugin 作为 skills、connectors/MCP 及可选 UI 的安装包；两者职责对照 | 产品能力仍在快速扩展。格式的可移植核心应以 Agent Skills 标准校验，Codex 字段和装配规则单独标注。 |
| [Plugins](https://learn.chatgpt.com/docs/plugins) 与 [Build plugins](https://learn.chatgpt.com/docs/build-plugins) | Codex Plugin 安装、使用与构建说明 | 清单、组件装配、分发、升级和供应链审计 | Plugin 会扩大执行和数据访问面；示例必须包含来源、权限、凭据、卸载与版本锁定检查。 |
| [MCP](https://learn.chatgpt.com/docs/extend/mcp) | Codex 的 MCP 客户端与扩展说明 | MCP server 配置、工具发现、认证与作用域 | 这是 Codex 产品集成层，不代替 MCP 规范；协议事实继续以当前 MCP specification 为准。 |
| [Responses API conversation state](https://developers.openai.com/api/docs/guides/conversation-state) 与 [Compaction](https://developers.openai.com/api/docs/guides/compaction) | OpenAI API 状态与上下文官方指南 | 手动历史、连续 response、上下文压缩；澄清“状态”和“持久 Memory”的区别 | API 状态机制和具体产品 Memory 不同；示例需明确由谁保存、何时删除、压缩后保留什么。 |
| [Function calling](https://developers.openai.com/api/docs/guides/function-calling)、[MCP and connectors](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) 与 [Agents SDK](https://developers.openai.com/api/docs/guides/agents) | OpenAI API 工具循环与 Agent 开发真源 | 手写 tool loop、远程 MCP/连接器、编排、guardrails、tracing 与 eval | 动态模型、价格和参数不宜进入稳定正文；独立为“当前版本卡片”，并只链接当前官方文档。 |
| [Claude Code overview](https://code.claude.com/docs/en/overview) 与 [Extend Claude Code](https://code.claude.com/docs/en/features-overview) | 产品概览、扩展能力地图 | Claude Code 入门；CLAUDE.md、Skill、MCP、Subagent、Hook、Plugin 的职责对照 | 产品快速迭代。每个实操页应记录测试过的 Claude Code 版本与复核日期。 |
| [How Claude remembers your project](https://code.claude.com/docs/en/memory) | 官方 Memory 行为说明 | 项目指令层级、CLAUDE.md、Auto Memory、跨会话记忆、可审计性 | Memory 与 context window 必须分开讲；本页还包含版本门槛和加载上限，数值可能变化。 |
| [Explore the context window](https://code.claude.com/docs/en/context-window)、[Best practices](https://code.claude.com/docs/en/best-practices) 与 [Checkpointing](https://code.claude.com/docs/en/checkpointing) | 交互说明、实践指南 | 上下文预算、压缩、子代理隔离、回退与会话恢复 | 产品行为而非跨工具标准；不要把 Claude Code 的压缩与记忆机制泛化成所有 Agent 的机制。 |
| [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands) | Claude Code Skill 完整参考 | 第一个 Skill、触发描述、渐进披露、作用域、权限、fork context | Claude Code 在开放标准之上增加了额外 frontmatter 与运行行为，应明确区分“标准字段”和“Claude 扩展”。 |
| [Create plugins](https://code.claude.com/docs/en/plugins)、[Plugins reference](https://code.claude.com/docs/en/plugins-reference) 与 [Discover plugins](https://code.claude.com/docs/en/discover-plugins) | Plugin 制作、清单、市场与安装参考 | Skill 和 Plugin 的区别；把 skills、agents、hooks、MCP、LSP 打包发布 | 第三方插件是可执行供应链入口。课程必须加入信任、权限、缓存、升级与卸载检查。 |
| [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) | Claude Code 的 MCP 客户端配置 | stdio/HTTP、作用域、项目共享配置、环境变量、Tool Search | 页面明确旧 SSE 已弃用；示例应优先 HTTP 或 stdio，并避免把密钥写入仓库。 |
| [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)、[How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop) 与 [Use Claude Code features in the SDK](https://code.claude.com/docs/en/agent-sdk/claude-code-features) | SDK 概念与运行时说明 | 从 CLI 使用者过渡到 Agent 开发者；工具、权限、会话、Skill、MCP | 旧名 Claude Code SDK 已更名；课程不要沿用旧包名或旧类型名。 |
| [Messages API](https://platform.claude.com/docs/en/api/messages/create) 与 [How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) | API 参考、工具循环解释 | 最小 API 请求；tool_use/tool_result 循环；客户端与服务端工具 | Messages API 是无状态接口，历史需要调用方回传；不要把 SDK 的持久会话误认为 API 自动记忆。 |
| [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) 与 [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) | API 上下文和持久记忆参考 | working memory、context rot、compaction、JIT memory retrieval | Memory tool 在客户端执行，存储由应用负责；这正适合用来解释“模型不会凭空长期记住”。 |
| [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) 与 [Using Agent Skills with the API](https://platform.claude.com/docs/en/build-with-claude/skills-guide) | Skills 架构与 API | Skill 的渐进披露、上传、版本固定、长任务 continuation | API Skills 与 Claude Code/Claude.ai 的安装面并非天然同步；课程应把源码仓库作为单一真源。 |
| [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture)、[Server concepts](https://modelcontextprotocol.io/docs/learn/server-concepts) 与 [Build a server](https://modelcontextprotocol.io/docs/develop/build-server) | 官方概念与入门教程 | Host/Client/Server；Tools、Resources、Prompts；第一个 server | 概念页可讲稳定心智模型；实现细节必须再对照当前版本规范，因为部分概览缓存仍可能描述旧生命周期。 |
| [MCP 2026-07-28 release](https://blog.modelcontextprotocol.io/posts/2026-07-28/) 与 [MCP specification](https://modelcontextprotocol.io/specification/latest) | 当前版本发布说明与规范 | 规范版本、无状态核心、扩展、授权、弃用与迁移 | 这是 MCP 实现事实的最高优先级。所有实验代码必须固定 SDK 大版本和规范版本。 |
| [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) | 官方调试工具说明 | 工具、资源、Prompt、日志的可视化检查；实验验收 | 适合成为 MCP 每个实验的统一验收工具，而不是只靠“客户端能连上”。 |
| [Agent Skills specification](https://agentskills.io/specification) | 开放格式规范 | SKILL.md 结构、必需字段、渐进披露、跨客户端可移植性 | 规范只定义可移植核心；触发、权限和运行细节仍由具体 Agent 产品决定。 |

## 3. 官方 GitHub 仓库证据表

除特别标注外，以下 pushed_at 均为 UTC 日期，stars/forks 是 2026-08-12 快照。数字只说明影响力和活跃度，不说明教学质量或许可安全。

| 仓库 | 类型 | Stars / Forks | 最近推送 | 许可证 | 可用于课程的内容与注意事项 |
| --- | --- | ---: | --- | --- | --- |
| [openai/codex](https://github.com/openai/codex) | Codex CLI 官方实现与参考仓库 | 105,520 / 15,997 | 2026-08-12 | Apache-2.0 | 安装、配置、CLI 行为、贡献结构和 issue 的代码真源；它是大型产品仓库而非线性教程，课堂命令仍以官方文档为准。 |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 官方 Python Agent SDK | 28,574 / 4,482 | 2026-08-12 | MIT | Agent、tools、handoffs、guardrails、sessions/tracing 与 eval 实验的首选 Python 参考；应在手写 tool loop 之后引入。 |
| [openai/openai-cookbook](https://github.com/openai/openai-cookbook) | 官方 API 配方与 Notebook | 75,206 / 12,713 | 2026-08-12 | MIT | Responses API、工具、agent、检索、上下文与评估的选择性实验源；不是按先修关系组织的课程，需要重写成统一项目。 |
| [openai/openai-python](https://github.com/openai/openai-python) | 官方 Python API SDK | 31,343 / 5,119 | 2026-08-12 | Apache-2.0 | 最小 API、Responses、流式和类型化请求的实现参考；不要用 SDK README 代替概念课，也不要在长期正文写死易变模型名。 |
| [openai/plugins](https://github.com/openai/plugins) | 当前官方 Codex/ChatGPT Plugin 示例集 | 约 5,100 / 686 | 2026-07-13（main 最新提交） | 仓库根目录未见统一 LICENSE | 适合解剖 manifest、skills、MCP/connectors、agents、commands 与 hooks 的装配；复用前必须检查每个 plugin 子目录的许可和外部条款。 |
| [openai/skills](https://github.com/openai/skills) | 已弃用的官方 Skill 示例仓库 | 24,854 / 1,689 | 2026-07-14 | 根目录未声明统一许可证；子 Skill 可能各自带 LICENSE | README 已标记 deprecated 并指向 openai/plugins。只可用于迁移/历史对照，不应成为当前课程链接或代码基线。 |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 产品发布、示例与问题跟踪仓库 | 141,182 / 22,681 | 2026-08-11 | 非开源；LICENSE.md 指向 Anthropic Commercial Terms | 用于确认官方入口和示例位置，不应当作可自由复制的开源教材或完整产品源码。README 已提示 npm 安装弃用。 |
| [anthropics/skills](https://github.com/anthropics/skills) | 官方 Skill 示例、模板与插件市场 | 168,462 / 20,068 | 2026-08-07 | 混合许可；许多示例为 Apache-2.0，docx/pdf/pptx/xlsx 等为 source-available | Skill 解剖、skill-creator、mcp-builder 和插件打包的首选示例。复用前必须查具体子目录许可。 |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) | Agent Skills 标准与文档 | 24,181 / 1,762 | 2026-08-09 | 代码 Apache-2.0；文档 CC-BY-4.0 | 课程中“跨工具 Skill 核心格式”的真源；适合制作标准字段与产品扩展字段对照实验。 |
| [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) | API Notebook 与配方库 | 51,416 / 6,097 | 2026-08-07 | MIT | Tool use、RAG、sub-agent、prompt caching 等实践案例。应挑选少量并重写成统一的课程项目，不要堆 Notebook。旧链接 anthropic-cookbook 已迁至当前名称。 |
| [anthropics/courses](https://github.com/anthropics/courses) | 官方教学 Notebook | 22,604 / 2,431 | 2025-11-13 | CC BY-NC 4.0 | API fundamentals、tool use、prompt evaluation 的教学顺序值得借鉴；README 仍以 Claude 3 Haiku 为低成本示例，模型名与参数需全量刷新。非商业限制需关注。 |
| [anthropics/claude-quickstarts](https://github.com/anthropics/claude-quickstarts) | 可部署应用示例 | 17,422 / 3,006 | 2026-08-06 | MIT | 浏览器自动化、客户支持、金融分析、版本化 memory-store wiki 等综合项目；适合进阶拆解，不适合作为零基础第一课。 |
| [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) | 官方 Python SDK | 7,867 / 1,217 | 2026-08-11 | MIT | Agent loop、hooks、MCP、权限和 SDK 集成实验的代码真源。课程须固定依赖版本并保留升级测试。 |
| [modelcontextprotocol/modelcontextprotocol](https://github.com/modelcontextprotocol/modelcontextprotocol) | MCP 规范与文档仓库 | 8,935 / 1,710 | 2026-08-11 | 正在从 MIT 迁至 Apache-2.0；文档为 CC-BY-4.0，部分旧贡献仍为 MIT | MCP 规范事实真源。当前 LICENSE 比 README 中笼统的 MIT 描述更准确，引用或再发布时以具体文件为准。 |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Steering group 维护的参考服务器 | 89,485 / 11,435 | 2026-08-10 | 同 MCP 许可迁移说明 | 只用于展示协议与 SDK 用法。README 明确说明不是 production-ready；大量早期 server 已归档或转由供应商维护。 |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | 官方 Python SDK | 23,993 / 3,776 | 2026-08-12 | MIT | Python MCP 实验首选。当前 pip install mcp 安装 2.x；README 要求尚未迁移者固定小于 2，旧教程极易失效。 |
| [modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk) | 官方 TypeScript SDK | 13,147 / 2,070 | 2026-08-11 | 当前仓库采用 MCP 许可迁移说明 | TypeScript MCP 实验首选；同样需要固定大版本和规范版本。 |
| [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | MCP 可视化测试工具 | 10,652 / 1,471 | 2026-08-12 | package.json 声明 MIT；仓库根目录未见独立 LICENSE 文件 | 适合作为 MCP server 实验的统一 QA 工具。若要再分发其源码或素材，先进一步确认许可文本。 |

## 4. 高影响力教程与模式库

| 仓库 | 类型 | Stars / Forks | 最近推送 | 许可证 | 适合借鉴的模块 | 关键 caveat |
| --- | --- | ---: | --- | --- | --- | --- |
| [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) | 17 课 Agent Harness 解剖课程 | 73,974 / 11,986 | 2026-08-12 | MIT | 用独立 Python `code.py` 从 agent loop 递进到 tools、permissions、hooks、skills、context compaction、memory、tasks、teams、MCP、workflow 与 goal loop；另有中英日讲义和 Next.js 网页 | 非官方 clean-room 教学实现，不是 Claude Code 产品事实源；刚从旧 12 课迁移、无 tag/release，应固定 [eb4307f](https://github.com/shareAI-lab/learn-claude-code/commit/eb4307f4e495d2ed22699e1e5682eb55f8076ade)。示例偏 Bash/POSIX，MCP 课仅为进程内 stand-in，安全层不能照抄。 |
| [microsoft/ai-agents-for-beginners](https://github.com/microsoft/ai-agents-for-beginners) | 18 课开源课程 | 72,000 / 23,854 | 2026-07-29 | MIT | Agent 定义、工具、RAG、规划、多 Agent、协议、context、memory、生产与安全的课程梯度；含简体中文等 50+ 语言入口 | 代码当前强绑定 Microsoft Agent Framework 与 Foundry；借鉴结构和多语言导航，不要把厂商栈当作 Agent 通用定义。 |
| [microsoft/mcp-for-beginners](https://github.com/microsoft/mcp-for-beginners) | 多语言 MCP 课程 | 16,969 / 5,524 | 2026-08-09 | MIT | 从概念到 server/client、安全、部署、case study 的模块化实验设计 | README 仍把 2025-11-25 称为最新稳定版，并把 2026-07-28 写成未来 RC；截至本快照已过时，只能先借鉴教学结构。 |
| [huggingface/agents-course](https://github.com/huggingface/agents-course) | 四单元课程 | 30,906 / 2,201 | 2026-06-30 | Apache-2.0 | Agent 基础、框架比较、observability/evaluation、Agentic RAG 与毕业考核 | 产品中立度较好，但重点是 smolagents/LangGraph/LlamaIndex，不覆盖 Claude Code 或 Plugin 体系。 |
| [datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents) | 中文系统课程 | 72,543 / 9,034 | 2026-08-12 | CC BY-NC-SA 4.0 | 最有价值的中文课程基准：范式、从零框架、Memory/RAG、上下文工程、MCP/A2A/ANP、评估和综合项目 | 与本项目受众高度重合，必须做原创结构与讲解；若课程有商业计划，不能直接复用其非商业、相同方式共享内容。 |
| [langchain-ai/langchain-academy](https://github.com/langchain-ai/langchain-academy) | LangGraph Notebook 课程 | 约 2,800 / 1,800 | 2026-06-15（main 最新提交） | MIT | 显式状态、持久执行、部署与调试练习；可为“stateful agent”提供一条可运行路径 | 强依赖 LangGraph、LangSmith、Tavily 等生态与密钥；只选一两个状态实验，不增设完整厂商支线。 |
| [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) | 生产设计原则 | 25,261 / 1,916 | 2025-09-21 | Apache-2.0 | Own your prompts/context/control flow、tool call、pause/resume、human-in-the-loop、错误压缩、小 Agent | 是观点鲜明的原则集而非完整课程；更新较旧，不能代替当前 SDK、MCP 与产品文档。 |
| [coleam00/context-engineering-intro](https://github.com/coleam00/context-engineering-intro) | Claude Code 中心的 PRP 模板教程 | 13,770 / 2,716 | 2026-03-16 | MIT | CLAUDE.md、需求输入、示例、文档检索、validation gates 的端到端上下文工作流 | 适合做“上下文包”实战；“10x/100x”等宣传性判断不是可验证事实，且仓库明确不以 RAG/工具为重点。 |
| [NirDiamant/GenAI_Agents](https://github.com/NirDiamant/GenAI_Agents) | 53+ Agent Notebook 案例库 | 23,773 / 3,990 | 2026-07-31 | 自定义非商业许可 | 会话 Agent、MCP、LangGraph、多 Agent、业务案例的选题库 | 依赖与框架分散，不宜用作主课程骨架；商业复用需另行获得许可。 |
| [obra/superpowers](https://github.com/obra/superpowers) | 跨工具 Skill 框架与软件工程方法 | 271,120 / 24,228 | 2026-08-12 | MIT | Skill 自动触发、Plugin 安装、设计→计划→TDD→subagent 的完整工作流 | 极度观点化；高 star 不能替代安全审查和效果评测。适合作为“一个插件如何塑造 Agent 行为”的案例。 |
| [wshobson/agents](https://github.com/wshobson/agents) | 多运行时 Plugin/Skill 市场 | 38,743 / 4,128 | 2026-08-05 | MIT | Plugin 目录结构、渐进披露、跨 Claude Code/Codex 等 harness 的适配、质量评估 | 体量很大且包含可执行工作流；只能选小样本做结构审计，安装前逐项检查权限、脚本和外部依赖。 |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Agent 状态图框架 | 39,533 / 6,636 | 2026-08-11 | MIT | 显式状态、checkpoint、memory 与可恢复工作流的实现选项 | 是框架参考而非入门课程；不要让框架 API 抢在 Agent loop 心智模型之前。 |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 独立 Memory 层与集成示例 | 63,116 / 7,355 | 2026-08-12 | Apache-2.0 | 可做长期记忆写入、检索、冲突、删除和评测的实现型实验 | 是一种产品/架构选择，不是 Memory 的中立定义；应与文件记忆、向量检索和平台内置 Memory 做对照。 |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 类型化 Agent 框架 | 19,246 / 2,507 | 2026-08-12 | MIT | API-first Agent、类型安全工具、结构化输出、测试 | 可做第二种框架风格对照，不应扩张为又一条完整主线。 |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | Claude Code 资源导航 | 约 52,200 / 4,600 | 活跃；本轮未单独核对 pushed_at | CC BY-NC-ND 4.0 | 发现 commands、hooks、skills、workflows 和工具候选 | “ND”禁止改编，且 awesome list 不是事实真源；只用于链接发现，不能复制改写成课程资源包。 |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | CLI、模板与组件目录 | 约 30,200 / 3,400 | 活跃；本轮未单独核对 pushed_at | MIT | agents、commands、hooks、MCP、settings、skills 的大规模目录案例 | 含第三方与推广内容；安装前做脚本、权限、网络和每个来源的二次审计，不能把目录规模当质量证明。 |

### 4.1 用户指定来源的并排定位

这些来源不是彼此替代关系。课程应明确给每个仓库分配一种角色，避免把教程、样例库、市场目录和产品仓库混成同一种“权威教程”。

| 用户指定来源 | 固定角色 | 2026-08-12 维护/许可信号 | 在本课程中负责什么 | 不能承担什么 |
| --- | --- | --- | --- | --- |
| [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) | **核心机制实验源：Agent Harness 解剖实验室** | 73,974 stars；11,986 forks；当天更新；MIT；无 tag/release | 借鉴“稳定 loop + 逐层增加机制 + 独立代码 + 最后集成”的实验节奏；重点支撑 tool loop、context、memory、permission、subagent、task 与 workflow | 不能定义 Claude Code 或 Codex 当前产品行为；不能直接提供 production security 或真实 MCP transport |
| [microsoft/ai-agents-for-beginners](https://github.com/microsoft/ai-agents-for-beginners) | **广度课程骨架** | 72,000 stars；23,854 forks；2026-07-29 更新；MIT | 补齐用例、设计模式、RAG、规划、多 Agent、评估、安全、生产化和多语言课程组织 | 不能把 Microsoft Agent Framework/Foundry 的概念和安装路径写成跨厂商标准 |
| [anthropics/skills](https://github.com/anthropics/skills) | **官方 Skill 实例与实验源** | 168,462 stars；20,068 forks；2026-08-07 更新；根目录无统一 SPDX，子目录混合许可 | 解剖真实 SKILL.md、渐进披露、skill-creator、mcp-builder 与 plugin packaging；与 Agent Skills 规范做字段对照 | 不能假定整个仓库都可按同一许可证复制；也不能用 Anthropic 扩展反推开放标准 |
| [microsoft/mcp-for-beginners](https://github.com/microsoft/mcp-for-beginners) | **MCP 教学脚手架** | 16,969 stars；5,524 forks；2026-08-09 更新；MIT | 借鉴 server/client、安全、部署与 case study 的教学梯度和多语言实验组织 | 不能作为当前规范真源；首页仍把已经发布的 2026-07-28 规范写成未来版本，实验必须按官方规范/SDK 重建 |
| [wshobson/agents](https://github.com/wshobson/agents) | **Plugin/Skill 模式目录与供应链审计样本** | 38,743 stars；4,128 forks；2026-08-05 更新；MIT | 选少量插件分析目录、触发描述、组件组合、跨 harness 适配和质量 rubric，并练习安装前审计 | 不能整体安装后当“最佳实践”；仓库许可不自动覆盖每个外部服务、脚本副作用和运行时依赖 |
| [openai/codex](https://github.com/openai/codex) | **Codex 官方实现/发行参考** | 105,520 stars；15,997 forks；当天更新；Rust；Apache-2.0 | 与 OpenAI 官方文档共同校验 Codex 安装、配置、CLI、issue、release 和实现细节；为真实仓库任务提供产品轨 | 不是线性入门课程；仓库实现也不能替代随时更新的产品文档、账号和托管端行为 |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | **Claude Code 官方产品/发行参考** | 141,182 stars；22,681 forks；2026-08-11 更新；LICENSE 指向 Commercial Terms | 与 code.claude.com 共同校验官方入口、配置、插件示例、变更和 issue；为真实仓库任务提供产品轨 | 不是可自由复制的开源课程或完整产品源码；Commercial Terms 下的内容不可因公开可见就视为 MIT/Apache 素材 |

建议组合不是“七选一”，而是：**Microsoft 课程给广度，shareAI-lab/learn-claude-code 给机制实验，Anthropic Skills 和 Microsoft MCP 课程给专题实验素材，wshobson/agents 给生态审计样本，两家官方仓库和官方文档负责事实校准。**

### 4.2 `shareAI-lab/learn-claude-code` 的当前结构与采用方式

#### 当前可复核版本

- 本轮固定到 [main commit `eb4307f4e495d2ed22699e1e5682eb55f8076ade`](https://github.com/shareAI-lab/learn-claude-code/commit/eb4307f4e495d2ed22699e1e5682eb55f8076ade)，提交时间为 2026-08-12 01:47:36 UTC，提交说明是将课程精简为 17 个 harness lessons。仓库级 `pushed_at` 为同日 14:52:21 UTC。
- 当前 [README](https://github.com/shareAI-lab/learn-claude-code/blob/main/README-zh.md) 指定的 canonical 课程是根目录 `s01_agent_loop` 到 `s17_goal_loop`；`docs/` 与 `agents/` 是旧 12 课迁移轨，并明确要求新读者不要混用新旧章节号。
- GitHub API 返回 0 个 release 和 0 个 tag，所以不能写“适用于 vX.Y”；进入课程的任何代码或图示都应固定上述 commit，并单独记录下一次复核日期。
- 根目录 [LICENSE](https://github.com/shareAI-lab/learn-claude-code/blob/main/LICENSE) 是 MIT。若实际复制代码，需保留版权与许可文本；课程讲解、图示和代码最好重新创作，第三方素材和商标仍逐项清权。

#### 两条互相正交的组织轴

该仓库的 README 先给出 17 课顺序：Agent loop → tool use → permission → hooks → TodoWrite → subagent → skill loading → context compact → memory → task system → background tasks → cron → agent teams → MCP → integrated harness → workflow runtime → goal loop。它又把学习旅程概括为七阶段：行动、处理复杂工作、跨会话记忆、长任务、多 Agent 协作、扩展与组装、编排与目标闭环。

同一个网页的 [layer definitions](https://github.com/shareAI-lab/learn-claude-code/blob/main/web/src/lib/constants.ts) 还提供横向能力层视图：Tools & Execution（s01–s04）、Planning & Control（s05–s07、s17）、Memory Management（s08–s09）、Concurrency & Scheduling（s11、s12、s16）和 Multi-Agent Platform（s10、s13–s15）。前者回答“先学什么”，后者回答“这项机制属于哪里”，这种双导航很值得借鉴。

本课程不复制它的章节名、文案、图示或五层分类，而采用同样的**双轴原则**重新组织：纵向用一个“研究与交付助手”逐步增强；横向则按“Agent 核心循环与工具 / 上下文与 Memory / Skill、Plugin 与 MCP / Codex 与 Claude Code 产品实践 / API、评估与生产治理”聚合。这样保留认知优势，同时补上原仓库较弱的 Codex、双 API、真实 MCP、评估和生产安全。

#### 实现栈与教学强项

- Agent 章节是 Python，使用 Anthropic SDK；[CI](https://github.com/shareAI-lab/learn-claude-code/blob/main/.github/workflows/test.yml) 固定 Python 3.11。[requirements.txt](https://github.com/shareAI-lab/learn-claude-code/blob/main/requirements.txt) 只有 `anthropic>=0.25.0`、`python-dotenv>=1.0.0`、`pyyaml>=6.0`，没有上限锁定。
- 每章提供中/英/日讲义、独立 `code.py` 和必要 SVG；网页从根课程抽取内容，[web/package.json](https://github.com/shareAI-lab/learn-claude-code/blob/main/web/package.json) 显示它使用 Node 20 CI、Next.js 16.1.6、React 19.2.3 与 TypeScript 5，并提供 lesson、compare、layers、timeline、simulator、architecture 等视图。
- 最可取的教学设计是：核心 loop 尽量不改，每章只让一个新机制进入；既能单独运行，也在 s15 汇合为 integrated harness。这比一开始抛出大型框架更适合解释“SDK/CLI 替你做了什么”。

#### 必须重写或补齐的风险

- 这是作者对 Claude Code 关键设计的非官方教学重建。关于“agency 来自哪里”等表述属于作者观点，关于 Claude Code/Codex 的事实必须回到两家官方文档和官方仓库。
- [s01/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/main/s01_agent_loop/code.py) 用 `subprocess.run(..., shell=True)` 执行模型生成的命令，只用少数字符串黑名单挡危险操作；[贡献指南](https://github.com/shareAI-lab/learn-claude-code/blob/main/CONTRIBUTING.md) 也明确教学代码刻意不做 production hardening。本课程必须改成 PowerShell 7 原生命令、明确工具 schema、路径边界、allow/deny policy、人工批准和隔离工作区。
- [s14 MCP lesson](https://github.com/shareAI-lab/learn-claude-code/blob/main/s14_mcp_plugin/README.md) 明确把 `docs`、`deploy` server 实现为进程内 stand-in，**没有真实 MCP transport**，依赖中也没有 MCP SDK。它只能解释动态工具发现、命名和 host policy；真正 MCP 实验必须另用当前官方 SDK、2026-07-28 规范和 Inspector。
- CI 只有 Ubuntu，README quickstart 使用 Bash/POSIX 命令；没有 Windows/PowerShell 验证。所有拟采用实验都要做 Windows 11 + PowerShell 7 的独立验收。
- 后半程不再是“nano”：commit-pinned GitHub contents 显示 s13 `code.py` 为 67,403 bytes，s15 为 117,612 bytes。面向初学者时应拆成可观察子系统，而不是整文件逐行讲。
- 没有 release/tag、SDK 仅设最低版本、示例需要 API key 与 `MODEL_ID`；真实调用具有成本、模型差异和非确定性。课程应锁依赖、提供录制 fixture/模拟验收与小额 live API 双模式，但不得把模拟通过写成真实 API 通过。

### 4.3 明确降级或排除

- [microsoft/autogen](https://github.com/microsoft/autogen)：仓库已进入 maintenance mode，并把新用户导向 Microsoft Agent Framework。可用于讲多 Agent 发展史，不作为新课代码栈。
- [anthropics/prompt-eng-interactive-tutorial](https://github.com/anthropics/prompt-eng-interactive-tutorial)：约 36,400 stars，但只有少量提交，示例仍以 Claude 3 系列命名，重点也是 prompt engineering 而非 Agent。只借鉴练习反馈方式，不进入 Agent 主线。
- [crewAIInc/crewAI-examples](https://github.com/crewAIInc/crewAI-examples)：6,131 stars、2,177 forks，最后推送 2026-04-20，仓库已归档且 GitHub 元数据未声明许可证。可以用于理解历史生态，不应成为新课程实验依赖。
- GitHub 上的 awesome 列表适合发现候选，不适合支撑接口事实；所有关键结论仍需回到官方文档、规范或原仓库。
- 任何没有固定依赖版本、没有验收步骤、只展示最终截图的 Agent 示例，都不应直接进入实战课程。

## 5. 对整体课程规划的直接启示

### 5.1 推荐的知识顺序

1. Agent 心智模型：模型、上下文、工具、循环、环境、权限与停止条件。
2. 第一个工具循环：先用原生 API 手写最小循环，再解释 CLI/SDK 替学员封装了什么。
3. Context：上下文窗口、token 成本、context rot、选择、隔离与压缩。
4. Memory：会话历史、工作记忆、持久记忆、检索、写入策略与遗忘。
5. 项目指令：用同一个仓库对照 Codex 的 AGENTS.md 与 Claude Code 的 CLAUDE.md，测试作用域和冲突优先级。
6. Skills：把可复用知识和流程做成按需加载资产，区分 Agent Skills 标准核心与产品扩展，并进行触发/误触发测试。
7. Plugins：把 Skill、Agent、Hook、MCP/Connector 等组件打包分发，补上清单、许可、供应链安全和升级策略。
8. MCP：先讲 Host/Client/Server 与 Tools/Resources/Prompts，再做 server、两个 client、Inspector、认证和错误实验。
9. Codex 实战：从受控只读任务到跨文件修改、验证、review，再接入 Skill、Plugin、MCP 和 SDK。
10. Claude Code 实战：在同一仓库完成等价任务，对照 checkpoint、subagent、hook、Skill、Plugin、MCP 与权限模型。
11. 双 API/SDK：OpenAI Responses API/Agents SDK 与 Anthropic Messages API/Agent SDK 各实现同一最小 Agent，比较状态所有权、工具循环和部署边界。
12. 生产化：评估、可观测性、HITL、故障恢复、成本、安全、隐私和版本迁移。
13. 综合项目：同一真实任务分别用 Codex、Claude Code 和一个 API Agent Application 实现，用统一 rubric 比较结果。

这个顺序故意把 Memory、Skill、Plugin、MCP 分开：

- Context 是模型本轮能看到的工作集。
- Memory 是跨步骤或跨会话保存并按需取回的信息。
- Skill 是按需加载的程序性知识、参考材料与脚本包。
- Plugin 是分发和装配多个扩展组件的容器。
- MCP 是 Host/Client/Server 之间交换工具、资源与 Prompt 能力的协议。
- API/SDK 是把 Agent loop 嵌入应用并控制状态、权限和执行环境的编程界面。

还应把 **Agent 产品体验** 与 **Agent Application 开发** 分成两条验收线：前者检验能否用 Codex/Claude Code 安全完成真实仓库任务，后者检验能否用 API/SDK 明确拥有状态、工具、权限、停止条件和失败恢复。两者共享概念，但不是同一种能力。

### 5.2 推荐的实战主线

建议全课只维护一个逐步增强的“研究与交付助手”，而不是每章换一个玩具 Demo：

1. API 请求回答一个问题。
2. 增加两个客户端工具并手写循环。
3. 给工具结果设预算，观察上下文膨胀与压缩。
4. 增加可审计的项目 Memory，并设计写入/检索/删除策略。
5. 把调研流程提取成 Skill，测试应触发与不应触发样例。
6. 把 Skill、Hook 与一个 MCP server 打成 Plugin。
7. 用 Inspector 验证 MCP tools/resources/prompts 与错误路径。
8. 在 Codex 中完成真实仓库任务，记录计划、权限、AGENTS.md、变更和验证证据。
9. 在 Claude Code 中完成同一任务，记录 CLAUDE.md、权限、checkpoint、subagent 和 context 使用。
10. 分别用 OpenAI Agents SDK 与 Claude Agent SDK 做一个最小后台任务；核心课程可二选一实现，进阶课完成双实现对照。
11. 加入评估集、人工审批、日志、成本上限、失败恢复和版本锁定，并由网页呈现相同验收 rubric。

### 5.3 每一课的维护契约

每个实操页至少显示：

- 最后验证日期、操作系统、客户端版本、模型标识、SDK/依赖锁定版本。
- 使用的协议版本；MCP 实验当前应明确写 2026-07-28 或说明兼容层。
- 预估 token/API 成本与是否需要付费账号。
- 权限与副作用：读、写、执行、网络、凭据、外部消息。
- 一条成功路径、一个预期失败、一个恢复步骤。
- 自动检查或可观察验收，而不是只凭最终自然语言回答。
- 来源与许可；摘录、改写、代码复用分别标记。

## 6. 建议的来源采用决策

| 用途 | 首选 | 次选 | 不建议 |
| --- | --- | --- | --- |
| 定义 Agent、context、memory、tool loop | OpenAI 与 Anthropic 官方 API/产品文档 + 原生 API 行为 | Microsoft/Hugging Face/Datawhale 的教学解释 | 社区博客的单句定义 |
| 全课广度与章节骨架 | microsoft/ai-agents-for-beginners 的覆盖矩阵 + 本课程自己的受众/项目目标 | Hugging Face/Datawhale 用于检查遗漏 | 逐章翻译任一现成课程 |
| Harness 机制实验 | 固定 commit 的 shareAI-lab/learn-claude-code，用其增量机制思路重写 Windows-safe 实验 | 官方 API tool loop 与 Agents SDK 例子交叉校验 | 直接运行其 shell 工具、安全黑名单或把其观点写成产品事实 |
| Codex | learn.chatgpt.com 官方文档 + openai/codex | openai/cookbook 与当前 openai/plugins 的小样本 | 已弃用 openai/skills 作为现行基线 |
| Claude Code | code.claude.com 官方文档 + anthropics/claude-code | shareAI-lab/learn-claude-code 用于解释机制；anthropics/skills、cookbooks、quickstarts 用于实验 | 把 clean-room 教学实现当真实产品内部，或把 Commercial Terms 仓库当可自由改编源码 |
| Skill 标准 | agentskills.io + agentskills/agentskills | Codex/Claude Code Skill 文档中的产品扩展；两家官方示例 | 从任意热门 Skill 反推“标准” |
| Plugin | 两家官方 Plugin 文档与当前官方示例 | wshobson/agents 的小样本解剖与供应链审计；Superpowers 作观点案例 | 直接安装巨大市场后当作教学环境 |
| MCP | 2026-07-28 规范、官方 SDK、Inspector | microsoft/mcp-for-beginners 的教学结构；shareAI s14 仅解释 tool-pool/host-policy 边界 | 把 shareAI 进程内 stand-in 或未标规范版本的旧 server 教程当真实互操作实验 |
| OpenAI API/SDK | Responses、conversation state、function calling、Agents SDK 官方文档和仓库 | openai-cookbook 的精选配方 | 从旧 Assistants 示例建立新课程主线 |
| Claude API/SDK | Messages API、tool use、Agent SDK 官方文档与官方仓库 | 官方 cookbook/quickstarts | 复制旧 Notebook 而不更新模型和 beta header |
| 中文课程表达 | 原创讲解；以 Hello-Agents 比较覆盖缺口 | 参考其章节梯度并重新设计 | 直接翻写受 CC BY-NC-SA 约束的正文 |

## 7. 后续研究缺口

- 确认课程的商业属性、代码许可证与截图/商标使用规则，再决定哪些第三方素材可进入网页。
- 对候选实验在 Windows PowerShell 7 环境做真实安装与运行验证；当前结论只完成资料与仓库层审计。
- 为 MCP 2026-07-28 选定 Python 或 TypeScript 主栈并做一个最小兼容性 PoC。
- 确定课程受众是否要求 Python/TypeScript 前置知识，以及 API 成本预算。
- 在课程范围确定后，逐项建立 Codex 与 Claude Code 的“相同概念、不同名称、无直接对应”能力矩阵；本轮只完成来源地图，不声称两者功能完全等价。

## 8. 核验说明

- GitHub 热度、许可证元数据和 pushed_at 来自各仓库的 GitHub REST 元数据；特殊许可证又读取了仓库内 LICENSE、LICENSE.md、LICENSE.txt 或 package.json。
- 课程内容、仓库类型与 caveat 均回到仓库 README 或官方文档核对，没有把搜索摘要当作唯一依据。
- Stars 与 forks 仅用于判断社区影响力，不用于判断正确性、安全性、教学质量或许可可用性。
- 本轮没有安装 Codex、Claude Code 或 SDK，没有调用付费 API，也没有完成 Windows、浏览器、账号权限和真实 MCP 互操作测试；“可用于实验”表示资料层适配，不表示实验已经跑通。
- GitHub 数字是快照；少数社区仓库无法在本轮稳定取得精确 pushed_at，已在表内直接标为“未单独核对”，没有用 stars 代替维护性证据。
- 许可证判断用于选材筛查，不构成法律意见。只要课程将公开发布或商业化，就应对实际复制的每个文件、图片、Notebook 与依赖重新做一次逐文件许可审计。
- 官方文档常没有稳定展示逐页更新时间。课程上线前应重新核验所有命令、配置键、模型、价格、beta header、SDK 大版本与 MCP 规范版本，并把核验结果写入页面的版本卡片。
