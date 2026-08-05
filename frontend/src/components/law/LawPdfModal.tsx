// FILE: src/components/law/LawPdfModal.tsx
// PHOENIX PROTOCOL - LAW PDF MODAL V5.0 (DIRECT FASTAPI BLOB & FALLBACK IFRAME)

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Minus, X, Maximize2, Loader2 } from 'lucide-react';
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
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoadingBlob, setIsLoadingBlob] = useState<boolean>(false);
  const [useFallbackIframe, setUseFallbackIframe] = useState<boolean>(false);

  useEffect(() => {
    if (!showPdfModal || !pdfUrl) {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
      }
      setUseFallbackIframe(false);
      return;
    }

    let isMounted = true;
    setIsLoadingBlob(true);
    setUseFallbackIframe(false);

    fetch(pdfUrl)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to stream PDF blob');
        return res.blob();
      })
      .then((blob) => {
        if (isMounted) {
          const createdBlobUrl = URL.createObjectURL(
            new Blob([blob], { type: 'application/pdf' })
          );
          setBlobUrl(createdBlobUrl);
        }
      })
      .catch((err) => {
        console.warn('Blob stream fallback triggered:', err);
        if (isMounted) setUseFallbackIframe(true);
      })
      .finally(() => {
        if (isMounted) setIsLoadingBlob(false);
      });

    return () => {
      isMounted = false;
    };
  }, [showPdfModal, pdfUrl]);

  return (
    <>
      <AnimatePresence>
        {showPdfModal && !isPdfMinimized && pdfUrl && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[200] p-1 sm:p-4">
            <motion.div
              initial={{ scale: 0.98, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.98, opacity: 0, y: 10 }}
              transition={{ duration: 0.2 }}
              className="glass-panel w-full sm:w-[95vw] max-w-7xl h-[95vh] sm:h-[92vh] rounded-2xl sm:rounded-3xl border border-main flex flex-col overflow-hidden shadow-2xl bg-canvas"
            >
              {/* MODAL HEADER */}
              <div className="px-4 sm:px-5 py-3 sm:py-4 bg-surface border-b border-main flex justify-between items-center shrink-0">
                <div className="flex items-center gap-2.5 sm:gap-3 min-w-0 pr-2">
                  <div className="p-2 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20 shrink-0">
                    <FileText size={18} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-xs sm:text-sm font-black text-text-primary uppercase tracking-tight truncate">
                      {article.law_title}
                    </h3>
                    <p className="text-[10px] sm:text-xs text-text-muted font-mono truncate">
                      {article.source} • SHIKIM ZYRTAR
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => onMinimizeModal(true)}
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none cursor-pointer"
                    title="Minimizo"
                  >
                    <Minus size={18} />
                  </button>

                  <button
                    type="button"
                    onClick={onCloseModal}
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none cursor-pointer"
                    title="Mbyll"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              {/* PDF STREAM SURFACE */}
              <div className="flex-1 w-full h-full bg-slate-900 relative p-1 sm:p-4 flex items-center justify-center">
                {isLoadingBlob && (
                  <div className="flex flex-col items-center justify-center gap-3 text-slate-300">
                    <Loader2 size={32} className="animate-spin text-primary-start" />
                    <span className="text-xs font-bold uppercase tracking-wider">
                      Duke ngarkuar dokumentin PDF...
                    </span>
                  </div>
                )}

                {!isLoadingBlob && blobUrl && (
                  <iframe
                    src={`${blobUrl}#toolbar=0&navpanes=0`}
                    title={article.law_title}
                    className="w-full h-full border-none rounded-xl"
                  />
                )}

                {!isLoadingBlob && useFallbackIframe && (
                  <iframe
                    src={pdfUrl}
                    title={article.law_title}
                    className="w-full h-full border-none rounded-xl"
                  />
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MINIMIZED CONTROLLER */}
      <AnimatePresence>
        {showPdfModal && isPdfMinimized && (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 50, opacity: 0 }}
            className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-[250] flex items-center gap-3 p-3 sm:p-3.5 bg-slate-900/95 text-white border border-slate-700/80 rounded-2xl shadow-2xl backdrop-blur-xl max-w-sm sm:max-w-md"
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
                title="Zgjero"
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