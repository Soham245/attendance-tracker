import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// Relative base keeps the build loadable from Electron's `file://` shell.
// `envDir` points at the repo root so the frontend reads the consolidated
// `.env` shared with the backend (only VITE_* keys reach the renderer).
export default defineConfig({
  plugins: [react()],
  base: './',
  envDir: path.resolve(__dirname, '..'),
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    strictPort: false,
  },
});
