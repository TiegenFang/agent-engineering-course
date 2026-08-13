# T33 发布安全、来源、许可证与时效审计

本目录的审计入口是 `scripts/release_audit.py`。它是离线优先、可重复的发布门禁：扫描密钥形状和敏感字段，验证 `content-contract.json` 与 `source-ledger.json` 的覆盖，检查课节风险卡片和许可证字段，核对 npm manifest/lock 的精确版本，并以固定 `--as-of` 日期执行 90 天时效门禁。

## 标准命令

Windows 11 + PowerShell 7：

```powershell
python .\scripts\release_audit.py --root . --as-of 2026-08-13 --report .audit\t33-release-audit.md --json-output .audit\t33-release-audit.json
```

默认模式不联网：它会收集并检查 URL 语法，但明确把远程链接是否存活标记为 `review`，不会把网络不可用误报为通过或失败。维护者在批准网络范围后才运行：

```powershell
python .\scripts\release_audit.py --root . --as-of 2026-08-13 --online --max-url-checks 100 --report .audit\t33-release-audit-online.md
```

`--online` 只执行有界 HTTP HEAD 检查；它仍不查询 npm/PyPI 最新版本、不代替人工许可证判断，也不验证付费 API、MCP、Codex 或 Claude Code 现场行为。网络审计的权限范围是读取公开 URL 的响应头；恢复方式是停止脚本并删除本地 `.audit` 输出，不会修改课程内容。

## 结果解释

- `failed`：存在静态门禁失败，例如疑似凭据、缺少来源/许可证/风险字段、manifest 与 lock 不一致、宽泛 workflow 权限或超过 90 天的课节核验日期。
- `passed`：没有静态失败；仍应阅读 `review` 项。离线模式一定会留下“链接存活未检查”和可能的“source pinned_version 无可解析日期”复核项。
- `review`：需要人工或批准网络路径复核，不是自动通过证明。

报告只保留命中规则、相对路径、行号和元数据，不输出疑似秘密、prompt、原始数据或文件内容。该工具不是完整安全扫描器、渗透测试、法律意见或密钥历史清理工具；若命中疑似凭据，必须人工确认并按真实密钥轮换/撤销流程处理。
