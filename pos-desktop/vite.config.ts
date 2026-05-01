import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vite renderer config for Electron POS shell.
// - base: './' so the built bundle uses relative URLs that work via
//   BrowserWindow.loadFile() (file:// protocol).
// - build.outDir: 'dist/renderer' — Electron loads from there in prod.
// - server.port: 5173 (dev), Electron loadURL('http://localhost:5173').
//
// NEXT_PUBLIC_* env replacement: the @shared/* code paths still reference
// process.env.NEXT_PUBLIC_CLERK_* (they're shared with the Next.js frontend
// which inlines those at build time). Vite does NOT replace process.env.*
// by default, so without the define block below the Clerk publishable key
// stays undefined at runtime — CLERK_KEY_CONFIGURED becomes false and the
// app shows the "Authentication not configured" error screen instead of
// initialising. Inline every NEXT_PUBLIC_* the build environment provides.
const inlineNextPublicEnv = (): Record<string, string> => {
  const inlined: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (key.startsWith("NEXT_PUBLIC_") && value !== undefined) {
      inlined[`process.env.${key}`] = JSON.stringify(value);
    }
  }
  // Always emit a stable NODE_ENV — Clerk's SDK branches on it.
  inlined["process.env.NODE_ENV"] = JSON.stringify(
    process.env.NODE_ENV ?? "production",
  );
  return inlined;
};

export default defineConfig({
  plugins: [react()],
  base: "./",
  define: inlineNextPublicEnv(),
  resolve: {
    alias: {
      "@pos": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "../frontend/src"),
      // Clerk's Next.js SDK pulls in next/navigation hooks (usePathname,
      // useRouter, useSearchParams) which only work inside a Next.js app.
      // The pos-desktop renderer is a pure Vite/React-Router bundle, so we
      // alias to @clerk/react — the framework-agnostic SDK that exposes
      // the same ClerkProvider / useAuth / useClerk / useUser surface
      // auth-bridge.tsx actually uses. Without this alias the bundle
      // tries to call useRouter() at boot, which throws under file://
      // and produces the v3.0.x black screen.
      "@clerk/nextjs": "@clerk/react",
    },
    // Force a single instance of every React-context-bearing package
    // across both pos-desktop/node_modules and frontend/node_modules.
    // Without this, Vite bundles two copies — the first one provides
    // ReactCurrentDispatcher to the main chunk, the second is what
    // separately-chunked code (e.g. the `headers-*.js` Clerk chunk)
    // imports, and useState() on the second instance returns null
    // because no dispatcher is set. Mirrors frontend/vitest.config.ts
    // dedupe list so dev/test/prod all share one React.
    dedupe: [
      "react",
      "react-dom",
      "react/jsx-runtime",
      "react/jsx-dev-runtime",
      "swr",
      "react-router-dom",
      "@tanstack/react-query",
      "zustand",
      "next-themes",
      "sonner",
      "focus-trap-react",
      "qrcode.react",
    ],
  },
  build: {
    outDir: "dist/renderer",
    emptyOutDir: true,
    target: "chrome120",
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "happy-dom",
    globals: true,
    include: ["__tests__/**/*.test.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
  },
});
