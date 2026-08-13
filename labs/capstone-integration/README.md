# T25：双轨结课集成实验

这个 lab 把同一个“设备遥测与报告工具”项目的公共能力证据，与科研结课轨道或企业结课轨道的交付证据放到一份共同验收量表中。它是离线、确定性、合成数据实验：不启动 Codex 或 Claude Code，不调用 OpenAI/Anthropic API，不读取凭据，不连接 MCP Server，也不访问真实科研或企业数据。

## Windows 11 + PowerShell 7 主路径

```powershell
$out = Join-Path ([System.IO.Path]::GetTempPath()) 't25-capstone-integration'
& .\labs\capstone-integration\run-integration.ps1 -OutputPath $out -Track enterprise
Get-ChildItem -LiteralPath $out
python -m course_check check t25-capstone-integration --root . `
  --evidence-file (Join-Path $out 't25-capstone-integration-evidence.json') --json
```

切换到科研轨道：

```powershell
& .\labs\capstone-integration\run-integration.ps1 -OutputPath $out -Track research
```

故障注入必须产生 `partial`，再用 `-Fault none` 重跑到新输出目录恢复。支持 `missing-core`、`unsafe-side-effect` 和 `incomplete-delivery`，分别模拟前置证据缺失、MCP/工具副作用未被边界约束和交付材料不完整。

## 证据边界

匿名 JSON 只有固定 lesson、版本、轨道、故障枚举、布尔检查和摘要，不包含 issue 正文、源码、路径、prompt、工具 payload、token、密钥、原始遥测或隐藏推理。检查器从这些字段重新推导结果，不能通过手改 `result` 伪造通过。

T25 证明的是“两个双场景轨道可以共享能力目标、验证维度和发布边界”的离线接缝。它不证明真实 Codex/Claude Code 客户端、API、远端 MCP、GitHub Issue/PR 或生产数据已经现场执行；这些路径要分别记录账号、版本、权限、成本、日期和人工确认。

许可证：课程原创脚本、fixture、检查器和页面代码按仓库 MIT/CC BY 4.0 边界发布；本目录未复制第三方资产。
