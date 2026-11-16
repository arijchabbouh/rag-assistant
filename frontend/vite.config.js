import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The page calls the API with relative paths ("/ask"): in production api.py serves this page itself, so it is the
// same origin. In development (npm run dev, port 5173) Vite forwards these paths to the API, by default
// http://localhost:8000 (API_PROXY_TARGET in .env.local to change it): still the same origin, no CORS needed.
const API_PATHS = ["/ask", "/feedback", "/health"];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.API_PROXY_TARGET || "http://localhost:8000";
  return {
    plugins: [react()],
    // Reuse the project's public/ folder (LOGO.jpg) instead of keeping a second copy.
    publicDir: "../public",
    server: {
      port: 5173,
      strictPort: true,
      proxy: Object.fromEntries(API_PATHS.map((path) => [path, { target, changeOrigin: true }])),
    },
  };
});
