import { access, constants, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const pagePath = resolve(siteRoot, "dist", "module-0-environment", "index.html");

const requiredText = [
  "模块 0：环境诊断学习旅程",
  "真实问题",
  "心智模型",
  "操作前预测",
  "主工具演示",
  "本地实验",
  "故障注入与恢复",
  "迁移挑战",
  "可核验成果",
  "风险与来源卡片",
  "Windows 11",
  "PowerShell 7",
  "macOS",
  "Linux",
  "course_check",
  "environment-evidence.json",
  "课程首页",
];

const fail = (message) => {
  console.error(`Module 0 page contract failed: ${message}`);
  process.exitCode = 1;
};

try {
  await access(pagePath, constants.R_OK);
  const page = await readFile(pagePath, "utf8");
  for (const value of requiredText) {
    if (!page.includes(value)) {
      fail(`built page is missing ${value}`);
    }
  }
  if (page.includes("导入本页")) {
    fail("built page makes a page-local import promise");
  }
} catch {
  fail("built module page is missing");
}

if (process.exitCode !== 1) {
  console.log("Module 0 page contract passed");
}
