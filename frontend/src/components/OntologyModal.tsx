// FILE: frontend/src/components/OntologyModal.tsx
// PHOENIX PROTOCOL - ONTOLOGY MODAL V7.0 (OPAQUE TASKBAR MINIMIZATION DOCK)

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Network, X, Maximize2, Minimize2, Minus } from 'lucide-react';
import EvidenceGraphTab from './EvidenceGraphTab';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

interface OntologyModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle?: string;
  clientPosition?: 'DEFENDANT' | 'PLAINTIFF';
}

export const OntologyModal: React.FC<OntologyModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseTitle,
  clientPosition = 'DEFENDANT',
}) => {
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  useLockBodyScroll(isOpen && !isMinimized);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isMinimized ? (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.9 }}
          className="fixed bottom-4 right-4 z-[300] flex items-center gap-3 bg-surface border-2 border-primary-start px-4 py-2.5 rounded-2xl shadow-2xl text-text-primary cursor-pointer opacity-100 backdrop-blur-xl hover:border-primary-start"
          onClick={() => setIsMinimized(false)}
        >
          <div className="w-8 h-8 rounded-xl bg-primary-start/15 text-primary-start flex items-center justify-center border border-primary-start/30 shrink-0">
            <Network size={16} />
          </div>
          <div className="flex flex-col text-left min-w-0 pr-2">
            <span className="text-xs font-black uppercase text-text-primary truncate">
              Ontologjia e Provave
            </span>
            <span className="text-[10px] text-text-muted font-medium truncate">
              {caseTitle || 'Grafiku i Minimizuar'}
            </span>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsMinimized(false);
            }}
            className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-colors"
            title="Zmadho përsëri"
          >
            <Maximize2 size={15} />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
              setIsMinimized(false);
            }}
            className="p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors"
            title="Mbyll"
          >
            <X size={15} />
          </button>
        </motion.div>
      ) : (
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
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20 shrink-0">
                  <Network size={20} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">
                      Ontologjia e Provave
                    </h3>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-primary-start/10 text-primary-start border border-primary-start/20 shrink-0">
                      {clientPosition === 'DEFENDANT' ? '🛡️ I PADITUR' : '⚔️ PADITËSI'}
                    </span>
                  </div>
                  {caseTitle && (
                    <p className="text-xs text-text-muted font-medium truncate mt-0.5">
                      Lënda: {caseTitle}
                    </p>
                  )}
                </div>
              </div>

              {/* Header Controls */}
              <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsFullScreen(!isFullScreen)}
                  className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all focus:outline-none"
                  title={isFullScreen ? 'Zvogëlo në madhësi standarde' : 'Zmadho në ekran të plotë'}
                >
                  {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                </button>

                <button
                  type="button"
                  onClick={() => setIsMinimized(true)}
                  className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
                  title="Minimizo në taskbar"
                >
                  <Minus size={18} />
                </button>

                <button
                  type="button"
                  onClick={onClose}
                  className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
                  aria-label="Mbyll"
                  title="Mbyll"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* MODAL BODY (ONTOLOGY GRAPH CANVAS) */}
            <div className="flex-1 overflow-hidden p-2 sm:p-3 bg-canvas relative">
              <EvidenceGraphTab caseId={caseId} caseTitle={caseTitle} />
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
      )}
    </AnimatePresence>
  );
};

export default OntologyModal;