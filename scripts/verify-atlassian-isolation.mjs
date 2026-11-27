import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const forbidden = [/@forge\//, /atlassian-forge/, /developer\.atlassian\.com/];
const scanRoots = [
  resolve(root, "apps/simulation-api/app"),
  resolve(root, "apps/web/lib"),
  resolve(root, "apps/web/components"),
  resolve(root, "contracts"),
];

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) walk(path, files);
    else files.push(path);
  }
  return files;
}

let failures = 0;
for (const scanRoot of scanRoots) {
  for (const file of walk(scanRoot)) {
    if (!/\.(py|ts|tsx|js|json)$/.test(file)) continue;
    const rel = relative(root, file).replaceAll("\\", "/");
    if (rel.startsWith("apps/simulation-api/app/integrations/")) continue;
    const content = readFileSync(file, "utf8");
    for (const pattern of forbidden) {
      if (pattern.test(content)) {
        console.error(`FAIL: ${relative(root, file)} matches ${pattern}`);
        failures += 1;
      }
    }
  }
}

if (failures > 0) {
  process.exit(1);
}
console.log("OK: OpsTwin Core and contracts do not depend on Atlassian-specific modules.");
