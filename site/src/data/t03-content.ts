export const t03Content = {
  course: {
    name: "Agent 工程入门",
    subtitle: "从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战",
    positioning: "面向科研与企业团队中技术型初学者的中文 Agent 工程课程",
    version: "0.1.0-foundation",
    coreDuration: "20–24 小时",
    advancedDuration: "8–12 小时",
  },
  hero: {
    label: "可见方向评审 · Foundation → Alpha",
    title: "把 Agent 能力，变成可核验的工作流。",
    summary:
      "从 Windows 11 与 PowerShell 7 的安全基线开始，在真实仓库里走过澄清、计划、执行、恢复、验证与交付；再把方法迁移到另一种 Coding Agent 和最小 API Agent loop。",
    cta: "打开能力地图",
    secondaryCta: "查看方向说明",
  },
  capabilityLayers: [
    {
      index: "01",
      title: "模型与 API",
      description: "先看模型响应、工具请求、结果回填和停止条件，建立最小 Agent loop。",
      evidence: "一张 loop 标注图 + 一次观察—行动—证据追踪",
    },
    {
      index: "02",
      title: "指令与规则",
      description: "把模糊请求改写成目标、上下文、约束、输出契约和验收标准。",
      evidence: "模糊版/工程版指令对照及失败证据",
    },
    {
      index: "03",
      title: "上下文与状态",
      description: "选择、压缩、刷新和交接工作集，识别遗漏、污染与失真。",
      evidence: "上下文预算实验与交接包",
    },
    {
      index: "04",
      title: "Memory",
      description: "决定什么值得保存、由谁保存、何时更新或删除，避免把历史全存下来。",
      evidence: "Memory 设计、污染实验与纠错记录",
    },
    {
      index: "05",
      title: "工具与 MCP",
      description: "区分 Host、Client、Server、Tool、Resource 与 Prompt，并用真实 transport 验证。",
      evidence: "能力清单、调用结果、权限与故障恢复证据",
    },
    {
      index: "06",
      title: "Skill 与 Plugin",
      description: "把稳定知识、流程、脚本与扩展打包，审计触发、版本、来源和供应链风险。",
      evidence: "自定义 Skill 与 Plugin 清单审计",
    },
    {
      index: "07",
      title: "编排与多 Agent",
      description: "比较单 Agent 基线与受控并行，计算时间、Token、冲突和验证成本。",
      evidence: "单 Agent / 多 Agent 对照实验",
    },
    {
      index: "08",
      title: "评测、安全、成本与运维",
      description: "给结果设预算、权限、人工确认点和可复现验收，让交付可以被复盘。",
      evidence: "风险与验证卡片 + 结课交付 rubric",
    },
  ],
  lessons: [
    {
      id: "M0",
      title: "前置技能补给站",
      question: "如何建立 Windows 11、PowerShell 7、编辑器、Python、账号与 Git 安全基线？",
      artifact: "环境诊断报告、首个基线提交、恢复演练记录",
      platform: "桌面实验",
    },
    {
      id: "M1",
      title: "Agent、模型与 Harness",
      question: "Agent 为什么不只是“模型加 Prompt”？最小循环如何运转？",
      artifact: "Agent loop 标注图、一次观察—行动—证据追踪",
      platform: "阅读 + 交互",
    },
    {
      id: "M2",
      title: "Agent 指令工程",
      question: "如何把模糊请求变成可执行、可验收的工程指令？",
      artifact: "模糊版/工程版对照及失败证据",
      platform: "桌面实验",
    },
    {
      id: "M3",
      title: "Codex 与 Claude Code 安全起步",
      question: "两类 Coding Agent 如何读仓库、规划、执行、复核和停手？",
      artifact: "一次主工具任务 + 另一工具的变化输入迁移",
      platform: "桌面实验",
    },
  ],
  proofPoints: [
    "每课留下文件、配置、测试输出、运行证据或提交记录。",
    "网页不记录“已读”作为成果；课程检查器只在本机检查并输出匿名 JSON。",
    "Codex 与 Claude Code 交替主讲：一个工具完成主实验，另一个工具承担迁移挑战。",
    "科研与企业轨道共享能力目标，再分别交付可复现研究工作流或 Issue-to-PR 工程工作流。",
  ],
  boundaries: [
    ["网站", "site"],
    ["练习", "labs"],
    ["检查器", "checker"],
    ["规划与来源", "docs"],
  ],
  reviewNote:
    "这是 T03 的 reviewable design demo。三版共享真实课程内容与能力地图，供维护者选择、混合或否决；尚未定为最终生产主题。",
} as const;

export const t03Products = [
  {
    id: "codex",
    name: "Codex",
    company: "OpenAI",
    kind: "官方文本 mark + 官方 wordmark 来源",
    officialUrl: "https://openai.com/index/introducing-the-codex-app/",
    brandUrl: "https://openai.com/brand/",
    uiStatus: "不嵌入 UI 截图；只链接官方产品页面",
  },
  {
    id: "claude-code",
    name: "Claude Code",
    company: "Anthropic",
    kind: "Anthropic 官方 press kit Slate SVG",
    officialUrl: "https://code.claude.com/docs/en/overview",
    brandUrl: "https://www.anthropic.com/news",
    logoPath: "brands/claude-code-logo-slate.svg",
    uiStatus: "不嵌入 UI 截图；官方 press kit 资产只作 logo",
  },
] as const;

export const t03DirectionIds = [
  "quiet-grid",
  "editorial-manual",
  "evidence-console",
] as const;
