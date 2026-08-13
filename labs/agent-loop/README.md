# 模块 1：Agent loop 本地实验

这个实验用一个浏览器内的 mock/deterministic trace 观察最小 Agent loop：模型响应、工具请求、工具执行、结果回填、下一次响应和停止条件。它是教学夹具，不是真实 Codex、Claude Code、模型、设备或 API 的行为；不会发起网络请求，也不需要账号或密钥。

## 学员路径

1. 打开课程站的 `module-1-agent-loop` 页面，先在每个事件前选择你预测的下一步。
2. 修改目标、`deviceId` 或阈值，观察确定性读数和停止说明如何变化。
3. 选择“工具错误”故障模式，执行到错误回填和停止；恢复为“无故障”后重新完成一次成功路径。
4. 完成或部分完成后点击“导出匿名证据”。页面下方的 `EvidenceLoop` 可以直接接收该结果，也可以把下载的 JSON 留作本地检查输入。

## PowerShell 7 检查证据

在课程工作区的 `checker` 目录运行：

```powershell
python -m course_check check t02-agent-loop --root .. --evidence-file ..\t02-agent-loop-evidence.json --output ..\t02-agent-loop-checked.json
```

`course_check` 会严格验证 `t02-agent-loop` 的固定 trace v1：`prediction-1 → response-1 → tool-request-1 → tool-execution-1 → tool-result-1 → response-2 → stop-1`；工具错误路径以 `outcome: error` 省略第二次响应。缺失、未知或重复的 trace ID 会被拒绝。网页导出的文档还保留 `course_version`，旧版本不会被改写为当前版本。未知字段会被丢弃，路径、密钥和原始遥测不会进入网页交换文档。没有导入页面导出的文件时，也可以运行：

```powershell
python -m course_check check t02-agent-loop --root .. --json
```

这条命令只检查课程页面、模拟器和实验契约的结构，输出 `partial` 的匿名结果；它不冒充已经执行了 trace。只有带有完整成功或错误 trace 的页面 evidence 才会得到 `passed`。

## 可核验成果

- 至少一次完整 trace：六个事件按预测、执行、回填和停止顺序出现。
- 一次故障 trace：工具错误被回填，循环在错误停止条件处结束。
- 一个不含路径、密钥和原始数据的 `agent-engineering-course/evidence` v1 JSON。

## 边界卡片

- 权限与副作用：页面只在浏览器内计算和渲染；下载与导入都是学员主动操作，不触碰设备、文件系统或网络。
- 费用与账号：免费，无模型/API/Agent 客户端账号要求。
- 失败与恢复：错误分支是预置的确定性故障；切回“无故障”并重置实验即可恢复。无故障页面不代表真实客户端现场验收。
- 版本：trace 与证据契约锁定在课程工作区当前版本，发布前需重新做浏览器和跨平台复核。
