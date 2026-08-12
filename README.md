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

课程正文与图解采用 CC BY 4.0；自有代码、练习脚手架和检查器采用 MIT。第三方依赖和资产保留各自许可证，详见 `THIRD_PARTY_NOTICES.md` 与来源账本。

