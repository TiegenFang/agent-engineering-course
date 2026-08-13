import { access, constants, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const pagePath = resolve(siteRoot, "dist", "module-6-memory", "index.html");

const requiredText = [
  "模块 6：受控 Memory",
  "真实问题",
  "心智模型",
  "操作前预测",
  "主工具演示",
  "本地实验",
  "故障注入与恢复",
  "迁移挑战",
  "可核验成果",
  "风险、版本与来源卡片",
  "短期 Memory",
  "长期 Memory",
  "外部 Memory",
  "上下文窗口",
  "摘要",
  "检索",
  "显式注入",
  "陈旧",
  "污染",
  "删除",
  "敏感信息",
  "t16-memory",
  "memory-ledger-v1",
  "agent-engineering-course/evidence",
  "course_check",
  "model_calls",
  "network_calls",
];

try {
  await access(pagePath, constants.R_OK);
  const page = await readFile(pagePath, "utf8");
  for (const value of requiredText) {
    if (!page.includes(value)) throw new Error(`built page is missing ${value}`);
  }
  if (page.includes("sk-test-only") || page.includes("C:\\Users\\")) {
    throw new Error("built page contains a sensitive fixture value");
  }
  if (!page.includes("不调用真实模型") || !page.includes("未验证真实 Codex")) {
    throw new Error("page must state offline and live-validation boundaries");
  }
  console.log("Module 6 page contract passed");
} catch (error) {
  console.error(`Module 6 page contract failed: ${error.message}`);
  process.exitCode = 1;
}
