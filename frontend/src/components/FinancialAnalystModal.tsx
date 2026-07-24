// FILE: frontend/src/components/FinancialAnalystModal.tsx
// PHOENIX PROTOCOL - FINANCIAL ANALYST MODAL V2.0 (STANDARDIZED EXECUTIVE SIZE: 95VW x 92VH)

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, X, Maximize2, Minimize2 } from 'lucide-react';
import SpreadsheetAnalyst from './SpreadsheetAnalyst';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

interface FinancialAnalystModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle?: string;
}

export const FinancialAnalystModal: React.FC<FinancialAnalystModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseTitle,
}) => {
  const [isFullScreen, setIsFullScreen] = useState(false);
  useLockBodyScroll(isOpen);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-2 sm:p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ duration: 0.2 }}
          className={`glass-panel w-[95vw] rounded-3xl shadow-2xl border border-main bg-canvas flex flex-col overflow-hidden transition-all duration-300 ${
            isFullScreen ? 'w-full h-full max-w-none rounded-none' : 'max-w-7xl h-[92vh]'
          }`}
        >
          {/* MODAL HEADER */}
          <div className="p-4 sm:p-5 border-b border-main bg-surface flex flex-wrap items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20 shrink-0">
                <Activity size={20} />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight">
                  Analisti Financiar Forenzik
                </h3>
                {caseTitle && (
                  <p className="text-xs text-text-muted font-medium truncate mt-0.5">
                    Lënda: {caseTitle}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsFullScreen(!isFullScreen)}
                className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors"
                title={isFullScreen ? 'Zvogëlo' : 'Zmadho në Ekran të Plotë'}
              >
                {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* MODAL BODY (SPREADSHEET ANALYST) */}
          <div className="flex-1 overflow-y-auto p-2 sm:p-4 bg-canvas">
            <SpreadsheetAnalyst caseId={caseId} />
          </div>

          {/* MODAL FOOTER */}
          <div className="p-3.5 sm:p-4 border-t border-main bg-surface flex items-center justify-end shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="h-10 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-md shadow-primary-start/15 transition-all"
            >
              Mbyll
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default FinancialAnalystModal;