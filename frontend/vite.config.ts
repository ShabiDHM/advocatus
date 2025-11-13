// FILE: vite.config.ts

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cp } from 'node:fs/promises'
import { resolve } from 'node:path'

// --- PHOENIX PROTOCOL CURE: ARCHITECTURALLY SOUND PDF WORKER RESOLUTION ---
const copyPdfWorkerPlugin = () => {
  return {
    name: 'copy-pdf-worker',
    async buildStart() {
      try {
        const pdfjsDistPath = resolve(process.cwd(), 'node_modules', 'pdfjs-dist');
        
        // PHOENIX PROTOCOL FIX: Check for multiple possible worker file locations
        const possibleWorkerPaths = [
          resolve(pdfjsDistPath, 'build', 'pdf.worker.min.js'),
          resolve(pdfjsDistPath, 'build', 'pdf.worker.js'),
          resolve(pdfjsDistPath, 'legacy', 'build', 'pdf.worker.min.js'),
          resolve(pdfjsDistPath, 'legacy', 'build', 'pdf.worker.js')
        ];

        let workerSrcPath: string | null = null;
        for (const path of possibleWorkerPaths) {
          try {
            await cp(path, path); // Test if file exists by trying to copy to itself
            workerSrcPath = path;
            console.log(`[vite-plugin-copy-pdf-worker] Found PDF worker at: ${path}`);
            break;
          } catch {
            continue;
          }
        }

        if (!workerSrcPath) {
          throw new Error('PDF worker not found in any expected location');
        }

        const workerDestPath = resolve(process.cwd(), 'public', 'pdf.worker.min.js');

        console.log(`[vite-plugin-copy-pdf-worker] Copying PDF.js worker from ${workerSrcPath} to public directory...`);
        await cp(workerSrcPath, workerDestPath);
        console.log(`[vite-plugin-copy-pdf-worker] PDF.js worker copied successfully.`);
      } catch (e) {
        console.error(`[vite-plugin-copy-pdf-worker] FAILED to copy PDF.js worker: ${e}`);
        // PHOENIX PROTOCOL: Fail the build if worker cannot be copied
        throw e;
      }
    },
  };
};
// --- END CURE ---

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    copyPdfWorkerPlugin(),
  ],
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  // PHOENIX PROTOCOL: Ensure public directory is properly handled
  publicDir: 'public'
})