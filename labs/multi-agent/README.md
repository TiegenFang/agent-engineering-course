# T22 受控多 Agent 对照实验

这是模块 10B 的离线证据边界。浏览器组件调用 `site/src/lib/multi-agent-lab.mjs` 的纯函数，比较单 Agent 基线与两种固定 Subagents 情形。三个路径共享同一个 `telemetry-report-v2` 目标和四项验收；它们不启动真实 Agent、模型、worktree、进程、网络或本地项目。

## 固定情形

| 情形 | 子任务边界 | 冲突 / 恢复 | 课程结论 |
| --- | --- | --- | --- |
| `independent-review` | `input-validation`、`summary-outline`、`acceptance-check` 各有唯一责任 | 无冲突；协调者统一验证 | `consider-bounded-parallel`：只在独立任务中继续比较 |
| `overlap-conflict` | 两个子代理错误地同时拥有 `report-summary` | `shared-output-collision` → `repartition-and-revalidate` | `do-not-adopt`：恢复成功也不抵消更高成本 |

固定成本单位用于教学比较，不是模型、订阅或 API 的真实时间、Token 或账单。匿名 evidence 采用 `usage_units`，而不是传递原始 Token/账户日志。

## 本地检查

在 Windows 11 + PowerShell 7 中，从课程工作区运行：

```powershell
Set-Location -LiteralPath .\checker
python -m course_check check t22-multi-agent --root .. --evidence-file ..\t22-multi-agent-evidence.json --output ..\t22-multi-agent-checked.json --json
Get-Content -LiteralPath ..\t22-multi-agent-checked.json
```

没有 evidence 文件时可以先做结构检查，结果是 `partial`：

```powershell
python -m course_check check t22-multi-agent --root .. --json
```

## 浏览器导出的匿名形状

页面只导出稳定 ID、固定教学单位和布尔结果。下面是单个冲突情形的 `partial` 匿名形状示例（省略任何真实 Prompt、路径、源码、日志、模型输出和账户数据）。它用于说明字段边界，不能替代浏览器在记录两种固定情形后导出的 `passed` evidence：

```json
{
  "contract": "agent-engineering-course/evidence",
  "contract_version": "1",
  "course_version": "2.0.0",
  "lesson_id": "t22-multi-agent",
  "result": "partial",
  "anonymous": true,
  "checked_on": "2026-08-13",
  "summary": "部分证据已通过，仍有证据需要补齐。",
  "evidence": [
    {"id": "same-goal-compared", "result": "passed"},
    {"id": "task-boundaries-declared", "result": "passed"},
    {"id": "time-usage-verification-compared", "result": "passed"},
    {"id": "conflict-recovered", "result": "passed"},
    {"id": "decision-supported", "result": "failed"},
    {"id": "offline-deterministic", "result": "passed"}
  ],
  "experiment": {
    "version": "1",
    "goal": "telemetry-report-v2",
    "comparisons": [
      {
        "id": "comparison-overlap-conflict",
        "scenario": "overlap-conflict",
        "goal": "telemetry-report-v2",
        "acceptance": ["valid-records-counted", "units-normalized", "report-produced", "verification-passed"],
        "single": {"mode": "single", "accepted": true, "elapsed_seconds": 18, "usage_units": 90, "verification_units": 2},
        "subagents": {"mode": "subagents", "accepted": true, "elapsed_seconds": 31, "usage_units": 225, "verification_units": 5},
        "boundaries": [
          {"id": "draft-a", "owns": "report-summary"},
          {"id": "draft-b", "owns": "report-summary"},
          {"id": "acceptance-review", "owns": "acceptance-check"}
        ],
        "shared_context": ["goal", "input-contract", "acceptance-contract"],
        "merge": "coordinator-repartitions",
        "conflict": "shared-output-collision",
        "recovery": "repartition-and-revalidate",
        "recommendation": "do-not-adopt",
        "offline": true
      }
    ],
    "observed_modes": ["single", "subagents"],
    "observed_boundaries": ["acceptance-check", "report-summary"],
    "observed_conflicts": ["shared-output-collision"],
    "observed_recoveries": ["repartition-and-revalidate"],
    "model_calls": 0,
    "network_calls": 0
  }
}
```

`course_check` 会重新推导固定情形、共同目标、成本数字、冲突、恢复和决策；它拒绝未知情形、篡改的成本、无恢复的冲突、重复对照、不兼容版本、非离线记录以及敏感字段。它不信任调用者手写的 `result` 或 `evidence` 状态。

## 课程边界

- Subagent 是被主协调者委派、返回摘要的工作者；它不是更好的默认写入者。
- 并行能缩短墙钟时间，不代表总使用量、验证成本或风险更低。
- 冲突恢复的成功证据只证明“该次恢复后同一验收通过”；它并不证明应在真实仓库采用同一编排。
- 真实 Codex、Claude Code、worktree、权限、模型、计费和并发限制需要按当前官方文档和实际账户现场复核；本 lab 不声称已经验证。
