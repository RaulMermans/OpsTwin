import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const canonicalPath = resolve(root, "examples", "product", "support-operations-baseline.json");
const runtimePath = resolve(root, "apps", "web", "lib", "templates", "support-operations-baseline.json");
const supportTsPath = resolve(root, "apps", "web", "lib", "templates", "support.ts");

function fail(message) {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
}

function parseJson(path, label) {
  let text;
  try {
    text = readFileSync(path, "utf8");
  } catch (error) {
    fail(`${label} could not be read (${path}): ${error.message}`);
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    fail(`${label} is not valid JSON (${path}): ${error.message}`);
    return null;
  }
}

function main() {
  const canonical = parseJson(canonicalPath, "canonical example");
  const runtime = parseJson(runtimePath, "web runtime baseline");

  if (canonical !== null && runtime !== null) {
    const canonicalText = JSON.stringify(canonical);
    const runtimeText = JSON.stringify(runtime);
    if (canonicalText !== runtimeText) {
      fail(
        "apps/web/lib/templates/support-operations-baseline.json is not semantically identical to " +
          "examples/product/support-operations-baseline.json",
      );
    }
  }

  let supportTs;
  try {
    supportTs = readFileSync(supportTsPath, "utf8");
  } catch (error) {
    fail(`support.ts could not be read (${supportTsPath}): ${error.message}`);
    supportTs = "";
  }

  if (supportTs && !supportTs.includes('from "./support-operations-baseline.json"')) {
    fail("apps/web/lib/templates/support.ts must import the local ./support-operations-baseline.json runtime asset");
  }
  if (supportTs && supportTs.includes("../../../../examples/")) {
    fail("apps/web/lib/templates/support.ts must not import from the .vercelignore-excluded ../../../../examples/ path");
  }

  if (process.exitCode === 1) {
    console.error("Vercel runtime packaging verification failed.");
    process.exit(1);
  }
  console.log("Vercel runtime packaging verification passed: runtime baseline matches canonical example and support.ts owns its runtime import.");
}

main();
