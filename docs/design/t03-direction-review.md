# T03 三套视觉方向评审入口

这是 Issue #4 的 reviewable design demo。三条 route 共享 `site/src/data/t03-content.ts` 的首页、能力地图、M0–M3 课节、产品适配和可核验证据；它们是候选方向，不是已经选定的生产主题。

## 预览入口

- [方向索引](/agent-engineering-course/t03/)
- [Quiet Grid / 可读校准](/agent-engineering-course/t03/quiet-grid/)
- [Editorial Manual / 现实迁移](/agent-engineering-course/t03/editorial-manual/)
- [Evidence Console / 现场证据](/agent-engineering-course/t03/evidence-console/)

浏览器验收截图（1440×900 桌面视口与约 390px 移动视口，整页截图）保存在 `artifacts/t03-screenshots/`：

可复现的浏览器命令、运行时边界和每张截图的 SHA-256/Chromium 版本见 `artifacts/t03-screenshots/manifest.json` 与 `t03-browser-verification.md`。

| 方向 | 桌面 | 移动 |
| --- | --- | --- |
| Quiet Grid | `quiet-grid-desktop.png` | `quiet-grid-mobile.png` |
| Editorial Manual | `editorial-manual-desktop.png` | `editorial-manual-mobile.png` |
| Evidence Console | `evidence-console-desktop.png` | `evidence-console-mobile.png` |

## 选择线索

### Quiet Grid / 可读校准

稳妥、克制、信息优先。浅纸白底、清楚的横向规则、双栏英雄区和原生 `details` 能力地图适合第一次接触 Agent 的学习者。它的优点是长文可扫描、响应式退化简单、键盘路径短；代价是品牌记忆点和戏剧性较弱。适合成为公共课程站的基础骨架。

### Editorial Manual / 现实迁移

以出版物和现场手册为参照。暖纸色、窄阅读列、左侧目录轨、章节序号和“八层地图 / 对应证据”切换，把课程当成一本可以带到真实仓库旁边使用的操作手册。它强调迁移阅读节奏和章节上下文；代价是首屏的密度和滚动长度更高，需确认新手不会把目录误读成额外任务。

### Evidence Console / 现场证据

大胆定制、证据驱动。深石墨底、巨大衬线标题、琥珀状态线、可选能力层和 READ / VERIFY 模式，直接把“边界、状态、证据”做成页面交互。它最适合强调课程不是 Prompt 清单，而是一条能留下产物的工程旅程；代价是长时间阅读的舒适度较低，适合从 Quiet Grid 或 Editorial Manual 借入正文节奏。

## 建议的混合方式

维护者应先选一套信息架构作为主骨架，再只借用一到两个可解释的交互/节奏元素：例如采用 Quiet Grid 的首页与基础可读性，加入 Editorial Manual 的章节目录，再吸收 Evidence Console 的 `READ / VERIFY` 证据切换。不要把三套颜色、标题、组件全部叠加，否则会损失方向差异，也会使课程视觉身份看起来像临时拼贴。

## 共同边界

Codex、Claude Code、OpenAI 和 Anthropic 只以真实文本、官方链接和按原样使用的官方 Claude Code Slate logo 出现。官方 UI 截图没有取得明确的再发布许可，因此页面保留“官方 UI 截图待许可核准”说明，不使用伪造终端、虚构数据或假产品面板。产品事实、品牌约束、许可证与未验证事项分别记录于 `t03-product-facts.md`、`t03-brand-spec.md` 和 `docs/sources/source-ledger.json`。
