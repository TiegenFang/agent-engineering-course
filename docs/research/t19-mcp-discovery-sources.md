# T19：真实 MCP Server 发现的来源校准

> 核验日期：2026-08-13（Asia/Shanghai）  
> 课程适配版本：MCP 2026-07-28、Python SDK `mcp==2.0.0`、Inspector `@modelcontextprotocol/inspector@2.2.0`。本文只记录本课使用的事实边界；具体安装时仍应查看锁定版本的官方文档。

## 采用的事实来源

| 来源 | 本课采用的事实 | 边界 |
| --- | --- | --- |
| [MCP 2026-07-28 specification](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/main/docs/specification/2026-07-28) | Host 管理一个或多个 Client；Client 与一个 Server 建立会话；Server 提供 primitives。Tools 是 model-controlled，Resources 是 application-controlled，Prompts 是 user-controlled。Transport 传递 JSON-RPC 消息，stdio 和 Streamable HTTP 是不同绑定。 | 规范是协议事实，不替代某个 Host 的产品 UI 或权限策略。 |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) / [run guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/index.md) | `ClientSession`、`stdio_client`、`StdioServerParameters` 可把 Python Server 作为真实本地子进程连接；stdio 的 stdout 是协议 wire，日志应走 stderr；Streamable HTTP 是现代 HTTP 传输。 | 本课固定 `mcp==2.0.0`；其他 SDK 版本的 API 可能不同。 |
| [MCP TypeScript SDK client guide](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/client.md) | 迁移挑战对应 `StdioClientTransport` 与 `StreamableHTTPClientTransport`；TypeScript 只作为 API 对照，不增加第二个正式实现。 | 本课未用 TypeScript 运行正式验收，也未验证所有当前 main API。 |
| [MCP Inspector CLI](https://github.com/modelcontextprotocol/inspector/tree/main/clients/cli) / [README](https://github.com/modelcontextprotocol/inspector) | Inspector 可启动本地 Server 并通过 `--method` 检查 `tools/list`、`resources/list`、`prompts/list`；CLI JSON 输出适合由 wrapper 提取能力名和退出状态。 | Inspector 是检查工具，不是 Host；原始输出可能含本地路径或其他诊断信息，本课只写脱敏摘要。官方 CLI 文档记录 Node `>=22.19.0`，本环境 Node `22.18.0` 虽可运行但不算满足推荐门槛。 |
| [Microsoft MCP for Beginners core concepts](https://github.com/microsoft/mcp-for-beginners/tree/main/01-CoreConcepts) | 用于核对面向初学者的 Host/Client/Server 和 primitives 解释方式，并链接到 2026-07-28 release candidate。 | 这是教学辅助来源；规范和 SDK 仍是本课产品事实真源。 |

## 本实验中的可核验映射

`labs/mcp-discovery/mcp_server.py` 是 Server；学员运行的 Python 进程是 Host 侧 client 程序，`ClientSession` 是连接一个 Server 的 Client。Server 注册一个合成 telemetry Tool、一个 Resource 和一个 Prompt。`mcp_client.py` 通过 Python SDK 的真实 stdio 子进程连接、发现并调用它；`inspector-check.mjs` 再用官方 Inspector CLI 独立检查三个 list 方法。

证据只保留以下稳定字段：协议版本、transport 标签、固定的能力名称、操作是否成功、恢复是否完成，以及 Inspector 方法 ID。不会写入绝对路径、环境变量、原始 telemetry、提示内容、账号或令牌。未知工具调用是本地错误注入；客户端随后调用已知 Tool，证明连接仍可恢复，不会访问外部系统。

## 正式路径与 fallback 的判定

- 正式完成必须同时看到 `mode=real-stdio`、`transport=stdio`、协商协议 `2026-07-28`、三类能力发现与调用、故障恢复，以及 Inspector 三个 list 方法的通过摘要。
- `--offline` 只返回固定的 `deterministic-in-memory` 摘要，帮助没有 Python/Node 环境的学员先练习术语和证据形状。Checker 会把它标成 `partial`，不会把它升级为正式 MCP 完成。
- 本课没有模型调用、远端 Server、设备操作、凭据或付费 API。安装依赖和 `npx` 首次解析可能联网；依赖装好后 Server、Client、Checker 均在本机运行。

## 尚未验证的边界

本次 Windows/PowerShell 验证覆盖 Python stdio、Inspector CLI、checker 和课程浏览器路径；未在本 release 中现场验证 macOS/Linux、Streamable HTTP、OAuth/远端授权、TypeScript Server/Client 或具体第三方 MCP Server。2026-07-28 规范和 SDK/Inspector 均属易变适配层，发版前应重新核对官方页面和锁定版本。
