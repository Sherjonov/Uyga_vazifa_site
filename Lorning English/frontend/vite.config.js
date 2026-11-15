import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// /api va /uploads so'rovlari backendga (8000) yo'naltiriladi: CORS muammosi yo'q.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
});
