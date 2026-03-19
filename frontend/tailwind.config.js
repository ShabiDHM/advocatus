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
        // Semantic Canvas
        'canvas': 'var(--bg-base)',
        'surface': 'var(--bg-surface)',
        'surface-secondary': 'var(--bg-surface-secondary)',
        'input-bg': 'var(--bg-input)',
        
        // Semantic Typography
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        
        // Semantic Accents (Dynamic based on theme)
        'primary-start': 'var(--accent-primary)',
        'primary-end': 'var(--accent-hover)',
        
        // Status
        'success-start': 'var(--status-success)',
        'warning-start': 'var(--status-warning)',
        'danger-start': 'var(--status-danger)',
      },
      boxShadow: {
        'lawyer-light': 'var(--shadow-md)',
        'lawyer-dark': 'var(--shadow-xl)',
        'accent-glow': 'var(--shadow-accent)',
      },
    },
  },
  plugins: [],
}