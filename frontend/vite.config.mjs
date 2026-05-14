import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 3000,
    strictPort: true,
    allowedHosts: 'all',
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
});
