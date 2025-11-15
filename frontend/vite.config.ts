// FILE: vite.config.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (ESM-COMPATIBLE PATH RESOLUTION)
// CORRECTION: The previous solution used CommonJS syntax (require) in an ES Module
// context, causing a TypeError. This has been corrected by using Node.js's
// 'createRequire' function, which is the standard, modern way to access legacy
// module features like 'resolve' from within an ES Module. This is the definitive
// fix for the build failure.

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import path from 'path';
import { createRequire } from 'module';

// Create a 'require' function that's compatible with ES Modules
const require = createRequire(import.meta.url);

// Use the compatible require function to find the absolute path to pdfjs-dist
const pdfjsDistPath = path.dirname(require.resolve('pdfjs-dist/package.json'));

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          // Use the dynamically and correctly found path to the worker file
          src: `${pdfjsDistPath}/build/pdf.worker.min.js`,
          dest: '',
        },
      ],
    }),
  ],
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  publicDir: 'public',
});