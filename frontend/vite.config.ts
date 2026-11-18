import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // One .env at the repo root; Vite only exposes VITE_* variables to the client.
  envDir: "..",
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // Same-origin API in dev, so the httpOnly guest cookie works without CORS.
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    // Unit tests cover the pure logic in src/lib; pages and components are covered by the Playwright suite.
    coverage: {
      provider: "v8",
      include: ["src/lib/**/*.ts"],
      exclude: ["src/lib/**/*.test.ts", "src/lib/api.ts"],
      reporter: ["text-summary"],
      thresholds: { lines: 80, functions: 80, branches: 70 },
    },
  },
});
