// /home/user/advocatus-frontend/src/i18n.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// --- Static Resources (to be loaded from the JSON files in the next steps) ---
import enTranslation from './locales/en/translation.json';
import alTranslation from './locales/al/translation.json';

i18n
  .use(initReactI18next) // passes i18n instance to react-i18next
  .init({
    resources: {
      en: {
        translation: enTranslation
      },
      al: {
        translation: alTranslation
      }
    },
    // IMPORTANT: Set 'al' as the default language as per your market directive
    lng: 'al', 
    fallbackLng: 'en', 

    interpolation: {
      escapeValue: false, // react already escapes safe HTML
    },
    
    // We are pre-loading static JSON files, so no need for backend detection
    // but keep configuration simple for now.
  });

export default i18n;