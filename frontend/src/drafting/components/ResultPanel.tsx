// FILE: src/drafting/components/ResultPanel.tsx
// PHOENIX PROTOCOL – RESTORED & VISUALLY REINFORCED v12.3

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
      <div className="glass-panel border border-border-main rounded-3xl p-0 flex flex-col h-auto lg:h-[750px] shadow-sm relative group overflow-hidden bg-surface/20">
        
        {/* Executive Header Toolbar */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-border-main flex-shrink-0 relative z-50 pointer-events-auto bg-surface/40 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <div className={`${statusUI.color} p-2 bg-canvas border border-border-main rounded-xl shadow-inner`}>
              {statusUI.icon}
            </div>
            <h3 className="text-text-primary text-xs font-black uppercase tracking-widest leading-none">
              {statusUI.text}
            </h3>
          </div>

          <div className="flex items-center gap-2">
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

      {/* Save Modal - REPAIRED FOR FULL VISIBILITY */}
      <AnimatePresence>
        {saveModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#000000CC] backdrop-blur-md p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="bg-[#12141C] border-2 border-white/10 rounded-[2.5rem] p-8 w-full max-w-md shadow-[0_0_50px_rgba(0,0,0,0.8)] relative"
            >
              <div className="flex justify-between items-center mb-8">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-primary-start text-white rounded-2xl shadow-lg shadow-primary-start/20">
                    <Briefcase size={22} />
                  </div>
                  <h3 className="text-lg font-black text-white uppercase tracking-tight">
                    {t('drafting.saveToCaseModalTitle', 'Lidh me Rastin')}
                  </h3>
                </div>
                <button onClick={() => setSaveModalOpen(false)} className="p-2 text-white/40 hover:text-white transition-colors">
                  <X size={20} />
                </button>
              </div>

              <p className="text-sm font-semibold text-white/60 mb-8 leading-relaxed italic">
                {t('drafting.saveToCaseModalDesc', 'Eksporto këtë dokument drejtpërdrejt në dosjen e rastit tuaj aktiv.')}
              </p>

              <div className="mb-10">
                <label className="text-[11px] font-black text-primary-start uppercase tracking-[0.2em] mb-3 block ml-1">
                  {t('drafting.documentTitleLabel', 'Titulli i Dokumentit')}
                </label>
                <input 
                  type="text" 
                  value={documentTitle}
                  onChange={(e) => setDocumentTitle(e.target.value)}
                  placeholder={t('drafting.documentTitlePlaceholder', 'psh. Kontratë Pune...')}
                  className="w-full p-5 bg-white/5 border-2 border-white/10 rounded-2xl text-sm font-bold text-white focus:border-primary-start outline-none transition-all placeholder:text-white/20 shadow-inner"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <button 
                  onClick={() => setSaveModalOpen(false)} 
                  className="py-4 px-6 bg-white/5 border border-white/10 text-white rounded-2xl text-[11px] font-black uppercase tracking-widest hover:bg-white/10 transition-all active:scale-95"
                >
                  {t('common.cancel', 'Anulo')}
                </button>
                <button
                  onClick={() => {
                    onSaveToCase(documentTitle.trim() || t('drafting.untitledDocument', 'Dokument i Paemërtuar'));
                    setSaveModalOpen(false);
                  }}
                  className="py-4 px-6 bg-primary-start text-white rounded-2xl text-[11px] font-black uppercase tracking-widest hover:shadow-xl hover:shadow-primary-start/30 transition-all active:scale-95"
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