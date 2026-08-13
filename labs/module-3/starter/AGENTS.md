# 设备遥测任务的仓库规则

## 工作范围

- 这是一次性、合成的本地练习仓库；只处理 `data/readings.csv` 的公开样例。
- 只修改 `src/telemetry_report.py` 与 `worklog/` 下的学习记录。不要修改测试来掩盖失败。
- 不访问网络、远程仓库、环境变量中的凭据、用户目录或真实设备数据。
- 不运行 `git push`、不提交到远端，也不要把 `artifacts/` 下的生成物加入提交。

## 完成标准

- `python -m unittest discover -s tests -v` 通过。
- `python -m telemetry_report --input data/readings.csv --output artifacts/report.json` 生成只含统计摘要的 JSON。
- 先检查 `git diff --check` 和 `git diff`，再由人决定是否提交。

## 操作边界

默认只读检查；修改前先说明计划并等待人工确认。失败时保留错误证据，修复后重新运行测试和报告命令。不要把原始遥测行、绝对路径、密钥或个人信息写入交付记录。
