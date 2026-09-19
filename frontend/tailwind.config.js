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
        // Foundation - RGB enabled for opacity support
        'canvas': 'var(--bg-base)',
        'card': 'var(--bg-card)',
        'surface': 'rgb(var(--bg-surface-rgb) / <alpha-value>)',
        'surface-secondary': 'var(--bg-surface-secondary)',
        'input': 'var(--bg-input)',
        
        // Typography - Simplified keys for standard utilities
        'primary': 'var(--accent-primary)',
        'primary-hover': 'var(--accent-hover)',
        
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'text-disabled': 'var(--text-disabled)',
        'text-inverse': '#FFFFFF',
        
        // Prestige Accents
        'primary-start': 'var(--accent-primary)',
        'primary-end': 'var(--accent-hover)',
        
        // Status with RGB support
        'success-start': 'rgb(var(--status-success-rgb) / <alpha-value>)',
        'warning-start': 'rgb(var(--status-warning-rgb) / <alpha-value>)',
        'danger-start': 'rgb(var(--status-danger-rgb) / <alpha-value>)',
        
        // Info status (holiday/weekend)
        'status-info': 'rgb(var(--status-info-rgb) / <alpha-value>)',
        
        // Role colors për pozicionet ligjore
        'role-plaintiff': 'var(--role-plaintiff)',
        'role-defendant': 'var(--role-defendant)',
        'role-neutral': 'var(--role-neutral)',
        
        // Border Colors
        'border-main': 'var(--border-main)',
        'border-strong': 'var(--border-strong)',
        
        // Brand Colors (external, static)
        'brand-whatsapp': '#25D366',
        'brand-viber': '#7360F2',
      },
      borderColor: {
        'main': 'var(--border-main)',
        'strong': 'var(--border-strong)',
        'primary': 'var(--border-primary)',
        'success': 'var(--border-success)',
        'danger': 'var(--border-danger)',
      },
      boxShadow: {
        'lawyer-light': 'var(--shadow-md)',
        'lawyer-dark': 'var(--shadow-xl)',
        'accent-glow': '0 0 15px rgba(var(--accent-primary-rgb), 0.3)',
        'inner-trough': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        'panel': '1.5rem',
      },
    },
  },
  plugins: [],
}