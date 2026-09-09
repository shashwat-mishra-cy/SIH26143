import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// SIH26143 frontend — Vite config.
// No backend proxy needed in Phase 1 (no API integration yet).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})