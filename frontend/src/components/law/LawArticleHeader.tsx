// FILE: src/components/law/LawArticleHeader.tsx
import React from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, Search, Loader2, BrainCircuit, X } from 'lucide-react';
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
  onBackToLibrary,
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
  return (
    <div className="flex flex-wrap items-center justify-between mb-8 gap-4">
      <button
        onClick={onBackToLibrary}
        className="group flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift cursor-pointer"
      >
        <div className="p-2 rounded-xl bg-canvas border border-main group-hover:border-primary-start transition-colors">
          <ArrowLeft size={16} className="text-primary-start" />
        </div>
        <span>Biblioteka Ligjore</span>
      </button>

      <div className="flex items-center gap-2 flex-wrap">
        {prevArticleNum !== null && (
          <button
            type="button"
            onClick={() => onNavigateToArticle(prevArticleNum)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none cursor-pointer"
            title="Neni i Mëparshëm"
          >
            <ChevronLeft size={14} className="text-primary-start" />
            <span className="hidden sm:inline">{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
          </button>
        )}

        <form onSubmit={onJumpSubmit} className="relative flex items-center">
          <Search size={12} className="absolute left-3 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Kërko nenin..."
            value={jumpInput}
            onChange={(e) => onJumpInputChange(e.target.value)}
            className="w-28 sm:w-32 h-9 pl-8 pr-2 bg-canvas border border-main rounded-xl text-xs font-bold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 focus:outline-none"
          />
        </form>

        {nextArticleNum !== null && (
          <button
            type="button"
            onClick={() => onNavigateToArticle(nextArticleNum)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none cursor-pointer"
            title="Neni i Ardhshëm"
          >
            <span className="hidden sm:inline">{`Neni ${nextArticleNum}`}</span>
            <ChevronRight size={14} className="text-primary-start" />
          </button>
        )}
      </div>

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
  );
};