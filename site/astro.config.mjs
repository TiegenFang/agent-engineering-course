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
          label: "Alpha 学习路径",
          items: [
            { label: "环境诊断学习旅程", link: "/module-0-environment/" },
            { label: "Git 安全修改与恢复", link: "/module-0-git-safety/" },
            { label: "Agent、模型与 Harness", link: "/module-1-agent-loop/" },
            { label: "自定义 Skill", link: "/module-7-skill/" },
            { label: "Plugin 打包与供应链审计", link: "/module-8-plugin/" },
            { label: "模块 9A：真实 MCP Server", link: "/module-9-mcp-discovery/" },
            { label: "Hooks 与 Tasks", link: "/module-10-hooks-tasks/" },
            { label: "受控多 Agent 对照", link: "/module-10-multi-agent/" },
            { label: "OpenAI Responses API 适配", link: "/module-11-openai-responses/" },
            { label: "Anthropic Messages API 迁移", link: "/module-11-anthropic-messages/" },
            { label: "科研核心结课", link: "/module-12-research-capstone/" },
            { label: "生产评测与成本控制", link: "/module-12-production/" },
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

