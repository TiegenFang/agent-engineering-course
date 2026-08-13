# 模块 7：`evidence-research` Skill 离线实验

这个目录提供一个课程原创、可审计的 Agent Skill 样例。它面向“整理合成设备遥测主张并留下来源卡片”的重复任务，展示 `SKILL.md`、`references/`、`assets/`、`scripts/` 和完成验证之间的关系。

实验不调用模型、Codex、Claude Code、API、MCP、网络或真实研究数据。页面中的触发矩阵是固定教学夹具；本地 Python 脚本只规范化合成输入。不能把页面通过或脚本通过写成某个真实客户端已经自动触发了 Skill。

## 目录合同

```text
evidence-research/
├─ SKILL.md
├─ references/
│  ├─ evidence-schema.md
│  └─ source-policy.md
├─ assets/
│  └─ telemetry-sample.json
└─ scripts/
   └─ normalize-evidence.py
```

`SKILL.md` 的 `name` 必须与目录名一致；`description` 同时写“做什么”和“何时使用”。正文只保留任务步骤和资源导航，详细证据规则放在 `references/`，合成输入放在 `assets/`，可执行规范化逻辑放在 `scripts/`。

## PowerShell 7 主路径

```powershell
$skillRoot = (Join-Path (Get-Location) 'labs\skill\evidence-research')
Get-Content -LiteralPath (Join-Path $skillRoot 'SKILL.md')
python (Join-Path $skillRoot 'scripts\normalize-evidence.py') `
  --input (Join-Path $skillRoot 'assets\telemetry-sample.json') `
  --output (Join-Path $env:TEMP 'agent-course-skill-normalized.json')
Get-Content -LiteralPath (Join-Path $env:TEMP 'agent-course-skill-normalized.json')
```

脚本输出是 `evidence-research/v1` 的状态摘要，包含合成 claim ID、来源计数和固定检查结果，不包含输入路径。输出目录应放在课程工作区之外的临时位置，避免把运行产物误提交。

## 练习任务与证据

1. 阅读 `SKILL.md`，指出 `inputs`、`references`、`assets`、`scripts` 和 `validation` 在方法中的位置。
2. 运行脚本两次，比较输出是否相同；把“相同”作为确定性证据，而不是把模型回答当作证据。
3. 在网页夹具中依次运行 `complete`、`missing-source`、`conflicting-evidence`、`untrusted-instruction`，记录每个状态。
4. 运行正向/负向触发夹具，确认研究任务匹配，而问候和一次性算式不匹配。
5. 导出 `t17-skill-evidence.json`，交给 `python -m course_check check t17-skill`。

证据检查器只接受固定 ID、状态、场景和布尔安全标记。它会重新推导场景期望，不接受把所有结果手写成 `passed` 的捷径。

## 安全与许可边界

- 输入和来源是合成的；不要替换成真实研究、企业或个人数据。
- 先审阅 Skill 内的 Markdown、脚本、网络需求、写入路径和许可证，再复制到任何客户端。
- 这个目录没有 `allowed-tools`、动态上下文注入或自动外部上传；其他产品的扩展字段不能当成开放规范要求。
- 原创实验代码采用 MIT；课程页和原创说明采用 CC BY 4.0；没有复制 Anthropic 官方 Skill 的代码或资产。
