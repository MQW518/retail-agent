import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发时把 /api 转发给 FastAPI（uvicorn server:app --port 8000）
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
})
