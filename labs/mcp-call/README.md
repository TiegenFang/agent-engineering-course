# T20 MCP 调用、权限与故障恢复实验

本实验包含一个课程原创合成 MCP Server、一个官方 TypeScript SDK v2 Client 和官方 Inspector CLI。

## 运行

在仓库根目录执行：

```powershell
npm install
node .\labs\mcp-call\client.mjs --live --approve --fault tool
node .\labs\mcp-call\inspect.mjs
```

`server.mjs` 只注册 `telemetry.read` 和 `report.publish`。后者只有在 Host 已记录人工确认并发送 `confirmed: true` 后才会写入由 Client 创建的临时输出目录。Server 不执行参数中的代码、不联网、不读取凭据。

`--fault transport|tool|data|protocol` 只注入固定的合成错误。Client 会把错误分类为稳定 fault ID，并在必要时创建新的 Client/transport 恢复。输出 evidence 只包含枚举和布尔状态。

`--offline` 是 deterministic fallback：不启动 MCP Server，不调用 Inspector，`formal_mcp` 必须为 `false`，不能用于完成正式 MCP 课节。

## 正式证据

```powershell
$evidence = Join-Path ([System.IO.Path]::GetTempPath()) 't20-mcp-evidence.json'
node .\labs\mcp-call\client.mjs --live --approve --fault tool --output $evidence
python -m course_check check t20-mcp-call --root . --evidence-file $evidence --json
```

要达到正式通过，需另外运行 `inspect.mjs`，再把 Inspector 检查结果合并到 evidence（课程验收不会把没有运行 Inspector 的调用算作完成）。自动化测试会单独验证 Inspector CLI 的真实连接。
