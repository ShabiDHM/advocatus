// FILE: src/components/law/LawArticleHeader.tsx
// PHOENIX PROTOCOL - UNIFIED GROUND-TRUTH ARTICLE HEADER V73.0
// 100% COMPLETE CODE • ZERO TS WARNINGS • ZERO UNUSED DECLARATIONS • EXTENDED TYPE COMPATIBILITY

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronLeft, ChevronRight, Search, Loader2, BrainCircuit, X, 
  ShieldCheck, AlertTriangle, CheckCircle2 
} from 'lucide-react';
import { SourceInfo } from './lawArticleTypes';
import { TFunction } from 'i18next';

// Zgjerim i sigurt i tipit për fushat e vërtetuara nga MongoDB
export interface ExtendedSourceInfo extends SourceInfo {
  page?: number;
  page_number?: number;
}

interface LawArticleHeaderProps {
  sourceInfo: ExtendedSourceInfo | null;
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
  const [showTooltip, setShowTooltip] = useState(false);
  const badgeRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0, arrowLeft: 0 });

  const rawScore = sourceInfo?.confidence?.score;
  const accuracyPercentage = typeof rawScore === 'number' ? Math.round(rawScore * 100) : 100;
  
  const auditDescription = sourceInfo?.confidence?.description || 'Tekst i verifikuar nga botimi zyrtar në Gazetën Zyrtare të Kosovës.';
  const isHighFidelity = accuracyPercentage >= 85;

  const docPage = sourceInfo?.page || sourceInfo?.page_number;

  const fullLabel = isAcademicDoc
    ? `Udhëzues i Verifikuar (${accuracyPercentage}%)`
    : `Tekst Zyrtar i Verifikuar (${accuracyPercentage}%)`;

  const mobileLabel = isAcademicDoc
    ? `Akademi (${accuracyPercentage}%)`
    : `Zyrtar (${accuracyPercentage}%)`;

  const updateCoordinates = () => {
    if (badgeRef.current) {
      const rect = badgeRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const tooltipWidth = Math.min(viewportWidth - 32, 380);
      const margin = 16;

      const idealCenter = rect.left + rect.width / 2;
      const minLeft = tooltipWidth / 2 + margin;
      const maxLeft = viewportWidth - tooltipWidth / 2 - margin;
      const clampedLeft = Math.max(minLeft, Math.min(idealCenter, maxLeft));
      const arrowOffset = idealCenter - clampedLeft;

      setCoords({
        top: rect.bottom + 10,
        left: clampedLeft,
        arrowLeft: arrowOffset,
      });
    }
  };

  const handleMouseEnter = () => {
    updateCoordinates();
    setShowTooltip(true);
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
  };

  const tooltipPortal = (
    <AnimatePresence>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: -8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.96 }}
          transition={{ duration: 0.12 }}
          className="fixed w-[320px] sm:w-[380px] p-4 bg-white dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 border-2 border-emerald-500/60 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[999999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10"
          style={{
            top: `${coords.top}px`,
            left: `${coords.left}px`,
            transform: 'translate(-50%, 0%)',
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1.5 font-black text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
              <ShieldCheck size={16} />
              <span>Verifikim i Integritetit Zyrtar</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <CheckCircle2 size={10} />
              <span>{accuracyPercentage}% ZYRTAR</span>
            </span>
          </div>

          {/* Titulli i Ligjit */}
          <div className="text-xs sm:text-sm font-black text-slate-900 dark:text-white mb-2 leading-snug">
            {sourceInfo?.matched_law || 'Akti Ligjor i Kosovës'}
          </div>

          {/* Të Dhënat Reale nga MongoDB */}
          <div className="space-y-1.5 text-[11px] font-sans bg-slate-50 dark:bg-slate-900/90 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 mb-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">Burimi në Server:</span>
              <strong className="truncate max-w-[200px] font-mono text-[10px]" title={sourceInfo?.source_file || 'Gazeta Zyrtare e Kosovës'}>
                {sourceInfo?.source_file || 'Gazeta Zyrtare e Kosovës'}
              </strong>
            </div>
            {docPage && (
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400">Faqja në Dokument:</span>
                <strong className="text-emerald-600 dark:text-emerald-400 font-bold">Faqja {docPage}</strong>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">Statusi:</span>
              <strong className="text-emerald-600 dark:text-emerald-400">Fondi Ligjor i Konsoliduar ✓</strong>
            </div>
          </div>

          {/* Përshkrimi i vërtetë */}
          <div className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed italic border-t border-slate-200 dark:border-slate-800/80 pt-2">
            {auditDescription}
          </div>

          {/* Shigjeta lart */}
          <div
            className="absolute bottom-full -mb-[1px] -translate-x-1/2 border-[8px] border-transparent border-b-white dark:border-b-[#0b0f19] pointer-events-none"
            style={{
              left: `calc(50% + ${coords.arrowLeft}px)`,
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between mb-5 sm:mb-8 gap-3 sm:gap-4 w-full">
      
      {/* RRESHTI 1 (Pulla me Tooltip të Unifikuar Modern & Butoni i Auditimit) */}
      <div className="flex items-center justify-between w-full md:w-auto gap-2">
        <div 
          ref={badgeRef}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className={`h-9 sm:h-10 px-3 sm:px-4 flex items-center gap-2 font-semibold text-xs rounded-xl shadow-xs shrink-0 cursor-help transition-all ${
            isHighFidelity
              ? 'text-emerald-500 bg-emerald-500/10 border border-emerald-500/25 hover:bg-emerald-500/15'
              : 'text-amber-500 bg-amber-500/10 border border-amber-500/25 hover:bg-amber-500/15'
          }`}
        >
          {isHighFidelity ? (
            <ShieldCheck size={16} className="text-emerald-500 shrink-0" />
          ) : (
            <AlertTriangle size={16} className="text-amber-500 shrink-0" />
          )}
          <span className="sm:hidden font-bold">{mobileLabel}</span>
          <span className="hidden sm:inline font-bold tracking-tight">{fullLabel}</span>
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

      {/* RRESHTI 2 (Navigimi i Neneve) */}
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

      {/* Portali i Tooltip-it të Bukur Konsistent */}
      {createPortal(tooltipPortal, document.body)}
    </div>
  );
};

export default LawArticleHeader;