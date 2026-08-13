import { readFile } from "node:fs/promises";
import { access } from "node:fs/promises";
import { constants } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const distRoot = resolve(siteRoot, "dist");
const workspaceRoot = resolve(siteRoot, "..");
const courseVersionPath = resolve(workspaceRoot, "course-version.json");
const sharedDataPath = resolve(siteRoot, "src", "data", "t03-content.ts");

const directions = [
  "quiet-grid",
  "editorial-manual",
  "evidence-console",
];

const requiredSharedContent = [
  "Agent 工程入门",
  "从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战",
  "Codex",
  "Claude Code",
  "20–24 小时",
  "8–12 小时",
  "模型与 API",
  "工具与 MCP",
  "前置技能补给站",
  "风险与验证卡片",
];

const courseVersion = JSON.parse(await readFile(courseVersionPath, "utf8"));

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

const indexSourcePath = resolve(siteRoot, "src", "pages", "t03", "index.astro");
const indexSource = await readFile(indexSourcePath, "utf8").catch(() => "");
if (!indexSource.includes("t03Content.course.subtitle")) {
  fail("/t03/ source does not render the shared course subtitle");
}
if (!indexSource.includes("prefers-reduced-motion")) {
  fail("/t03/ source does not declare reduced-motion handling");
}

const indexPagePath = resolve(distRoot, "t03", "index.html");
try {
  await access(indexPagePath, constants.R_OK);
  const indexPage = await readFile(indexPagePath, "utf8");
  for (const value of [
    "同一份真实课程内容",
    "从 Codex 与 Claude Code，到 Memory、Skills、MCP 与 API 实战",
    "等待维护者视觉选择",
    courseVersion.course_version,
  ]) {
    if (!indexPage.includes(value)) {
      fail(`/t03/ is missing index content ${value}`);
    }
  }
  for (const direction of directions) {
    if (!indexPage.includes(`/agent-engineering-course/t03/${direction}/`)) {
      fail(`/t03/ is missing a route to ${direction}`);
    }
  }
} catch {
  fail("missing built direction index /t03/");
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
  for (const value of [...requiredSharedContent, courseVersion.course_version]) {
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
