import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const proxyTarget = process.env.DEV_PROXY_TARGET || 'http://localhost:8000';
const usePolling = process.env.DEV_USE_POLLING === 'true';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
    hmr: {
      clientPort: 8080,
    },
    watch: {
      usePolling,
      interval: usePolling ? 1000 : undefined,
    },
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/auth': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/users': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/sessions': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
});
