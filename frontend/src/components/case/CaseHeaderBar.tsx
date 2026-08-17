// FILE: src/components/case/CaseHeaderBar.tsx
// PHOENIX PROTOCOL - CASE HEADER BAR V11.0 (EXECUTIVE NATURAL TITLE TYPOGRAPHY)

import React from 'react';
import { motion } from 'framer-motion';
import { Case, Document } from '../../data/types';
import { DocumentSelector } from '../DocumentSelector';
import {
  Briefcase,
  Calendar,
  Shield,
  Swords,
  Scale,
  Lock,
  Activity,
  Network,
  RefreshCw,
  Trash2,
  ShieldCheck,
  Loader2,
} from 'lucide-react';

interface CaseHeaderBarProps {
  caseDetails: Case;
  documents: Document[];
  onOpenRoleModal: () => void;
  onRunAnalysis: (forceReanalyze?: boolean) => void;
  onViewExistingAnalysis: () => void;
  onOpenOntologyModal: () => void;
  onOpenAnalystModal: () => void;
  onClearAnalysis: () => void;
  isAnalyzing: boolean;
  isPro: boolean;
  isAdmin: boolean;
  selectedDocumentIds: string[];
  onDocumentSelectionChange: (ids: string[]) => void;
}

export const CaseHeaderBar: React.FC<CaseHeaderBarProps> = ({
  caseDetails,
  documents,
  onOpenRoleModal,
  onRunAnalysis,
  onViewExistingAnalysis,
  onOpenOntologyModal,
  onOpenAnalystModal,
  onClearAnalysis,
  isAnalyzing,
  isPro,
  isAdmin,
  selectedDocumentIds,
  onDocumentSelectionChange,
}) => {
  const hasExistingAnalysis = !!(caseDetails as any).latest_analysis && selectedDocumentIds.length === 0;
  const clientPosition = (caseDetails as any).client_position || 'DEFENDANT';

  const analyzeButtonText = isAnalyzing ? (
    <span className="flex items-center justify-center gap-1 sm:gap-2 min-w-0">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary-start shrink-0" />
      <span className="text-primary-start truncate text-[10px] sm:text-xs">ANALIZO...</span>
    </span>
  ) : selectedDocumentIds.length === 0 ? (
    <span className="flex items-center justify-center gap-1 sm:gap-2 min-w-0">
      <ShieldCheck size={14} className="text-primary-start shrink-0" />
      <span className="text-primary-start truncate text-[10px] sm:text-xs">ANALIZO RASTIN</span>
    </span>
  ) : (
    <span className="flex items-center justify-center gap-1 sm:gap-2 min-w-0">
      <ShieldCheck size={14} className="text-primary-start shrink-0" />
      <span className="text-primary-start truncate text-[10px] sm:text-xs">KRYQËZO</span>
    </span>
  );

  const buttonBase =
    'h-10 sm:h-11 flex items-center justify-center gap-1.5 sm:gap-2 px-2 sm:px-4 rounded-xl glass-panel bg-surface border border-main shadow-sm transition-all duration-200 hover:bg-hover text-[10px] sm:text-xs font-bold uppercase tracking-wider text-text-primary focus:outline-none cursor-pointer';

  const rawTitle = caseDetails.title || (caseDetails as any).name || 'Rast pa Titull';

  return (
    <motion.div
      className="relative mb-4 sm:mb-6 z-[30]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="bg-surface border border-main rounded-2xl p-3.5 sm:p-5 shadow-sm mb-3 sm:mb-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2.5 sm:p-3 bg-primary-start/10 text-primary-start border border-primary-start/20 rounded-2xl shrink-0">
            <Briefcase size={20} className="sm:w-5 sm:h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              {/* Executive natural casing title without uppercase forcing */}
              <h1 className="text-base sm:text-xl font-bold text-text-primary tracking-tight truncate leading-snug">
                {rawTitle}
              </h1>

              <button
                type="button"
                onClick={onOpenRoleModal}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] sm:text-[10px] font-black uppercase tracking-wider border transition-all shadow-sm cursor-pointer ${
                  clientPosition === 'DEFENDANT'
                    ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 hover:bg-blue-500/20'
                    : clientPosition === 'PLAINTIFF'
                    ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30 hover:bg-purple-500/20'
                    : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                }`}
                title="Kliko për të ndryshuar pozicionin e klientit"
              >
                {clientPosition === 'DEFENDANT' ? <Shield size={11} /> : clientPosition === 'PLAINTIFF' ? <Swords size={11} /> : <Scale size={11} />}
                <span>{clientPosition === 'DEFENDANT' ? '🛡️ I PADITUR' : clientPosition === 'PLAINTIFF' ? '⚔️ PADITËSI' : '⚖️ NEUTRAL'}</span>
              </button>
            </div>

            <div className="flex items-center gap-2 sm:gap-3 text-[11px] sm:text-xs text-text-muted mt-0.5 sm:mt-1 font-medium">
              <span className="flex items-center gap-1">
                <Calendar size={12} className="text-primary-start/70" />
                {new Date(caseDetails.created_at).toLocaleDateString()}
              </span>
              <span>•</span>
              <span className="font-mono text-text-secondary">{documents.length} Dok</span>
            </div>
          </div>
        </div>

        <div className="w-full sm:w-64 z-[60]">
          <DocumentSelector
            documents={documents.map((d) => ({ id: d.id, file_name: d.file_name }))}
            selectedIds={selectedDocumentIds}
            onChange={onDocumentSelectionChange}
            disabled={!isPro}
          />
        </div>
      </div>

      {isAdmin && (
        <div className="grid grid-cols-3 gap-1.5 sm:gap-3 animate-in fade-in duration-200">
          <button
            type="button"
            onClick={onOpenAnalystModal}
            disabled={!isPro}
            className={`${buttonBase} w-full ${!isPro && 'opacity-40 cursor-not-allowed'}`}
          >
            {!isPro ? <Lock size={13} className="shrink-0 text-text-muted" /> : <Activity size={14} className="text-primary-start shrink-0" />}
            <span className="truncate">FINANCAT</span>
          </button>

          <button
            type="button"
            onClick={onOpenOntologyModal}
            className={`${buttonBase} w-full hover:border-primary-start/80`}
          >
            <Network size={14} className="text-primary-start shrink-0" />
            <span className="truncate">ONTOLOGJIA</span>
          </button>

          <div className="w-full">
            {hasExistingAnalysis ? (
              <div className="h-10 sm:h-11 flex items-center justify-between rounded-xl glass-panel bg-surface border border-main shadow-sm text-[10px] sm:text-xs font-bold uppercase tracking-wider text-text-primary overflow-hidden w-full">
                <button
                  type="button"
                  onClick={onViewExistingAnalysis}
                  disabled={isAnalyzing}
                  className="flex-1 h-full flex items-center justify-center px-1.5 sm:px-3 hover:bg-hover hover:text-primary-start transition-all duration-200 focus:outline-none min-w-0 cursor-pointer"
                  title="Shiko Analizën ekzistuese"
                >
                  <span className="truncate text-primary-start font-bold">ANALIZA</span>
                </button>

                <div className="border-r border-main h-5 sm:h-6 shrink-0" />

                <button
                  type="button"
                  onClick={() => onRunAnalysis(false)}
                  disabled={isAnalyzing}
                  className="px-1.5 sm:px-2.5 h-full flex items-center justify-center hover:bg-hover hover:text-primary-start transition-all duration-200 focus:outline-none shrink-0 cursor-pointer"
                  title="Rianalizo sërish me AI"
                >
                  <RefreshCw size={13} className={`text-text-muted shrink-0 ${isAnalyzing ? 'animate-spin text-primary-start' : ''}`} />
                </button>

                <div className="border-r border-main h-5 sm:h-6 shrink-0" />

                <button
                  type="button"
                  onClick={onClearAnalysis}
                  disabled={isAnalyzing}
                  className="px-1.5 sm:px-2.5 h-full flex items-center justify-center hover:bg-hover hover:text-danger-start transition-all duration-200 focus:outline-none shrink-0 cursor-pointer"
                  title="Fshi analizën e ruajtur"
                >
                  <Trash2 size={13} className="text-text-muted hover:text-rose-600 shrink-0" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onRunAnalysis(false)}
                disabled={!isPro || isAnalyzing}
                className={`${buttonBase} w-full disabled:opacity-40`}
              >
                {analyzeButtonText}
              </button>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default CaseHeaderBar;