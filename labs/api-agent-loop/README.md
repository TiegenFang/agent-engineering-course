# T26：离线最小 Agent loop

这是模块 11A 的桌面实验。它用 Python 标准库实现一个不依赖上层 Agent 框架的最小 Agent Application 控制流：

```text
模型响应 fixture → 工具调用 → 参数校验与工具执行 → 状态回填 → 下一次响应/结构化输出 → 停止
```

这里的“模型响应”是固定脚本，不是 OpenAI、Anthropic、Codex 或 Claude Code 的响应。实验不会读取环境凭据，不发送网络请求，不调用真实模型/API，也不读写真实设备或研究数据。

## 运行

主路径是 Windows 11 + PowerShell 7。请在课程仓库根目录执行，并把生成物放到一次性临时目录：

```powershell
$t26OutputDir = Join-Path ([System.IO.Path]::GetTempPath()) "agent-course-t26"
New-Item -ItemType Directory -Force -Path $t26OutputDir | Out-Null
python labs/api-agent-loop/run.py --scenario all --output (Join-Path $t26OutputDir "t26-evidence.json")
```

`--scenario all` 会依次执行五条确定性路径：

- `success`：一次合法工具调用、结果回填、结构化成功输出。
- `tool-failure`：工具返回不可用错误；循环报告结构化失败并安全停止。
- `invalid-args`：fixture 先给出无效参数；Harness 拒绝后回填错误，随后接受修正调用。
- `budget-stop`：`max_steps=1`，达到预算时停止，不伪造最终输出。
- `retry-recovery`：第一次瞬时工具错误，限制一次重试后恢复并完成。

可以单独观察一条路径：

```powershell
python labs/api-agent-loop/run.py --scenario invalid-args
python labs/api-agent-loop/run.py --scenario retry-recovery --retry-budget 1
python labs/api-agent-loop/run.py --scenario budget-stop --max-steps 1
```

如果要把输出交给课程检查器，`--output` 必须是一个明确指定的新 JSON 路径。runner 不会自行创建仓库内的 artifacts，也不会把本机路径写进 evidence。

## 检查匿名证据

在课程仓库根目录执行：

```powershell
$t26Evidence = Join-Path ([System.IO.Path]::GetTempPath()) "agent-course-t26\t26-evidence.json"
python -m course_check check t26-offline-agent-loop --root . --evidence-file $t26Evidence --json
```

检查器会重新验证事件顺序、状态回填、无效参数、失败停止、预算停止、结构化输出和重试恢复，然后只输出稳定的场景/状态摘要。它不会把 prompt、工具参数、源码、绝对路径、凭据或原始数据带入匿名 JSON。缺少场景时结果为 `partial`，不是伪造通过。

## 可核验成果

完成本实验后应留下：

1. `t26-evidence.json`（匿名 evidence contract v1）；
2. 一段说明“状态由 Harness 拥有、工具由应用执行、停止由预算/结果共同控制”的记录；
3. 至少一次无效参数或工具失败后的恢复证据。

## 与 Coding Agent 客户端的边界

Codex 和 Claude Code 是能够在真实代码仓库中规划、调用工具并执行工程工作的 Coding Agent/Harness；本实验是学员自己编写的 Agent Application loop。两者可以共享“响应—工具—状态—停止”的能力目标，但客户端权限、上下文管理、账号、模型、费用和产品行为不能由这个 fixture 推断。T26 的离线通过只证明本地控制流和证据契约；真实 OpenAI/Anthropic API 冒烟、成本和部署验收另列为未验证边界。

## 实现约束

- `agent_loop.py` 只使用 Python 标准库；无 Agent SDK、框架、HTTP 客户端或环境凭据。
- 工具 schema 明确 `device_id` 的类型、正则和禁止额外字段；工具执行永远返回合成读数或可分类错误。
- `max_steps` 计算模型响应轮数；工具校验、执行与状态回填属于同一轮，预算停止后不再发起响应。
- 结构化输出只接受固定字段：`status`、`summary`、`reading`、`anomaly`、`attempts`；错误结果必须显式为 `status=failed`，不能把缺失读数包装成成功。

## 为后续 API 适配保留的 seam

`run_agent_loop()` 默认构造离线 `DeterministicResponseFixture` 和 `DeterministicTelemetryTool`。若后续课程把某个已授权、受预算限制的 API 响应适配进来，只能通过两个显式参数接入：

- `response_source.respond(state) -> FixtureResponse`：适配层把外部响应归一成 `kind`、`tool_name`、`arguments` 或固定的结构化输出；它不直接改写 Harness 状态。
- `tool_executor.execute(arguments) -> ToolExecution`：应用继续拥有本地工具执行、参数校验与错误分类。

这两个 seam 是 Python 标准库中的本地协议，不是 API 客户端、SDK 或模型调用。T26 的默认命令仍然只运行确定性 fixture；现场 API 路径必须另行记录账号、模型、SDK、日期、预算和结果。

## 风险、版本与来源

- 账号与成本：离线 fixture、runner 和 checker 免费；本课不需要 OpenAI/Anthropic 账号或额度。
- 权限与副作用：runner 只在你指定的输出路径写 JSON；建议使用临时目录，不要把输出路径指向真实项目文件。
- 隐私：只使用 `telemetry-17` 等合成标识符；不要把个人、设备、研究数据或凭据改进到 fixture。
- 预期失败与恢复：先看失败事件是参数校验、工具执行还是预算停止，再调整 `retry_budget`/`max_steps`，重跑后由 checker 复核。
- 验证边界：本实验已验证 Python 本地 fixture、checker 与课程构建；未验证真实模型/API、SDK、Codex、Claude Code、真实工具、跨平台现场或生产安全。
- 来源与许可：正文和实验设计为课程原创（CC BY 4.0）；`agent_loop.py`、runner 与 checker 代码为项目代码（MIT）。Python JSON 标准库和 OpenAI/Anthropic 工具使用文档只作事实/迁移参考，不复制其代码或产品字段。
