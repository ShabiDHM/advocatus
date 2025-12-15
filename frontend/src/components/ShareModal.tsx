// FILE: src/components/ShareModal.tsx
// PHOENIX PROTOCOL - SHARE MODAL V1.1 (FIXED IMPORTS)
// 1. FIXED: Added missing 'MessageSquare' import for Viber icon.
// 2. CLEANUP: Removed unused 'Instagram' import.

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
  // Ensures we don't get double slashes if env var ends with /
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
        className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
          className="bg-background-dark w-full max-w-sm rounded-2xl border border-glass-edge shadow-2xl p-6"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-white">Ndaj me Klientin</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20}/></button>
          </div>

          <div className="space-y-3">
            {/* WhatsApp - Primary */}
            <button onClick={handleWhatsApp} className="w-full flex items-center justify-between p-4 bg-[#25D366]/10 hover:bg-[#25D366]/20 border border-[#25D366]/30 rounded-xl group transition-all">
                <div className="flex items-center gap-3">
                    <Smartphone className="text-[#25D366]" />
                    <span className="font-bold text-[#25D366]">WhatsApp</span>
                </div>
                <Share2 size={16} className="text-[#25D366] opacity-50 group-hover:opacity-100" />
            </button>

            {/* Viber */}
            <button onClick={handleViber} className="w-full flex items-center justify-between p-4 bg-[#7360f2]/10 hover:bg-[#7360f2]/20 border border-[#7360f2]/30 rounded-xl group transition-all">
                <div className="flex items-center gap-3">
                    <MessageSquare className="text-[#7360f2]" />
                    <span className="font-bold text-[#7360f2]">Viber</span>
                </div>
                <Share2 size={16} className="text-[#7360f2] opacity-50 group-hover:opacity-100" />
            </button>

            {/* Copy Link - Fallback */}
            <button onClick={handleCopy} className="w-full flex items-center justify-between p-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl group transition-all">
                <div className="flex items-center gap-3">
                    <Copy className="text-gray-400" />
                    <span className="font-medium text-gray-300">Kopjo Linkun</span>
                </div>
            </button>
          </div>
          
          <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">Ky link skadon automatikisht pas 7 ditësh për siguri.</p>
          </div>

        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
};

export default ShareModal;