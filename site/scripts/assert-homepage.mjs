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
  ...Object.values(contract.boundaries),
];

const missing = requiredText.filter((value) => !homepage.includes(value));
if (missing.length > 0) {
  console.error(`Homepage is missing contract values: ${missing.join(", ")}`);
  process.exitCode = 1;
} else {
  console.log(`Homepage contract check passed for ${contract.course_version}`);
}
