// FILE: vite.config.ts
// PHOENIX PROTOCOL - DEFINITIVE AND FINAL VERSION (ASSET MANAGEMENT)
// CORRECTION: The flawed custom plugin has been replaced with 'vite-plugin-static-copy'.
// This is the architecturally sound solution to copy the required pdf.worker.min.js
// from node_modules into the final build directory, guaranteeing version synchronization
// and eliminating the fragile CDN dependency.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          src: 'node_modules/react-pdf/node_modules/pdfjs-dist/build/pdf.worker.min.js',
          dest: ''
        }
      ]
    })
  ],
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  publicDir: 'public'
})