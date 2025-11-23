// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ARCHITECTURAL FIX
// 1. PORTAL: Moved to document.body to fix header overlap issues.
// 2. Z-INDEX: Boosted to z-[9999].
// 3. MOBILE: Header layout hardened to ensure Close button is always clickable.

import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import { CaseAnalysisResult } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, AlertTriangle, Scale, HelpCircle, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: CaseAnalysisResult;
}

// --- Custom Scrollbar Styles ---
const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
`;

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result }) => {
  const { t } = useTranslation();

  // Handle Body Scroll Lock
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        // Z-9999 ensures it's above everything. Fixed inset-0 covers viewport.
        className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999] p-0 sm:p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[90vh] sm:max-w-4xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header (Fixed & Hardened) */}
          <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0 gap-4">
            <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2 min-w-0">
              <div className="p-1.5 bg-primary-start/10 rounded-lg flex-shrink-0">
                 <Scale className="text-primary-start h-5 w-5 sm:h-6 sm:w-6" />
              </div>
              <span className="truncate">{t('analysis.modalTitle', 'Analiza e Rastit')}</span>
            </h2>
            <button 
                onClick={onClose} 
                className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors flex-shrink-0"
                title={t('general.close', 'Mbyll')}
            >
                <X size={24} />
            </button>
          </div>

          {/* Content (Scrollable) */}
          <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-background-dark/50">
            <style>{scrollbarStyles}</style>
            
            {/* Summary */}
            <div className="bg-background-light/30 p-4 sm:p-5 rounded-xl border border-glass-edge">
              <h3 className="text-base sm:text-lg font-semibold text-white mb-2">{t('analysis.summary', 'Përmbledhje Ekzekutive')}</h3>
              <p className="text-text-secondary text-sm leading-relaxed whitespace-pre-wrap">{result.summary_analysis}</p>
            </div>

            {/* 3 Columns Grid (Stacks on Mobile) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Risks */}
              <div className="space-y-3 p-4 bg-red-900/10 rounded-xl border border-red-500/10">
                  <div className="flex items-center gap-2 text-red-400 font-bold border-b border-red-500/30 pb-2 text-sm sm:text-base">
                      <AlertTriangle size={18} /> {t('analysis.risks', 'Rreziqe Ligjore')}
                  </div>
                  {result.risks?.length > 0 ? (
                      <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                          {result.risks.map((r, i) => <li key={i} className="leading-relaxed">{r}</li>)}
                      </ul>
                  ) : <p className="text-xs text-gray-500 italic">Nuk u gjetën rreziqe madhore.</p>}
              </div>

              {/* Contradictions */}
              <div className="space-y-3 p-4 bg-orange-900/10 rounded-xl border border-orange-500/10">
                  <div className="flex items-center gap-2 text-orange-400 font-bold border-b border-orange-500/30 pb-2 text-sm sm:text-base">
                      <FileText size={18} /> {t('analysis.contradictions', 'Kontradikta')}
                  </div>
                  {result.contradictions?.length > 0 ? (
                      <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                          {result.contradictions.map((c, i) => <li key={i} className="leading-relaxed">{c}</li>)}
                      </ul>
                  ) : <p className="text-xs text-gray-500 italic">Dokumentet janë konsistente.</p>}
              </div>

              {/* Missing Info */}
              <div className="space-y-3 p-4 bg-blue-900/10 rounded-xl border border-blue-500/10">
                  <div className="flex items-center gap-2 text-blue-400 font-bold border-b border-blue-500/30 pb-2 text-sm sm:text-base">
                      <HelpCircle size={18} /> {t('analysis.missing', 'Mungesa')}
                  </div>
                  {result.missing_info?.length > 0 ? (
                      <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                          {result.missing_info.map((m, i) => <li key={i} className="leading-relaxed">{m}</li>)}
                      </ul>
                  ) : <p className="text-xs text-gray-500 italic">Dosja duket e plotë.</p>}
              </div>

            </div>
          </div>
          
          {/* Footer (Fixed) */}
          <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0 safe-area-pb">
              <button onClick={onClose} className="w-full sm:w-auto px-6 py-3 sm:py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-medium transition-all shadow-lg glow-primary active:scale-95">
                  {t('general.close', 'Mbyll')}
              </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  // Render via Portal to ensure it sits on top of everything
  return ReactDOM.createPortal(modalContent, document.body);
};

export default AnalysisModal;