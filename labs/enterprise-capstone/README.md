# T24 企业核心结课轨道：Issue-to-PR 工程交付

这个实验把贯穿课程的合成“设备遥测与报告工具”收束成一条企业结课路径：从 Issue 澄清开始，使用受控 Context、Memory、Skill 和 MCP 边界，留下变更、测试、评审和交付证据，再用变化 Issue 完成迁移挑战。

## 运行边界

实验只使用 Python 标准库和内置合成状态；不会调用模型、Codex、Claude Code、远端 MCP、真实企业仓库、GitHub API 或付费 API。脚本只写入学员显式指定的新输出目录。

Windows 11 + PowerShell 7 主路径：

```powershell
$out = Join-Path ([System.IO.Path]::GetTempPath()) 't24-enterprise-capstone'
python .\labs\enterprise-capstone\run_lab.py --output $out --variant feature-issue
Get-ChildItem -LiteralPath $out
Set-Location -LiteralPath .\checker
python -m course_check check t24-enterprise-capstone --root .. --evidence-file (Join-Path $out 't24-enterprise-capstone-evidence.json') --json
```

`--variant bug-fix` 是迁移挑战：它把功能 Issue 换成压力单位换算缺陷，但保留同一组 Issue-to-PR 验收。`--fault ambiguous-issue`、`--fault test-failure`、`--fault review-requested` 和 `--fault mcp-denied` 会留下 partial 证据；先记录失败，再用 `--fault none` 恢复。

## 交付合同

输出目录包含：

- `issue-clarification.md`：目标、非目标和验收条件；
- `change-summary.md`：变更边界摘要；
- `tests.txt`：测试结果与恢复提示；
- `review.md`：评审状态；
- `delivery.md`：交付说明和副作用边界；
- `enterprise-record.json`：Context、Memory、Skill、MCP 与恢复状态；
- `t24-enterprise-capstone-evidence.json`：不含路径、源码、日志、凭据或企业正文的匿名证据。

检查器会从固定 Issue 变化输入和故障状态重新推导证据，不信任手写的 `result` 或 check 状态。公共评分量表包含问题澄清、上下文质量、操作安全、变更、测试、评审、可复现性、迁移能力和交付清晰度；页面阅读状态不算成果。

## 故障注入与恢复

先运行一个故障分支，观察为什么不能把 partial 交付合并：

```powershell
python .\labs\enterprise-capstone\run_lab.py --output $out --variant feature-issue --fault test-failure
python .\labs\enterprise-capstone\run_lab.py --output $out --variant feature-issue
```

`ambiguous-issue` 要求先回到需求澄清；`review-requested` 要求处理评审意见后再交付；`mcp-denied` 要求保持只读并留下阻塞记录。恢复不是修改 JSON 中的结果字段，而是重新满足同一验收合同。

## 迁移挑战

```powershell
python .\labs\enterprise-capstone\run_lab.py --output $out --variant bug-fix
```

迁移输入改变 Issue 类型和验收上下文，但仍要求变更、测试、评审、交付以及匿名 evidence。可以将澄清与评审清单交给 Codex 或 Claude Code 做方法迁移；真实客户端现场必须单独记录版本、账号、权限、成本和日期，本实验不把未执行调用标为成功。

## 风险与验证边界

- 离线 lab、checker、Node 测试和浏览器路径免费，不需要账号或网络。
- 不会写入真实仓库、创建分支、提交、推送、调用 MCP 或触发外部副作用；输出目录由学员显式指定。
- 不要把真实 Issue 正文、企业代码、个人信息、令牌、绝对路径或账单写入 evidence、截图或报告。
- fixture 合同为 `telemetry-report-issue-v1` / evidence v1，核验日期为 2026-08-13。真实 Issue-to-PR、Codex/Claude Code 子代理、权限审批和企业身份治理尚未在本实验现场验证。
- 正文和实验代码为课程原创；正文 CC BY 4.0，代码、fixture 与 checker MIT。
