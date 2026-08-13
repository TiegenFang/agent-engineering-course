import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(scriptDirectory, "../..");
const lab = await readFile(resolve(repoRoot, "labs/project-rules/README.md"), "utf8");
const script = await readFile(resolve(repoRoot, "labs/project-rules/project-rules.ps1"), "utf8");
const page = await readFile(
  resolve(repoRoot, "site/src/content/docs/module-4-project-rules.mdx"),
  "utf8",
);

for (const phrase of [
  "AGENTS.md",
  "AGENTS.override.md",
  "CLAUDE.md",
  "@AGENTS.md",
  ".claude/rules/",
  "故障注入与恢复",
  "匿名 evidence",
]) {
  assert.match(`${lab}\n${script}\n${page}`, new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
}
assert.match(script, /拒绝复用已有 LabPath/);
assert.match(script, /课程仓库之外/);
assert.match(script, /trace_version = "1"/);
assert.doesNotMatch(page, /sk-[A-Za-z0-9]{8,}/);
assert.doesNotMatch(lab, /C:\\Users\\/);
console.log("Project rules Node contract passed");
