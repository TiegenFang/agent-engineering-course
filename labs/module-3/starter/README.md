# 设备遥测与报告工具：Codex 安全仓库任务

这是课程模块 3 的一次性合成练习仓库。它不联网，不读取真实设备或研究数据，也不要求把任何凭据放入仓库。

## 本地运行

在仓库根目录执行：

```powershell
python -m unittest discover -s tests -v
python -m telemetry_report --input data/readings.csv --output artifacts/report.json
git diff --check
git diff -- src/telemetry_report.py worklog
```

基线测试有一个已知缺陷，因此第一次测试失败是预期的。请按 `TASK.md` 和仓库 `AGENTS.md` 先澄清目标、写计划，再让 Codex 进行最小修改。失败和恢复只记录状态与动作，不记录原始遥测、绝对路径或账号信息。
