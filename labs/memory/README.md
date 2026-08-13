# T16：受控 Memory 离线实验

本实验对应课程页 `module-6-memory.mdx` 和课节 ID `t16-memory`。浏览器页面加载 `site/src/lib/memory-engine.mjs` 的固定状态机，依次观察：

```text
design → write → recall → stale-update → pollution → delete
```

其中 `pollution` 之前要先点击一次“注入污染备注”。实验只使用合成的 Memory ledger：

- 短期、长期、外部 Memory 的类型边界；
- `purpose`、`owner`、`lifetime`、`delete_when` 的记录合同；
- Context window 的预算、summary、retrieval、injection；
- 正确回忆、陈旧条目更新、不可信备注隔离恢复和删除确认。

## 安全与确定性边界

- 不调用模型、Codex、Claude Code、API、MCP、数据库、文件系统或网络。
- 页面不会执行污染备注中的“外发”语义；它只记录固定的 `passed`/`failed` 观察。
- 导出的 evidence 只包含稳定 ID、状态、版本和合成阶段枚举，不包含记录正文、绝对路径、密钥、token、账号或原始研究数据。
- 不要把真实 Memory 文件复制到课程仓库或粘贴到页面；真实产品还需要权限、审计、保留、缓存/备份和删除证明。

## 本地验收

在课程工作区根目录打开网站并完成页面实验后，把下载的 `t16-memory-evidence.json` 放到工作区外，再执行 Windows 11 + PowerShell 7 主路径：

```powershell
Set-Location -LiteralPath .\checker
python -m course_check check t16-memory --root .. --evidence-file ..\t16-memory-evidence.json --output ..\t16-memory-checked.json --json
Get-Content -LiteralPath ..\t16-memory-checked.json
```

完整结果需要 13 个检查项全部通过：生命周期四项、三类 Memory、Context 装配三项、正确回忆、陈旧纠错、污染恢复、敏感排除、删除复核以及离线确定性。checker 会从 `experiment.stages` 重新推导检查项，不能靠手写状态伪造通过。

## 公开证据合同

匿名边界使用仓库统一的 `agent-engineering-course/evidence v1`：

```json
{
  "contract": "agent-engineering-course/evidence",
  "contract_version": "1",
  "course_version": "0.1.0-alpha",
  "lesson_id": "t16-memory",
  "result": "passed",
  "anonymous": true,
  "evidence": [
    {"id": "purpose-defined", "result": "passed"},
    {"id": "pollution-contained", "result": "passed"},
    {"id": "deletion-confirmed", "result": "passed"}
  ],
  "experiment": {
    "version": "1",
    "baseline_id": "memory-ledger-v1",
    "memory_types": ["short-term", "long-term", "external"],
    "context_modes": ["window-budget", "summary", "retrieval", "injection"],
    "pollution_injected": true,
    "pollution_recovered": true,
    "model_calls": 0,
    "network_calls": 0
  }
}
```

示例为字段形状说明，实际文件必须由页面导出并包含完整阶段；不要将示例 JSON 当作完成证据。
