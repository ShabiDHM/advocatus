// /home/user/advocatus-frontend/tailwind.config.js
// DEFINITIVE VERSION 3.2: USE CSS VARIABLES FOR THEME COLORS
// 1. CHANGED: All color values now reference CSS custom properties.
// 2. RETAINED: darkMode: 'class' and all animations.

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    'text-success-start',
  ],
  theme: {
    extend: {
      colors: {
        'primary-start': 'var(--color-primary-start)',
        'primary-end': 'var(--color-primary-end)',
        'secondary-start': 'var(--color-secondary-start)',
        'secondary-end': 'var(--color-secondary-end)',
        'accent-start': 'var(--color-accent-start)',
        'accent-end': 'var(--color-accent-end)',
        'success-start': 'var(--color-success-start)',
        'success-end': 'var(--color-success-end)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'glass-edge': 'var(--color-glass-edge)',
        'background-dark': 'var(--color-background-dark)',
        'background-light': 'var(--color-background-light)',
      },
      animation: {
        'gradient-shift': 'gradient-shift 15s ease infinite',
        'particle-float': 'particle-float 60s linear infinite',
        'pulse-slow': 'pulse 8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'particle-float': {
          '0%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
          '100%': { transform: 'translateY(0px)' },
        }
      },
    },
  },
  plugins: [],
}