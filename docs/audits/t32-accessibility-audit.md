# T32 移动端与无障碍发布审计

T32 的自动化入口是：

```powershell
npm run audit:accessibility
```

它运行 `scripts/accessibility_audit.py` 的离线静态检查，并与 CI 中已经存在的 Playwright 桌面/移动端路线验证组合（`verify-course-shell.mjs`、`verify-instruction.mjs`、`verify-context-budget.mjs` 等）。静态门检查：

- 共享 CSS 是否保留 `:focus-visible`、`prefers-reduced-motion`、响应式媒体查询、网格重排和触摸目标尺寸；
- 课程组件与页面中的按钮/表单控件是否有可发现的名称；
- 图片和 iframe 是否提供替代文本或标题；
- 动态组件是否声明 live/status 输出，并记录没有 no-JavaScript fallback 的人工复核项；
- 首页 shell 是否保留地标、导航命名、搜索/移动阅读路径文案。

现有浏览器脚本已经覆盖主页和代表性课节的桌面/390px 移动视口、横向溢出、减少动态效果、跳转到内容、键盘焦点、表单标签、动态状态、无 JavaScript fallback 与 44px 触摸目标；新增静态门避免这些契约只存在于脚本而没有源文件回归检查。

`audit:accessibility` 是发布前的回归门，不是 WCAG 2.2 AA 认证。T34 仍必须在 Windows 11 + PowerShell 7 以及 macOS 或 Linux 上完成键盘、焦点顺序、缩放/重排、对比度、非颜色编码、读屏和真实工具现场复核，并记录日期、版本、费用和阻塞。任何人工复核未完成时，不得把 T32 或 v1 写成“完整无障碍认证”。
