import type { Config } from "tailwindcss";

/**
 * Tailwind CSS v4 — RTL/LTR variants are NATIVE.
 *
 * The Egypt-ready foundation plan (PR 4, Task 6, #604) originally called for
 * installing @tailwindcss/rtl. That package targets Tailwind v3 and does NOT
 * exist on npm for v4. Tailwind v4 ships `rtl:` and `ltr:` variants natively
 * via its built-in variant system — no plugin install needed.
 *
 * Use `rtl:me-4` / `ltr:ms-4` etc. directly in any component. The `dir`
 * attribute on <html> (set by layout.tsx via isRtl(locale)) drives the variants.
 *
 * Plugins in v4 are registered in globals.css via `@plugin "..."` (not here).
 * This config file is retained for content-path scanning only.
 */
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
};

export default config;
