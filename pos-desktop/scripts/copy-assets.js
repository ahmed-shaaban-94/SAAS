// Copies non-TypeScript assets into dist/ after tsc build.
const fs = require("fs");
const path = require("path");

const pairs = [
  ["electron/db/schema.sql", "dist/electron/db/schema.sql"],
];

for (const [src, dst] of pairs) {
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
  console.log(`copied ${src} -> ${dst}`);
}
