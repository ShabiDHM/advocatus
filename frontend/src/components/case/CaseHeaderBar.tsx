// FILE: src/components/case/CaseHeaderBar.tsx
// PHOENIX PROTOCOL - CASE HEADER BAR V16.0 (5/7 COLUMN GEOMETRIC ALIGNMENT & EXECUTIVE DOCK)

import React from 'react';
import { motion } from 'framer-motion';
import { Case, Document } from '../../data/types';
import {
  Briefcase,
  Calendar,
  Shield,
  Swords,
  Scale,
  Lock,
  Activity,
  RefreshCw,
  Trash2,
  ShieldCheck,
  Loader2,
  Sparkles,
  ChevronRight
} from 'lucide-react';

interface CaseHeaderBarProps {
  caseDetails: Case;
  documents: Document[];
  onOpenRoleModal: () => void;
  onRunAnalysis: (forceReanalyze?: boolean) => void;
  onViewExistingAnalysis: () => void;
  onOpenAnalystModal: () => void;
  onClearAnalysis: () => void;
  isAnalyzing: boolean;
  isPro: boolean;
  isAdmin: boolean;
  selectedDocumentIds?: string[];
}

export const CaseHeaderBar: React.FC<CaseHeaderBarProps> = ({
  caseDetails,
  documents,
  onOpenRoleModal,
  onRunAnalysis,
  onViewExistingAnalysis,
  onOpenAnalystModal,
  onClearAnalysis,
  isAnalyzing,
  isPro,
  isAdmin,
  selectedDocumentIds = [],
}) => {
  const hasExistingAnalysis = !!(caseDetails as any).latest_analysis && selectedDocumentIds.length === 0;
  const clientPosition = (caseDetails as any).client_position || 'DEFENDANT';

  const rawTitle = caseDetails.title || (caseDetails as any).name || 'Rast pa Titull';

  const roleLabel =
    clientPosition === 'DEFENDANT'
      ? 'ROLI: I PADITUR'
      : clientPosition === 'PLAINTIFF'
      ? 'ROLI: PADITËS'
      : 'ROLI: NEUTRAL';

  return (
    <motion.div
      className="relative mb-4 sm:mb-6 z-[30]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* 1. TOP CASE IDENTITY BAR */}
      <div className="bg-surface border border-main rounded-2xl p-4 sm:p-5 shadow-sm mb-3 sm:mb-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5 min-w-0 flex-1">
          <div className="p-3 bg-primary-start/10 text-primary-start border border-primary-start/20 rounded-2xl shrink-0">
            <Briefcase size={22} className="sm:w-6 sm:h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-base sm:text-xl font-bold text-text-primary tracking-tight truncate leading-tight">
              {rawTitle}
            </h1>

            <div className="flex items-center gap-2 sm:gap-3 text-[11px] sm:text-xs text-text-muted mt-1 font-medium">
              <span className="flex items-center gap-1">
                <Calendar size={12} className="text-primary-start/70" />
                {new Date(caseDetails.created_at).toLocaleDateString()}
              </span>
              <span>•</span>
              <span className="font-mono text-text-secondary">{documents.length} Dok</span>
            </div>
          </div>
        </div>

        {/* Right Role Switcher Button */}
        <div className="flex items-center justify-end shrink-0">
          <button
            type="button"
            onClick={onOpenRoleModal}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[10px] sm:text-[11px] font-bold uppercase tracking-wider border transition-all shadow-xs cursor-pointer ${
              clientPosition === 'DEFENDANT'
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 hover:bg-blue-500/20'
                : clientPosition === 'PLAINTIFF'
                ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30 hover:bg-purple-500/20'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
            }`}
            title="Kliko për të ndryshuar rolin procedural të klientit"
          >
            {clientPosition === 'DEFENDANT' ? (
              <Shield size={12} className="shrink-0" />
            ) : clientPosition === 'PLAINTIFF' ? (
              <Swords size={12} className="shrink-0" />
            ) : (
              <Scale size={12} className="shrink-0" />
            )}
            <span>{roleLabel}</span>
          </button>
        </div>
      </div>

      {/* 2. SYMMETRIC 12-COLUMN ACTION DOCK (5-Col / 7-Col Matched with Bottom Panels) */}
      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 animate-in fade-in duration-200">
          
          {/* LEFT BUTTON: Matches 5-Col Evidence Vault Width Exactly */}
          <div className="lg:col-span-5">
            <button
              type="button"
              onClick={onOpenAnalystModal}
              disabled={!isPro}
              className={`w-full h-12 px-4 rounded-2xl bg-surface hover:bg-hover border border-main shadow-sm flex items-center justify-between transition-all duration-200 group focus:outline-none cursor-pointer ${
                !isPro ? 'opacity-40 cursor-not-allowed' : 'hover:border-primary-start/50'
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center border border-primary-start/20 shrink-0 group-hover:scale-105 transition-transform">
                  {!isPro ? <Lock size={14} className="text-text-muted" /> : <Activity size={15} />}
                </div>
                <div className="text-left min-w-0">
                  <span className="text-xs font-bold text-text-primary uppercase tracking-wider block truncate">
                    Financat e Lëndës
                  </span>
                  <span className="text-[10px] text-text-muted font-medium block truncate">
                    Shpenzimet & Dëmet Financiare
                  </span>
                </div>
              </div>

              <ChevronRight size={15} className="text-text-muted group-hover:text-primary-start transition-colors shrink-0" />
            </button>
          </div>

          {/* RIGHT BUTTON: Matches 7-Col Chat Panel Width Exactly */}
          <div className="lg:col-span-7">
            {hasExistingAnalysis ? (
              <div className="w-full h-12 px-2 sm:px-3 rounded-2xl bg-surface border border-main shadow-sm flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={onViewExistingAnalysis}
                  disabled={isAnalyzing}
                  className="flex-1 h-full flex items-center gap-2.5 px-2 hover:bg-hover rounded-xl transition-all duration-200 focus:outline-none min-w-0 cursor-pointer text-left"
                  title="Shiko Analizën Strategjike Ekzistuese"
                >
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center border border-emerald-500/20 shrink-0">
                    <Sparkles size={15} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-xs font-bold text-primary-start uppercase tracking-wider block truncate">
                      Analiza Strategjike
                    </span>
                    <span className="text-[10px] text-text-muted font-medium block truncate">
                      Raporti i Gatshëm Ligjor
                    </span>
                  </div>
                </button>

                <div className="flex items-center gap-1 shrink-0 border-l border-main pl-2">
                  <button
                    type="button"
                    onClick={() => onRunAnalysis(false)}
                    disabled={isAnalyzing}
                    className="p-2 text-text-muted hover:text-primary-start hover:bg-hover rounded-xl transition-colors focus:outline-none cursor-pointer"
                    title="Rianalizo Lëndën me AI"
                  >
                    <RefreshCw size={15} className={isAnalyzing ? 'animate-spin text-primary-start' : ''} />
                  </button>

                  <button
                    type="button"
                    onClick={onClearAnalysis}
                    disabled={isAnalyzing}
                    className="p-2 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-xl transition-colors focus:outline-none cursor-pointer"
                    title="Fshi Analizën e Ruajtur"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onRunAnalysis(false)}
                disabled={!isPro || isAnalyzing}
                className="w-full h-12 px-4 rounded-2xl bg-surface hover:bg-hover border border-main hover:border-primary-start/50 shadow-sm flex items-center justify-between transition-all duration-200 group focus:outline-none cursor-pointer disabled:opacity-40"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center border border-primary-start/20 shrink-0 group-hover:scale-105 transition-transform">
                    {isAnalyzing ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary-start" />
                    ) : (
                      <ShieldCheck size={16} />
                    )}
                  </div>
                  <div className="text-left min-w-0">
                    <span className="text-xs font-bold text-primary-start uppercase tracking-wider block truncate">
                      {isAnalyzing ? 'Duke Analizuar...' : 'Analizo Rastin me AI'}
                    </span>
                    <span className="text-[10px] text-text-muted font-medium block truncate">
                      Skanim i Thellë i Fashikullit
                    </span>
                  </div>
                </div>

                <ChevronRight size={15} className="text-text-muted group-hover:text-primary-start transition-colors shrink-0" />
              </button>
            )}
          </div>

        </div>
      )}
    </motion.div>
  );
};

export default CaseHeaderBar;