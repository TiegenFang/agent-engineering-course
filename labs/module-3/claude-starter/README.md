# 设备遥测与报告工具：Claude Code 迁移任务

这是模块 3 的 Claude Code 迁移输入。它仍使用公开合成数据，但和 Codex 主实验有意改变了领域、单位、验收字段与失败恢复：这里处理压力（`kPa`、`psi`、`bar`），输出峰值和告警计数，不处理温度的华氏度归一化。

本目录可单独复制到一次性本地 Git 仓库，因此没有 Codex 账号也能完成 Claude-only 路径。双工具路径可以把 Codex 主实验的状态摘要写入 `worklog/codex-reference.md`，但这个本地脚本不会调用或伪造 Claude Code、Codex、模型、API 或账号结果。

## 本地运行

在仓库根目录执行：

```powershell
python -m unittest discover -s tests -v
python -m pressure_report --input data/readings.csv --output artifacts/report.json
git diff --check
git diff -- src/pressure_report.py worklog CLAUDE.md
```

基线测试有一个已知的单位换算缺陷，因此第一次测试失败是预期的。按 `TASK.md` 和 `CLAUDE.md` 先澄清目标、权限和停止条件，再由学员决定是否在一次性目录中使用 Claude Code。阶段脚本只记录状态，不声称发生过 live Claude 调用。

生成匿名证据的脚本在课程仓库的 `labs/module-3/claude-migration.ps1`。
