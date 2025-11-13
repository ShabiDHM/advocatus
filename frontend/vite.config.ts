// /home/user/advocatus-frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cp } from 'node:fs/promises'
import { resolve } from 'node:path'

// --- PHOENIX PROTOCOL CURE: ARCHITECTURAL FIX FOR PDF WORKER ---
// This custom plugin solves the CORS error by making the PDF worker a first-party asset.
const copyPdfWorkerPlugin = () => {
  return {
    name: 'copy-pdf-worker',
    // The `buildStart` hook ensures this runs for both `vite dev` and `vite build`.
    async buildStart() {
      try {
        const pdfjsDistPath = resolve(process.cwd(), 'node_modules', 'pdfjs-dist');
        const workerSrcPath = resolve(pdfjsDistPath, 'build', 'pdf.worker.min.js');
        const workerDestPath = resolve(process.cwd(), 'public', 'pdf.worker.min.js');

        console.log(`[vite-plugin-copy-pdf-worker] Copying PDF.js worker to public directory...`);
        // Copy the worker file from node_modules to the public folder.
        await cp(workerSrcPath, workerDestPath);
        console.log(`[vite-plugin-copy-pdf-worker] PDF.js worker copied successfully.`);
      } catch (e) {
        console.error(`[vite-plugin-copy-pdf-worker] FAILED to copy PDF.js worker: ${e}`);
      }
    },
  };
};
// --- END CURE ---

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Add the custom plugin to the Vite pipeline.
    copyPdfWorkerPlugin(),
  ],
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})