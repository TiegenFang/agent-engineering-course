# T28：Anthropic Messages API 迁移实验

本实验把 T26 的 Python 最小 Agent loop 接到 Anthropic Messages API 的**离线**适配器。它不读取环境变量、不接受 API key、不会产生网络请求，也不会调用 Anthropic 服务。

## 目标与边界

- 保留 T26 对 `max_steps`、重试、工具参数和结构化输出的控制权。
- 由 `MessagesResponseSource` 把 Messages 的 `tool_use` / `tool_result` 往返翻译为 T26 的 `FixtureResponse`。
- 明确 Messages API 是无状态的：应用保存并在每次请求时重放 `messages` 历史。
- 用 `tools[].input_schema` 描述 `read_telemetry`，并以 `output_config.format` 的 JSON Schema 记录结构化输出请求形状。
- 用五个 fixture 情形比较成功、无效工具参数、坏结构化输出、传输错误和认证错误。

这不是生产客户端，也不声称已完成现场 API 验收。真实 API 的 live smoke 元数据固定为 `not-run`；如将来进行现场验证，必须在独立的、显式授权的会话中提供凭据，并如实记录模型、SDK、日期、成本、权限与失败证据。

## 运行离线 fixture

在仓库根目录使用 PowerShell 7：

```powershell
python labs/anthropic-messages/run_fixture.py --case offline-success --output ./.artifacts/t28-anthropic-messages-evidence.json
```

可选情形为：

- `offline-success`
- `invalid-arguments`
- `malformed-structured-output`
- `transport-error`
- `authentication-error`

输出是匿名、可由 `course_check --lesson t28-anthropic-messages` 读取的 JSON 证据。输出路径必须由学习者显式传入；脚本不会自动创建或覆盖课程仓库中的证据文件。

## Python SDK 与 Claude Agent SDK 的位置

`make_live_messages_client` 仅展示将显式传入的凭据和 `anthropic.Anthropic` 客户端连接到适配器的边界。离线实验不导入 SDK，也不安装它。

Claude Agent SDK 在本课只作为迁移比较对象：它可以承载 Agent loop，但不替代本实验中可检查的 T26 harness loop。不要从本 fixture 推断 SDK 与 T26 共享调用次数、token 或费用预算；现场启用 SDK 前要重新核对当前权限、工具策略和官方文档。

## 可核验结论

离线证据应显示：

1. 请求记录含 `input_schema`、`tool_use_id` 和 JSON Schema 的结构化输出意图；
2. 每个成功工具调用都以用户 `tool_result` 内容块回填同一 `tool_use_id`；
3. 应用持有并重放消息历史，而不是把历史状态交给服务端；
4. T26 loop 仍拥有步骤/重试预算和最终 JSON Schema 校验；
5. 传输与认证问题被归类为安全、无凭据的错误类别；
6. `live_smoke.status` 保持 `not-run`。

官方来源与字段版本注意事项见 [`docs/research/t28-anthropic-api-sources.md`](../../docs/research/t28-anthropic-api-sources.md)。
