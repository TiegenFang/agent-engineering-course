import { access, constants, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const pagePath = resolve(siteRoot, "dist", "module-7-skill", "index.html");

const requiredText = [
  "模块 7：自定义 Skill",
  "真实问题",
  "心智模型",
  "操作前预测",
  "主工具演示",
  "本地实验",
  "故障注入与恢复",
  "迁移挑战",
  "可核验成果",
  "风险、版本与来源卡片",
  "Prompt",
  "SKILL.md",
  "references/",
  "assets/",
  "scripts/",
  "渐进披露",
  "触发",
  "误触发",
  "不可信输入",
  "t17-skill",
  "agent-engineering-course/evidence",
  "不调用模型",
  "Agent Skills specification",
  "Anthropic",
  "许可证",
];

try {
  await access(pagePath, constants.R_OK);
  const page = await readFile(pagePath, "utf8");
  for (const value of requiredText) {
    if (!page.includes(value)) throw new Error(`built page is missing ${value}`);
  }
  console.log("Module 7 page contract passed");
} catch (error) {
  console.error(`Module 7 page contract failed: ${error.message}`);
  process.exitCode = 1;
}
