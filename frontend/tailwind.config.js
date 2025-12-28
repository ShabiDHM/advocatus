// /home/user/advocatus-frontend/tailwind.config.js
// DEFINITIVE VERSION 3.0: ANIMATION LOGIC UPDATE
// FIX: Added 'pulse-slow' and 'float' to support the new MainLayout ambient background.

/** @type {import('tailwindcss').Config} */
export default {
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
        'primary-start': '#2563eb',
        'primary-end': '#3b82f6',
        'secondary-start': '#7c3aed',
        'secondary-end': '#9333ea',
        'accent-start': '#f59e0b',
        'accent-end': '#fbbf24',
        'success-start': '#10b981',
        'success-end': '#22c55e',
        'text-primary': '#f9fafb',
        'text-secondary': '#d1d5db',
        'glass-edge': 'rgba(255, 255, 255, 0.1)',
        'background-dark': '#030712',
        'background-light': '#1f2937',
      },
      // --- NEW: ANIMATION DEFINITIONS ---
      animation: {
        'gradient-shift': 'gradient-shift 15s ease infinite',
        'particle-float': 'particle-float 60s linear infinite',
        'pulse-slow': 'pulse 8s cubic-bezier(0.4, 0, 0.6, 1) infinite', // Added for Ambient Glows
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