import { defineConfig, type PluginOption } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
// `npm run dev`        -> plain http  (same as before)
// `npm run dev:https`  -> https with a self-signed cert + /api proxy to the backend
export default defineConfig(async ({ mode }) => {
  const useHttps = mode === 'https'

  const plugins: PluginOption[] = [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons.svg'],
      manifest: {
        name: 'Fire Safety Extinguisher System',
        short_name: 'FireSafety',
        description: 'Fire Extinguisher Inspection & Asset Management',
        theme_color: '#d32f2f',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'favicon.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
            purpose: 'any maskable'
          }
        ]
      }
    })
  ]

  if (useHttps) {
    // Loaded only in https mode so plain `npm run dev` never needs it.
    const { default: basicSsl } = await import('@vitejs/plugin-basic-ssl')
    plugins.push(basicSsl())
  }

  return {
    server: {
      host: true, // expose dev server on the LAN so a phone can open it
      // The browser only talks to this one https origin; Vite forwards /api to
      // the http backend on this same machine. No mixed content, no CORS.
      // 127.0.0.1 (not "localhost") avoids Windows resolving localhost to ::1.
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          xfwd: true, // pass real client IP/proto so rate limits stay per-user
        },
      },
    },
    plugins,
  }
})
