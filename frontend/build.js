// Bundles every frontend/src/<page>.ts into ../static/js/<page>.js.
// Run via `npm run build` (also runs `tsc --noEmit` first for type-checking).
// This file is plain JS on purpose -- esbuild's own Node API scripts are
// conventionally written this way even in TypeScript projects, since it's
// build tooling, not application code.
const esbuild = require("esbuild");
const fs = require("fs");
const path = require("path");

const srcDir = path.join(__dirname, "src");
const outDir = path.join(__dirname, "..", "static", "js");

fs.mkdirSync(outDir, { recursive: true });

const entryPoints = fs
  .readdirSync(srcDir)
  .filter((f) => f.endsWith(".ts") && f !== "types.ts")
  .map((f) => path.join(srcDir, f));

for (const entry of entryPoints) {
  const name = path.basename(entry, ".ts");
  esbuild.buildSync({
    entryPoints: [entry],
    outfile: path.join(outDir, `${name}.js`),
    bundle: true,
    format: "iife",
    target: "es2020",
    sourcemap: false,
    logLevel: "info",
  });
}

console.log(`Built ${entryPoints.length} bundle(s) into ${outDir}`);
