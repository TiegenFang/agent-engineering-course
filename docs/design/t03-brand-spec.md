# T03 Brand / Asset Spec

> 采集日期：2026-08-13
> 资产完整度：部分（logo 已核验；UI 截图未取得明确再发布许可）
> 使用范围：Issue #4 的三套方向评审，不代表课程最终品牌规范。

## 核心资产

### OpenAI / Codex

- 真实产品 mark：`Codex` 文本，旁注 `OpenAI`；适用于课程中的“Codex 主讲/迁移”语境。
- 官方 wordmark 来源：[OpenAI Design Guidelines](https://openai.com/brand/)；页面中的官方 CDN 资源作为可选远程引用：`https://images.ctfassets.net/kftzwdyauwt9/2fkAIT3PbTRytKTBx9cx8o/229bc28cb338565fe735d8935abc801f/OpenAI_Wordmark_Gif.gif?fm=webp&q=90&w=3840`。
- 使用约束：按原样使用；只在直接相关的 OpenAI/Codex 说明中出现；不拉伸、重绘、加效果、融入课程 logo；不暗示 OpenAI 赞助、合作或背书。OpenAI marks 仍归 OpenAI 所有，当前页面的使用条款优先于本文件。
- 本 demo 的离线降级：如果远程 wordmark 无法加载，保留可见的 `OpenAI` / `Codex` 文本 mark 和官方链接，不显示破图图标。

### Anthropic / Claude Code

- 本地资产：`site/public/brands/claude-code-logo-slate.svg`。
- 来源：Anthropic 官方 Newsroom 的 `Download press kit`（官方 press kit 条目名：`Anthropic media resources/Anthropic logos/Claude logos/2 Claude Code logo/SVG/Claude Code logo - Slate.svg`）。
- 许可/条款：官方 press kit / 商标资产，未声明以 MIT、Apache 或 CC 重新许可；使用仅限直接介绍 Claude Code 的课程语境，保留原始 SVG 内容和比例，不改色、不裁切、不暗示 Anthropic 认可本项目。发布前应重新查看 Anthropic 当前 press-kit/brand 条款。
- 本 demo 使用 Slate 版本；深底方向为原始 logo 提供浅色承托区，保留实际深色字与赤陶橙 mark，并提供文字链接，避免在暗底上人为反色或制造低对比度。

## 辅助色与排印

颜色是方向性实验，不把方向色冒充品牌规范：

- OpenAI 官方 wordmark 只作为黑白资产；不从截图臆测产品 UI 色。
- Claude Code 官方 Slate SVG 中可观察到深色字 `#151514` 与赤陶橙 `#d97757`。方向二以此作为小面积锚点，不满屏铺橙。
- Quiet Grid 使用中性纸白、炭黑和低饱和青绿，强调可读性；Editorial Manual 使用纸白、墨色和赤陶橙，强调出版节奏；Evidence Console 使用石墨底、暖白字和琥珀/珊瑚状态线，避免 GitHub-dark 深蓝加紫色 glow。
- 西文 display 预设 `Newsreader` / `Geist`，中文优先 `Noto Serif SC` / `Noto Sans SC`，本地未打包字体时安全回退到 `Georgia`、`Songti SC`、`Microsoft YaHei` 等；正文基准 16–18px，中文行高 1.7–1.8。

## UI / 图片策略

- 未纳入 Codex 或 Claude Code 官方 UI 截图；没有明确许可的页面图像不进入课程包。
- 不用 CSS 剪影、手绘 SVG、stock photo、生成插画、假终端或假 dashboard 替代真实产品界面。
- 页面使用文字说明“官方 UI 截图待许可核准”，并链接官方页面；这是诚实占位，不是产品数据展示。

## 禁区

- 不使用紫色渐变万能公式、emoji 图标、虚构统计、虚构用户评价、圆角卡片加左彩色边框。
- 不把方向 demo 的临时色、字体或布局描述为 OpenAI、Anthropic、Codex 或 Claude Code 的官方品牌规范。
- 不使用 logo 作为课程自有 logo，不制作“Powered by OpenAI/Anthropic”式背书，不把第三方产品 mark 与课程身份混成一体。
