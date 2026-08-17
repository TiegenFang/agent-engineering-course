# Agent 工程入门

本仓库用于建设公开、免费、可版本化的中文网页课程《Agent 工程入门：从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战》。课程面向科研与企业团队中的技术型 Agent 初学者，以 Coding Agent 实战为主，并用最小 Agent Application 解释底层能力。

## Current state

- v1.0.0 已发布（2026-08-16，GitHub Pages 正式站与 tag `v1.0.0`）：自动化门槛全绿；T34 真人跨平台与真实工具验收、T12 试学审计按维护者决定延后，issue 保持开启，课节内继续如实标注未验证边界；工程决定与验证证据记录在 [worklog.md](./docs/worklog.md)。
- 2026-08-17 起按维护者决定启动 v2 零基础重定位：受众词条、网页端起步章、BYO-key 浏览器直连实验（ADR-0008）与案例参考库；规格与 ticket 见 [v2 总规格](./docs/specs/agent-engineering-course-v2.md)，实现按 ticket 推进、不顺手扩scope。
- v1 总规格是 GitHub [Issue #1](https://github.com/TiegenFang/agent-engineering-course/issues/1)，状态为 `ready-for-agent`。
- 实施顺序固定为 Foundation、Alpha 纵向切片、Core Beta、v1；推进时仍按依赖前沿逐个 ticket 解锁，不在实现中顺手扩展范围。
- 工作区已连接 Git remote（origin/main）；GitHub 操作按 [issue tracker](./docs/agents/issue-tracker.md) 约定显式使用 `--repo TiegenFang/agent-engineering-course`。
- 本地 ticket 工作区使用 git worktree；`node_modules` 通过目录 junction 共享主工作区副本，操作约定见 [worktree workflow](./docs/agents/worktree-workflow.md)。

## Source-of-truth order

先按当前 ticket 控制本次工作范围，再按以下顺序解释项目约束：

1. [CONTEXT.md](./CONTEXT.md)：课程领域语言；命名课程概念时使用其中定义的术语。
2. [课程总体规划](./docs/course-plan.md)：受众、课程结构、练习、网站、维护和发布门槛。
3. [架构决策](./docs/adr/)：已经接受且需要长期保持的取舍。
4. [v1 总规格](./docs/specs/agent-engineering-course-v1.md)：完整用户故事、实现决定、测试决定和范围边界。
5. [资料源版图](./docs/research/agent-course-source-landscape.md)：截至 2026-08-12 的来源审计快照；它不是当前产品行为的永久真源。

当前 ticket 可以收窄交付范围，但不能静默推翻领域语言、规划或 ADR。发现冲突时，明确指出冲突及其影响，待维护者决定是否修改上层决策。

## Read by task

- 修改课程定位、模块、课节或结课项目：读课程总体规划、相关 ADR 和 v1 总规格。
- 修改 Codex、Claude Code、API、Skill、Plugin 或 MCP 内容：再读资料源版图，并在实现当天核对相应官方文档或规范。
- 修改网站、交互、移动端或无障碍：读 ADR-0004、ADR-0006，以及课程总体规划的网站与发布章节。
- 修改练习、检查器或学习记录：读 v1 总规格的 Implementation Decisions 与 Testing Decisions，并保持匿名 JSON 契约。
- 引入第三方文字、代码、图示、数据或依赖：读 ADR-0003、ADR-0005 和资料源版图，并更新来源账本。
- 操作 issue、标签或工程技能：读 [issue tracker](./docs/agents/issue-tracker.md)、[triage labels](./docs/agents/triage-labels.md) 和 [domain docs](./docs/agents/domain.md)。

完成条件：开始修改前，必须能说清本次任务所属里程碑、受影响的课程能力、需要产出的可核验成果，以及适用的 ADR。

## Product contract

- 核心线为 20–24 小时；进阶线为 8–12 小时。核心线完成真实仓库任务、上下文管理、Memory、Skill 与 MCP；进阶线再完成 Python 最小 Agent loop。
- 13 个模块从前置环境与 Git 开始，经 Agent/Harness、Agent 指令工程、Codex/Claude Code、规则、上下文、Memory、Skill、Plugin、MCP 和编排，最后进入 API 与双轨结课。
- 稳定知识层组织厂商无关概念；工具适配层承载版本易变的客户端、模型、SDK、API、安装和配置内容。
- Codex 与 Claude Code 同等重要，采用交替主讲和迁移挑战。一个能力单元只做一个完整主实验，另一工具使用变化输入验证迁移，不逐步骤复制两套课程。
- 阅读和概念层保持免费；核心实战只要求至少一种 Coding Agent；需要双工具或付费 API 的内容必须显示账号、成本和替代路径。
- 公共练习统一使用合成“设备遥测与报告工具”，不使用真实敏感科研或企业数据，也不为每章更换无关联玩具项目。
- 科研结课轨道交付可复现研究工作流；企业结课轨道交付 Issue-to-PR 工程工作流。二者共享能力目标和评价维度。
- API 进阶以 Python 和官方 API/SDK 手写最小 Agent loop；TypeScript 只作对照，框架比较放在理解最小循环之后。
- v1 范围以课程总体规划的“明确不做”和 Issue #1 的 Out of Scope 为准，不在实现中顺手扩展训练、完整 RAG、复杂云平台或其他 Coding Agent 系统课。

## Content contract

每个正式实操课节都必须包含：

1. 真实问题
2. 心智模型
3. 操作前预测
4. 主工具演示
5. 本地实验
6. 故障注入与恢复
7. 迁移挑战
8. 可核验成果
9. 风险、版本与来源卡片

课节元数据至少记录课节 ID、阶段、时长、先修、学习成果、产物、主讲与迁移工具、平台、客户端/SDK/模型/协议、最后核验日期、账号、成本、权限、副作用、来源、许可证和过时风险。

- 正文使用中文解释；规范名首次出现时保留英文 canonical name；命令、配置键和 API 名称保持原样。
- 采用证据先行语气，区分官方事实、课程判断、实验结果和待核验信息。
- Agent 指令工程教授目标、上下文、约束、工具边界、输出契约、验收标准和失败证据，不输出脱离场景的“万能 Prompt 库”。
- 每课留下文件、配置、测试结果、运行证据或提交记录；网页上的阅读状态不属于可核验成果。
- 解题支持按预测、方向提示、诊断提示、检查证据、带解释参考实现逐层开放。
- 原创叙事和实验独立编写。第三方课程只作为教学参考，官方文档与协议规范才是产品事实真源。

完成条件：课节通过内容契约校验，学员能够在不查看最终答案的情况下识别成功证据、常见失败和恢复方法。

## Architecture and privacy

- 课程站采用 Astro、Starlight、MDX 和少量 React islands；静态内容优先，不引入首版应用服务器、数据库或账号系统。
- 计划中的顶层产品区域为 `site/`、`labs/`、`checker/` 和 `docs/`。创建前沿用这些边界，不另造平行课程仓库或重复内容根目录。
- 网站、练习、检查规则和工具适配元数据由同一个课程 release tag 锁定。
- 学习记录只保存在浏览器本地，并支持 JSON 导出/导入；站点不加入广告、分析追踪或排行榜。
- 课程检查器在学员本机验证结果和证据，同时输出人类可读结果与匿名 JSON。检查器不上传源码、密钥、绝对个人路径或原始研究数据，也不限定唯一实现。
- 原创正文和图解采用 CC BY 4.0；自有代码、练习脚手架和检查器采用 MIT；第三方资产保留原许可证并进入来源账本。

## Implementation workflow

1. **Orient**：查看工作树和当前 ticket，读取本任务触发的领域文档与 ADR。完成条件是范围、现状和已有用户改动均已识别。
2. **Slice**：选择满足 ticket 的最小纵向改动，优先贯通页面、练习、检查器和证据契约。完成条件是验收行为和验证入口明确。
3. **Implement**：保持稳定知识层与工具适配层分离；保留用户已有改动；为易变事实记录版本、日期和来源。完成条件是范围内产物可运行或可阅读。
4. **Verify**：先运行最高可用接缝，再运行必要下层检查；记录实际执行的环境和输出。完成条件是成功证据与剩余验证边界均明确。
5. **Handoff**：说明改了什么、验证了什么、尚未验证什么，并关联 ticket。完成条件是维护者无需阅读过程日志即可判断交付状态。

监测到上游变化时只报告和定位影响，由人工复核工具适配层；自动化不得直接重写课程正文。

## Testing contract

唯一的最高层测试接缝是端到端学习旅程：从一个锁定课程版本出发，学员能够在 Windows 11 + PowerShell 7 中打开课程、完成正式实验、通过 `course_check` 获得匿名 JSON，并导入网页形成可核验完成状态。

- 测试外部行为、产物与证据，不绑定组件、函数、目录细节或唯一答案。
- 内容契约、链接、许可证、检查器样例和模拟器测试是该旅程的下层验证器。
- 所有正式实验必须在 Windows 11 + PowerShell 7 实跑；每个课程版本还要在 macOS 或 Linux 至少复核一条路径。
- Codex、Claude Code、付费 API 和真实 MCP 的现场验证必须如实标注客户端、SDK、模型/协议、日期、成本和限制。
- MCP 正式实验必须使用真实 transport 和检查工具；进程内替身只能用于解释概念。
- 无障碍从纵向切片开始按 WCAG 2.2 AA 检查键盘、焦点、对比度、减少动态效果、非颜色编码和文本替代。
- 不以构建成功替代课程通关，不以静态检查替代真实客户端、API、MCP 或浏览器验收。

## Windows execution rules

- Shell 命令只使用 PowerShell Core 7.x（`pwsh`），使用 Windows 原生路径。
- 用 `Join-Path` 构造路径；支持时对 PowerShell 文件 cmdlet 使用 `-LiteralPath`。
- 动态外部命令参数使用参数数组或 splatting，不拼接命令字符串供后续求值。
- 每次外部/native 命令后检查 `$LASTEXITCODE`；非零值按失败处理，除非命令明确把该值定义为预期结果。
- 文件内容修改只使用专用 `apply_patch`；Shell 只用于只读检查、运行构建和测试等操作。
- 命令失败后先诊断并改变方法，不原样重试；不修改 PowerShell `ExecutionPolicy`。
- 修复 Shell 或构建环境时保持应用和课程内容不变，除非 ticket 明确要求修改它们。

## Safety and validation boundaries

- 不把密钥、令牌、个人信息、真实研究数据或企业数据写入仓库、日志、截图、检查器输出或教学示例。
- 有外部副作用的命令、API、MCP Tool 和 Agent 操作必须说明权限范围、人工确认点和恢复办法。
- 不把来源审计快照中的 star、日期、安装方式或产品行为当作当前事实；易变事实在使用当天重新核验。
- 没有执行的现场验证明确写为“未验证”。源码检查、模拟测试、浏览器验收和真实服务验收分别报告。
- 工作树可能包含维护者的未提交改动；修改前检查并保留，不用破坏性 Git 操作清理。

## Definition of done

一个实现任务只有同时满足以下条件才算完成：

- ticket 的范围内用户故事与验收行为均有对应产物。
- 相关领域术语、课程规划和 ADR 得到遵守，或冲突已由维护者明确批准。
- 最高可用测试接缝通过，必要的下层检查也通过。
- Windows 主路径已经验证；无法执行的外部、跨平台或付费验证被清楚列为边界。
- 新增第三方内容具有来源、固定版本、使用方式和许可证记录。
- 交付说明列出改动、证据、风险和后续工作，不把部分完成描述为课程版本完成。

## Agent skills

### Issue tracker

Issues and specs are tracked in GitHub Issues for `TiegenFang/agent-engineering-course`. See [issue-tracker.md](./docs/agents/issue-tracker.md).

### Triage labels

Use the five canonical triage labels. See [triage-labels.md](./docs/agents/triage-labels.md).

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`. See [domain.md](./docs/agents/domain.md).
