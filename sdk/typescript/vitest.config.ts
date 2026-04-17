import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    testTimeout: 30_000,
    // Note: Vite injects BASE_URL="/" into process.env, so integration tests
    // use AGP_BASE_URL to specify the server address instead.
  },
});
