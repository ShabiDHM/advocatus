// FILE: frontend/src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - MOBILE PERFECTED
// 1. LAYOUT: Stacks 3 columns on mobile (grid-cols-1), side-by-side on desktop (md:grid-cols-3).
// 2. PADDING: Responsive padding (p-4 on mobile, p-6 on desktop) to maximize reading space.
// 3. SCROLLBAR: Sleek, dark scrollbar integrated.

import React from 'react';
import { CaseAnalysisResult } from '../data/types';
import { motion } from 'framer-motion';
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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-background-dark border border-glass-edge rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header (Fixed) */}
        <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/50 flex-shrink-0">
          <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2">
            <Scale className="text-primary-start h-5 w-5 sm:h-6 sm:w-6" />
            {t('analysis.modalTitle', 'Analiza e Rastit')}
          </h2>
          <button onClick={onClose} className="text-text-secondary hover:text-white transition-colors p-1"><X size={24} /></button>
        </div>

        {/* Content (Scrollable) */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative">
          <style>{scrollbarStyles}</style>
          
          {/* Summary */}
          <div className="bg-background-light/30 p-4 rounded-xl border border-glass-edge">
            <h3 className="text-base sm:text-lg font-semibold text-white mb-2">{t('analysis.summary', 'Përmbledhje Ekzekutive')}</h3>
            <p className="text-text-secondary text-sm leading-relaxed whitespace-pre-wrap">{result.summary_analysis}</p>
          </div>

          {/* 3 Columns Grid (Stacks on Mobile) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Risks */}
            <div className="space-y-3">
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
            <div className="space-y-3">
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
            <div className="space-y-3">
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
        <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0">
            <button onClick={onClose} className="w-full sm:w-auto px-6 py-3 sm:py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-medium transition-all shadow-lg glow-primary">
                {t('general.close', 'Mbyll')}
            </button>
        </div>
      </motion.div>
    </div>
  );
};

export default AnalysisModal;