/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#0a0e17',
        surface: '#111827',
        'surface-2': '#162033',
        border: '#1f2937',
        'border-2': '#273449',
        text: {
          DEFAULT: '#e5e7eb',
          muted: '#9ca3af',
          subtle: '#6b7280',
        },
        brand: {
          DEFAULT: '#3b82f6',
          soft: '#1e40af',
        },
        severity: {
          healthy: '#10b981',
          low: '#34d399',
          medium: '#fbbf24',
          high: '#f97316',
          critical: '#ef4444',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(59,130,246,0.25), 0 4px 20px -8px rgba(59,130,246,0.25)',
      },
    },
  },
  plugins: [],
}
