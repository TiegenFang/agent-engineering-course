# 模块 9A：真实 MCP Server 发现实验

这个实验让 Host 中的一个最小 Client 通过真实 `stdio` transport 启动本地 MCP Server，发现并检查 Tool、Resource、Prompt，再注入一次未知 Tool 故障并恢复。Server 只返回合成设备遥测，不访问文件、网络、账号、密钥、真实设备、模型或付费 API。

## 正式路径：Python SDK + stdio + Inspector

正式完成必须同时具备：

1. `mcp_client.py` 的真实子进程 stdio JSON-RPC 调用证据；
2. 官方 `@modelcontextprotocol/inspector@2.2.0` CLI 对同一 Server 的 `tools/list`、`resources/list`、`prompts/list` 检查证据；
3. `course_check` 重新从 capability 和观察字段推导通过状态，而不是信任学员手写的 `passed`。

Windows 11 + PowerShell 7 主路径（每条外部命令后都检查非零退出）：

```powershell
$lab = (Resolve-Path -LiteralPath .\labs\mcp-discovery).Path
$venv = Join-Path $lab ".venv"
python -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install -r (Join-Path $lab "requirements.lock")
if ($LASTEXITCODE -ne 0) { throw "MCP SDK installation failed" }
```

Inspector v2 要求 Node.js `>=22.19.0`；`inspector-check.mjs` 通过参数数组启动 `npx` 的 Node 入口，避免 Windows `.cmd` shim 的 `spawn EINVAL`，并只保存方法 ID、计数和目标名称是否出现。可先确认 Node 版本：

```powershell
node --version
if ($LASTEXITCODE -ne 0) { throw "Node.js is required" }
```

建议让脚本创建一个仓库之外的新临时目录，并串起 Inspector、Client 与 checker：

```powershell
pwsh -NoProfile -File .\labs\mcp-discovery\run_mcp_discovery.ps1 `
  -OutputDirectory (Join-Path $env:TEMP "agent-engineering-course\t19-mcp-discovery-run")
if ($LASTEXITCODE -ne 0) { throw "MCP discovery journey failed" }
```

脚本会生成 `inspector.json`、`mcp-client.json` 和匿名 `t19-mcp-discovery-evidence.json`。如果目标已经存在，脚本会停止而不是覆盖未知文件；只有人工审阅后才显式增加 `-AllowOverwrite`。checker 输出不含绝对路径、原始 Tool 结果、提示正文、环境变量、密钥或个人信息。

手动拆开观察时，Inspector 的等价 CLI 形式是（命令选项顺序遵循 Inspector v2）：

```powershell
npx --yes @modelcontextprotocol/inspector@2.2.0 --cli $python (Join-Path $lab "mcp_server.py") --method tools/list --format json
if ($LASTEXITCODE -ne 0) { throw "Inspector tools/list failed" }
npx --yes @modelcontextprotocol/inspector@2.2.0 --cli $python (Join-Path $lab "mcp_server.py") --method resources/list --format json
if ($LASTEXITCODE -ne 0) { throw "Inspector resources/list failed" }
npx --yes @modelcontextprotocol/inspector@2.2.0 --cli $python (Join-Path $lab "mcp_server.py") --method prompts/list --format json
if ($LASTEXITCODE -ne 0) { throw "Inspector prompts/list failed" }
& $python (Join-Path $lab "mcp_client.py")
if ($LASTEXITCODE -ne 0) { throw "MCP client failed" }
```

不要直接运行 `python mcp_server.py` 期待屏幕打印结果：stdio 的 stdout 是 MCP wire，Server 会等待 Host/Inspector 发来的 JSON-RPC 请求。诊断信息应写 stderr；本示例没有额外日志。

## Server / Client 观察点

`mcp_server.py` 由官方 Python SDK `MCPServer` 注册三类能力：

- `summarize_telemetry`：只读合成 Tool，客户端随后调用一次；
- `telemetry://demo/snapshot`：JSON Resource，客户端执行 `resources/read`；
- `review-telemetry`：参数化 Prompt，客户端执行 `prompts/get`。

Client 首先调用 `server/discover`，再列出三类能力，调用它们，最后调用一个不存在的 Tool。未知 Tool 的错误可能由 SDK 作为 `MCPError` 抛出，也可能作为 `is_error` 结果返回；两种都属于真实协议失败证据。Client 随后重新调用已知 Tool，把连接存活和恢复动作记录为 `failure_recovered`。

## 离线 deterministic fallback（不等于正式完成）

没有可用 Python SDK、Node 或 Inspector 时可运行：

```powershell
& $python (Join-Path $lab "mcp_client.py") --offline
if ($LASTEXITCODE -ne 0) { throw "offline fallback failed" }
```

该分支只返回固定的内存对象，`transport` 是 `deterministic-in-memory`，`protocol_version` 是 `conceptual-only`，且 `inspector.verified` 为 `false`。它可帮助学员练习“能力清单—调用—失败—恢复”的记录格式，但没有启动 Server、没有 JSON-RPC wire，也没有 Inspector；checker 会拒绝把它标成 `passed`。页面中的离线按钮同样只导出 partial evidence。

## 权限、成本与副作用

- 账号、模型、API key、付费额度：不需要；Python SDK、Node 与 Inspector 均为公开开发依赖，网络只用于首次安装/下载。
- Server 权限：本示例仅在本地子进程中运行合成计算；没有文件系统、网络、环境凭据或真实设备权限。真实第三方 MCP Server 不能套用这个结论，连接前应逐项审阅启动命令、环境变量、目录和 Tool annotations。
- Inspector 副作用：CLI 会启动本地 Server 子进程；Inspector 本身可能在用户目录写入其 catalog/storage。课程 wrapper 不把这些路径写入 evidence，也不连接远端 MCP。
- 人工确认点：在 Inspector 或任何 Host 中点击会改变数据、发送网络请求、写文件或触发外部服务的 Tool 之前，先核对名称、schema、权限和副作用；本例没有这种 Tool。
- 输出安全：只把 checker 生成的匿名 JSON 导入网页；不要粘贴原始 Inspector 日志、Prompt 正文、绝对路径、用户名、token、研究/企业数据。

## 版本、来源与边界

- MCP 协议事实按 `2026-07-28` 规范核验：现代请求携带 `_meta`，可用 `server/discover` 做能力发现；Streamable HTTP 使用单端点 POST 并镜像 `Mcp-Method`/`Mcp-Name` 标头；stdio 仍是本地子进程 JSON-RPC transport。
- Python SDK 锁定 `mcp==2.0.0`；Inspector 锁定 `@modelcontextprotocol/inspector@2.2.0`；Inspector 的 Node engine 是 `>=22.19.0`。SDK/Inspector 版本、协议后续修订和 CLI 参数在每次课程发布前必须重新核验。
- TypeScript SDK 同样提供 `StdioClientTransport`/`StreamableHTTPClientTransport`；本课选 Python 作为 Windows 主路径，TypeScript 只作迁移阅读，不重复制作第二套实验。
- 本次已现场验证：Windows PowerShell 中 Python SDK `mcp==2.0.0` 的真实 stdio server/client、`server/discover`、Tools/Resources/Prompts 列表与调用、未知 Tool 恢复，以及 Inspector CLI v2.2.0 三个 list 方法。当前 Node 为 `v22.18.0`，运行 Inspector 时出现 Node engine warning；因此“Node 满足 `>=22.19.0` 的正式发布环境”仍需复核。未验证：远程 Streamable HTTP、OAuth、真实第三方 MCP Server、真实设备、Codex/Claude Code Host、macOS/Linux 和浏览器现场接受。

原创正文、Server/Client、wrapper、fallback 和 checker 测试按课程代码/内容许可执行；官方规范、SDK、Inspector 和 Microsoft 初学者课程只作引用，不复制其代码或资产。
