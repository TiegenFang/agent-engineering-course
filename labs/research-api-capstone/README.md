# T30 科研进阶 API 结课：一个受预算约束的研究步骤

本实验只接管一个边界明确的步骤：把合成设备遥测快照整理为 `status-summary-v1` 状态摘要。它不是完整科研自动化系统，也不读取真实研究数据。

## 离线路径

离线夹具用 Python 标准库展示三种可观察状态：成功的 tool round-trip、工具失败后的安全默认恢复，以及达到请求预算后的停止。它不导入 provider SDK、不读取环境变量中的密钥、不发送网络请求。

Windows 11 + PowerShell 7：

```powershell
$out = Join-Path ([System.IO.Path]::GetTempPath()) 't30-research-api-capstone'
python .\labs\research-api-capstone\run_fixture.py --output $out --variant pressure-night
python -m course_check check t30-research-api-capstone --root . --evidence-file (Join-Path $out 't30-research-api-evidence.json') --json
```

`temperature-daily` 是另一种合成输入；`pressure-night` 是迁移挑战。输出只包含状态、计数、固定枚举和预算元数据，不包含 prompt、tool payload、报告正文、路径、原始记录或凭据。

## 受预算 live seam

`t30-live-smoke-plan.json` 只是现场路径计划，不是现场结果。真正执行前必须由人选择 provider、SDK、模型和已审核 credential，并确认：最多 2 次请求、最多 96 output tokens、教学预算上限 `$0.01`，且输入仍是合成摘要。任何真实副作用、上传数据或超预算重试都在范围外。

完成现场路径后，学习者应另存匿名的客户端、SDK、模型、日期、成本和限制摘要；不得把 key、原始消息、工具参数、原始研究数据或绝对路径放进 evidence。课程 checker 不会把 `not-run` 改写为成功。

## 恢复与边界

- 工具失败：保留失败枚举，使用安全默认并重新验证结构化输出。
- 预算停止：停止 loop，不通过增加重试或修改 evidence `result` 伪造成功。
- 真实科研数据：不允许进入本实验、截图、日志、导出文件或 issue。
- Codex/Claude Code：可用来审阅计划或迁移输入，但不属于本夹具的 API 现场证据。
