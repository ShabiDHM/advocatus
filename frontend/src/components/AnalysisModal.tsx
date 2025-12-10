// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V5.3 (THE DEBATE ARENA)
// 1. UI: Implements a "Split View" to visualize the two opposing parties and their claims.
// 2. LOGIC: Replaces 'Risks' with 'Conflicting Parties' data from the new backend logic.
// 3. UX: Highlights the 'Contradictions' as the central friction point of the case.

import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import { CaseAnalysisResult } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Scale, FileText, HelpCircle, User, ShieldAlert, Swords } from 'lucide-react';
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
        className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-0 sm:p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[95vh] sm:max-w-5xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0 gap-4">
            <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2 min-w-0">
              <div className="p-1.5 bg-primary-start/10 rounded-lg flex-shrink-0">
                 <Scale className="text-primary-start h-5 w-5 sm:h-6 sm:w-6" />
              </div>
              <span className="truncate">{t('analysis.modalTitle', 'Analiza Strategjike e Rastit')}</span>
            </h2>
            <button 
                onClick={onClose} 
                className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors flex-shrink-0"
            >
                <X size={24} />
            </button>
          </div>

          {/* Content (Scrollable) */}
          <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-background-dark/50">
            <style>{scrollbarStyles}</style>
            
            {/* 1. Executive Summary */}
            <div className="bg-background-light/20 p-5 rounded-xl border border-white/5">
              <h3 className="text-sm font-bold text-primary-start uppercase tracking-wider mb-2 flex items-center gap-2">
                  <FileText size={16}/> {t('analysis.summary', 'Përmbledhje e Konfliktit')}
              </h3>
              <p className="text-gray-200 text-sm leading-relaxed">{result.summary_analysis}</p>
            </div>

            {/* 2. THE ARENA: Conflicting Parties */}
            {result.conflicting_parties && result.conflicting_parties.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {result.conflicting_parties.map((party, idx) => (
                        <div key={idx} className={`p-4 rounded-xl border ${idx === 0 ? 'bg-blue-900/10 border-blue-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <User size={16} className={idx === 0 ? 'text-blue-400' : 'text-red-400'} />
                                <h4 className={`font-bold text-sm ${idx === 0 ? 'text-blue-300' : 'text-red-300'}`}>
                                    {party.party_name || `Pala ${idx + 1}`}
                                </h4>
                            </div>
                            <p className="text-gray-300 text-xs italic">"{party.core_claim}"</p>
                        </div>
                    ))}
                </div>
            )}

            {/* 3. The Clash: Contradictions */}
            {result.contradictions && result.contradictions.length > 0 && (
                <div className="bg-orange-900/10 p-5 rounded-xl border border-orange-500/20">
                    <h3 className="text-sm font-bold text-orange-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Swords size={16}/> {t('analysis.contradictions', 'Pikat e Përplasjes (Kontradiktat)')}
                    </h3>
                    <ul className="space-y-3">
                        {result.contradictions.map((c, i) => (
                            <li key={i} className="flex gap-3 text-sm text-gray-300 bg-black/20 p-3 rounded-lg border border-white/5">
                                <span className="text-orange-500 font-bold">•</span>
                                <span className="leading-relaxed">{c}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* 4. Evidence & Missing Info Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Key Evidence */}
                <div className="space-y-3">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                        <ShieldAlert size={14}/> {t('analysis.evidence', 'Provat Kyçe')}
                    </h4>
                    {result.key_evidence && result.key_evidence.length > 0 ? (
                        <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                            {result.key_evidence.map((e, i) => <li key={i}>{e}</li>)}
                        </ul>
                    ) : <p className="text-xs text-gray-500 italic">Nuk u identifikuan prova specifike.</p>}
                </div>

                {/* Missing Info */}
                <div className="space-y-3">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                        <HelpCircle size={14}/> {t('analysis.missing', 'Informacion i Munguar')}
                    </h4>
                    {result.missing_info && result.missing_info.length > 0 ? (
                        <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                            {result.missing_info.map((m, i) => <li key={i}>{m}</li>)}
                        </ul>
                    ) : <p className="text-xs text-gray-500 italic">Dosja duket e plotë.</p>}
                </div>
            </div>

          </div>
          
          {/* Footer */}
          <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold transition-all shadow-lg glow-primary">
                  {t('general.close', 'Mbyll')}
              </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default AnalysisModal;