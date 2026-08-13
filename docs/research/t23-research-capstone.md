# T23 科研核心结课轨道：来源与验证边界

## 设计依据

T23 将 `CONTEXT.md` 中的“科研结课轨道”落实为同一合成设备遥测主题上的可复现工作流：数据检查、分析脚本、图表、实验记录和报告。它复用 T16 Memory、T17 Skill、T20 MCP 调用和 T22 多 Agent 的能力目标，但不复制其页面或把真实客户端调用伪装成离线通过。

实验实现固定为 Python 标准库和状态摘要合同 `telemetry-research-v1`。页面夹具、lab、checker 和 Node/Python/Playwright 测试都是本课程原创；source ledger 中的 `course-research-capstone-original-t23` 记录了用途、版本和许可证边界。

## 不变的验收目标

- Context 记录问题、范围、非目标和停止条件；
- Memory 有 owner、用途和 lifetime，过期记录不会直接进入当前工作集；
- Skill 固定分析步骤并保留触发边界；
- MCP 观察保持只读，写出需要人工确认；
- 输出包含脚本、图表、记录、报告和匿名 evidence；
- 压力夜班是变化输入，改变主题、单位与记录限制但保持同一评分量表；
- checker 从匿名实验状态重新推导检查结果，并拒绝路径、秘密、原始研究数据和伪造的 `result`。

## 验证范围

本轮验证目标是 Windows 11 + PowerShell 7 下的离线实验、checker、Node 单元脚本、静态站构建和浏览器页面。真实 Codex、Claude Code、模型 API、远端 MCP、科研数据和跨平台现场路径未验证；页面和 lesson metadata 必须保留这一边界。
