import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Resolved from the config file's own location rather than process.cwd(),
// so `vite` behaves the same whether it's launched from this directory or
// from the repo root (e.g. `vite --config desktop/frontend/vite.config.ts`).
const projectRoot = fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, '')
  const backendPort = env.VITE_BACKEND_PORT || '8080'

  return {
    root: projectRoot,
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // The Electron shell talks to the backend directly (it knows the real
      // port, which can shift if 8080 is taken). In plain-browser dev mode
      // there is no Electron preload bridge, so proxy /api to the backend
      // started via `uv run python main.py` instead. Override
      // VITE_BACKEND_PORT (e.g. in .env.development.local) if 8080 is
      // already used by something else on your machine.
      proxy: {
        '/api': `http://127.0.0.1:${backendPort}`,
      },
    },
  }
})
