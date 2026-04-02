// FILE: src/drafting/components/ResultPanel.tsx
// PHOENIX PROTOCOL – REMOVED SAVE TO CASE BUTTON & MODAL

import React, { useMemo, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, AlertCircle, CheckCircle, Clock,
  FileText, Trash2, Scale, Copy,
  BrainCircuit
} from 'lucide-react';
import { ResultPanelProps } from '../types';
import { ThinkingDots } from './ThinkingDots';
import { DraftResultRenderer } from './DraftResultRenderer';

export const ResultPanel: React.FC<ResultPanelProps> = ({
  t,
  currentJob,
  notification,
  onRetry,
  onClear}) => {
  const [] = useState(''); // kept only to avoid hook order change, not used
  const documentRef = useRef<HTMLDivElement>(null);

  const statusUI = useMemo(() => {
    switch (currentJob.status) {
      case 'COMPLETED':
        return { text: t('drafting.statusCompleted', 'Përfunduar'), color: 'text-success-start', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED':
        return { text: t('drafting.statusFailed', 'Dështoi'), color: 'text-danger-start', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING':
        return { text: t('drafting.statusWorking', 'Duke Gjeneruar...'), color: 'text-warning-start', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default:
        return { text: t('drafting.statusResult', 'Rezultati'), color: 'text-primary-start', icon: <Scale className="h-5 w-5" /> };
    }
  }, [currentJob.status, t]);

  const actionButtonBase = "p-3 bg-surface border border-border-main text-text-primary hover:text-primary-start hover:border-primary-start/50 rounded-xl transition-all shadow-sm hover:shadow-md hover-lift disabled:opacity-30 disabled:hover:shadow-none pointer-events-auto flex items-center justify-center";

  const handleCopy = () => {
    if (!currentJob.result) return;
    if (documentRef.current) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(documentRef.current);
      selection?.removeAllRanges();
      selection?.addRange(range);
      try {
        document.execCommand('copy');
      } catch (err) {
        navigator.clipboard.writeText(documentRef.current.innerText);
      } finally {
        selection?.removeAllRanges();
      }
    }
  };

  return (
    <>
      <div className="glass-panel border border-border-main rounded-3xl p-0 flex flex-col h-auto lg:h-[750px] shadow-sm relative group overflow-hidden">
        
        {/* Executive Header Toolbar */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-border-main flex-shrink-0 relative z-50 pointer-events-auto">
          <div className="flex items-center gap-4">
            <div className={`${statusUI.color} p-2 bg-canvas border border-border-main rounded-xl shadow-inner`}>
              {statusUI.icon}
            </div>
            <h3 className="text-text-primary text-xs font-black uppercase tracking-widest leading-none">
              {statusUI.text}
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={handleCopy} title={t('drafting.copy', 'Kopjo')} disabled={!currentJob.result} className={actionButtonBase}>
              <Copy size={18} className="stroke-[2.5px]" />
            </button>

            {currentJob.status === 'FAILED' && (
              <button onClick={onRetry} title={t('common.retry', 'Riprovo')} className={actionButtonBase}>
                <RefreshCw size={18} className="text-danger-start" />
              </button>
            )}

            <div className="h-6 w-px bg-border-main mx-1" />

            <button
              onClick={onClear}
              title={t('drafting.clear', 'Pastro')}
              disabled={!currentJob.result && currentJob.status !== 'FAILED'}
              className="p-3 bg-surface border border-border-main text-danger-start hover:text-danger-start/80 hover:border-danger-start/30 rounded-xl transition-all shadow-sm hover:shadow-md disabled:opacity-30 hover-lift flex items-center justify-center"
            >
              <Trash2 size={18} className="stroke-[2.5px]" />
            </button>
          </div>
        </div>

        {/* Viewer Area */}
        <div className="flex-1 bg-transparent overflow-y-auto custom-scrollbar p-6 sm:p-10 relative z-10">
          <div className="min-h-full w-full flex flex-col items-center">
            {notification && (
              <motion.div 
                initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                className={`mb-6 px-5 py-3 text-xs font-black uppercase tracking-widest rounded-xl flex items-center gap-3 border shadow-md w-full max-w-[21cm] z-20 ${
                  notification.type === 'success' ? 'bg-success-start/10 text-success-start border-success-start/20' : 'bg-danger-start/10 text-danger-start border-danger-start/20'
                }`}
              >
                {notification.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                {notification.msg}
              </motion.div>
            )}

            <AnimatePresence mode="wait">
              {currentJob.result ? (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="w-full max-w-[21cm]"
                >
                  <div
                    ref={documentRef}
                    className="bg-white text-black p-12 sm:p-16 shadow-[0_0_40px_rgba(0,0,0,0.1)] rounded-sm min-h-[29.7cm] border border-gray-200 font-serif leading-relaxed text-[11pt]"
                  >
                    <div className="text-black prose-p:text-black prose-headings:text-black prose-strong:text-black">
                      <DraftResultRenderer text={currentJob.result} t={t} />
                    </div>
                  </div>
                </motion.div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center mt-32 opacity-50">
                   {currentJob.status === 'PROCESSING' ? (
                     <div className="flex flex-col items-center">
                        <BrainCircuit className="w-10 h-10 text-primary-start animate-pulse mb-4" />
                        <p className="text-text-primary font-black uppercase tracking-widest text-xs">
                          {t('drafting.statusWorking', 'Duke Gjeneruar Dokumentin')}
                          <ThinkingDots />
                        </p>
                     </div>
                   ) : (
                     <FileText size={64} className="text-text-muted mb-6" strokeWidth={1.5} />
                   )}
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Save modal is removed entirely */}
    </>
  );
};