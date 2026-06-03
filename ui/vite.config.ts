import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      scope: '/',
      base: '/',
      includeAssets: ['icons/*.png', 'favicon.ico'],  // ← thêm dòng này
      manifest: {
        name: "Dormy's Point",
        short_name: "Dormy's",
        description: "ドーミーイン ポイントプログラム",
        lang: 'ja',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,ico,png,svg,woff2}'],
        navigateFallback: null,
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: ['viable-superb-basilisk.ngrok-free.app'],
  },
})