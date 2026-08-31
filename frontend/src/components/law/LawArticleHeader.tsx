// FILE: src/components/law/LawArticleHeader.tsx
// PHOENIX PROTOCOL - CLEAN 2-ICON STEP NAVIGATION & AUDITOR HEADER

import React from 'react';
import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, Search, Loader2, BrainCircuit, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { TFunction } from 'i18next';

interface LawArticleHeaderProps {
  onBackToLibrary: () => void;
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
  const navigate = useNavigate();

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-3 sm:gap-4 w-full">
      
      {/* RRESHTI 1: Dy Ikonat e Navigimit (← Mbrapa / → Përpara) */}
      <div className="flex items-center justify-between w-full sm:w-auto gap-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="p-2.5 rounded-xl bg-canvas border border-main hover:border-primary-start/60 text-text-primary hover:text-primary-start transition-all hover-lift cursor-pointer shadow-sm"
            title="Mbrapa"
          >
            <ArrowLeft size={16} />
          </button>
          <button
            type="button"
            onClick={() => navigate(1)}
            className="p-2.5 rounded-xl bg-canvas border border-main hover:border-primary-start/60 text-text-primary hover:text-primary-start transition-all hover-lift cursor-pointer shadow-sm"
            title="Përpara"
          >
            <ArrowRight size={16} />
          </button>
        </div>

        {/* Butoni i Auditimit në Mobile */}
        <div className="sm:hidden shrink-0">
          {!chatVisible ? (
            <button
              onClick={onStartAudit}
              disabled={isSummarizing}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all shadow-sm bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer"
            >
              {isSummarizing ? <Loader2 size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
              <span>{isSummarizing ? 'Analizon...' : 'Auditimi'}</span>
            </button>
          ) : (
            <button
              onClick={onCloseAuditor}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all shadow-sm bg-canvas border border-main text-text-primary hover:text-danger-start cursor-pointer"
            >
              <X size={13} />
              <span>Mbyll</span>
            </button>
          )}
        </div>
      </div>

      {/* RRESHTI 2: Navigimi i Neneve (< Search >) */}
      <div className="flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 w-full sm:w-auto">
        {prevArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(prevArticleNum)}
            className="flex items-center justify-center w-9 sm:w-auto sm:px-3 h-9 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none cursor-pointer shrink-0"
            title="Neni i Mëparshëm"
          >
            <ChevronLeft size={15} className="text-primary-start" />
            <span className="hidden md:inline ml-1">{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
          </button>
        ) : (
          <div className="w-9 sm:hidden" />
        )}

        <form onSubmit={onJumpSubmit} className="relative flex-1 sm:flex-initial max-w-[180px] sm:max-w-none">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Neni (p.sh. 390)..."
            value={jumpInput}
            onChange={(e) => onJumpInputChange(e.target.value)}
            className="w-full sm:w-36 h-9 pl-8 pr-2 bg-canvas border border-main rounded-xl text-xs font-bold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 focus:outline-none"
          />
        </form>

        {nextArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(nextArticleNum)}
            className="flex items-center justify-center w-9 sm:w-auto sm:px-3 h-9 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none cursor-pointer shrink-0"
            title="Neni i Ardhshëm"
          >
            <span className="hidden md:inline mr-1">{`Neni ${nextArticleNum}`}</span>
            <ChevronRight size={15} className="text-primary-start" />
          </button>
        ) : (
          <div className="w-9 sm:hidden" />
        )}
      </div>

      {/* Butoni i Auditimit në Desktop */}
      <div className="hidden sm:flex items-center shrink-0">
        {!chatVisible ? (
          <button
            onClick={onStartAudit}
            disabled={isSummarizing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm hover-lift bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer"
          >
            {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
            {isSummarizing ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.auditBtn', 'Auditimi Ligjor')}
          </button>
        ) : (
          <button
            onClick={onCloseAuditor}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm bg-canvas border border-main text-text-primary hover:border-danger-start hover:text-danger-start cursor-pointer"
          >
            <X size={14} />
            {t('lawArticle.closeAuditor', 'Mbyll Auditorin')}
          </button>
        )}
      </div>

    </div>
  );
};

export default LawArticleHeader;