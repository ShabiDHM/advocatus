// FILE: src/components/Footer.tsx
// PHOENIX PROTOCOL - UI COMPACTING
// 1. HEIGHT REDUCTION: Reduced padding from 'py-6' to 'py-3 sm:py-4'.
// 2. SPACING: Tightened gaps for a sleeker profile.
// 3. LAYOUT: Maintains responsiveness (stacked on mobile, row on desktop).

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
      <footer className="w-full py-3 sm:py-4 border-t border-glass-edge/50 bg-background-light/50 backdrop-blur-md mt-auto flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-2 sm:gap-4 text-xs sm:text-sm text-text-secondary">
            
            {/* Branding & Copyright */}
            <div className="text-center md:text-left">
                <p className="font-medium text-text-primary">
                    &copy; 2025 Data And Human Management.
                </p>
                <p className="text-[10px] sm:text-xs opacity-60">
                    {t('footer.allRightsReserved', 'Të gjitha të drejtat e rezervuara.')}
                </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-4 sm:gap-6">
                <button 
                    onClick={() => setIsContactOpen(true)}
                    className="hover:text-primary-start transition-colors font-medium"
                >
                    {t('footer.contactSupport', 'Kontakto Mbështetjen')}
                </button>
                
                <span className="text-glass-edge opacity-50">|</span>
                
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