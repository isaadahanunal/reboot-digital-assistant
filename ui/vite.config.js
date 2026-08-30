import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The FastAPI server owns /api and serves the built bundle from ui/dist.
// In dev, Vite proxies /api to it so `npm run dev` behaves like production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8765' },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
