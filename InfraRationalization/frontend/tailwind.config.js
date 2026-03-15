/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0f1117',
          card:    '#1a1d26',
          hover:   '#1e2132',
          border:  '#2a2d3e',
        },
        brand: {
          cyan:   '#61dafb',
          blue:   '#3b82f6',
          indigo: '#6366f1',
          green:  '#10b981',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #6366f1 100%)',
      },
    },
  },
  plugins: [],
}
