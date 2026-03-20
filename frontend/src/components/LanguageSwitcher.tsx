// FILE: src/components/LanguageSwitcher.tsx
// PHOENIX PROTOCOL - LANGUAGE SWITCHER V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, border-main, text-text-secondary, text-text-primary.
// 2. Dropdown uses glass-panel styling with border-main.
// 3. Preserved all i18n logic.

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Globe } from 'lucide-react';

const languages = {
  sq: { nativeName: 'Shqip', flag: 'SQ' },
  en: { nativeName: 'English', flag: 'EN' },
  sr: { nativeName: 'Srpski', flag: 'SR' },
};

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const currentLanguage = languages[i18n.language as keyof typeof languages] || languages.sq;

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-2 text-text-secondary hover:text-text-primary hover:bg-surface/30 rounded-lg transition-colors"
      >
        <Globe size={20} />
        <span className="text-xs font-bold">{currentLanguage.flag}</span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-40 glass-panel border border-main rounded-xl shadow-2xl py-2 z-20 animate-in fade-in slide-in-from-top-2">
            {Object.keys(languages).map((lng) => (
              <button
                key={lng}
                onClick={() => changeLanguage(lng)}
                className="w-full flex items-center px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-surface/30 transition-colors"
              >
                <span className="font-bold mr-3">{languages[lng as keyof typeof languages].flag}</span>
                {languages[lng as keyof typeof languages].nativeName}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default LanguageSwitcher;