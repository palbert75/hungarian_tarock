/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Installable app. The game itself needs the server, so only the app
    // shell is cached: it opens instantly and then connects.
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/apple-touch-icon.png', 'robots.txt', 'sitemap.xml'],
      manifest: {
        id: '/',
        name: 'Tarokk – magyar tarokk online',
        short_name: 'Tarokk',
        description: 'Magyar tarokk – négy játékos, élőben, barátokkal vagy gépek ellen',
        lang: 'hu',
        categories: ['games', 'entertainment'],
        display: 'standalone',
        // Phones play upright; a desktop window may be wide
        orientation: 'any',
        start_url: '/',
        scope: '/',
        theme_color: '#0f3d2e',
        background_color: '#0f3d2e',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,svg,webp,woff2}'],
        navigateFallbackDenylist: [/^\/socket\.io/, /^\/robots\.txt$/, /^\/sitemap\.xml$/, /^\/og\.jpg$/],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3003,
    proxy: {
      '/socket.io': {
        target: 'http://localhost:8000',
        ws: true,
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
