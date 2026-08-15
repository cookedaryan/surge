import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Browser-driven end-to-end specs need a running stack, so they are not part of the
    // default unit run. See src/test/e2e/README.md.
    exclude: ['node_modules/**', 'dist/**', 'src/test/e2e/**']
  }
});
