// FILE: /home/user/advocatus-frontend/src/main.tsx
// DEFINITIVE VERSION 8.3 - ABSOLUTE FINAL MOMENT.JS LOCALIZATION FIX

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import i18n from './i18n'; 
import moment from 'moment'; 
// Explicitly import the Albanian locale to ensure it is bundled and available
import 'moment/locale/sq'; 

// --- MOMENT.JS LOCALIZATION FINAL FIX V2 ---
const updateMomentLocale = (lng: string) => {
  // Map i18n's 'al' code to Moment's 'sq' (Albanian) code. Default to 'en'.
  const momentLocale = lng === 'al' ? 'sq' : 'en';
  moment.locale(momentLocale);
  console.log(`Moment locale set to: ${momentLocale}`);
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