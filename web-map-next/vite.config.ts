import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Defaults to the backend docker compose publishes. Overridable so a dev server can be pointed at
// a second stack — a throwaway database, a colleague's branch — without editing this file and
// risking the change being committed.
const apiTarget = process.env.SURGE_API_TARGET ?? 'http://localhost:8080';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true
      }
    }
  }
});
