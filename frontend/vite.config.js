import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        // Ensure SSE headers are preserved and not buffered by the dev server
        bypass: (req, res, options) => {
          res.setHeader('Cache-Control', 'no-cache');
        }
      }
    }
  },
  build: {
    outDir: '../backend/static', // Build output directly to FastAPI static serve directory!
    emptyOutDir: true
  }
})
