# 任务：迁移到压力安全报告

## 背景

`data/readings.csv` 是公开合成数据，不代表真实设备。这个变化任务需要把压力读数统一为 `kPa`，并在固定阈值上统计告警；它不是 Codex 主实验的温度报告复刻。

## 目标

修复 `src/pressure_report.py`，让已有测试和报告命令通过；保持 `pressure-report-v1` 的字段结构，不把原始记录复制进报告。

## 非目标

- 不引入网络、数据库、第三方服务或真实设备连接。
- 不修改 `tests/` 或 `data/readings.csv` 来绕过失败。
- 不读取、粘贴或提交凭据、个人信息、真实科研/企业数据。
- 不提交或推送，除非人工审阅 diff 后明确决定。
- 不把本地 checker 的状态记录写成“Claude 已经被调用”的证明。

## 验收标准

1. `kPa` 保持原值，`psi` 按 `kPa = psi * 6.89476` 转换，`bar` 按 `kPa = bar * 100` 转换。
2. 非法时间戳、非法数值和不支持的单位被忽略。
3. 报告输出 `pressure-report-v1`、`valid_count`、`mean_kpa`、`peak_kpa` 和 `alarm_count`；结果稳定为 3、101.317、101.325、2。
4. 报告不含 `timestamp` 或原始行列表，测试、报告命令和 `git diff --check` 通过。
5. 变化输入、权限/成本对照、故障恢复和官方资料记录在 `worklog/` 中；`claude-only` 与 `dual-tool` 两条路径都能按说明完成。

## 故障注入与恢复

基线测试预期失败：这是已知缺陷证据，不要删除测试。修复后重新运行测试和报告命令，在 `worklog/recovery.md` 记录失败原因、最小修复和恢复命令。若 Claude Code 需要写入或执行命令，先在一次性目录和官方权限模式下得到人工确认；遇到越界、网络、凭据或不确定的破坏性动作立即停止。

## 官方资料现场核验入口

- 安装与 Windows shell：[Claude Code advanced setup](https://code.claude.com/docs/en/installation)
- 操作权限：[Configure permissions](https://code.claude.com/docs/en/permissions)
- 失败回退：[Checkpointing](https://code.claude.com/docs/en/checkpointing)
- 成本边界：[Manage costs effectively](https://code.claude.com/docs/en/costs)

这些链接在课程制作日（2026-08-13）现场打开；本地实验不联网，也不把页面打开当成真实客户端验收。
