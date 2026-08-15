# 工程工作日志

按日期倒序记录课程的工程实施、验证与发布决策。课程内容层面的领域语言见 [CONTEXT.md](../CONTEXT.md)；本日志只记录工程事实与维护者决定。

## 2026-08-16：v1.0.0 发布

**发布决定（维护者指令记录）**：维护者指示正式推出 v1。按 [课程总体规划 §11.2](./course-plan.md) 的发布门槛逐项核对时存在一项冲突：T34（跨平台与真实工具现场验收）与 T12（8–12 人试学审计）为 `ready-for-human` 项，尚未由真人执行。维护者选择带边界发布，处置如下：

- 已满足的门槛：内容契约（T33 审计校验）、Windows 11 + PowerShell 7 自动化实测（`npm run verify` 全绿，含 155 项检查器测试、构建与桌面/390px 浏览器契约）、密钥/来源/许可证/90 天时效审计（0 失败）、无障碍自动化门（0 失败）、检查器正反样例。
- 未满足且延后的门槛：真实 Codex/Claude Code/MCP/付费 API 现场行为、macOS 或 Linux 跨平台复核、读屏/键盘/对比度人工复核、试学审计。以上全部在 issue [#35](https://github.com/TiegenFang/agent-engineering-course/issues/35) 与 [#13](https://github.com/TiegenFang/agent-engineering-course/issues/13) 保持开启，课节内继续如实标注「未验证」。
- 结论：v1.0.0 是**自动化门槛全绿 + 现场人工验收延后**的发布；不得对外表述为「完整无障碍认证」或「真实工具全部实测通过」。

**本次交付**：

1. T11 试学包（`site/src/content/docs/trial-guide.mdx`）：招募画像、三项试学任务、观察记录表、Alpha 指标阈值与已知边界，随站点发布。
2. T35 下一步学习地图（`site/src/content/docs/next-steps.mdx`）：v1 明确不做主题的先修关系导航，链接以官方真源域为主。
3. 侧边栏补全：原导航缺 9 个课节（模块 2、3×2、4、5×2、6、9B、11 离线 loop），重组为按模块分组的完整目录并加入附录区。
4. GitHub Pages 部署：新增 `deploy-pages.yml`（显式最小权限 `contents: read` + `pages: write` + `id-token: write`），启用 build_type=workflow 的 Pages 站点。
5. 每周维护自动化：新增 `weekly-maintenance.yml`，周一运行两项离线审计并以 `--online` 有界核对链接存活，只报告不重写正文（落实规划 §11.1）。
6. 版本提升：`0.1.0-alpha` → `1.0.0` 统一替换 30 个文件（course-version、npm manifest/lock、checker 测试常量、站点库回退值、7 个课节版本卡片重新锁定；核验日期保持 2026-08-13 不变），`released_on` 为 2026-08-16。
7. 验证：本地 `npm run verify` 全绿；T32/T33 审计以 2026-08-16 日期重跑通过；CI（ubuntu + windows 矩阵）通过；部署后线上 URL 可访问。
8. 发布证据：tag `v1.0.0` 与 GitHub Release，说明含上述边界声明。

## 2026-08-15：工作区清理与 tracker 对齐

1. worktree 清理：确认 25 个 ticket worktree 的未合并内容后，将 8 个脏工作区的未提交改动以 `wip: preserve ...` 提交到各自分支留档（ticket-23/24/29/30 为源码草稿，其余为截图），随后移除全部 worktree，释放约 3.98 GB / 235,407 个文件；26 个本地分支全部保留。
2. 建立并实测 node_modules 共享方案：worktree 通过目录 junction 链接主工作区中央副本（模块解析与 astro CLI 穿过 junction 验证通过）；操作约定固化到 [worktree-workflow.md](./agents/worktree-workflow.md)。
3. T32 收尾：修复审计测试夹具缺失的 Search 标记，155 项测试全绿，无障碍静态审计门合入 CI，关闭 #33。
4. T33 验收：以 2026-08-15 日期实跑发布审计（0 失败/3 条复核项），关闭 #34。
5. tracker 对齐：核实 #23–#32（T22–T31）内容已在 main 且验证通过，逐条附证据关闭；发现 #12（T11）试学包从未制作，保持开启并记录缺口。
6. 状态文档对齐：AGENTS.md、课程总体规划、README 的「当前状态」从过时的 Alpha 描述更新为真实阶段；修正「未连接 remote」的过时说明。

## 2026-08-13：内容层实现（由 Codex 完成）

Foundation、Alpha 纵向切片、Core Beta（模块 4–10）、进阶线（模块 11–12）与 T33 审计脚本在此日由 Codex 按 ticket worktree 流程实现并合入 main，共 68 个提交；详细历史见 git log 与各课节版本卡片，此处不重复记录。
