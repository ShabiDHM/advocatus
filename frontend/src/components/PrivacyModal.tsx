// FILE: src/components/PrivacyModal.tsx
// PHOENIX PROTOCOL - PRIVACY MODAL V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary.
// 2. Scrollbar styling preserved with semantic color hints.
// 3. Button uses btn-secondary class.

import React from 'react';
import { motion } from 'framer-motion';
import { X, Shield, Lock, Eye } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const scrollbarStyles = `
  .privacy-scroll::-webkit-scrollbar { width: 6px; }
  .privacy-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
  .privacy-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
  .privacy-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
`;

const PrivacyModal: React.FC<PrivacyModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <style>{scrollbarStyles}</style>
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="glass-panel border border-main rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col"
      >
        <div className="p-6 border-b border-main flex justify-between items-center bg-surface/30">
          <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
            <Shield className="text-primary-start h-5 w-5" />
            {t('footer.privacyPolicy', 'Politika e Privatësisë')}
          </h2>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto privacy-scroll space-y-6 text-text-secondary text-sm leading-relaxed">
          <div className="space-y-2">
            <h3 className="text-text-primary font-semibold text-lg flex items-center gap-2">
                <Lock size={16} className="text-primary-start" /> Mbrojtja e Të Dhënave
            </h3>
            <p>
              Në <strong>Data And Human Management</strong>, ne e trajtojmë sigurinë e të dhënave tuaja si prioritetin tonë absolut. 
              Ky dokument shpjegon se si ne mbledhim, përdorim dhe mbrojmë informacionin tuaj personal dhe ligjor.
            </p>
          </div>

          <div className="space-y-2">
            <h3 className="text-text-primary font-semibold text-lg flex items-center gap-2">
                <Eye size={16} className="text-primary-start" /> Përdorimi i Informacionit
            </h3>
            <p>
              Të dhënat e ngarkuara në platformën Advocatus AI përdoren ekskluzivisht për qëllimin e analizës ligjore, 
              ekstraktimit të të dhënave dhe menaxhimit të rasteve. Ne nuk i ndajmë të dhënat tuaja me palë të treta 
              pa pëlqimin tuaj të shprehur.
            </p>
            <ul className="list-disc pl-5 space-y-1 mt-2 opacity-80">
                <li>Enkriptim i nivelit të lartë (AES-256) për të gjitha dokumentet.</li>
                <li>Përpunim i automatizuar pa ndërhyrje njerëzore.</li>
                <li>Fshirje e menjëhershme e të dhënave sipas kërkesës.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h3 className="text-text-primary font-semibold text-lg">Të Drejtat e Përdoruesit</h3>
            <p>
              Ju keni të drejtën të kërkoni akses, korrigjim ose fshirje të të dhënave tuaja personale në çdo kohë. 
              Për çdo shqetësim lidhur me privatësinë, ju lutemi përdorni formularin e kontaktit.
            </p>
          </div>

          <div className="pt-4 border-t border-main/30 text-xs text-center opacity-50">
            Përditësuar së fundmi: Nëntor 2025
          </div>
        </div>

        <div className="p-4 border-t border-main bg-canvas/80 text-center">
            <button onClick={onClose} className="btn-secondary px-6 py-2 rounded-xl font-medium transition-all">
                {t('general.close', 'Mbyll')}
            </button>
        </div>
      </motion.div>
    </div>
  );
};

export default PrivacyModal;