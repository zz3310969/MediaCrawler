import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 开发模式：代理 API 请求到后端
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      // 开发模式：代理 WebSocket 到后端
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
  build: {
    // 关键配置：构建输出到后端的 webui 目录
    outDir: '../api/webui',
    emptyOutDir: true,
  },
})

