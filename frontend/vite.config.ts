// FILE: vite.config.ts

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// --- PHOENIX PROTOCOL CURE: VERCEL-COMPATIBLE PDF WORKER SOLUTION ---
// Vercel build environment doesn't have access to node_modules file system during build.
// We'll rely on CDN for PDF worker in production and skip the file copy operation.
const vercelSafePdfPlugin = () => {
  return {
    name: 'vercel-pdf-fix',
    buildStart() {
      // In Vercel, we cannot access node_modules files during build
      // This plugin now only serves to indicate we're handling PDF workers via CDN
      console.log('[vercel-pdf-fix] Using CDN for PDF.js worker in Vercel environment');
    },
  };
};

export default defineConfig({
  plugins: [
    react(),
    vercelSafePdfPlugin(),
  ],
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  publicDir: 'public'
})