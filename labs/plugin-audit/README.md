# T18 Plugin 打包与供应链审计

这是模块 8 的离线证据边界。浏览器组件使用 `site/src/lib/plugin-audit.mjs` 的纯函数审计三个课程夹具；夹具只包含脱敏 manifest 元数据，不下载 marketplace、不执行命令或脚本、不启动 hook/MCP、不调用真实 Coding Agent。

## 本地检查

在 Windows 11 + PowerShell 7 中，从课程工作区运行：

```powershell
Set-Location -LiteralPath .\checker
python -m course_check check t18-plugin-audit --root .. --evidence-file ..\t18-plugin-audit-evidence.json --json
```

没有证据文件时可以先做结构检查，结果是 `partial`：

```powershell
python -m course_check check t18-plugin-audit --root .. --json
```

## 浏览器导出的匿名形状

页面导出既有 `agent-engineering-course/evidence` v1 envelope，也附带只含稳定 ID 的 `audit`：

```json
{
  "contract": "agent-engineering-course/evidence",
  "contract_version": "1",
  "course_version": "2.0.0",
  "lesson_id": "t18-plugin-audit",
  "result": "passed",
  "anonymous": true,
  "checked_on": "2026-08-13",
  "summary": "所有必需证据均已通过。",
  "evidence": [
    {"id": "manifest-reviewed", "result": "passed"},
    {"id": "component-composition-mapped", "result": "passed"},
    {"id": "supply-chain-fields-audited", "result": "passed"},
    {"id": "unsafe-package-contained", "result": "passed"},
    {"id": "lifecycle-reviewed", "result": "passed"},
    {"id": "offline-no-install", "result": "passed"}
  ],
  "audit": {
    "version": "1",
    "runs": [
      {
        "id": "run-1",
        "fixture": "needs-review",
        "status": "do-not-install",
        "findings": ["license-unknown", "network-enabled"],
        "components": ["skill", "command", "hook", "mcp"],
        "inspected": ["origin", "version", "license", "permissions", "network", "dependencies", "lifecycle", "execution"],
        "lifecycle": ["upgrade", "rollback", "uninstall"],
        "offline": true,
        "executed": false
      }
    ],
    "observed_findings": ["license-unknown", "network-enabled"],
    "observed_components": ["command", "hook", "mcp", "skill"],
    "observed_fields": ["dependencies", "execution", "license", "lifecycle", "network", "origin", "permissions", "version"],
    "observed_lifecycle": ["rollback", "uninstall", "upgrade"]
  }
}
```

`course_check` 会从每次运行的 stable fields 重新推导六项检查，不信任调用者手写的 `result` 或检查状态。它会拒绝未知 fixture、未知组件/风险 ID、重复运行 ID、缺字段、执行标记为 true、非离线记录、不兼容课程版本及敏感字段。原始 manifest、路径、命令、依赖版本、网络响应和凭据不会进入网页交换文档。

## 课程边界

- **Skill** 是可复用任务方法；**脚本**是可能产生副作用的执行文件；**Tool** 是 Agent 可调用的外部能力；**Plugin** 承担能力包的发现、组合、版本和治理。
- 目录形状和市场可发现性只能说明“存在一个候选包”，不能证明许可证、来源、权限、依赖或安全。
- 生产环境的 Plugin 安装必须遵循实际客户端官方文档，由人确认 scope、权限、网络、许可证和回滚路径。本实验故意不伪造该现场过程。
