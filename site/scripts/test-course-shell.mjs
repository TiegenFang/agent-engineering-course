import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("课程首页使用统一课程壳并公开学习路径", () => {
  const page = read("src/content/docs/index.mdx");
  const shell = read("src/components/CourseShell.astro");

  assert.match(page, /<CourseShell\s*\/>/);
  assert.match(shell, /技术型 Agent 初学者/);
  assert.match(shell, /核心课程结业线/);
  assert.match(shell, /进阶实战线/);
  assert.match(shell, /阅读、概念和本地 mock\/checker 路径免费/);
  assert.match(shell, /module-0-environment/);
  assert.match(shell, /module-0-git-safety/);
  assert.match(shell, /module-1-agent-loop/);
});

test("能力地图明确分离稳定知识与工具适配并提供 READ/VERIFY", () => {
  const map = read("src/components/CapabilityMap.astro");

  assert.match(map, /稳定知识层八层能力/);
  assert.match(map, /稳定知识层/);
  assert.match(map, /工具适配层/);
  assert.match(map, /data-mode="read"/);
  assert.match(map, /data-mode="verify"/);
  assert.match(map, /aria-live="polite"/);
  assert.match(map, /prefers-reduced-motion/);
});

test("Starlight 导航暴露已实现的 Alpha 学习路径", () => {
  const config = readFileSync(join(workspaceRoot, "site", "astro.config.mjs"), "utf8");

  assert.match(config, /sidebar:/);
  assert.match(config, /module-0-environment/);
  assert.match(config, /module-0-git-safety/);
  assert.match(config, /module-1-agent-loop/);
  assert.match(config, /能力地图/);
});
