import { readFile } from "node:fs/promises";
import { access } from "node:fs/promises";
import { constants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const distRoot = resolve(siteRoot, "dist");
const sharedDataPath = resolve(siteRoot, "src", "data", "t03-content.ts");

const directions = [
  "quiet-grid",
  "editorial-manual",
  "evidence-console",
];

const requiredSharedContent = [
  "Agent 工程入门",
  "Codex",
  "Claude Code",
  "20–24 小时",
  "8–12 小时",
  "模型与 API",
  "工具与 MCP",
  "前置技能补给站",
  "风险与验证卡片",
];

const fail = (message) => {
  console.error(`Design directions contract failed: ${message}`);
  process.exitCode = 1;
};

const sharedData = await readFile(sharedDataPath, "utf8").catch(() => "");
if (!sharedData) {
  fail("shared content data is missing");
} else {
  for (const value of requiredSharedContent) {
    if (!sharedData.includes(value)) {
      fail(`shared content is missing ${value}`);
    }
  }
}

for (const direction of directions) {
  const sourcePath = resolve(siteRoot, "src", "pages", "t03", `${direction}.astro`);
  const source = await readFile(sourcePath, "utf8").catch(() => "");
  if (!source.includes("prefers-reduced-motion")) {
    fail(`/t03/${direction}/ source does not declare reduced-motion handling`);
  }

  const pagePath = resolve(distRoot, "t03", direction, "index.html");
  try {
    await access(pagePath, constants.R_OK);
  } catch {
    fail(`missing built direction /t03/${direction}/`);
    continue;
  }

  const page = await readFile(pagePath, "utf8");
  for (const value of requiredSharedContent) {
    if (!page.includes(value)) {
      fail(`/t03/${direction}/ is missing shared content ${value}`);
    }
  }

  if (!page.includes('aria-label="跳到主要内容"')) {
    fail(`/t03/${direction}/ is missing the keyboard skip link`);
  }
}

if (process.exitCode !== 1) {
  console.log(`Design directions contract passed for ${directions.length} variants`);
}
