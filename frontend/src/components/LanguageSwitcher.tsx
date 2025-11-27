// FILE: src/components/LanguageSwitcher.tsx
// PHOENIX PROTOCOL - CORE FUNCTIONALITY (I18N)
// 1. COMPONENT: A new component providing a user interface for language selection.
// 2. LOGIC: Integrates with 'i18next' to display the current language and handle language changes.
// 3. USAGE: To be integrated into the main application Header.tsx.

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
        className="flex items-center gap-2 p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors"
      >
        <Globe size={20} />
        <span className="text-xs font-bold">{currentLanguage.flag}</span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-40 bg-background-dark border border-glass-edge rounded-xl shadow-2xl py-2 z-20 animate-in fade-in slide-in-from-top-2">
            {Object.keys(languages).map((lng) => (
              <button
                key={lng}
                onClick={() => changeLanguage(lng)}
                className="w-full flex items-center px-4 py-2 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors"
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