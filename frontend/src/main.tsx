// FILE: /home/user/advocatus-frontend/src/main.tsx

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import i18n from './i18n';
import moment from 'moment';
import 'moment/locale/sq';

// PHOENIX PROTOCOL CURE: Corrected global import path for react-pdf styles.
// This ensures the production bundler (Rollup) can find and process them correctly.
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

const updateMomentLocale = (lng: string | undefined) => {
  const locale = lng || 'en';
  moment.locale(locale);
  console.log(`Moment locale definitively set to: ${locale}`);
};

// 1. Set the initial locale immediately
updateMomentLocale(i18n.language);

// 2. Subscribe to language changes
i18n.on('languageChanged', updateMomentLocale);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);