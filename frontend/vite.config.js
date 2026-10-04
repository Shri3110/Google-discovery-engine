import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/stats': 'http://localhost:8000',
      '/ask': 'http://localhost:8000',
      '/clusters': 'http://localhost:8000',
      '/search': 'http://localhost:8000'
    }
  }
})
