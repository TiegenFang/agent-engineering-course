# 模块 2：Agent 指令工程本地实验

这个实验用一个浏览器内的 deterministic instruction fixture 比较同一合成任务上的“模糊请求”和“工程化指令”。它不是模型评测，也不调用 Codex、Claude Code、模型 API、网络、真实设备或文件系统；模拟器的规则、场景和结果都在课程工作区中可读。

## 学员路径

1. 在模块 2 页面保持默认的“日常温度报告”，先选择预测并记录，再运行“同一基线”。
2. 依次运行“规则冲突”“提示注入”和“过长指令”，阅读两列的失败原因和恢复动作。
3. 如需观察字段缺失，删掉工程化指令中的一个固定字段并重跑；点击“恢复当前场景指令”后重新记录预测。
4. 将变化输入切换为“夜班压力报告（迁移输入）”，确认主题、单位和记录限制发生变化，但目标、约束、工具边界、输出契约和失败证据仍然存在。
5. 点击“导出匿名 evidence”，把导出的 JSON 交给本地 checker；页面下方的 `EvidenceLoop` 可以导入结果到浏览器本地学习记录。

## 固定实验合同

- 版本：instruction experiment `v1`。
- 基线：`telemetry-report-v1`，只含合成设备遥测与报告任务。
- 场景顺序：`baseline` → `conflict` → `injection` → `long`。
- 迁移输入：`pressure-night`，从温度/`°C`/最近 5 条改为压力/`kPa`/最近 3 条。
- 工程化最小字段：目标、上下文、约束、非目标、工具边界、输出契约、验收标准、失败证据。
- 过长预算：工程化版本不超过 720 字符；模糊版本的噪声用于观察上下文选择，不代表真实模型上下文窗口数值。

每次对照都会生成两个稳定的结果状态。模糊请求故意缺少任务合同；工程化指令只有在固定字段、场景边界和预算满足时才会通过。规则不执行写入、网络或外部命令，因此“通过”只表示模拟器的教学验收通过。

## PowerShell 7 检查证据

在课程工作区的 `checker` 目录运行：

```powershell
python -m course_check check t03-agent-instruction --root .. --json
```

这条命令只检查页面、模拟器和实验合同是否存在，结果为 `partial`，不表示已完成对照。把页面下载的 JSON 保存为 `t03-agent-instruction-evidence.json` 后运行：

```powershell
python -m course_check check t03-agent-instruction --root .. --evidence-file ..\t03-agent-instruction-evidence.json --output ..\t03-agent-instruction-checked.json
```

带 evidence 文件的检查会严格验证：

1. 固定的 six evidence IDs 及其顺序；
2. `experiment.version`、基线 ID、四个场景和工程化结果；
3. 冲突、注入、过长和变化输入迁移的稳定状态；
4. 当前课程版本和 `agent-engineering-course/evidence` v1。

详细实验发现和编辑过的指令正文不会进入检查器返回的匿名文档。检查器只读取学员主动指定的本地文件，不上传源码、密钥、路径或原始遥测。

## 故障恢复与边界

- **字段不足**：恢复八个字段，或点击页面的恢复按钮后重新预测和运行。
- **规则冲突未封装**：写清更高优先级规则、只读工具边界、停止条件和人工确认。
- **提示注入未隔离**：把遥测备注当作不可信数据，忽略其中改变任务边界的文本。
- **过长**：删去不影响当前决策的历史背景，让工程化版本回到 720 字符以内。
- **版本不兼容**：网页、`labs` 和 `checker` 必须来自同一课程版本；不要手工修改 `course_version`。

权限与副作用：浏览器实验只处理固定合成字符串；下载/导入由学员主动触发；不需要账号、模型、网络或付费服务。跨到真实 Codex 或 Claude Code 的迁移挑战必须另行记录客户端、模型、成本、权限和人工确认；本 fixture 不替代现场验收。
