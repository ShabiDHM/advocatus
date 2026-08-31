// FILE: src/components/law/LawArticleHeader.tsx
// PHOENIX PROTOCOL - ULTRA-RESPONSIVE MOBILE & TABLET LAW ARTICLE HEADER

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

  const fullLabel = isAcademicDoc
    ? `Udhëzues i Verifikuar (${accuracyPercentage}%)`
    : `Tekst Zyrtar i Verifikuar (${accuracyPercentage}%)`;

  const mobileLabel = isAcademicDoc
    ? `Akademi (${accuracyPercentage}%)`
    : `Zyrtar (${accuracyPercentage}%)`;

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between mb-5 sm:mb-8 gap-3 sm:gap-4 w-full">
      
      {/* RRESHTI 1 (Në Mobile: Badge Majtas & Butoni Auditimit Djathtas) */}
      <div className="flex items-center justify-between w-full md:w-auto gap-2">
        <div 
          className="h-9 sm:h-10 px-2.5 sm:px-3.5 flex items-center gap-1.5 sm:gap-2 text-emerald-500 font-semibold text-xs bg-emerald-500/10 border border-emerald-500/20 rounded-xl shadow-xs shrink-0"
          title={`Verifikuar nga baza zyrtare me saktësi ${accuracyPercentage}%`}
        >
          <ShieldCheck size={15} className="text-emerald-500 shrink-0" />
          <span className="sm:hidden font-bold">{mobileLabel}</span>
          <span className="hidden sm:inline truncate">{fullLabel}</span>
        </div>

        {/* Butoni i Auditimit për Mobile */}
        <div className="md:hidden shrink-0">
          {!chatVisible ? (
            <button
              onClick={onStartAudit}
              disabled={isSummarizing}
              className="h-9 px-3 flex items-center gap-1.5 rounded-xl text-xs font-semibold shadow-sm bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer active:scale-95 transition-all"
            >
              {isSummarizing ? <Loader2 size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
              <span>{isSummarizing ? 'Analizon...' : 'Auditimi'}</span>
            </button>
          ) : (
            <button
              onClick={onCloseAuditor}
              className="h-9 px-3 flex items-center gap-1.5 rounded-xl text-xs font-semibold shadow-sm bg-surface border border-main text-text-primary hover:text-danger-start cursor-pointer active:scale-95 transition-all"
            >
              <X size={13} />
              <span>Mbyll</span>
            </button>
          )}
        </div>
      </div>

      {/* RRESHTI 2 (Navigimi i Neneve - 100% Mobile Responsive) */}
      <div className="flex items-center justify-between sm:justify-center gap-1.5 sm:gap-2 w-full md:w-auto">
        {prevArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(prevArticleNum)}
            className="h-9 sm:h-10 px-2.5 sm:px-3.5 flex items-center justify-center rounded-xl text-xs font-semibold bg-surface border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm cursor-pointer shrink-0 gap-1"
            title="Neni i Mëparshëm"
          >
            <ChevronLeft size={15} className="text-primary-start" />
            <span className="hidden sm:inline">{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
          </button>
        ) : (
          <div className="w-8 sm:w-10 opacity-0 pointer-events-none" />
        )}

        <form onSubmit={onJumpSubmit} className="relative flex-1 sm:flex-initial min-w-[120px] max-w-[200px] sm:max-w-none">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Neni (p.sh. 390)..."
            value={jumpInput}
            onChange={(e) => onJumpInputChange(e.target.value)}
            className="w-full sm:w-44 h-9 sm:h-10 pl-7 sm:pl-8 pr-2.5 bg-surface border border-main rounded-xl text-xs font-semibold text-text-primary placeholder:text-text-muted/60 focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 focus:outline-none transition-all"
          />
        </form>

        {nextArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(nextArticleNum)}
            className="h-9 sm:h-10 px-2.5 sm:px-3.5 flex items-center justify-center rounded-xl text-xs font-semibold bg-surface border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm cursor-pointer shrink-0 gap-1"
            title="Neni i Ardhshëm"
          >
            <span className="hidden sm:inline">{`Neni ${nextArticleNum}`}</span>
            <ChevronRight size={15} className="text-primary-start" />
          </button>
        ) : (
          <div className="w-8 sm:w-10 opacity-0 pointer-events-none" />
        )}
      </div>

      {/* Butoni i Auditimit në Tablet & Desktop */}
      <div className="hidden md:flex items-center shrink-0">
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
            className="h-10 px-4 flex items-center gap-2 rounded-xl text-xs font-semibold transition-all shadow-sm bg-surface border border-main text-text-primary hover:border-danger-start hover:text-danger-start cursor-pointer"
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