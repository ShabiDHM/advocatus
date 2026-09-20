// FILE: vite.config.ts
// PHOENIX PROTOCOL - BUILD FIX V2.4 (LOCAL PROXY FOR DEV)

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  base: '/', 
  
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'Juristi AI',
        short_name: 'Juristi',
        description: 'Platforma e Inteligjencës Ligjore',
        theme_color: '#111827', 
        background_color: '#111827',
        display: 'standalone', 
        orientation: 'portrait',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable' 
          }
        ]
      },
      workbox: {
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
      }
    })
  ],
  // --- PROXY CONFIGURATION (V2.4 — LOCAL DEV) ---
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // V2.4: lokal per dev
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  publicDir: 'public'
})