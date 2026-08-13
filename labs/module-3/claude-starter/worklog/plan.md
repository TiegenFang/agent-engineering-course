# 执行计划

## Files

只读取 `CLAUDE.md`、`TASK.md`、`data/readings.csv`、`tests/test_report.py`；只修改 `src/pressure_report.py` 与 `worklog/`。

## Commands

先运行 `python -m unittest discover -s tests -v` 记录预期失败；修复后再次运行测试、报告命令和 `git diff --check`。

## Permissions

使用一次性本地仓库和 Claude Code 的默认/plan 权限；写入或执行命令前由人确认，禁止网络、远程、凭据和真实数据。

## Stop

遇到越界路径、网络请求、凭据、破坏性命令、权限不确定或测试无法解释时立即停止，并把状态写入 `worklog/recovery.md`。
