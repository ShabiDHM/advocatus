// FILE: vite.config.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (DYNAMIC PATH RESOLUTION)
// CORRECTION: The fragile, hardcoded path to pdf.worker.min.js has been replaced
// with a dynamic, programmatic path resolution. This uses Node.js's 'require.resolve'
// to find the 'pdfjs-dist' package wherever npm has placed it, making the build
// process resilient and permanently fixing the "No file was found" error.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import path from 'path'

// Find the absolute path to the pdfjs-dist package
const pdfjsDistPath = path.dirname(require.resolve('pdfjs-dist/package.json'));

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          // Use the dynamically found path to the worker file
          src: `${pdfjsDistPath}/build/pdf.worker.min.js`,
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