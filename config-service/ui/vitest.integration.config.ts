import { defineConfig } from "vite";

export default defineConfig({
  test: {
    include: ["src/integration/**/*.test.ts"],
  },
});
