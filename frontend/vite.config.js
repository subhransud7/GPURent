import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: false,
    allowedHosts: [
      'localhost',
      '.replit.dev',
      '.spock.replit.dev', 
      'c423f10c-2ea3-44c5-b32c-de2943dafbc9-00-1ahkiakiocr0o.spock.replit.dev'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  define: {
    'process.env': {}
  }
})