// FILE: src/components/case/GatekeeperNoticeModal.tsx
// PHOENIX PROTOCOL - GATEKEEPER NOTICE MODAL V33.0 (CLEAN PROFESSIONAL UI WITH X CLOSE & RIANALIZO)

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, FileText, RefreshCw, X } from 'lucide-react';

interface GatekeeperNoticeModalProps {
  notice: string | null;
  documentCount: number;
  onClose: () => void;
  onForceReanalyze?: () => void;
}

export const GatekeeperNoticeModal: React.FC<GatekeeperNoticeModalProps> = ({
  notice,
  documentCount,
  onClose,
  onForceReanalyze,
}) => {
  return (
    <AnimatePresence>
      {notice && (
        <div 
          className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[300] p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="glass-panel w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl border border-warning-start/30 bg-canvas text-center text-text-primary relative"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Top Right Close Icon X */}
            <button
              type="button"
              onClick={onClose}
              className="absolute top-4 right-4 p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all focus:outline-none"
              aria-label="Mbyll"
              title="Mbyll"
            >
              <X size={18} />
            </button>

            <div className="w-14 h-14 bg-amber-500/15 border border-amber-500/30 rounded-2xl flex items-center justify-center mx-auto mb-4 text-amber-400">
              <AlertTriangle size={28} />
            </div>

            <h3 className="text-lg sm:text-xl font-black uppercase tracking-tight mb-2">
              Analizë e Përditësuar
            </h3>

            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium mb-5 px-2">
              {notice}
            </p>

            <div className="p-3 bg-surface border border-main rounded-xl text-[11px] text-text-muted flex items-center gap-2 font-mono mb-6 justify-center">
              <FileText size={14} className="text-primary-start shrink-0" />
              <span>Dokumente të Analizuara: {documentCount}</span>
            </div>

            {/* Single Clean Professional Re-analyze Button */}
            {onForceReanalyze && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onForceReanalyze();
                }}
                className="btn-primary w-full h-11 rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-primary-start/15 flex items-center justify-center gap-2 transition-all active:scale-95 focus:outline-none"
              >
                <RefreshCw size={14} /> Rianalizo
              </button>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};