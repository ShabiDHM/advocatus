// FILE: src/context/ThemeContext.tsx
// PHOENIX PROTOCOL - THEME CONTEXT V1.0
// 1. PROVIDES: theme state (light/dark) and toggle function.
// 2. PERSISTS: theme in localStorage.
// 3. APPLIES: class to html element on mount and change.

import React, { createContext, useState, useContext, useEffect } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(() => {
    // Check localStorage first, fallback to system preference or 'dark'
    const saved = localStorage.getItem('theme') as Theme | null;
    if (saved && (saved === 'light' || saved === 'dark')) return saved;
    
    // Optional: check system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'dark'; // default to dark for now
  });

  useEffect(() => {
    // Apply theme class to html element
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    
    // Save to localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};