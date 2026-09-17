// FILE: src/components/ShareModal.tsx
// PHOENIX PROTOCOL - SHARE MODAL V7.0 (BRAND COLORS CENTRALIZED)
// V7.0: Ngjyrat WhatsApp/Viber kaluar në tailwind.config.js si brand-*.
// V6.0: Executive Design System.

import React from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Copy, Share2, Smartphone, MessageSquare } from 'lucide-react';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle: string;
}

const ShareModal: React.FC<ShareModalProps> = ({ isOpen, onClose, caseId, caseTitle }) => {
  if (!isOpen) return null;

  // The Smart Link (Points to Backend for Meta Tags)
  const apiUrl = (import.meta.env.VITE_API_URL || '').replace(/\/api\/v1\/?$/, '');
  const shareUrl = `${apiUrl}/api/v1/share/c/${caseId}`;
  
  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl);
    alert("Linku u kopjua!");
  };

  const handleWhatsApp = () => {
    const text = `Përshëndetje, po ndaj me ju dosjen e rastit: ${caseTitle}. Shikojeni këtu: ${shareUrl}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  const handleViber = () => {
      const text = `Dosja: ${caseTitle} - ${shareUrl}`;
      window.open(`viber://forward?text=${encodeURIComponent(text)}`, '_blank');
  };

  return ReactDOM.createPortal(
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-canvas/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
          className="glass-panel border border-main w-full max-w-sm rounded-2xl shadow-2xl p-6"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-text-primary">Ndaj me Klientin</h3>
            <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
              <X size={20}/>
            </button>
          </div>

          <div className="space-y-3">
            {/* WhatsApp - Primary */}
            <button 
              onClick={handleWhatsApp} 
              className="w-full flex items-center justify-between p-4 bg-brand-whatsapp/10 hover:bg-brand-whatsapp/20 border border-brand-whatsapp/30 rounded-xl group transition-all"
            >
                <div className="flex items-center gap-3">
                    <Smartphone className="text-brand-whatsapp" />
                    <span className="font-bold text-brand-whatsapp">WhatsApp</span>
                </div>
                <Share2 size={16} className="text-brand-whatsapp opacity-50 group-hover:opacity-100" />
            </button>

            {/* Viber */}
            <button 
              onClick={handleViber} 
              className="w-full flex items-center justify-between p-4 bg-brand-viber/10 hover:bg-brand-viber/20 border border-brand-viber/30 rounded-xl group transition-all"
            >
                <div className="flex items-center gap-3">
                    <MessageSquare className="text-brand-viber" />
                    <span className="font-bold text-brand-viber">Viber</span>
                </div>
                <Share2 size={16} className="text-brand-viber opacity-50 group-hover:opacity-100" />
            </button>

            {/* Copy Link - Fallback */}
            <button 
              onClick={handleCopy} 
              className="w-full flex items-center justify-between p-4 bg-surface/30 hover:bg-surface/50 border border-main rounded-xl group transition-all"
            >
                <div className="flex items-center gap-3">
                    <Copy className="text-text-muted" />
                    <span className="font-medium text-text-secondary">Kopjo Linkun</span>
                </div>
            </button>
          </div>
          
          <div className="mt-6 text-center">
              <p className="text-xs text-text-muted">Ky link skadon automatikisht pas 7 ditësh për siguri.</p>
          </div>

        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
};

export default ShareModal;