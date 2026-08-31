// FILE: src/components/law/LawArticleHeader.tsx
// PHOENIX PROTOCOL - UNIFIED TYPOGRAPHY & FIXED-HEIGHT COMPONENT ALIGNMENT

import React from 'react';
import { ChevronLeft, ChevronRight, Search, Loader2, BrainCircuit, X, ShieldCheck } from 'lucide-react';
import { SourceInfo } from './lawArticleTypes';
import { TFunction } from 'i18next';

interface LawArticleHeaderProps {
  sourceInfo: SourceInfo | null;
  isAcademicDoc: boolean;
  prevArticleNum: string | null;
  nextArticleNum: string | null;
  onNavigateToArticle: (num: string) => void;
  jumpInput: string;
  onJumpInputChange: (val: string) => void;
  onJumpSubmit: (e: React.FormEvent) => void;
  chatVisible: boolean;
  isSummarizing: boolean;
  onStartAudit: () => void;
  onCloseAuditor: () => void;
  t: TFunction;
}

export const LawArticleHeader: React.FC<LawArticleHeaderProps> = ({
  sourceInfo,
  isAcademicDoc,
  prevArticleNum,
  nextArticleNum,
  onNavigateToArticle,
  jumpInput,
  onJumpInputChange,
  onJumpSubmit,
  chatVisible,
  isSummarizing,
  onStartAudit,
  onCloseAuditor,
  t,
}) => {
  const accuracyPercentage = sourceInfo?.confidence?.score
    ? Math.round(sourceInfo.confidence.score * 100)
    : 100;

  const verificationLabel = isAcademicDoc
    ? `Udhëzues i Verifikuar (${accuracyPercentage}%)`
    : `Tekst Zyrtar i Verifikuar (${accuracyPercentage}%)`;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-3 sm:gap-4 w-full">
      
      {/* 1. MAJTAS: Badge i Verifikimit (Lartësi Standarde h-10) */}
      <div className="flex items-center justify-between w-full sm:w-auto gap-2">
        <div 
          className="h-10 px-3.5 flex items-center gap-2 text-emerald-500 font-semibold text-xs bg-emerald-500/10 border border-emerald-500/20 rounded-xl shadow-xs shrink-0"
          title={`Verifikuar nga baza zyrtare me saktësi ${accuracyPercentage}%`}
        >
          <ShieldCheck size={16} className="text-emerald-500 shrink-0" />
          <span className="truncate">{verificationLabel}</span>
        </div>

        {/* Butoni i Auditimit në Mobile */}
        <div className="sm:hidden shrink-0">
          {!chatVisible ? (
            <button
              onClick={onStartAudit}
              disabled={isSummarizing}
              className="h-10 px-3.5 flex items-center gap-1.5 rounded-xl text-xs font-semibold transition-all shadow-sm bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer"
            >
              {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
              <span>{isSummarizing ? 'Analizon...' : 'Auditimi Ligjor'}</span>
            </button>
          ) : (
            <button
              onClick={onCloseAuditor}
              className="h-10 px-3.5 flex items-center gap-1.5 rounded-xl text-xs font-semibold transition-all shadow-sm bg-canvas border border-main text-text-primary hover:text-danger-start cursor-pointer"
            >
              <X size={14} />
              <span>Mbyll</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. QENDRA: Navigimi i Neneve (Të gjitha me Lartësi Standarde h-10) */}
      <div className="flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 w-full sm:w-auto">
        {prevArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(prevArticleNum)}
            className="h-10 px-3 flex items-center justify-center rounded-xl text-xs font-semibold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm cursor-pointer shrink-0 gap-1"
            title="Neni i Mëparshëm"
          >
            <ChevronLeft size={15} className="text-primary-start" />
            <span className="hidden md:inline">{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
          </button>
        ) : (
          <div className="w-10 sm:hidden" />
        )}

        <form onSubmit={onJumpSubmit} className="relative flex-1 sm:flex-initial max-w-[190px] sm:max-w-none">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Neni (p.sh. 390)..."
            value={jumpInput}
            onChange={(e) => onJumpInputChange(e.target.value)}
            className="w-full sm:w-40 h-10 pl-8 pr-2.5 bg-canvas border border-main rounded-xl text-xs font-semibold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 focus:outline-none"
          />
        </form>

        {nextArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(nextArticleNum)}
            className="h-10 px-3 flex items-center justify-center rounded-xl text-xs font-semibold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm cursor-pointer shrink-0 gap-1"
            title="Neni i Ardhshëm"
          >
            <span className="hidden md:inline">{`Neni ${nextArticleNum}`}</span>
            <ChevronRight size={15} className="text-primary-start" />
          </button>
        ) : (
          <div className="w-10 sm:hidden" />
        )}
      </div>

      {/* 3. DJATHTAS: Butoni i Auditimit në Desktop (Lartësi Standarde h-10) */}
      <div className="hidden sm:flex items-center shrink-0">
        {!chatVisible ? (
          <button
            onClick={onStartAudit}
            disabled={isSummarizing}
            className="h-10 px-4 flex items-center gap-2 rounded-xl text-xs font-semibold transition-all shadow-sm hover-lift bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer"
          >
            {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
            <span>{isSummarizing ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.auditBtn', 'Auditimi Ligjor')}</span>
          </button>
        ) : (
          <button
            onClick={onCloseAuditor}
            className="h-10 px-4 flex items-center gap-2 rounded-xl text-xs font-semibold transition-all shadow-sm bg-canvas border border-main text-text-primary hover:border-danger-start hover:text-danger-start cursor-pointer"
          >
            <X size={14} />
            <span>{t('lawArticle.closeAuditor', 'Mbyll Auditorin')}</span>
          </button>
        )}
      </div>

    </div>
  );
};

export default LawArticleHeader;