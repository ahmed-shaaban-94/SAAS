import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/__tests__/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/components/**", "src/hooks/**", "src/lib/**"],
      exclude: ["src/__tests__/**"],
      thresholds: { statements: 4, branches: 4, functions: 4, lines: 4 },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@pos": path.resolve(__dirname, "../pos-desktop/src"),
      "@shared": path.resolve(__dirname, "./src"),
    },
    // Force a single instance of every React-context-bearing package across
    // both pos-desktop/node_modules and frontend/node_modules. Without this,
    // the package gets bundled twice and useContext returns null when a
    // pos-desktop file calls a hook that the frontend test rendered.
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
    ],
  },
});
