import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// 直接从根目录 .env 加载环境变量
import dotenv from 'dotenv'
dotenv.config({ path: path.resolve(__dirname, '../.env') })

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  envDir: path.resolve(__dirname, '..'), // 指向项目根目录
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.VITE_API_PORT || 8001}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://localhost:${process.env.VITE_API_PORT || 8001}`,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
