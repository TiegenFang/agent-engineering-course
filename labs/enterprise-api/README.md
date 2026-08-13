# T31 企业进阶 API 结课：Issue-to-PR 单步骤 Agent

这个实验把 API Agent 限定为一个可回退的 `draft-validation-plan` 子步骤：读取合成 Issue 摘要，生成结构化的验证计划草稿，并把结果交还给人审。它不能 `merge`、`push`、发布消息或写入真实仓库。

## Windows + PowerShell 7 主路径

```powershell
$output = Join-Path ([System.IO.Path]::GetTempPath()) 't31-enterprise-api.json'
python .\labs\enterprise-api\run_fixture.py --scenario baseline --output $output
python -m course_check check t31-enterprise-api --root . --evidence-file $output --json
Get-Content -LiteralPath $output
```

预算停止分支会在模型调用前停止：

```powershell
python .\labs\enterprise-api\run_fixture.py --scenario budget-stop --output $output
python -m course_check check t31-enterprise-api --root . --evidence-file $output --json
```

## 实验约束

- **范围**：只生成验证计划草稿；`merge-or-push` 永远是高影响操作，必须人工批准，夹具不执行它。
- **输出**：固定 `issue-plan-v1` 状态结构，应用侧仍需验证字段；自然语言自称成功不算证据。
- **预算**：`budget_status=stopped` 时 `model_call_started=false`，不得把预算停止改写成成功。
- **恢复**：注入一次合成 `tool-timeout`，只允许一次有界重试；不可恢复时停在人工确认点。
- **隐私**：证据只保留稳定 ID、状态、聚合成本和版本，不含 prompt、工具 payload、路径、密钥或原始 Issue 内容。
- **现场边界**：runner 不导入 OpenAI/Anthropic SDK、不读取环境变量中的密钥、不联网、不调用真实 API；通过 checker 仅证明离线控制流。

`rubric.json` 是机器可读评价维度；`checker/course_check/enterprise_api.py` 会重新计算 check 结果并拒绝篡改或敏感字段。
