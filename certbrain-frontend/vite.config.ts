import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    // Build output goes directly into Flask's static folder
    build: {
      outDir: path.resolve(__dirname, '../static'),
      emptyOutDir: true,
      // Assets will be referenced as /static/assets/... matching Flask's static_url_path
      assetsDir: 'assets',
    },
    base: '/static/',
    // Dev server: proxy /api/* to Flask on :5000
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api': {
          target: 'http://localhost:5000',
          changeOrigin: true,
        },
      },
    },
  };
});
