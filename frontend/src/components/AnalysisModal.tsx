// FILE: frontend/src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - NEW COMPONENT
// Displays Cross-Examination Results with 3 distinct risk sections.

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

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result }) => {
  const { t } = useTranslation();
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-background-dark border border-glass-edge rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/50">
          <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Scale className="text-primary-start h-6 w-6" />
            {t('analysis.modalTitle', 'Analiza e Rastit')}
          </h2>
          <button onClick={onClose} className="text-text-secondary hover:text-white"><X size={24} /></button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          
          {/* Summary */}
          <div className="bg-background-light/30 p-4 rounded-xl border border-glass-edge">
            <h3 className="text-lg font-semibold text-white mb-2">{t('analysis.summary', 'Përmbledhje Ekzekutive')}</h3>
            <p className="text-text-secondary text-sm leading-relaxed">{result.summary_analysis}</p>
          </div>

          {/* 3 Columns Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            {/* Risks */}
            <div className="space-y-3">
                <div className="flex items-center gap-2 text-red-400 font-bold border-b border-red-500/30 pb-2">
                    <AlertTriangle size={18} /> {t('analysis.risks', 'Rreziqe Ligjore')}
                </div>
                {result.risks?.length > 0 ? (
                    <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                        {result.risks.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                ) : <p className="text-xs text-gray-500 italic">Nuk u gjetën rreziqe madhore.</p>}
            </div>

            {/* Contradictions */}
            <div className="space-y-3">
                <div className="flex items-center gap-2 text-orange-400 font-bold border-b border-orange-500/30 pb-2">
                    <FileText size={18} /> {t('analysis.contradictions', 'Kontradikta')}
                </div>
                {result.contradictions?.length > 0 ? (
                    <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                        {result.contradictions.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                ) : <p className="text-xs text-gray-500 italic">Dokumentet janë konsistente.</p>}
            </div>

            {/* Missing Info */}
            <div className="space-y-3">
                <div className="flex items-center gap-2 text-blue-400 font-bold border-b border-blue-500/30 pb-2">
                    <HelpCircle size={18} /> {t('analysis.missing', 'Mungesa')}
                </div>
                {result.missing_info?.length > 0 ? (
                    <ul className="list-disc pl-4 space-y-2 text-sm text-gray-300">
                        {result.missing_info.map((m, i) => <li key={i}>{m}</li>)}
                    </ul>
                ) : <p className="text-xs text-gray-500 italic">Dosja duket e plotë.</p>}
            </div>

          </div>
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center">
            <button onClick={onClose} className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-medium transition-all">
                {t('general.close', 'Mbyll')}
            </button>
        </div>
      </motion.div>
    </div>
  );
};

export default AnalysisModal;