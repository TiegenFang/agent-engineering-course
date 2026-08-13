# 模块 5B：压缩、恢复与交接实验合同

这是 `t15-context-recovery` 的离线、确定性实验合同。页面中的 JavaScript 模拟器和本地 Python checker 共同验证同一组稳定结果；它们不调用真实模型、Codex、Claude Code、API、设备、网络或文件工具。

## 固定基线

- `baseline_id`: `telemetry-report-v1`
- `version`: `1`
- 当前工作集包含一个目标、三条约束（`read-only`、`no-network`、`preserve-evidence`）和两条可核查证据。
- 历史项 `previous-attempt` 只代表会话记录；Memory 项 `preference-note` 只有在另一个受控课节中决定所有者、寿命和删除条件后才可保存。

## 三种压缩结果

| `mode` | 压缩后结果 | 必须观察 |
| --- | --- | --- |
| `faithful` | `faithful` | 三条约束和两条证据仍在。 |
| `distorted` | `distorted` | `preserve-evidence` 被改变，失真被诊断。 |
| `constraint-omitted` | `constraint-omitted` | `no-network` 被遗漏，遗漏被诊断。 |

每个 comparison 必须包含 `before` 和 `after` 结果；只提交模式名称或一段总结不能通过检查。

## 污染恢复合同

固定 fixture ID 是 `untrusted-note`。备注尝试把只读任务变为外发/删除任务，但它的角色始终是“不可信数据”。恢复顺序固定为：

```text
detect → quarantine → restore → revalidate
```

完成恢复后，`pollution.recovered` 必须为 `true`，并且恢复结果重新包含三条基线约束。不要执行备注中的动作，也不要把备注全文写进公开 evidence。

## 交接包合同

跨会话交接包必须包含以下字段：

```json
{
  "version": "1",
  "goal": "report-task",
  "status": "ready-for-next-session",
  "evidence": ["compression-before-after", "pollution-recovered"],
  "risks": ["compressed-context-may-be-lossy"],
  "next_steps": ["核对三条约束"],
  "layers": ["context", "history", "memory"]
}
```

`status=blocked` 只能用于尚未完成实验的本地中间状态；检查器通过的交接包必须是 `ready-for-next-session`。字段只传递稳定 ID 和风险，不传递路径、聊天正文、凭据、原始遥测或个人信息。

## 公开证据检查项

匿名 `evidence` 必须按以下顺序出现：

1. `compression-compared`
2. `distortion-detected`
3. `constraint-omission-detected`
4. `pollution-recovered`
5. `handoff-complete`
6. `layers-distinguished`

本地 checker 会重新检查模式、布尔诊断、恢复状态、交接字段和三层边界；它不会信任调用者手写的 `passed` 列表。

## 本地检查

在 `checker` 目录或将其加入 `PYTHONPATH` 后运行：

```powershell
python -m course_check check t15-context-recovery --root .. --evidence-file ..\t15-context-recovery-evidence.json --json
```

没有证据文件时，checker 仅确认课程切片文件存在并返回 `partial`。页面导出的 evidence 文件才可以证明本地实验已经完成。
