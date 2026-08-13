# Agent 工程入门

从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战。

本仓库统一承载中文课程站、设备遥测练习、课程检查器和规划文档。当前版本为 Foundation，先建立可构建、可测试、可追溯的课程基础。

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

课程正文与图解采用 CC BY 4.0；自有代码、练习脚手架和检查器采用 MIT。第三方依赖和资产保留各自许可证，详见 `THIRD_PARTY_NOTICES.md` 与来源账本。

