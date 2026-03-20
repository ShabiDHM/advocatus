// /home/user/advocatus-frontend/tailwind.config.js
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
        // Semantic Canvas - The Foundation
        'canvas': 'var(--bg-base)',
        'surface': 'var(--bg-surface)',
        'surface-secondary': 'var(--bg-surface-secondary)',
        'input-bg': 'var(--bg-input)',
        
        // Semantic Typography
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'text-disabled': 'var(--text-disabled)',
        
        // High-Prestige Accents
        'primary-start': 'var(--accent-primary)',
        'primary-end': 'var(--accent-hover)',
        
        // Professional Status
        'success-start': 'var(--status-success)',
        'warning-start': 'var(--status-warning)',
        'danger-start': 'var(--status-danger)',
      },
      boxShadow: {
        'lawyer-light': 'var(--shadow-md)',
        'lawyer-dark': 'var(--shadow-xl)',
        'accent-glow': 'var(--shadow-accent)',
        'inner-trough': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        'panel': '1.5rem', // 24px
      },
    },
  },
  plugins: [],
}