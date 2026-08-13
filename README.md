# Agent 工程入门

从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战。

本仓库统一承载中文课程站、设备遥测练习、课程检查器和规划文档。当前版本为 Alpha 纵向切片，在 Foundation 基础上加入模块 0 环境诊断学习旅程。

## 工作区边界

- `site`：Astro、Starlight 与 MDX 静态课程站
- `labs`：贯穿课程的设备遥测练习
- `checker`：本地课程检查器及匿名结果契约
- `docs`：课程规划、ADR、规格、来源账本和维护记录

## 本地验证

在 Windows 11 与 PowerShell 7 中：

```powershell
python -m unittest discover -s checker\tests -v
npm.cmd install
npm.cmd run check
npm.cmd run build
npm.cmd run test:site
```

## 导出本地证据

在 `checker` 目录中运行首个 Foundation 检查，并把匿名结果写到课程工作区：

```powershell
python -m course_check check t01-foundation --root .. --output ..\evidence.json
```

随后在课程首页选择 `evidence.json` 导入。检查器结果只包含课程版本、课节身份、结果和证据摘要；网页只在浏览器本地保存学习记录，并支持导出和清除。

## 模块 0：环境诊断

在 Windows 11 + PowerShell 7 中，先运行只读环境诊断：

```powershell
pwsh -NoProfile -File .\labs\module-0\diagnose-environment.ps1 `
  -EditorReady -GitHubReady -CodingAgent codex `
  -OutputPath .\environment-diagnostic.json
```

它只记录命令可见性、版本状态和你主动确认的布尔状态，不联网、不读取源码或身份变量，也不把绝对路径写进 JSON。再在 `checker` 目录运行：

```powershell
python -m course_check check t05-environment `
  --root .. `
  --environment-file ..\environment-diagnostic.json `
  --output ..\environment-evidence.json `
  --json
```

只有 `environment-evidence.json` 是可导入网页的匿名 evidence contract；两个本地 JSON 文件已加入 `.gitignore`，不要提交。macOS/Linux 的 `python3`、`command -v` 和 Shell 差异见模块 0 页面，正式实验主路径仍是 Windows 11 + PowerShell 7。

## 模块 2：Agent 指令工程

模块 2 的本地证据命令为：

```powershell
python -m course_check check t03-agent-instruction --root .. --evidence-file ..\t03-agent-instruction-evidence.json --output ..\t03-agent-instruction-checked.json
```

它只读取学员主动指定的匿名 JSON；不会把编辑的指令、路径、密钥或原始遥测上传到网站。

课程正文与图解采用 CC BY 4.0；自有代码、练习脚手架和检查器采用 MIT。第三方依赖和资产保留各自许可证，详见 `THIRD_PARTY_NOTICES.md` 与来源账本。

