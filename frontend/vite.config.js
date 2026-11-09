import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Reuse the project's public/ folder (LOGO.jpg) instead of keeping a second copy.
  publicDir: "../public",
  server: { port: 5173, strictPort: true }, // must match ALLOWED_ORIGINS in the API's .env
});
