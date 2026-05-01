import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vite renderer config for Electron POS shell.
// - base: './' so the built bundle uses relative URLs that work via
//   BrowserWindow.loadFile() (file:// protocol).
// - build.outDir: 'dist/renderer' — Electron loads from there in prod.
// - server.port: 5173 (dev), Electron loadURL('http://localhost:5173').
export default defineConfig({
  plugins: [react()],
  base: "./",
  resolve: {
    alias: {
      "@pos": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "../frontend/src"),
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
