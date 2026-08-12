/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        panel: 'var(--panel)',
        surface: 'var(--surface)',
        surface2: 'var(--surface-2)',
        border: 'var(--border)',
        borderStrong: 'var(--border-strong)',
        text: 'var(--text)',
        textMuted: 'var(--text-muted)',
        textFaint: 'var(--text-faint)',
        accent: 'var(--accent)',
        accentSoft: 'var(--accent-soft)',
        accentInk: 'var(--accent-ink)',
        success: 'var(--success)',
        successSoft: 'var(--success-soft)',
        warning: 'var(--warning)',
        warningSoft: 'var(--warning-soft)',
        danger: 'var(--danger)',
        dangerSoft: 'var(--danger-soft)'
      },
      fontFamily: {
        ui: ['-apple-system', '"Segoe UI"', 'Inter', 'sans-serif'],
        mono: ['ui-monospace', '"SF Mono"', '"Cascadia Code"', '"Roboto Mono"', 'Consolas', 'monospace']
      }
    }
  },
  plugins: []
};
