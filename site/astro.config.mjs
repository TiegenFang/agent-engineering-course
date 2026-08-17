import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://tiegenfang.github.io",
  base: "/agent-engineering-course",
  trailingSlash: "always",
  integrations: [
    starlight({
      title: "Agent 工程入门",
      description: "从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战",
      customCss: ["./src/styles/custom.css"],
      locales: {
        root: { label: "简体中文", lang: "zh-CN" },
      },
      defaultLocale: "root",
      sidebar: [
        {
          label: "开始学习",
          items: [
            { label: "课程首页", link: "/" },
            { label: "能力地图", link: "/#map" },
          ],
        },
        {
          label: "网页端起步（无需安装）",
          items: [
            { label: "W1 · 什么是 Agent", link: "/start-1-what-is-agent/" },
            { label: "W2 · 与模型对话的正确姿势", link: "/start-2-dialogue-basics/" },
            { label: "W3 · API key 与第一次真实调用", link: "/start-3-api-key-chat/" },
            { label: "W4 · 从网页到终端", link: "/start-4-web-to-terminal/" },
          ],
        },
        {
          label: "前置与核心起步（模块 0–3）",
          items: [
            { label: "环境诊断学习旅程", link: "/module-0-environment/" },
            { label: "Git 安全修改与恢复", link: "/module-0-git-safety/" },
            { label: "Agent、模型与 Harness", link: "/module-1-agent-loop/" },
            { label: "Agent 指令工程", link: "/module-2-agent-instruction/" },
            { label: "Codex 安全仓库任务", link: "/module-3-codex-task/" },
            { label: "Claude Code 迁移挑战", link: "/module-3-claude-migration/" },
          ],
        },
        {
          label: "规则、上下文与 Memory（模块 4–6）",
          items: [
            { label: "项目指令与规则作用域", link: "/module-4-project-rules/" },
            { label: "上下文预算模拟器", link: "/module-5-context-budget/" },
            { label: "上下文压缩恢复与交接", link: "/module-5-context-recovery/" },
            { label: "受控 Memory", link: "/module-6-memory/" },
          ],
        },
        {
          label: "Skill、Plugin 与 MCP（模块 7–9）",
          items: [
            { label: "自定义 Skill", link: "/module-7-skill/" },
            { label: "Plugin 打包与供应链审计", link: "/module-8-plugin/" },
            { label: "模块 9A：真实 MCP Server 发现", link: "/module-9-mcp-discovery/" },
            { label: "模块 9B：MCP 调用权限与恢复", link: "/module-9b-mcp-call/" },
          ],
        },
        {
          label: "编排、API 与结课（模块 10–12）",
          items: [
            { label: "Hooks 与 Tasks", link: "/module-10-hooks-tasks/" },
            { label: "受控多 Agent 对照", link: "/module-10-multi-agent/" },
            { label: "离线最小 Agent loop", link: "/module-11-agent-loop/" },
            { label: "OpenAI Responses API 适配", link: "/module-11-openai-responses/" },
            { label: "Anthropic Messages API 迁移", link: "/module-11-anthropic-messages/" },
            { label: "生产评测与成本控制", link: "/module-12-production/" },
            { label: "科研核心结课", link: "/module-12-research-capstone/" },
            { label: "科研进阶 API 结课", link: "/module-12-research-api-capstone/" },
            { label: "企业核心结课", link: "/module-12-enterprise-capstone/" },
            { label: "企业进阶 API 结课", link: "/module-12-enterprise-api/" },
            { label: "双轨结课集成", link: "/module-12-capstone-integration/" },
          ],
        },
        {
          label: "附录",
          items: [
            { label: "试学指南与观察表", link: "/trial-guide/" },
            { label: "下一步学习地图", link: "/next-steps/" },
            { label: "案例参考库", link: "/case-library/" },
          ],
        },
      ],
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/TiegenFang/agent-engineering-course",
        },
      ],
    }),
  ],
});

