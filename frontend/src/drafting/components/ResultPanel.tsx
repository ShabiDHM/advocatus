// FILE: src/drafting/components/ResultPanel.tsx
// ARCHITECTURE: PIXEL-PERFECT THEME SYNC & STREAMLINED UX – COPY EXACT VISIBLE CONTENT

import React, { useMemo, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, AlertCircle, CheckCircle, Clock,
  FileText, Trash2, Scale, Copy, Download,
  BrainCircuit, Briefcase, X
} from 'lucide-react';
import { ResultPanelProps } from '../types';
import { ThinkingDots } from './ThinkingDots';
import { DraftResultRenderer } from './DraftResultRenderer';

export const ResultPanel: React.FC<ResultPanelProps> = ({
  t,
  currentJob,
  saving,
  notification,
  onRetry,
  onClear,
  selectedCaseId,
  saveModalOpen,
  setSaveModalOpen,
  onSaveToCase
}) => {
  const [documentTitle, setDocumentTitle] = useState('');
  // Ref to the white A4 canvas that holds the rendered document
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

    // Try to copy the exact visible content by programmatically selecting the document area.
    if (documentRef.current) {
      // Save current selection (if any)
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(documentRef.current);
      selection?.removeAllRanges();
      selection?.addRange(range);

      try {
        // Copy the selected content
        const success = document.execCommand('copy');
        if (success) {
          // Clear selection
          selection?.removeAllRanges();
          // Optional: show a small notification that it worked (already handled via toast?)
          return;
        }
      } catch (err) {
        console.warn('Copy failed, falling back to innerText', err);
      } finally {
        // Ensure selection is cleared
        selection?.removeAllRanges();
      }
    }

    // Fallback: copy innerText (or raw markdown)
    if (documentRef.current) {
      navigator.clipboard.writeText(documentRef.current.innerText);
    } else {
      navigator.clipboard.writeText(currentJob.result);
    }
  };

  const handleDownload = () => {
    if (currentJob.result) {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const casePrefix = selectedCaseId ? `Rasti_${selectedCaseId}_` : '';
      a.download = `Advokatus_${casePrefix}Dokument_${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handleOpenSaveModal = () => {
    setDocumentTitle(''); 
    setSaveModalOpen(true);
  };

  return (
    <>
      {/* Outer wrapper: Strictly "glass-panel" without any hardcoded background colors */}
      <div className="glass-panel border border-border-main rounded-3xl p-0 flex flex-col h-auto lg:h-[750px] shadow-sm relative group overflow-hidden">
        
        {/* Executive Header Toolbar */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-border-main flex-shrink-0 relative z-50 pointer-events-auto bg-transparent">
          <div className="flex items-center gap-4">
            <div className={`${statusUI.color} p-2 bg-canvas border border-border-main rounded-xl shadow-inner`}>
              {statusUI.icon}
            </div>
            <h3 className="text-text-primary text-xs font-black uppercase tracking-widest leading-none">
              {statusUI.text}
            </h3>
          </div>

          <div className="flex items-center gap-2">
            
            {/* Save to Case Button - Now unconditionally active if there is a result */}
            <button
              onClick={handleOpenSaveModal}
              title={t('drafting.saveToCase', 'Lidh me Rastin')}
              disabled={!currentJob.result || saving}
              className={actionButtonBase}
            >
              <Briefcase size={18} className="stroke-[2.5px]" />
            </button>
            
            <button onClick={handleCopy} title={t('drafting.copy', 'Kopjo')} disabled={!currentJob.result} className={actionButtonBase}>
              <Copy size={18} className="stroke-[2.5px]" />
            </button>
            
            <button onClick={handleDownload} title={t('drafting.download', 'Shkarko')} disabled={!currentJob.result} className={actionButtonBase}>
              <Download size={18} className="stroke-[2.5px]" />
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

        {/* The "Viewer" Area - Now COMPLETELY transparent so the glass-panel matches the left side 100% */}
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
                  exit={{ opacity: 0, scale: 0.98 }}
                  className="w-full max-w-[21cm]"
                >
                  {/* BULLETPROOF A4 CANVAS (Stays purely white despite dark mode) */}
                  <div
                    ref={documentRef}
                    className="bg-white text-black p-12 sm:p-16 shadow-[0_0_40px_rgba(0,0,0,0.1)] dark:shadow-[0_0_50px_rgba(0,0,0,0.4)] rounded-sm min-h-[29.7cm] border border-gray-200 font-serif leading-relaxed text-[11pt]"
                  >
                    <div className="text-black prose-p:text-black prose-headings:text-black prose-strong:text-black">
                      <DraftResultRenderer text={currentJob.result} t={t} />
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center text-center mt-32 pointer-events-none opacity-50"
                >
                  {currentJob.status === 'PROCESSING' ? (
                    <div className="flex flex-col items-center">
                      <div className="w-20 h-20 rounded-[1.5rem] bg-primary-start flex items-center justify-center shadow-[0_0_30px_rgba(var(--primary-start-rgb),0.5)] mb-8 animate-pulse">
                        <BrainCircuit className="w-10 h-10 text-white" />
                      </div>
                      <p className="text-text-primary font-black uppercase tracking-widest text-xs">
                        {t('drafting.statusWorking', 'Duke Gjeneruar Dokumentin')}
                        <ThinkingDots />
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <FileText size={64} className="text-text-muted mb-6" strokeWidth={1.5} />
                      <p className="text-text-muted font-black text-xs uppercase tracking-widest">
                        {t('drafting.emptyState', 'Rezultati do të shfaqet këtu')}
                      </p>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Save Modal Overlays */}
      <AnimatePresence>
        {saveModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/60 backdrop-blur-sm pointer-events-auto p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-surface border border-border-main rounded-3xl p-6 sm:p-8 w-full max-w-md shadow-2xl relative"
            >
              <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary-start/10 rounded-xl border border-primary-start/20 text-primary-start">
                    <Briefcase size={20} />
                  </div>
                  <h3 className="text-sm font-black text-text-primary uppercase tracking-widest leading-none">
                    {t('drafting.saveToCaseModalTitle', 'Lidh me Rastin')}
                  </h3>
                </div>
                <button onClick={() => setSaveModalOpen(false)} className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors">
                  <X size={18} />
                </button>
              </div>
              <p className="text-sm font-medium text-text-muted mb-6 leading-relaxed">
                {t('drafting.saveToCaseModalDesc', 'Eksporto këtë dokument drejtpërdrejt në dosjen e rastit tuaj aktiv.')}
              </p>
              <div className="mb-8">
                <label className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-2 block">
                  {t('drafting.documentTitleLabel', 'Titulli i Dokumentit')}
                </label>
                <input 
                  type="text" 
                  value={documentTitle}
                  onChange={(e) => setDocumentTitle(e.target.value)}
                  placeholder={t('drafting.documentTitlePlaceholder', 'psh. Kontratë Pune ose Padi...')}
                  className="w-full p-4 bg-canvas border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start outline-none transition-all placeholder:text-text-muted/50"
                  autoFocus
                />
              </div>
              <div className="flex gap-4 w-full">
                <button onClick={() => setSaveModalOpen(false)} className="flex-1 py-3.5 px-4 bg-transparent border border-border-main text-text-primary rounded-xl text-xs font-black uppercase tracking-widest hover:bg-hover transition-all">
                  {t('common.cancel', 'Anulo')}
                </button>
                <button
                  onClick={() => {
                    onSaveToCase(documentTitle.trim() || t('drafting.untitledDocument', 'Dokument i Paemërtuar'));
                    setSaveModalOpen(false);
                  }}
                  className="flex-1 py-3.5 px-4 bg-primary-start text-white rounded-xl text-xs font-black uppercase tracking-widest hover:shadow-lg hover:shadow-primary-start/20 transition-all"
                >
                  {t('common.confirm', 'Ruaj')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};