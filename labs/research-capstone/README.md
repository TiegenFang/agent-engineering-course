# T23 科研核心结课轨道：可复现实验

这个实验把贯穿课程的合成“设备遥测与报告工具”收束成一条科研交付路径：先写清上下文与受控 Memory，再用 Skill 固定分析步骤，以 MCP 只读边界读取合成快照，最后留下脚本、图表、实验记录、报告和匿名 evidence。

## 运行边界

实验只使用 Python 标准库和课程内置的合成数据；不会调用模型、Codex、Claude Code、MCP 远端服务、真实研究数据或付费 API。脚本写入一个由学员显式指定的新输出目录，输出只包含合成摘要和可复核状态。

Windows 11 + PowerShell 7 主路径：

```powershell
$out = Join-Path ([System.IO.Path]::GetTempPath()) 't23-research-capstone'
python .\labs\research-capstone\run_lab.py --output $out --variant temperature-daily
Get-ChildItem -LiteralPath $out
python -m course_check check t23-research-capstone --root . --evidence-file (Join-Path $out 't23-research-capstone-evidence.json') --json
```

运行 `--variant pressure-night` 完成变化输入迁移挑战；它改变主题、单位和最近记录限制，不复制第一条路径的答案。`--fault missing-values`、`--fault stale-memory` 和 `--fault mcp-denied` 是可恢复故障，程序会在输出中标出 partial 证据而不伪造通过。

## 交付合同

输出目录包含：

- `analysis.py`：可重复执行的分析脚本副本；
- `figure.svg`：由脚本生成的合成图表；
- `experiment-record.json`：上下文、Memory、Skill、MCP 边界和恢复状态；
- `report.md`：带输入、方法、限制和结果摘要的报告；
- `t23-research-capstone-evidence.json`：不含路径、原始数据、凭据或个人信息的匿名证据。

检查器按固定观察重新推导证据，不信任学员手写的 `result`。科研评分量表共有七项：问题定义、上下文质量、操作安全、验证证据、可复现性、迁移能力、交付清晰度。每项由“证据存在、边界说明、恢复记录”组成；页面只保存稳定枚举，不上传研究数据。

## 故障注入与恢复

先运行一个故障分支，记录为什么不能把不完整图表当作成功；再用安全默认重新运行。`stale-memory` 要求确认 Memory 的版本/寿命后重建；`mcp-denied` 要求在没有人工确认时保持只读；`missing-values` 要求先回到数据质量检查再绘图。所有恢复动作都在本地完成，不会打开网络或外部副作用。

## 迁移挑战

将主实验的温度日间输入迁移为夜班压力输入：保持同一评价目标，但改变单位 `kPa`、最近有效记录数 3 和输出字段。可以把检查单交给 Codex 或 Claude Code 做概念对照；现场调用是可选的，必须另存匿名状态并注明客户端、模型和日期。本实验本身不声称真实工具调用成功。
