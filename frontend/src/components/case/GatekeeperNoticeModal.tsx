// FILE: src/components/case/GatekeeperNoticeModal.tsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, FileText } from 'lucide-react';

interface GatekeeperNoticeModalProps {
  notice: string | null;
  documentCount: number;
  onClose: () => void;
}

export const GatekeeperNoticeModal: React.FC<GatekeeperNoticeModalProps> = ({ notice, documentCount, onClose }) => {
  return (
    <AnimatePresence>
      {notice && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[300] p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="glass-panel w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl border border-warning-start/30 bg-canvas text-center text-text-primary"
          >
            <div className="w-14 h-14 bg-warning-start/15 border border-warning-start/30 rounded-2xl flex items-center justify-center mx-auto mb-5 text-warning-start">
              <AlertTriangle size={28} />
            </div>

            <h3 className="text-lg sm:text-xl font-bold uppercase tracking-tight mb-3">
              S'ka Ndryshime në Lëndë
            </h3>

            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium mb-6">
              {notice}
            </p>

            <div className="p-3.5 bg-surface border border-main rounded-xl text-[11px] text-text-muted flex items-center gap-2 font-mono mb-6 justify-center">
              <FileText size={14} className="text-primary-start shrink-0" />
              <span>Dokumente Aktive: {documentCount}</span>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="btn-primary w-full h-11 rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-primary-start/15 focus:outline-none"
            >
              E Kuptova
            </button>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};