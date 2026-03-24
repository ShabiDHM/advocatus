// FILE: src/drafting/components/ResultPanel.tsx
// PHOENIX PROTOCOL - RESULT PANEL V6.8 (WHITE PAPER + FIXED HOVER)

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, AlertCircle, CheckCircle, Clock,
  FileText, Trash2, Archive, Scale, Copy, Download,
  BrainCircuit
} from 'lucide-react';
import { ResultPanelProps } from '../types';
import { ThinkingDots } from './ThinkingDots';
import { DraftResultRenderer } from './DraftResultRenderer';

export const ResultPanel: React.FC<ResultPanelProps> = ({
  t,
  currentJob,
  saving,
  notification,
  onSave,
  onRetry,
  onClear,
}) => {
  
  const statusUI = useMemo(() => {
    switch (currentJob.status) {
      case 'COMPLETED':
        return { text: t('drafting.statusCompleted'), color: 'text-success-start', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED':
        return { text: t('drafting.statusFailed'), color: 'text-danger-start', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING':
        return { text: t('drafting.statusWorking'), color: 'text-warning-start', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default:
        return { text: t('drafting.statusResult', 'Rezultati'), color: 'text-primary-start', icon: <Scale className="h-5 w-5" /> };
    }
  }, [currentJob.status, t]);

  const actionButtonBase = "p-3 bg-surface border border-border-main text-text-muted hover:text-primary-start hover:border-primary-start/50 rounded-xl transition-all shadow-sm hover:shadow-md hover-lift disabled:opacity-30 disabled:hover:shadow-none";

  return (
    <div className="glass-panel border border-border-main p-0 flex flex-col h-auto lg:h-[700px] overflow-hidden shadow-sm hover-lift rounded-3xl hover:border-primary-start/50 transition-all duration-300">
      
      {/* Executive Header Toolbar - removed z-10 */}
      <div className="flex justify-between items-center px-6 py-4 bg-surface border-b border-border-main flex-shrink-0 relative">
        <div className="flex items-center gap-4">
          <div className={`${statusUI.color} p-2 bg-canvas border border-border-main rounded-xl shadow-inner`}>
            {statusUI.icon}
          </div>
          <h3 className="text-text-primary text-xs font-black uppercase tracking-widest leading-none">
            {statusUI.text}
          </h3>
        </div>
        
        {/* Action Button Cluster */}
        <div className="flex items-center gap-2">
          <button
            onClick={onSave}
            title={t('drafting.saveToArchive')}
            disabled={!currentJob.result || saving}
            className={actionButtonBase}
          >
            {saving ? <RefreshCw className="animate-spin" size={16} /> : <Archive size={16} />}
          </button>
          <button
            onClick={() => {
              if (currentJob.result) {
                navigator.clipboard.writeText(currentJob.result);
              }
            }}
            title={t('drafting.copy')}
            disabled={!currentJob.result}
            className={actionButtonBase}
          >
            <Copy size={16} />
          </button>
          <button
            onClick={() => {
              if (currentJob.result) {
                const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `draft-${Date.now()}.txt`;
                a.click();
                URL.revokeObjectURL(url);
              }
            }}
            title={t('drafting.download')}
            disabled={!currentJob.result}
            className={actionButtonBase}
          >
            <Download size={16} />
          </button>
          
          {currentJob.status === 'FAILED' && (
            <button onClick={onRetry} title="Riprovo" className="p-3 text-warning-start bg-surface border border-border-main hover:border-warning-start/30 rounded-xl transition-all hover-lift">
              <RefreshCw size={16} />
            </button>
          )}
          
          <div className="h-6 w-px bg-border-main mx-1" />
          
          <button
            onClick={onClear}
            title={t('drafting.clear')}
            disabled={!currentJob.result && currentJob.status !== 'FAILED'}
            className="p-3 text-danger-start bg-surface border border-border-main hover:border-danger-start/30 rounded-xl transition-all disabled:opacity-30 hover-lift"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* The Paper Reading Surface */}
      <div className="flex-1 bg-surface/30 overflow-y-auto custom-scrollbar p-6 sm:p-10">
        <div className="min-h-full w-full flex justify-center">
          <AnimatePresence mode="wait">
            {currentJob.result ? (
              <motion.div
                key="result"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="w-full max-w-[21cm]"
              >
                {notification && (
                  <div
                    className={`mb-6 p-4 text-xs font-black uppercase tracking-widest rounded-xl flex items-center gap-3 border shadow-sm w-full ${
                      notification.type === 'success'
                        ? 'bg-success-start/10 text-success-start border-success-start/20'
                        : 'bg-danger-start/10 text-danger-start border-danger-start/20'
                    }`}
                  >
                    {notification.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                    {notification.msg}
                  </div>
                )}
                {/* WHITE PAPER WRAPPER */}
                <div className="bg-white p-12 text-black shadow-lg rounded-sm min-h-[29.7cm] border border-gray-200">
                  <DraftResultRenderer text={currentJob.result} t={t} />
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center text-center mt-32 pointer-events-none opacity-40"
              >
                {currentJob.status === 'PROCESSING' ? (
                  <div className="flex flex-col items-center">
                    <div className="w-20 h-20 rounded-[1.5rem] bg-primary-start flex items-center justify-center shadow-accent-glow mb-8 animate-pulse">
                      <BrainCircuit className="w-10 h-10 text-white" />
                    </div>
                    <p className="text-text-primary font-black uppercase tracking-widest text-xs">
                      {t('drafting.statusWorking', 'Duke Gjeneruar...')}
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
  );
};