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
        surface3: 'var(--surface-3)',
        border: 'var(--border)',
        borderStrong: 'var(--border-strong)',
        text: 'var(--text)',
        textMuted: 'var(--text-muted)',
        textFaint: 'var(--text-faint)',
        accent: 'var(--accent)',
        accent100: 'var(--accent-100)',
        accent200: 'var(--accent-200)',
        accent400: 'var(--accent-400)',
        accent600: 'var(--accent-600)',
        accentSoft: 'var(--accent-soft)',
        accentInk: 'var(--accent-ink)',
        success: 'var(--success)',
        successSoft: 'var(--success-soft)',
        warning: 'var(--warning)',
        warningSoft: 'var(--warning-soft)',
        danger: 'var(--danger)',
        dangerSoft: 'var(--danger-soft)'
      },
      // Named sizes bound to the values already in use. The app had ~60 `text-[11.5px]` literals;
      // these render identically, so adopting them is a naming change with no visual delta.
      fontSize: {
        xs: ['10.5px', { lineHeight: '1.45' }],
        sm: ['11.5px', { lineHeight: '1.5' }],
        base: ['13.5px', { lineHeight: '1.5' }],
        lg: ['15px', { lineHeight: '1.4' }],
        xl: ['18px', { lineHeight: '1.35' }],
        '2xl': ['22px', { lineHeight: '1.25' }]
      },
      borderRadius: {
        sm: 'var(--r-sm)',
        md: 'var(--r-md)',
        lg: 'var(--r-lg)',
        xl: 'var(--r-xl)'
      },
      boxShadow: {
        1: 'var(--shadow-1)',
        2: 'var(--shadow-2)',
        3: 'var(--shadow-3)'
      },
      transitionDuration: {
        fast: 'var(--dur-fast)',
        DEFAULT: 'var(--dur)',
        slow: 'var(--dur-slow)'
      },
      transitionTimingFunction: {
        out: 'var(--ease-out)',
        spring: 'var(--ease-spring)'
      },
      fontFamily: {
        ui: ['-apple-system', '"Segoe UI"', 'Inter', 'sans-serif'],
        mono: ['ui-monospace', '"SF Mono"', '"Cascadia Code"', '"Roboto Mono"', 'Consolas', 'monospace']
      },
      // The surge-* keyframes themselves live in globals.css, next to the tokens whose durations
      // they consume. Declaring them here as well would give the app two sources of truth.
      animation: {
        'fade-in': 'surge-fade-in var(--dur) var(--ease-out)',
        'fade-out': 'surge-fade-out var(--dur-fast) var(--ease-out)',
        'scale-in': 'surge-scale-in var(--dur) var(--ease-spring)',
        'scale-out': 'surge-scale-out var(--dur-fast) var(--ease-out)',
        'slide-up': 'surge-slide-up var(--dur) var(--ease-out)',
        'slide-in-right': 'surge-slide-in-right var(--dur-slow) var(--ease-spring)',
        'slide-out-right': 'surge-slide-out-right var(--dur) var(--ease-out)',
        'pulse-ring': 'surge-pulse-ring 1.8s var(--ease-out) infinite',
        draw: 'surge-draw 1.6s var(--ease-out) forwards'
      }
    }
  },
  plugins: []
};
