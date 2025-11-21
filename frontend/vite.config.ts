// FILE: vite.config.ts
// PHOENIX PROTOCOL - PWA ENABLED
// 1. ADDED: 'vite-plugin-pwa' configuration.
// 2. MANIFEST: Defines name, colors, and icons for "Add to Home Screen".
// 3. BEHAVIOR: 'standalone' mode removes the browser URL bar when installed.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate', // Automatically updates the app when you deploy
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'Juristi AI',
        short_name: 'Juristi',
        description: 'Platforma e Inteligjencës Ligjore',
        theme_color: '#111827', // Dark background color
        background_color: '#111827',
        display: 'standalone', // Looks like a native app (no address bar)
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
            purpose: 'any maskable' // Ensures icon looks good on Android round icons
          }
        ]
      }
    })
  ],
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  publicDir: 'public'
})