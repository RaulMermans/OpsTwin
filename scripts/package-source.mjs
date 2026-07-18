import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { createDeterministicZip } from "./zip-writer.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = resolve(root, "artifacts");
const zipPath = resolve(outputDir, "opstwin-source.zip");
const manifestPath = resolve(outputDir, "opstwin-source.manifest.json");
const MAX_ZIP_BYTES = 15 * 1024 * 1024;

// Defense in depth over .gitignore/git ls-files: a path containing any of
// these segments must never enter the archive even if it were ever tracked.
const FORBIDDEN_SEGMENTS = [
  "node_modules",
  ".venv",
  ".next",
  ".vercel",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  "coverage",
  "artifacts",
  ".git",
];
const FORBIDDEN_PATTERNS = [
  /(^|\/)dist\//,
  /(^|\/)build\//,
  /\.egg-info\//,
  /\.tsbuildinfo$/,
  /(^|\/)pip-[^/]+\//,
  /(^|\/)pytest-of-[^/]+\//,
  /(^|\/)build-env-[^/]+\//,
];

function isForbidden(relativePath) {
  const segments = relativePath.split("/");
  if (segments.some((segment) => FORBIDDEN_SEGMENTS.includes(segment))) return true;
  return FORBIDDEN_PATTERNS.some((pattern) => pattern.test(relativePath));
}

function listCandidateFiles() {
  const output = execFileSync(
    "git",
    ["ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    { cwd: root, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
  );
  return output.split("\0").filter(Boolean);
}

function main() {
  mkdirSync(outputDir, { recursive: true });

  const candidates = listCandidateFiles();
  const excludedByCategory = {};
  const entries = [];
  let uncompressedBytes = 0;

  for (const relativePath of candidates) {
    if (isForbidden(relativePath)) {
      const category = relativePath.split("/")[0];
      excludedByCategory[category] = (excludedByCategory[category] ?? 0) + 1;
      throw new Error(
        `Refusing to package forbidden path "${relativePath}". ` +
          "git ls-files should already exclude it via .gitignore; investigate before rerunning.",
      );
    }
    const absolutePath = resolve(root, relativePath);
    const content = readFileSync(absolutePath);
    entries.push({ path: relativePath, content });
    uncompressedBytes += content.length;
  }

  entries.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));

  const zipBuffer = createDeterministicZip(entries);
  if (zipBuffer.length > MAX_ZIP_BYTES) {
    throw new Error(
      `Source package is ${zipBuffer.length} bytes, exceeding the ${MAX_ZIP_BYTES}-byte threshold. ` +
        "Document a justified source-asset reason before raising MAX_ZIP_BYTES.",
    );
  }
  writeFileSync(zipPath, zipBuffer);

  const sha256 = createHash("sha256").update(zipBuffer).digest("hex");
  const manifest = {
    generatedAt: "deterministic", // no wall-clock timestamp: manifest content stays reproducible
    fileCount: entries.length,
    uncompressedSourceBytes: uncompressedBytes,
    zipBytes: zipBuffer.length,
    sha256,
    excludedCategoryCounts: excludedByCategory,
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

  console.log(`Packaged ${entries.length} files, ${zipBuffer.length} bytes -> ${zipPath}`);
  console.log(`Manifest -> ${manifestPath}`);
  console.log(`SHA-256 ${sha256}`);
}

main();
