import { readFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const README_MAX_BYTES = 150 * 1024;
const PRODUCTION_HOST = "ops-twin.vercel.app";

const REQUIRED_FILES = [
  "SECURITY.md",
  "CONTRIBUTING.md",
  "CHANGELOG.md",
  "README.md",
  "docs/REFERENCES.md",
  "docs/PUBLIC_CLAIM_REGISTER.md",
  "docs/PUBLIC_RELEASE_CHECKLIST.md",
  "docs/PORTFOLIO_CONTENT_PACK.md",
  "docs/SCREENSHOT_PLAN.md",
  "docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md",
  ".github/ISSUE_TEMPLATE/bug_report.yml",
  ".github/pull_request_template.md",
];

const STALE_CLAIM_PATTERNS = [
  /vercel deployment remains proposed/i,
  /no vercel project is linked/i,
  /preview verification is deferred/i,
  /preview validation remains (intentionally )?deferred/i,
  /frontend testing is blocked/i,
  /repository has no commits/i,
  /guided flow is undeployed/i,
  /sprint 12\.1 remains incomplete/i,
  /adr-014 remains proposed/i,
];

const PROHIBITED_PHRASES = [
  /enterprise-ready/i,
  /industry-leading/i,
  /guaranteed improvement/i,
  /customer-proven/i,
  /real-world validated/i,
  /fully autonomous/i,
  /accurate prediction/i,
  /production-grade at scale/i,
];

const SECRET_PATTERNS = [
  /AKIA[0-9A-Z]{16}/,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /sk-[a-zA-Z0-9]{20,}/,
  /ghp_[a-zA-Z0-9]{20,}/,
  /xox[baprs]-[a-zA-Z0-9-]{10,}/,
];

// Requires at least one real path character after the username segment so a
// redacted/illustrative placeholder like `C:\Users\...` (three literal dots)
// does not falsely match — that pattern is documentation of a historical
// bug, not a real local filesystem path.
const LOCAL_PATH_PATTERN = /\/Users\/[a-zA-Z0-9_-][a-zA-Z0-9_.-]*\/|C:\\Users\\[a-zA-Z0-9_-][a-zA-Z0-9_.-]*\\/;

// Built from parts so this file's own source doesn't trip its own check.
const SHARE_TOKEN_MARKER = ["_vercel", "share"].join("_");

// Historical evidence documents may legitimately retain a developer's local
// path or a dated "this was deferred at the time" claim. Current-state
// documents must not.
const HISTORICAL_PATH_ALLOWLIST = [/^docs\/sprints\//, /^docs\/adrs\//, /^docs\/superpowers\//];

let failures = 0;

function fail(message) {
  console.error(`FAIL: ${message}`);
  failures += 1;
}

function ok(message) {
  console.log(`OK: ${message}`);
}

function gitLsFiles() {
  // --cached (already tracked) plus --others --exclude-standard (new, not
  // gitignored) so newly-added-but-not-yet-committed files are scanned too —
  // otherwise a brand-new file could ship with a secret or stale claim that
  // this check would silently miss simply because it hadn't been staged yet.
  const result = spawnSync("git", ["ls-files", "--cached", "--others", "--exclude-standard"], {
    cwd: root,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    fail(`git ls-files failed: ${result.stderr || result.error?.message || "unknown error"}`);
    return [];
  }
  return [...new Set(result.stdout.split("\n").filter(Boolean))];
}

function readTracked(relativePath) {
  try {
    return readFileSync(resolve(root, relativePath), "utf8");
  } catch {
    return null;
  }
}

function checkRequiredFiles() {
  for (const relativePath of REQUIRED_FILES) {
    try {
      statSync(resolve(root, relativePath));
      ok(`required file exists: ${relativePath}`);
    } catch {
      fail(`required file missing: ${relativePath}`);
    }
  }
}

function checkReadmeSize() {
  const size = statSync(resolve(root, "README.md")).size;
  if (size > README_MAX_BYTES) {
    fail(`README.md is ${size} bytes, over the ${README_MAX_BYTES}-byte threshold`);
  } else {
    ok(`README.md is ${size} bytes (under ${README_MAX_BYTES})`);
  }
}

function checkReadmeImagePaths() {
  const readme = readTracked("README.md") ?? "";
  const matches = [...readme.matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)];
  if (matches.length === 0) {
    fail("README.md has no embedded images");
    return;
  }
  for (const match of matches) {
    const imagePath = match[1];
    if (/^https?:\/\//.test(imagePath)) {
      fail(`README.md image path is not relative: ${imagePath}`);
      continue;
    }
    try {
      statSync(resolve(root, imagePath));
      ok(`README image resolves: ${imagePath}`);
    } catch {
      fail(`README image path does not resolve on disk: ${imagePath}`);
    }
  }
}

function checkReadmeProductionUrls() {
  const readme = readTracked("README.md") ?? "";
  const urls = [...readme.matchAll(/https?:\/\/[^\s)"'`]+/g)].map((m) => m[0]);
  const nonProductionAppUrls = urls.filter(
    (url) => url.includes("vercel.app") && !url.includes(PRODUCTION_HOST),
  );
  if (nonProductionAppUrls.length > 0) {
    fail(`README.md references a non-production *.vercel.app URL: ${nonProductionAppUrls.join(", ")}`);
  } else {
    ok(`README.md's vercel.app references all use the production host (${PRODUCTION_HOST})`);
  }
}

function checkReferencesFile() {
  const references = readTracked("docs/REFERENCES.md") ?? "";
  if (references.includes("https://github.com/filipecalegario/awesome-vibe-coding.git")) {
    ok("docs/REFERENCES.md contains the required Awesome Vibe Coding reference");
  } else {
    fail("docs/REFERENCES.md is missing the required Awesome Vibe Coding reference");
  }
}

function checkLicenseWording() {
  const files = gitLsFiles();
  const hasLicenseFile = files.some((f) => /^LICENSE(\.[A-Za-z]+)?$/.test(f));
  const readme = readTracked("README.md") ?? "";
  const hasDisclosure = readme.includes("No software license has been granted yet");
  if (hasLicenseFile) {
    fail("a LICENSE file exists but this sprint's process assumes none — re-check the license gate manually before shipping");
  } else if (!hasDisclosure) {
    fail("no LICENSE file exists, but README.md is missing the required no-license disclosure sentence");
  } else {
    ok("no LICENSE file exists and README.md carries the required disclosure sentence");
  }
}

function checkNoSecretsOrLocalPaths() {
  const files = gitLsFiles();
  for (const relativePath of files) {
    if (relativePath.endsWith(".png") || relativePath.endsWith(".jpg") || relativePath.endsWith(".webp")) continue;
    if (/(^|\/)\.env(\..+)?$/.test(relativePath) && relativePath !== ".env.example") {
      fail(`tracked .env-style file: ${relativePath}`);
      continue;
    }
    const content = readTracked(relativePath);
    if (content === null) continue;

    for (const pattern of SECRET_PATTERNS) {
      if (pattern.test(content)) {
        fail(`possible secret pattern (${pattern}) in tracked file: ${relativePath}`);
      }
    }
    // This script's own source is exempt: it necessarily names the literal
    // token it's searching for.
    if (relativePath !== "scripts/verify-public-release.mjs" && content.includes(SHARE_TOKEN_MARKER)) {
      fail(`temporary Vercel share-link token found in tracked file: ${relativePath}`);
    }
    const isHistorical = HISTORICAL_PATH_ALLOWLIST.some((allow) => allow.test(relativePath));
    if (!isHistorical && LOCAL_PATH_PATTERN.test(content)) {
      fail(`absolute local filesystem path found in current-state file: ${relativePath}`);
    }
  }
  ok(`scanned ${files.length} tracked files for secrets, .env files, _vercel_share tokens, and local paths`);
}

function checkStaleClaims() {
  const currentStateDocs = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/ROADMAP.md",
    "docs/VERCEL_DEPLOYMENT.md",
  ];
  for (const relativePath of currentStateDocs) {
    const content = readTracked(relativePath);
    if (content === null) continue;
    for (const pattern of STALE_CLAIM_PATTERNS) {
      if (pattern.test(content)) {
        fail(`stale current-state claim (${pattern}) found in ${relativePath}`);
      }
    }
  }
  ok("checked current-state documents for known stale deployment/testing claims");
}

function checkProhibitedPhrases() {
  const files = gitLsFiles().filter(
    (f) => f === "README.md" || (f.startsWith("docs/") && f.endsWith(".md")),
  );
  for (const relativePath of files) {
    const content = readTracked(relativePath);
    if (content === null) continue;
    for (const pattern of PROHIBITED_PHRASES) {
      if (pattern.test(content)) {
        fail(`prohibited marketing phrase (${pattern}) found in ${relativePath}`);
      }
    }
  }
  ok(`checked ${files.length} markdown files for prohibited marketing phrases`);
}

function main() {
  checkRequiredFiles();
  checkReadmeSize();
  checkReadmeImagePaths();
  checkReadmeProductionUrls();
  checkReferencesFile();
  checkLicenseWording();
  checkNoSecretsOrLocalPaths();
  checkStaleClaims();
  checkProhibitedPhrases();

  if (failures > 0) {
    console.error(`Public-release verification failed with ${failures} finding(s).`);
    process.exit(1);
  }
  console.log("Public-release verification passed.");
}

main();
