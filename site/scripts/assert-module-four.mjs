import { access, constants, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const pagePath = resolve(siteRoot, "dist", "module-4-project-rules", "index.html");

const requiredText = [
  "模块 4：项目指令与规则作用域",
  "真实问题",
  "心智模型",
  "操作前预测",
  "主工具演示",
  "本地实验",
  "故障注入与恢复",
  "迁移挑战",
  "可核验成果",
  "风险、版本与来源卡片",
  "AGENTS.md",
  "AGENTS.override.md",
  "CLAUDE.md",
  ".claude/rules/",
  "PowerShell 7",
  "t04-project-rules",
  "course_check",
  "agent-engineering-course/evidence",
  "不需要账号",
  "已有目标",
];

try {
  await access(pagePath, constants.R_OK);
  const page = await readFile(pagePath, "utf8");
  for (const value of requiredText) {
    if (!page.includes(value)) {
      throw new Error(`built page is missing ${value}`);
    }
  }
  if (!page.includes("未在本次制作中执行真实客户端现场验收")) {
    throw new Error("page must state the live client validation boundary");
  }
  console.log("Module 4 page contract passed");
} catch (error) {
  console.error(`Module 4 page contract failed: ${error.message}`);
  process.exitCode = 1;
}
