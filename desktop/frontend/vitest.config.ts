import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const projectRoot = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  root: projectRoot,
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    // Run in the main thread instead of spawning worker forks. On a heavily
    // loaded machine, worker spawn can time out; a single thread is slower
    // but reliable.
    pool: 'threads',
    poolOptions: { threads: { singleThread: true } },
    testTimeout: 20000,
  },
})
