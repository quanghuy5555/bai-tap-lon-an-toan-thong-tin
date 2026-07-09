import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server chạy ở cổng 5173; backend FastAPI ở cổng 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
