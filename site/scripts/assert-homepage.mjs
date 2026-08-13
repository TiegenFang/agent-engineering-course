import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const workspaceRoot = resolve(siteRoot, "..");
const contractPath = resolve(workspaceRoot, "course-version.json");
const homepagePath = resolve(siteRoot, "dist", "index.html");

const contract = JSON.parse(await readFile(contractPath, "utf8"));
const homepage = await readFile(homepagePath, "utf8");
const requiredText = [
  contract.course.name,
  contract.course.positioning,
  contract.course_version,
  contract.course.core_duration,
  contract.course.advanced_duration,
  "受众",
  "核心课程结业线",
  "进阶实战线",
  "成本",
  "免费",
  "稳定知识层",
  "工具适配层",
  "READ",
  "VERIFY",
  "移动阅读路径",
  "桌面实战路径",
  "module-0-environment",
  "module-0-git-safety",
  "module-1-agent-loop",
  ...Object.values(contract.boundaries),
];

const missing = requiredText.filter((value) => !homepage.includes(value));
if (missing.length > 0) {
  console.error(`Homepage is missing contract values: ${missing.join(", ")}`);
  process.exitCode = 1;
} else {
  console.log(`Homepage course-shell contract check passed for ${contract.course_version}`);
}
