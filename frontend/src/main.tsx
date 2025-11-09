// FILE: /home/user/advocatus-frontend/src/main.tsx
// PHOENIX PROTOCOL DEFINITIVE CURE V9.0 (LOCALIZATION):
// 1. DISEASE IDENTIFIED: The locale mapping logic was flawed. The i18n instance uses 'sq',
//    not 'al', for Albanian. The conditional was never being met.
// 2. THE CURE: The logic has been simplified and corrected. The application now directly
//    sets the Moment.js locale using the language code provided by i18n. This guarantees
//    that 'moment.locale('sq')' is called, which will fix all date formatting issues.

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import i18n from './i18n'; 
import moment from 'moment'; 
import 'moment/locale/sq'; 

// --- DEFINITIVE CURE for Moment.js Localization ---
const updateMomentLocale = (lng: string | undefined) => {
  // Directly use the language code. If it's 'sq', moment will use the imported Albanian locale.
  // Otherwise, it will default to English.
  const locale = lng || 'en';
  moment.locale(locale);
  console.log(`Moment locale definitively set to: ${locale}`);
};

// 1. Set the initial locale immediately
updateMomentLocale(i18n.language);

// 2. Subscribe to language changes
i18n.on('languageChanged', updateMomentLocale);
// ---------------------------------

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);