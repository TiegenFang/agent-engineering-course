# Claude Code 迁移练习规则

## 工作范围

- 这是一次性、合成的本地练习仓库，只处理 `data/readings.csv` 的公开样例。
- 只允许修改 `src/pressure_report.py` 与 `worklog/` 下的学习记录；不要修改 `tests/`、`data/` 或本文件。
- 默认只读检查；写入前先说明计划并等待人工确认。不要执行网络、远程仓库、真实设备或凭据相关操作。

## 完成标准

- `python -m unittest discover -s tests -v` 通过。
- `python -m pressure_report --input data/readings.csv --output artifacts/report.json` 生成只含统计摘要的 JSON。
- 先检查 `git diff --check` 和允许范围内的 `git diff`，再由人决定是否提交。

## 安全边界

- `worklog/official-sources.md` 只记录官方资料、日期和事实/未验证边界，不记录 token、路径或原始数据。
- 本地阶段脚本的 `live_call` 状态必须保持 `not-verified`；不要伪造 Claude Code 或 Codex 的调用结果。
- 如果权限提示、路径解析、网络访问或修复结果不确定，停止并记录原因。
