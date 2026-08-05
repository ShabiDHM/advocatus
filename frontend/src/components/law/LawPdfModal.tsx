// FILE: src/components/law/LawPdfModal.tsx
// PHOENIX PROTOCOL - LAW PDF MODAL V2.0 (VIEW-ONLY MODE - DOWNLOAD BUTTON REMOVED)

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Minus, X, Maximize2 } from 'lucide-react';
import { ArticleData } from './lawArticleTypes';

interface LawPdfModalProps {
  showPdfModal: boolean;
  isPdfMinimized: boolean;
  pdfUrl: string | null;
  article: ArticleData;
  onCloseModal: () => void;
  onMinimizeModal: (minimized: boolean) => void;
}

export const LawPdfModal: React.FC<LawPdfModalProps> = ({
  showPdfModal,
  isPdfMinimized,
  pdfUrl,
  article,
  onCloseModal,
  onMinimizeModal,
}) => {
  return (
    <>
      {/* FULLSCREEN VIEW-ONLY PDF MODAL */}
      <AnimatePresence>
        {showPdfModal && !isPdfMinimized && pdfUrl && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-2 sm:p-4">
            <motion.div
              initial={{ scale: 0.98, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.98, opacity: 0, y: 10 }}
              transition={{ duration: 0.2 }}
              className="glass-panel w-[95vw] max-w-7xl h-[92vh] rounded-3xl border border-main flex flex-col overflow-hidden shadow-2xl bg-canvas"
            >
              {/* MODAL HEADER - STRICT VIEW-ONLY CONTROLS */}
              <div className="px-5 py-4 bg-surface border-b border-main flex justify-between items-center shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20 shrink-0">
                    <FileText size={18} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-tight truncate">
                      {article.law_title}
                    </h3>
                    <p className="text-xs text-text-muted font-mono truncate">
                      {article.source} • SHIKIM ZYRTAR
                    </p>
                  </div>
                </div>

                {/* HEADER ACTIONS: MINIMIZE AND CLOSE ONLY */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onMinimizeModal(true)}
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none cursor-pointer"
                    title="Minimizo"
                    aria-label="Minimizo"
                  >
                    <Minus size={18} />
                  </button>

                  <button
                    type="button"
                    onClick={onCloseModal}
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none cursor-pointer"
                    title="Mbyll"
                    aria-label="Mbyll"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              {/* PDF EMBEDDED IFRAME SURFACE */}
              <div className="flex-1 w-full h-full bg-slate-900 relative p-4">
                <iframe src={pdfUrl} title={article.law_title} className="w-full h-full border-none" />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MINIMIZED FLOATING CONTROLLER */}
      <AnimatePresence>
        {showPdfModal && isPdfMinimized && (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 50, opacity: 0 }}
            className="fixed bottom-6 right-6 z-[250] flex items-center gap-3 p-3.5 bg-slate-900/95 text-white border border-slate-700/80 rounded-2xl shadow-2xl backdrop-blur-xl max-w-md"
          >
            <div className="p-2.5 bg-sky-500/15 text-sky-400 rounded-xl shrink-0 border border-sky-500/30">
              <FileText size={18} />
            </div>

            <div className="min-w-0 flex-1 cursor-pointer" onClick={() => onMinimizeModal(false)}>
              <p className="text-xs font-bold text-slate-100 truncate tracking-tight">{article.law_title}</p>
              <p className="text-[10px] text-sky-400/90 font-mono truncate">{article.source} • I MINIMIZUAR</p>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => onMinimizeModal(false)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all focus:outline-none cursor-pointer"
                title="Zgjero (Full Screen)"
              >
                <Maximize2 size={16} />
              </button>

              <button
                type="button"
                onClick={onCloseModal}
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition-all focus:outline-none cursor-pointer"
                title="Mbyll"
              >
                <X size={16} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};