import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("进度向导保持零网络并覆盖无 JavaScript 与触控场景", () => {
  const wizard = read("src/components/ProgressWizard.astro");

  assert.match(wizard, /aria-live="polite"/);
  assert.match(wizard, /<noscript>/);
  assert.match(wizard, /min-height: 44px/);
  assert.doesNotMatch(wizard, /\bfetch\s*\(/);
  assert.doesNotMatch(wizard, /XMLHttpRequest/);
  assert.doesNotMatch(wizard, /sendBeacon/);
});

test("进度向导用普通话解释匿名证据与浏览器本地记录", () => {
  const wizard = read("src/components/ProgressWizard.astro");

  assert.match(wizard, /匿名 JSON 文件/);
  assert.match(wizard, /浏览器本地/);
  assert.match(wizard, /为什么要这么麻烦？/);
  assert.match(wizard, /不上传你的源码/);
});

test("进度向导提供与 README 一致的入门课节命令", () => {
  const wizard = read("src/components/ProgressWizard.astro");
  const readme = readFileSync(join(workspaceRoot, "README.md"), "utf8");

  assert.match(wizard, /course_check/);
  assert.match(wizard, /t01-foundation/);
  assert.match(wizard, /t05-environment/);
  assert.match(wizard, /t03-agent-instruction/);

  const foundationCommand = readme.match(/python -m course_check check t01-foundation[^\n]*/)?.[0] ?? "";
  assert.ok(foundationCommand.includes("--output"), "README 未找到 Foundation 检查命令");
  const wizardSource = wizard.replace(/\\\\/g, "\\");
  assert.ok(
    wizardSource.includes(foundationCommand),
    "向导的 Foundation 命令必须与 README「导出本地证据」一致",
  );
});

test("进度向导引导到现有导入入口而不是重复实现导入逻辑", () => {
  const wizard = read("src/components/ProgressWizard.astro");

  assert.match(wizard, /#evidence-loop-title/);
  assert.match(wizard, /data-evidence-status/);
  assert.doesNotMatch(wizard, /type="file"/);
});

test("课程首页同时挂载课程壳与进度向导", () => {
  const page = read("src/content/docs/index.mdx");

  assert.match(page, /<CourseShell\s*\/>/);
  assert.match(page, /<ProgressWizard\s*\/>/);
  assert.match(page, /import ProgressWizard from '\.\.\/\.\.\/components\/ProgressWizard\.astro';/);
});
