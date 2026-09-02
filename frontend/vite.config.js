import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend runs on http://localhost:8000 with CORS allowing localhost.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
