// /home/user/advocatus-frontend/tailwind.config.js
// DEFINITIVE VERSION 2.1: REVOLUTIONARY DESIGN TRANSFORMATION
// FIX APPLIED 18.10: Added 'safelist' to force generation of text-success-start class, resolving persistent build issue.

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // FIX: Force CSS generation for the problematic class.
  safelist: [
    'text-success-start',
  ],
  theme: {
    extend: {
      // --- NEW: DYNAMIC COLOR PALETTE & GRADIENTS ---
      colors: {
        'primary-start': '#2563eb', // Sky Blue
        'primary-end': '#3b82f6',   // Ocean Blue
        'secondary-start': '#7c3aed', // Magenta
        'secondary-end': '#9333ea',   // Violet
        'accent-start': '#f59e0b',  // Orange
        'accent-end': '#fbbf24',    // Amber
        'success-start': '#10b981', // Emerald
        'success-end': '#22c55e',   // Green
        'text-primary': '#f9fafb',   // Near White
        'text-secondary': '#d1d5db', // Light Gray
        'glass-edge': 'rgba(255, 255, 255, 0.1)', // For Glass Morphism border
        'background-dark': '#030712', // Near Black
        'background-light': '#1f2937', // Dark Gray
      },
      animation: {
        'gradient-shift': 'gradient-shift 15s ease infinite',
        'particle-float': 'particle-float 60s linear infinite',
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
  plugins: [
    // --- NEW: GLOW EFFECT PLUGIN ---
    function ({ addUtilities, theme }) {
      const newUtilities = {
        '.glow-primary': {
          boxShadow: `0 0 15px 0 ${theme('colors.primary-end')}`,
        },
        '.glow-secondary': {
          boxShadow: `0 0 15px 0 ${theme('colors.secondary-end')}`,
        },
        '.glow-accent': {
          boxShadow: `0 0 15px 0 ${theme('colors.accent-end')}`,
        },
      }
      addUtilities(newUtilities, ['responsive', 'hover', 'focus'])
    }
  ],
}