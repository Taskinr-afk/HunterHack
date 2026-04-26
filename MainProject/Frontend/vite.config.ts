import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/potholes": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/stats": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/predict": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/alerts": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/docs": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});