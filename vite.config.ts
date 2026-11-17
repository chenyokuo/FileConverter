import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwind from "@tailwindcss/vite";
export default defineConfig({
  plugins: [react(), tailwind()],
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      ignored: [
        "**/.tools/**",
        "**/.venv/**",
        "**/src-tauri/target/**",
        "**/src-tauri/binaries/**",
        "**/src-tauri/notices/**",
        "**/src-tauri/bundled-engines/**",
        "**/src-tauri/webview-runtime/**",
        "**/release/**",
        "**/vendor/**",
        "**/test-results/**",
      ],
    },
  },
  clearScreen: false,
});
