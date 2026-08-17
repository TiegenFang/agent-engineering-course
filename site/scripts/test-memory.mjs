import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  MemoryStateError,
  buildMemoryEvidence,
  createMemorySession,
  injectMemoryPollution,
  runCompleteMemorySession,
  runMemoryAction,
} from "../src/lib/memory-engine.mjs";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const workspaceRoot = resolve(siteRoot, "..");

test("完整 Memory journey 是确定性的且不调用模型或网络", () => {
  const first = runCompleteMemorySession();
  const second = runCompleteMemorySession();
  assert.deepEqual(first, second);
  assert.equal(first.status, "complete");
  assert.equal(first.stages.length, 6);
  assert.equal(first.pollutionInjected, true);
  assert.equal(first.pollutionRecovered, true);
  const evidence = buildMemoryEvidence(first, {
    courseVersion: "2.0.0",
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.experiment.model_calls, 0);
  assert.equal(evidence.experiment.network_calls, 0);
  assert.equal(evidence.experiment.stages.length, 6);
  assert.equal(evidence.evidence.length, 13);
});

test("Memory journey 要求先设计和更新，再隔离污染", () => {
  const session = createMemorySession();
  assert.throws(() => runMemoryAction(session, "recall"), MemoryStateError);
  let current = session;
  for (const action of ["design", "write", "recall", "stale-update"]) {
    current = runMemoryAction(current, action);
  }
  current = injectMemoryPollution(current);
  assert.equal(current.pollutionInjected, true);
  current = runMemoryAction(current, "pollution");
  assert.equal(current.pollutionRecovered, true);
});

test("页面、实验说明和组件保留隐私/真实调用边界", async () => {
  const [page, lab, component] = await Promise.all([
    readFile(resolve(workspaceRoot, "site/src/content/docs/module-6-memory.mdx"), "utf8"),
    readFile(resolve(workspaceRoot, "labs/memory/README.md"), "utf8"),
    readFile(resolve(workspaceRoot, "site/src/components/MemoryLab.astro"), "utf8"),
  ]);
  const combined = `${page}\n${lab}\n${component}`;
  for (const phrase of [
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
    "敏感",
    "model_calls",
    "network_calls",
    "t16-memory",
  ]) {
    assert.match(combined, new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.doesNotMatch(combined, /sk-[A-Za-z0-9]{8,}/);
  assert.doesNotMatch(combined, /C:\\Users\\/);
  assert.match(component, /data-memory-action="inject-pollution"/);
  assert.match(component, /data-export-memory-evidence/);
});
