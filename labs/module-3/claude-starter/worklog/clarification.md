# 澄清记录

## Goal

把合成压力读数统一为 kPa，输出稳定的压力摘要和告警计数，并在不声称发生 live 调用的前提下完成 Claude Code 迁移挑战。

## Non-goals

不联网、不接真实设备、不修改测试或数据、不读取凭据、不推送；不把 Codex 主实验原样复制成温度任务。

## Acceptance

测试和报告命令通过；压力输入、权限/成本对照、失败恢复、官方资料日期和路径选择均留下状态证据；报告不含原始行。

## Migration

变化输入是 `pressure-night`：压力而非温度，`kPa`/`psi`/`bar` 而非 `C`/`F`，并增加 `peak_kpa` 与 `alarm_count` 验收字段。
