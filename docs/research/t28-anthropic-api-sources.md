# T28 Anthropic API 迁移实验：官方来源核验

> 核验日期：2026-08-13。本文只记录课程实现所需的稳定协议边界；模型可用性、SDK 版本、费用、限流值和账户权限均应在实际 live 验证当天重新核对。

## 本实验的事实边界

| 课程断言 | 官方依据 | T28 的实现取舍 |
| --- | --- | --- |
| Messages 请求是应用驱动的无状态交互，调用者提交所需的对话历史。 | [API primer](https://platform.claude.com/docs/en/claude_api_primer)、[Create a Message](https://platform.claude.com/docs/en/api/messages/create) | `MessagesResponseSource` 保存并重放本地 `messages`；不把 state 所有权交给 fixture client。 |
| 客户端工具在 `tools` 中以 JSON Schema 的 `input_schema` 描述；assistant 返回 `tool_use`，包含 `id`、`name`、`input`。 | [How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)、[Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls) | adapter 将这一形状转换为 T26 的统一 tool-call response。 |
| 工具结果作为后续 user message 的 `tool_result` 内容块回填，以 `tool_use_id` 关联；工具调用与结果需要按协议相邻、按顺序处理。 | [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls) | fixture 显式记录 assistant → user 的历史，并验证相同 `tool_use_id`。 |
| 当前 raw Messages API 的结构化 JSON 请求使用 `output_config: { format: { type: "json_schema", schema } }`。 | [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | adapter 记录 request 形状；最终 JSON Schema 校验仍由 T26 loop 执行。 |
| 成功 HTTP 响应仍可能以 stop reason 表示状态；`refusal` 不能当作 HTTP transport failure。 | [Handling stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons) | 离线 fixture 把 protocol/transport/authentication 分开；不把成功 stop state 伪装为网络错误。 |
| HTTP 错误、请求 ID、重试和 `Retry-After` 需要与模型 stop state 分层处理。 | [Errors](https://platform.claude.com/docs/en/api/errors)、[Rate limits](https://platform.claude.com/docs/en/api/rate-limits) | fixture 只记录安全错误类别；真实退避/限流实现需在被授权的 live path 中单独测试。 |
| Claude Agent SDK 可以承载 agent loop，但其当前权限、工具策略和运行时行为必须单独核验。 | [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)、[Agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) | T28 只作比较，不导入或调用 SDK；不可从此 fixture 推断任何 SDK 预算。 |

## 字段名称与迁移陷阱

- `output_format` 在部分便利层或旧材料中出现；本课记录的是 raw current API 的 `output_config.format`。不要无证据地把两者当作同一稳定 request contract。
- `tool_result` 在 user content block 中，不是独立的 `tool` role。结果必须用对应的 `tool_use_id` 回填。
- `pause_turn` 是 server tool 的特定停止流，不应作为客户端工具 loop 的通用“继续”信号。
- `refusal` 属于成功响应的停止理由而非 HTTP error；课程错误练习不应把它混入连接、认证或限流类别。
- `max_tokens`、模型标识、SDK 版本、收费与账户授权均属于易变适配层。`claude-sonnet-4-5` 在 T28 只是 fixture 元数据，不是本课程的 live 可用性声明。

## 课程判断（非官方事实）

1. 先以 T26 的手写 loop 展示步骤预算、重试、工具参数与最终结构化输出校验，再做厂商协议迁移，符合 ADR-0002 的最小 loop 优先原则。
2. 离线 fixture 把网络和凭据状态固定为 `not-called` / `not-required`；这能验证课程边界，不能证明真实账号、模型或服务可用。
3. Claude Agent SDK 的比较只帮助学习者辨认 loop 所有权差异；它不是第二套逐步骤复写的主实验。

## 许可证与使用方式

上述链接是 Anthropic 官方文档，作为产品事实来源而非转载材料。本课独立编写中文叙事、adapter、fixture 和 checker；不复制 SDK 源码或大段第三方文档文字。来源记录还应进入 `docs/sources/source-ledger.json`，以锁定课程版本、用途、许可证线索和过时风险。
