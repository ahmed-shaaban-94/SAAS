#!/usr/bin/env node
/**
 * Bundle budget checker — fails the build if any JS chunk exceeds its threshold.
 *
 * Run after `next build`:
 *   node scripts/check-bundle-budget.js
 *
 * Thresholds (uncompressed bytes — Next.js outputs uncompressed; gzip is ~30-35%):
 *   - Any single page chunk:  500 KB
 *   - framework chunk:        200 KB  (React + React DOM)
 *   - main chunk:             150 KB
 *   - Total first-load JS:    750 KB  (Next.js shows this in build output)
 *
 * These numbers are intentionally generous to avoid blocking normal development.
 * Tighten them as the codebase matures and code-splitting improves.
 */

import { readdirSync, statSync, readFileSync, existsSync } from "fs";
import { join } from "path";

const NEXT_DIR = join(process.cwd(), ".next");
const CHUNKS_DIR = join(NEXT_DIR, "static", "chunks");

// Thresholds in bytes (uncompressed)
const BUDGETS = [
  {
    pattern: /^framework-/,
    label: "framework (React + React DOM)",
    maxBytes: 200 * 1024,
  },
  {
    pattern: /^main-/,
    label: "main chunk",
    maxBytes: 150 * 1024,
  },
  {
    pattern: /\.js$/,
    label: "any single chunk",
    maxBytes: 500 * 1024,
  },
];

if (!existsSync(CHUNKS_DIR)) {
  console.error(`[bundle-budget] ERROR: .next/static/chunks not found.`);
  console.error(`  Run 'next build' first, then re-run this script.`);
  process.exit(1);
}

let failures = 0;
const files = readdirSync(CHUNKS_DIR).filter((f) => f.endsWith(".js"));

for (const file of files) {
  const filePath = join(CHUNKS_DIR, file);
  const bytes = statSync(filePath).size;
  const kb = (bytes / 1024).toFixed(1);

  for (const budget of BUDGETS) {
    if (budget.pattern.test(file) && bytes > budget.maxBytes) {
      const maxKb = (budget.maxBytes / 1024).toFixed(0);
      console.error(
        `[bundle-budget] FAIL: ${file} (${kb} KB) exceeds ${maxKb} KB limit for "${budget.label}"`
      );
      failures++;
    }
  }
}

// Also check build-manifest for total first-load JS
const buildManifestPath = join(NEXT_DIR, "build-manifest.json");
if (existsSync(buildManifestPath)) {
  const manifest = JSON.parse(readFileSync(buildManifestPath, "utf-8"));
  const commonChunks = manifest.devFiles ?? manifest.pages?.["/_app"] ?? [];
  const totalBytes = commonChunks.reduce((sum, chunkPath) => {
    const absPath = join(NEXT_DIR, chunkPath.replace(/^\/_next\//, ""));
    return existsSync(absPath) ? sum + statSync(absPath).size : sum;
  }, 0);

  const FIRST_LOAD_BUDGET = 750 * 1024;
  if (totalBytes > FIRST_LOAD_BUDGET) {
    const kb = (totalBytes / 1024).toFixed(1);
    const maxKb = (FIRST_LOAD_BUDGET / 1024).toFixed(0);
    console.error(
      `[bundle-budget] FAIL: Total first-load JS (${kb} KB) exceeds ${maxKb} KB limit`
    );
    failures++;
  }
}

if (failures === 0) {
  console.log(`[bundle-budget] PASS: All ${files.length} chunks within budget.`);
} else {
  console.error(`[bundle-budget] ${failures} budget violation(s) found.`);
  console.error(`  Run 'npm run build:analyze' to identify large dependencies.`);
  process.exit(1);
}
