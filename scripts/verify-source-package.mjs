import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { inflateRawSync } from "node:zlib";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const zipPath = resolve(root, "artifacts", "opstwin-source.zip");
const manifestPath = resolve(root, "artifacts", "opstwin-source.manifest.json");

const REQUIRED_PATHS = [
  "package.json",
  "pnpm-workspace.yaml",
  "contracts/operational-model.schema.json",
  "docs/ARCHITECTURE.md",
  "examples/support-baseline.json",
  "apps/web/package.json",
  "apps/simulation-api/pyproject.toml",
];
const FORBIDDEN_SEGMENTS = [
  "node_modules",
  ".venv",
  ".next",
  ".vercel",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  ".git",
];
const FORBIDDEN_PATTERNS = [/(^|\/)dist\//, /(^|\/)build\//, /\.egg-info\//];
const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /AKIA[0-9A-Z]{16}/,
  /xox[abpr]-[0-9A-Za-z-]{10,}/,
];

function readZipEntries(buffer) {
  const entries = [];
  const eocdSignature = 0x06054b50;
  let eocdOffset = -1;
  for (let i = buffer.length - 22; i >= 0; i--) {
    if (buffer.readUInt32LE(i) === eocdSignature) {
      eocdOffset = i;
      break;
    }
  }
  if (eocdOffset === -1) throw new Error("ZIP end-of-central-directory record not found");
  const totalEntries = buffer.readUInt16LE(eocdOffset + 10);
  const centralDirOffset = buffer.readUInt32LE(eocdOffset + 16);

  let cursor = centralDirOffset;
  for (let i = 0; i < totalEntries; i++) {
    if (buffer.readUInt32LE(cursor) !== 0x02014b50) throw new Error("Malformed central directory entry");
    const method = buffer.readUInt16LE(cursor + 10);
    const compressedSize = buffer.readUInt32LE(cursor + 20);
    const uncompressedSize = buffer.readUInt32LE(cursor + 24);
    const nameLength = buffer.readUInt16LE(cursor + 28);
    const extraLength = buffer.readUInt16LE(cursor + 30);
    const commentLength = buffer.readUInt16LE(cursor + 32);
    const localHeaderOffset = buffer.readUInt32LE(cursor + 42);
    const name = buffer.toString("utf8", cursor + 46, cursor + 46 + nameLength);
    cursor += 46 + nameLength + extraLength + commentLength;

    const localNameLength = buffer.readUInt16LE(localHeaderOffset + 26);
    const localExtraLength = buffer.readUInt16LE(localHeaderOffset + 28);
    const dataStart = localHeaderOffset + 30 + localNameLength + localExtraLength;
    const raw = buffer.subarray(dataStart, dataStart + compressedSize);
    const content = method === 0 ? Buffer.from(raw) : inflateRawSync(raw);
    if (content.length !== uncompressedSize) {
      throw new Error(`Decompressed size mismatch for ${name}`);
    }
    entries.push({ name, content });
  }
  return entries;
}

function fail(message) {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
}

function main() {
  const zipBuffer = readFileSync(zipPath);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

  const actualSha256 = createHash("sha256").update(zipBuffer).digest("hex");
  if (actualSha256 !== manifest.sha256) fail("manifest SHA-256 does not match archive bytes");
  if (zipBuffer.length !== manifest.zipBytes) fail("manifest zipBytes does not match archive size");

  const entries = readZipEntries(zipBuffer);
  const names = new Set(entries.map((entry) => entry.name));

  for (const required of REQUIRED_PATHS) {
    if (!names.has(required)) fail(`required file missing from archive: ${required}`);
  }

  for (const name of names) {
    const segments = name.split("/");
    if (segments.some((segment) => FORBIDDEN_SEGMENTS.includes(segment))) {
      fail(`forbidden path present in archive: ${name}`);
    }
    if (FORBIDDEN_PATTERNS.some((pattern) => pattern.test(name))) {
      fail(`forbidden path present in archive: ${name}`);
    }
    const baseName = segments.at(-1) ?? name;
    if (baseName.startsWith(".env") && baseName !== ".env.example") {
      fail(`unexpected environment file present in archive: ${name}`);
    }
    const homeMarker = process.env.HOME ? process.env.HOME.split("/").filter(Boolean).at(-1) : null;
    if (homeMarker && name.includes(homeMarker)) {
      fail(`archived path appears to embed a local username: ${name}`);
    }
  }

  const manifestText = JSON.stringify(manifest);
  const homeMarker = process.env.HOME ? process.env.HOME.split("/").filter(Boolean).at(-1) : null;
  if (homeMarker && manifestText.includes(homeMarker)) {
    fail("manifest embeds a local username or absolute path");
  }
  if (/[A-Za-z]:\\|\/Users\/|\/home\//.test(manifestText)) {
    fail("manifest embeds a local absolute path");
  }

  for (const entry of entries) {
    const isLikelyText = !/\.(png|jpg|jpeg|gif|ico|zip|woff2?|ttf|eot)$/i.test(entry.name);
    if (!isLikelyText) continue;
    const text = entry.content.toString("utf8");
    for (const pattern of SECRET_PATTERNS) {
      if (pattern.test(text)) fail(`potential secret pattern in archived file: ${entry.name}`);
    }
  }

  if (process.exitCode === 1) {
    console.error("Source package verification failed.");
    process.exit(1);
  }
  console.log(`Source package verification passed: ${entries.length} files, ${zipBuffer.length} bytes.`);
}

main();
