import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    host: true,
  },
  resolve: {
    alias: {
      // 确保 Monaco Editor 可以正确解析
    },
  },
  optimizeDeps: {
    include: ['monaco-editor'],
  },
})
