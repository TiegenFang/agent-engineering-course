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

