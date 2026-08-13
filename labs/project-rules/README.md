# 项目指令与规则作用域实验

本实验用一个一次性目录观察两种 Coding Agent 的项目规则机制：Codex 的
`AGENTS.md`/`AGENTS.override.md`，以及 Claude Code 的 `CLAUDE.md`、
`@AGENTS.md` 导入和 `.claude/rules/` 路径规则。实验不要求账号、模型、API key
或网络；脚本只在你明确指定且事先不存在的目录中创建合成文件，然后删除该目录内
故意冲突的 override，生成只含状态的本地诊断 JSON。

## Windows 11 + PowerShell 7 主路径

下面的命令把实验目录和输出放在临时目录，避免把规则文件写进课程仓库。先确认两
个目标都不存在；脚本会拒绝复用已有实验目录、Git 仓库或课程源码路径。

```powershell
$labParent = Join-Path $env:TEMP "agent-engineering-course"
if (-not (Test-Path -LiteralPath $labParent -PathType Container)) {
  New-Item -ItemType Directory -Path $labParent | Out-Null
}
$labRoot = Join-Path $labParent "t04-project-rules-practice"
$output = Join-Path $labParent "t04-project-rules-diagnostic.json"
if ((Test-Path -LiteralPath $labRoot) -or (Test-Path -LiteralPath $output)) {
  throw "目标已存在；请先人工审阅或换一个一次性目录。"
}
pwsh -NoProfile -File .\labs\project-rules\project-rules.ps1 `
  -LabPath $labRoot `
  -OutputPath $output
```

脚本生成的规则正文只有合成标签，不是课程仓库的指令。可以在重新创建的新目录
中替换规则句子，保持目录关系不变；检查器看的是发现、冲突、恢复和复核的行为
证据，不匹配某一段固定文案。

## 观察和预测

先不要运行脚本，预测以下结果，再对照 `journey.stages` 中的布尔观察：

1. Codex 从实验根目录进入 `src` 时，根 `AGENTS.md` 会进入链；同一目录同时有
   `AGENTS.md` 和 `AGENTS.override.md` 时，override 被选中，普通文件不再单独
   进入该目录的链；更靠近当前目录的规则在合并文本中更晚出现。
2. Claude Code 不读取 `AGENTS.md` 这个文件名本身；根 `CLAUDE.md` 可以用
   `@AGENTS.md` 导入它，祖先与当前目录的 `CLAUDE.md` 都会进入上下文，二者是
   拼接而非 Codex 式的同目录二选一。`.claude/rules/` 中有 `paths` 的规则只在
   匹配文件被访问时相关。
3. 当两层 Claude 指令互相矛盾时，不应把“更近”当成硬权限；官方文档提示冲突
   可能任意选择。先记录冲突和加载层级，再收窄或删除重复规则。

## 故障注入与恢复

脚本会在 `src` 同时放入普通 `AGENTS.md` 与故意冲突的
`AGENTS.override.md`，并保留根/嵌套 `CLAUDE.md` 供诊断。恢复动作只删除这个
一次性目录内的 override，然后重新检查普通规则仍在、Claude 项目规则仍在。若要
手工演练：

- 确认启动目录是否真的是实验目录的 `src`；先记录当前目录和分支，不要在真实仓
  库中执行同样的清理。
- 只移动或删除一次性目录内明确的冲突文件，保留副本；不要对真实仓库运行
  `Remove-Item -Recurse`、`git clean` 或覆盖根 `AGENTS.md`/`CLAUDE.md`。
- Claude Code 的设置权限（例如 deny 或 sandbox）是客户端约束，不是
  `CLAUDE.md` 文字规则；发现行为仍越过安全边界时，应停下并检查设置/人工确认，
  不能靠改写一段规则文字“授权”。

脚本的 `$output` 只包含安全 ID、布尔观察和 `passed`/`failed`，不包含路径、规则
   正文、用户名、凭据或原始数据。检查器会从阶段观察重新推导 6 个公开检查；手写
   全部 `passed` 但与阶段不一致的文件会被拒绝。

## 生成匿名 evidence

```powershell
Push-Location .\checker
python -m course_check check t04-project-rules `
  --root .. `
  --evidence-file $output `
  --output $labParent\t04-project-rules-evidence.json `
  --json
Pop-Location
```

只把最后生成的 `t04-project-rules-evidence.json` 导入课程页面；它遵循
`agent-engineering-course/evidence` v1。无证据文件运行 checker 只能验证页面、
脚本和实验契约，结果是 `partial`，不代表真实工具客户端已经现场执行。

## 迁移挑战

如果你有 Codex 或 Claude Code，任选一个在同一个一次性目录中复核加载层级；另一种
工具只需写一段差异说明，保持任务目标、冲突诊断、恢复动作和隐私边界不变。记录
客户端版本和日期，但不要把会话日志、绝对路径或规则全文提交。没有账号时，脚本
和 checker 路径已经覆盖核心能力；不要伪造“真实工具已运行”的证据。

本目录中的脚本和实验设计是课程原创，代码按仓库 MIT；正文说明按 CC BY 4.0。
