# T14 上下文预算模拟器

这是模块 5A 的离线证据边界。浏览器组件使用 `site/src/lib/context-budget.mjs` 的纯函数分配器；它不调用模型、网络、文件、设备或真实 Coding Agent。数字是相对占用量，不是任何厂商的上下文上限。

## 本地检查

在 Windows 11 + PowerShell 7 中，从课程工作区运行：

```powershell
Set-Location -LiteralPath .\checker
python -m course_check check t14-context-budget --root .. --evidence-file ..\t14-context-budget-evidence.json --json
```

没有证据文件时可以运行结构检查，结果是 `partial`：

```powershell
python -m course_check check t14-context-budget --root .. --json
```

## 浏览器导出的最小匿名形状

页面导出的文件遵循已有 `agent-engineering-course/evidence` v1 envelope，并附带只含稳定 ID 的 `simulation`：

```json
{
  "contract": "agent-engineering-course/evidence",
  "contract_version": "1",
  "course_version": "0.1.0-alpha",
  "lesson_id": "t14-context-budget",
  "result": "passed",
  "anonymous": true,
  "checked_on": "2026-08-13",
  "summary": "所有必需证据均已通过。",
  "evidence": [
    {"id": "working-set-selected", "result": "passed"},
    {"id": "risk-signals-observed", "result": "passed"},
    {"id": "boundary-tested", "result": "passed"},
    {"id": "offline-deterministic", "result": "passed"}
  ],
  "simulation": {
    "version": "1",
    "runs": [
      {"id": "run-1", "finding": "insufficient", "findings": ["insufficient", "crowding"], "boundary": true}
    ],
    "observed": ["crowding", "insufficient", "pollution"]
  }
}
```

`course_check` 会根据 `runs` 重新推导四项检查，不信任调用者手写的 `result`；它会拒绝未知风险 ID、重复运行 ID、缺失边界标记和非匿名/不兼容版本。运行详情（容量、输入数字、原始文本、路径和凭据）不会进入网页交换文档。

## 课程边界

- **Context**：本轮推理可见的有限工作集。
- **History**：当前会话已有轮次，可能被压缩、截断或清理。
- **Memory**：受控跨任务保留的信息；必须有用途和更新/删除边界，不等于全部 History。
- **模拟分配**：只是教学夹具，不声称复刻 OpenAI、Anthropic、Codex 或 Claude Code 的实现。
