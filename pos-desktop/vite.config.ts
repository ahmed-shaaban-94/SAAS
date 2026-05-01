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
