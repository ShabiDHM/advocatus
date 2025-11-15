// FILE: vite.config.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (STANDARD BUILD CONFIG)
// CORRECTION: The faulty 'vite-plugin-static-copy' plugin and all related logic
// have been completely removed. We will now rely on Vite's standard, built-in
// asset handling, which is the robust and correct architectural approach.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
  ],
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  publicDir: 'public'
})