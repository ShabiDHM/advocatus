// FILE: src/i18n.ts
// PHOENIX PROTOCOL - I18N CORE FIX
// 1. LANGUAGE CODE: Corrected the language code for Albanian from non-standard 'al' to the ISO standard 'sq'.
// 2. IMPORT PATH: Updated the import path to match the new 'sq' directory.
// 3. CONFIGURATION: Updated the resources object and default language to use 'sq'. This resolves the language switcher failure.

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import enTranslation from './locales/en/translation.json';
import sqTranslation from './locales/sq/translation.json'; // PHOENIX: Corrected path
import srTranslation from './locales/sr/translation.json';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: enTranslation
      },
      sq: { // PHOENIX: Corrected language code
        translation: sqTranslation
      },
      sr: {
        translation: srTranslation
      }
    },
    lng: 'sq', // PHOENIX: Corrected default language
    fallbackLng: 'en', 

    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;