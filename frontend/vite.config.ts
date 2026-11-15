import { demoEvidencePlugin } from './scripts/demoEvidence.ts'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'

export default defineConfig(({ mode }) => ({
  base: './',
  plugins: [react(), demoEvidencePlugin()],
  server: { proxy: { '/api': { target: loadEnv(mode, process.cwd(), '').API_PROXY_TARGET || 'http://127.0.0.1:8000', changeOrigin: true } } },
  preview: { proxy: {} },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
}))
