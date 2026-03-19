/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Professional Legal Palette
        'primary-start': 'var(--color-primary-start)',
        'primary-end': 'var(--color-primary-end)',
        'secondary-start': 'var(--color-secondary-start)',
        'secondary-end': 'var(--color-secondary-end)',
        'accent-start': 'var(--color-accent-start)',
        'accent-end': 'var(--color-accent-end)',
        'success-start': 'var(--color-success-start)',
        'success-end': 'var(--color-success-end)',
        
        // Semantic Surfaces
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'surface-border': 'var(--color-surface-border)',
        'canvas': 'var(--color-canvas)',
        'surface': 'var(--color-surface)',
      },
      boxShadow: {
        'lawyer-light': '0 1px 3px 0 rgba(0, 0, 0, 0.02), 0 1px 2px -1px rgba(0, 0, 0, 0.02)',
        'lawyer-elevated': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        'lawyer-dark': '0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.2)',
      },
      animation: {
        'gradient-shift': 'gradient-shift 15s ease infinite',
      },
      keyframes: {
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
    },
  },
  plugins: [],
}