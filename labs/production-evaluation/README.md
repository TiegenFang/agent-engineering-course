# T29 生产验证、评测与成本控制实验

本实验用一个完全离线、确定性的 evaluator 复现生产前门禁：成功、失败、变化输入、恢复、日志脱敏、成本预算与版本锁定。它不调用 OpenAI、Anthropic、Codex、Claude Code 或任何付费 API。

## PowerShell 7

```powershell
$root = (Get-Location).Path
$result = Join-Path ([System.IO.Path]::GetTempPath()) 't29-evaluation.json'
& .\labs\production-evaluation\run-evaluation.ps1 -OutputPath $result
Get-Content -LiteralPath $result
python -m course_check check t29-production --root $root --evidence-file $result --json
```

The evaluator uses only synthetic telemetry and writes only to the explicit output path. The result contains stable check IDs and aggregate counters, never prompts, tool payloads, paths, secrets, raw records, or hidden reasoning.

`rubric.json` is the machine-readable common evaluation vocabulary for the OpenAI and Anthropic migration challenges. Provider-specific response fields remain adapter evidence and are never treated as cross-provider standards.

## Modes

- `baseline`: successful response with the expected structured contract.
- `failure`: a deterministic tool failure is observed and recovered without retrying a non-idempotent action.
- `variant`: the same evaluator receives a changed device and unit input; the expected output is derived from the input, not copied from the baseline.
- `budget`: the estimated cost exceeds the configured offline budget and execution stops before a model call.

The fixture is a teaching contract, not a production benchmark and not evidence that a live model, SDK, provider price, latency SLO or API quota was tested. Live API verification must be performed separately by a human with an approved account and a small explicit budget.

## Deterministic evaluator contract

`evaluate.py` accepts `--fixture`, `--budget-usd`, and `--output`. It emits a JSON document with:

- `lesson_id`, `course_version`, `evaluator_version`, and `input_id`;
- six shared checks: `success-case`, `failure-case`, `variant-input`, `recovery-observed`, `budget-gate`, `log-redaction`;
- aggregate `evaluation` fields for cases passed, failures recovered, estimated tokens, estimated cost, budget status, and versions;
- a `logs` summary containing counts and allowed event names only.

Do not add API keys, authorization headers, raw prompts, raw telemetry, file paths, user IDs, exception text, or hidden chain-of-thought to the fixture or output.
