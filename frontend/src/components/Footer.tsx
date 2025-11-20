// FILE: src/components/Footer.tsx
// PHOENIX PROTOCOL - NEW COMPONENT
// 1. REDESIGN: Professional footer component separated from pages.
// 2. INTEGRATION: Opens ContactModal and PrivacyModal.
// 3. BRANDING: Updated copyright to "Data And Human Management".

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ContactModal from './ContactModal';
import PrivacyModal from './PrivacyModal';

const Footer: React.FC = () => {
  const { t } = useTranslation();
  const [isContactOpen, setIsContactOpen] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);

  return (
    <>
      <footer className="w-full py-6 border-t border-glass-edge/50 bg-background-light/50 backdrop-blur-md mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-text-secondary">
            
            {/* Branding & Copyright */}
            <div className="text-center md:text-left">
                <p className="font-medium text-text-primary">
                    &copy; 2025 Data And Human Management.
                </p>
                <p className="text-xs opacity-60 mt-1">
                    {t('footer.allRightsReserved', 'Të gjitha të drejtat e rezervuara.')}
                </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-6">
                <button 
                    onClick={() => setIsContactOpen(true)}
                    className="hover:text-primary-start transition-colors font-medium"
                >
                    {t('footer.contactSupport', 'Kontakto Mbështetjen')}
                </button>
                
                <span className="text-glass-edge">|</span>
                
                <button 
                    onClick={() => setIsPrivacyOpen(true)}
                    className="hover:text-primary-start transition-colors font-medium"
                >
                    {t('footer.privacyPolicy', 'Politika e Privatësisë')}
                </button>
            </div>
        </div>
      </footer>

      <ContactModal isOpen={isContactOpen} onClose={() => setIsContactOpen(false)} />
      <PrivacyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />
    </>
  );
};

export default Footer;