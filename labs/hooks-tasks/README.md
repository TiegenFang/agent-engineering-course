# T21 Hooks 与 Tasks 离线实验

这是模块 10A 的实验合同与恢复说明。浏览器页面使用 `site/src/lib/hooks-tasks.mjs` 的 deterministic fixture；它只计算稳定状态，不启动 Codex、Claude Code、模型、API、MCP、PowerShell 命令、网络或真实副作用。

## 观察合同

一次记录包含以下匿名状态：

- `trigger`：Hook 是否因生命周期事件触发；
- `deduplicated`：重复 Hook 是否只执行一次；
- `permission`：副作用动作是 `blocked` 还是 `allowed`；
- `failed` / `recovered`：故障是否注入以及是否恢复；
- `stopped`：是否达到完成或步数停止条件；
- `taskCreated`：是否有显式 Task/Todo；
- `sideEffect`：是否真的发生副作用（安全默认必须是 `false`）。

checker 只接受这些枚举和布尔/计数摘要，不接受命令、路径、任务正文、凭据、会话日志或原始数据。页面生成的匿名文件名为 `t21-hooks-tasks-evidence.json`。

## Windows 11 + PowerShell 7 主路径

```powershell
Push-Location .\checker
python -m course_check check t21-hooks-tasks `
  --root .. `
  --evidence-file $env:TEMP\t21-hooks-tasks-evidence.json `
  --output $env:TEMP\t21-hooks-tasks-checked.json `
  --json
Get-Content -LiteralPath $env:TEMP\t21-hooks-tasks-checked.json
Pop-Location
```

未提供证据时结果为 `partial`，这是结构检查，不是假装真实客户端执行。只有夹具导出的匿名实验状态能让 checker 推导 `passed`。

## 故障注入与恢复

1. 运行“持续失败：看停止”，记录失败未恢复和停止预算。
2. 切回“安全默认：全证据”，记录一次失败恢复、权限 blocked 和副作用 `false`。
3. 再点击“单独记录一次显式 Task/Todo”，确认它不是 Hook 自动创建。
4. 选择 `schedule` 或 `background`，观察它们只登记编排面，不在本地夹具自动启动工作。

不要把“允许副作用：看风险”的结果当成安全通过；该分支只演示权限一旦放行就会改变风险状态，夹具仍不会真实写出、发布、联网或通知。

## 官方事实核验（2026-08-13）

- Codex Hooks：`https://learn.chatgpt.com/docs/hooks`
- Codex Scheduled tasks：`https://learn.chatgpt.com/docs/automations`
- Claude Code Hooks guide/reference：`https://code.claude.com/docs/en/hooks-guide`、`https://code.claude.com/docs/en/hooks`
- Claude Code scheduled tasks：`https://code.claude.com/docs/en/scheduled-tasks`
- Claude Code tools reference：`https://code.claude.com/docs/en/tools-reference`

上述链接是工具适配层事实源；本 README、fixture、测试与证据状态是课程原创内容。制作时未执行真实 Codex/Claude Code Hook、Task、schedule 或 background，发布前需重新核验。
