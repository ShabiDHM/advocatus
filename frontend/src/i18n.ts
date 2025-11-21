// FILE: src/i18n.ts
// PHOENIX PROTOCOL - LANGUAGE REGISTRATION
// 1. ADDED: Import for 'sr' (Serbian) translations.
// 2. REGISTERED: Added 'sr' to the resources object.

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// --- Static Resources ---
import enTranslation from './locales/en/translation.json';
import alTranslation from './locales/al/translation.json';
import srTranslation from './locales/sr/translation.json'; // <--- NEW IMPORT

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: enTranslation
      },
      al: {
        translation: alTranslation
      },
      sr: {
        translation: srTranslation // <--- REGISTERED
      }
    },
    // Default language remains Albanian ('al')
    lng: 'al', 
    fallbackLng: 'en', 

    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;