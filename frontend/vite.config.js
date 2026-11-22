import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api y /admin se redirigen al backend Django (evita problemas de CORS).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
    },
  },
});
