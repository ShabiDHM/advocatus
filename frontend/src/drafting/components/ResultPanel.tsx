// src/drafting/components/ResultPanel.tsx
import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, AlertCircle, CheckCircle, Clock,
  FileText, Trash2, Archive, Scale, Save, Copy, Download,
  BrainCircuit
} from 'lucide-react';
import { ResultPanelProps } from '../types';
import { SaveModal } from './SaveModal';
import { ThinkingDots } from './ThinkingDots';
import { DraftResultRenderer } from './DraftResultRenderer';

export const ResultPanel: React.FC<ResultPanelProps> = ({
  t,
  currentJob,
  saving,
  notification,
  onSave,
  onSaveToCase,
  onRetry,
  onClear,
  selectedCaseId,
  saveModalOpen,
  setSaveModalOpen,
}) => {
  const statusUI = useMemo(() => {
    switch (currentJob.status) {
      case 'COMPLETED':
        return { text: t('drafting.statusCompleted'), color: 'text-green-400', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED':
        return { text: t('drafting.statusFailed'), color: 'text-red-400', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING':
        return { text: t('drafting.statusWorking'), color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default:
        return { text: t('drafting.statusResult'), color: 'text-white', icon: <Scale className="h-5 w-5 text-gray-500" /> };
    }
  }, [currentJob.status, t]);

  return (
    <div className="flex flex-col h-auto lg:h-[700px] rounded-2xl bg-[#0d0f14] border border-white/10 overflow-hidden shadow-2xl shrink-0">
      <div className="flex justify-between items-center p-4 bg-white/5 border-b border-white/5 flex-shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className={`${statusUI.color} p-2 bg-white/5 rounded-lg`}>{statusUI.icon}</div>
          <h3 className="text-white text-xs sm:text-sm font-semibold uppercase tracking-widest leading-none">{statusUI.text}</h3>
        </div>
        <div className="flex gap-1 sm:gap-2">
          {currentJob.status === 'COMPLETED' && selectedCaseId && (
            <button
              onClick={() => setSaveModalOpen(true)}
              title="Ruaj në lëndë"
              className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-primary-start transition-colors"
            >
              <Save size={18} />
            </button>
          )}
          <button
            onClick={onSave}
            title={t('drafting.saveToArchive')}
            disabled={!currentJob.result || saving}
            className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-primary-start transition-colors disabled:opacity-30"
          >
            {saving ? <RefreshCw className="animate-spin" size={18} /> : <Archive size={18} />}
          </button>
          <button
            onClick={() => {
              if (currentJob.result) {
                navigator.clipboard.writeText(currentJob.result);
              }
            }}
            title={t('drafting.copy')}
            className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-colors"
          >
            <Copy size={18} />
          </button>
          <button
            onClick={() => {
              if (currentJob.result) {
                const blob = new Blob([currentJob.result], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `draft-${Date.now()}.txt`;
                a.click();
              }
            }}
            title={t('drafting.download')}
            className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-colors"
          >
            <Download size={18} />
          </button>
          {currentJob.status === 'FAILED' && (
            <button
              onClick={onRetry}
              title="Riprovo"
              className="p-2.5 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 rounded-lg transition-colors"
            >
              <RefreshCw size={18} />
            </button>
          )}
          <button
            onClick={onClear}
            title={t('drafting.clear')}
            className="p-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
      <div className="flex-1 bg-gray-900/40 overflow-y-auto relative custom-scrollbar">
        <div className="min-h-full w-full flex justify-center p-4 sm:p-8">
          <AnimatePresence mode="wait">
            {currentJob.result ? (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="w-full max-w-[21cm]"
              >
                {notification && (
                  <div
                    className={`mb-4 p-3 text-xs rounded-lg flex items-center gap-2 border w-full ${
                      notification.type === 'success'
                        ? 'bg-green-500/20 text-green-400 border-green-500/20'
                        : 'bg-red-500/20 text-red-400 border-red-500/20'
                    }`}
                  >
                    {notification.type === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}{' '}
                    {notification.msg}
                  </div>
                )}
                <DraftResultRenderer text={currentJob.result} t={t} />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center text-center mt-20 pointer-events-none"
              >
                {currentJob.status === 'PROCESSING' ? (
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg shadow-primary-start/20 mb-6 animate-pulse">
                      <BrainCircuit className="w-8 h-8 text-white" />
                    </div>
                    <p className="text-white font-medium flex items-center">
                      {t('drafting.statusWorking')}
                      <ThinkingDots />
                    </p>
                  </div>
                ) : (
                  <div className="opacity-20 flex flex-col items-center">
                    <FileText size={56} className="text-gray-600 mb-4" />
                    <p className="text-gray-400 text-sm">{t('drafting.emptyState')}</p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      <SaveModal
        isOpen={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSave={onSaveToCase}
        saving={saving}
      />
    </div>
  );
};