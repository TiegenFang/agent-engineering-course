# 设备遥测与报告工具

`labs` 将承载贯穿课程的合成设备遥测项目。模块 0 先提供一个不接触遥测数据的环境诊断脚本：

```powershell
pwsh -NoProfile -File .\labs\module-0\diagnose-environment.ps1
```

脚本只输出 `t05-environment` 的命令/版本/人工确认状态，供 `course_check` 生成既有匿名 evidence contract。模块 3 在 `module-3/starter` 提供一次性合成设备遥测仓库，并由 `initialize-codex-task.ps1` 与 `codex-task.ps1` 记录离线的 Codex 仓库任务检查点；脚本不会调用 Codex 或任何网络服务。

模块 3 的实验必须在显式指定的一次性目录中运行。不要把课程仓库、真实研究数据、企业数据、密钥或个人信息作为 `-WorkspacePath` 或仓库输入。

当前已加入 `agent-loop/` 的 Agent loop 合同和 `agent-instructions/` 的指令工程对照合同；真实数据、CLI 和设备接入不属于这些浏览器夹具。

- `agent-loop/`：模块 1 的确定性响应—工具—停止 trace。
- `agent-instructions/`：模块 2 的模糊/工程化指令、冲突、提示注入、过长预算和迁移输入。
- `module-3/claude-starter/`：模块 3 的压力变化输入、`CLAUDE.md` 规则、故障样例和 Claude-only/dual-tool 路径模板。
- `module-3/initialize-claude-migration.ps1` 与 `module-3/claude-migration.ps1`：只在明确的一次性目录创建基线并记录有序匿名状态；不调用或伪造 Claude Code、Codex、API 或真实设备结果。

这里不得加入真实敏感科研数据、企业数据、密钥或个人信息。

模块 4 的项目规则实验位于 `labs/project-rules/`。它只允许在课程仓库之外的
一次性目录中创建合成 `AGENTS.md`/`CLAUDE.md` 文件，并输出匿名状态证据；不要把
实验规则复制到真实仓库，也不要把真实规则正文或客户端日志提交到课程仓库。

模块 8 的 Plugin 审计实验位于 `labs/plugin-audit/`。它只审计课程内置的脱敏
manifest 元数据，不添加 marketplace、不安装包、不执行脚本/hook、不启动 MCP，
并由 checker 重新推导匿名审计证据。

