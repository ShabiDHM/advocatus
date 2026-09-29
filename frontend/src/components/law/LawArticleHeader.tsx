// FILE: src/components/law/LawArticleHeader.tsx
// PHOENIX PROTOCOL - UNIFIED ARTICLE HEADER V75.0.2
//
// V75.0.2: FIX terma teknike → shqip.
//          - `title_match_type` në tooltip → përkthyer (getMatchTypeLabel)
//
// V75.0.1: FIX TS2339 — hequr referenca ndaj page_number.
// V75.0: FIX fake verification.

import React, { useState, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronLeft, ChevronRight, Search, Loader2, BrainCircuit, X,
  ShieldCheck, AlertTriangle,
} from 'lucide-react';
import type { SourceInfo } from './lawArticleTypes';
import type { TFunction } from 'i18next';
import { getMatchTypeLabel } from '../../utils/lawLabels';

interface LawArticleHeaderProps {
  sourceInfo: SourceInfo | null;
  isRepealed?: boolean;
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
  isRepealed = false,
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

  const hasSourceInfo = sourceInfo !== null && sourceInfo !== undefined;
  const confidence = sourceInfo?.confidence;
  const level = confidence?.level ?? null;

  const rawScore = confidence?.score;
  const hasScore = typeof rawScore === 'number' && rawScore >= 0;
  const accuracyPercentage = hasScore ? Math.round(rawScore * 100) : null;

  const auditDescription = confidence?.description ?? null;

  const confidenceLabel = (() => {
    if (!hasSourceInfo) return t('lawArticle.noSourceInfo', 'Verifikim i padisponueshëm');
    switch (level) {
      case 'HIGH':   return t('lawArticle.confHigh', 'Përputhje e saktë');
      case 'MEDIUM': return t('lawArticle.confMedium', 'Përputhje e mirë');
      case 'LOW':    return t('lawArticle.confLow', 'Përputhje e dobët');
      case 'NONE':   return t('lawArticle.confNone', 'Nuk u gjet');
      default:       return t('lawArticle.confUnknown', 'Status i panjohur');
    }
  })();

  const confidenceFullLabel = accuracyPercentage !== null
    ? `${confidenceLabel} (${accuracyPercentage}%)`
    : confidenceLabel;

  const confidenceMobileLabel = accuracyPercentage !== null
    ? `${accuracyPercentage}%`
    : '—';

  const badgeStyles = (() => {
    if (!hasSourceInfo) return 'text-text-muted bg-surface border border-main';
    if (level === 'HIGH')   return 'text-success-start bg-success-start/10 border border-success-start/25';
    if (level === 'MEDIUM') return 'text-primary-start bg-primary-start/10 border border-primary-start/25';
    if (level === 'LOW')    return 'text-warning-start bg-warning-start/10 border border-warning-start/25';
    return 'text-danger-start bg-danger-start/10 border border-danger-start/25';
  })();

  const badgeIcon = (() => {
    if (!hasSourceInfo) return <AlertTriangle size={16} className="text-text-muted shrink-0" />;
    if (level === 'HIGH' || level === 'MEDIUM') return <ShieldCheck size={16} className="shrink-0" />;
    return <AlertTriangle size={16} className="shrink-0" />;
  })();

  const docPage = sourceInfo?.page ?? null;
  const pageAvailable =
    sourceInfo?.page_available !== false &&
    typeof docPage === 'number' &&
    docPage > 0;

  // V75.0.2: Përkthim i match_type
  const matchTypeLabel = useMemo(
    () => getMatchTypeLabel(sourceInfo?.title_match_type, t),
    [sourceInfo?.title_match_type, t],
  );

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

  const handleMouseLeave = () => setShowTooltip(false);

  const tooltipPortal = (
    <AnimatePresence>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: -8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.96 }}
          transition={{ duration: 0.12 }}
          className="fixed w-[320px] sm:w-[380px] p-4 bg-card text-text-primary border-2 border-main rounded-2xl shadow-2xl z-[999999] pointer-events-none"
          style={{
            top: `${coords.top}px`,
            left: `${coords.left}px`,
            transform: 'translate(-50%, 0%)',
          }}
        >
          <div className="flex items-center justify-between mb-2.5 pb-2 border-b border-main">
            <div className="flex items-center gap-1.5 font-black text-xs uppercase tracking-wider text-text-primary">
              <ShieldCheck size={16} />
              <span>{t('lawArticle.verificationTitle', 'Verifikim')}</span>
            </div>
            {accuracyPercentage !== null && (
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md font-bold ${
                level === 'HIGH'   ? 'bg-success-start/10 text-success-start border border-success-start/20' :
                level === 'MEDIUM' ? 'bg-primary-start/10 text-primary-start border border-primary-start/20' :
                level === 'LOW'    ? 'bg-warning-start/10 text-warning-start border border-warning-start/20' :
                'bg-danger-start/10 text-danger-start border border-danger-start/20'
              }`}>
                {accuracyPercentage}%
              </span>
            )}
          </div>

          <div className="text-xs sm:text-sm font-black text-text-primary mb-2 leading-snug">
            {sourceInfo?.matched_law || t('lawArticle.legalAct', 'Akti Ligjor')}
          </div>

          <div className="space-y-1.5 text-[11px] font-sans bg-surface/90 p-2.5 rounded-xl border border-main text-text-secondary mb-2">
            {sourceInfo?.source_file && (
              <div className="flex items-center justify-between">
                <span className="text-text-muted">{t('lawArticle.source', 'Burimi')}:</span>
                <strong className="truncate max-w-[200px] font-mono text-[10px]" title={sourceInfo.source_file}>
                  {sourceInfo.source_file}
                </strong>
              </div>
            )}
            {pageAvailable && docPage !== null && (
              <div className="flex items-center justify-between">
                <span className="text-text-muted">{t('lawArticle.page', 'Faqja')}:</span>
                <strong className="text-primary-start font-bold">
                  {t('lawArticle.page', 'Faqja')} {docPage}
                </strong>
              </div>
            )}

            {/* V75.0.2: match_type në shqip */}
            {sourceInfo?.title_match_type && (
              <div className="flex items-center justify-between">
                <span className="text-text-muted">{t('lawArticle.matchType', 'Lloj përputhje')}:</span>
                <strong className="text-text-primary">{matchTypeLabel}</strong>
              </div>
            )}

            {typeof sourceInfo?.match_count === 'number' && sourceInfo.match_count > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-text-muted">{t('lawArticle.matchCount', 'Përputhje')}:</span>
                <strong className="text-text-primary">{sourceInfo.match_count}</strong>
              </div>
            )}
          </div>

          {auditDescription && (
            <div className="text-[11px] text-text-muted leading-relaxed italic border-t border-main/80 pt-2">
              {auditDescription}
            </div>
          )}

          {!hasSourceInfo && (
            <div className="text-[11px] text-warning-start leading-relaxed border-t border-main/80 pt-2">
              {t('lawArticle.noSourceInfoTooltip', '⚠️ Backend nuk dha informacion verifikimi për këtë nen.')}
            </div>
          )}

          <div
            className="absolute bottom-full -mb-[1px] -translate-x-1/2 border-[8px] border-transparent border-b-card pointer-events-none"
            style={{ left: `calc(50% + ${coords.arrowLeft}px)` }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between mb-5 sm:mb-8 gap-3 sm:gap-4 w-full">
      <div className="flex items-center justify-between w-full md:w-auto gap-2">
        <div className="flex items-center gap-2">
          <div
            ref={badgeRef}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            className={`h-9 sm:h-10 px-3 sm:px-4 flex items-center gap-2 font-semibold text-xs rounded-xl shadow-xs shrink-0 cursor-help transition-all ${badgeStyles}`}
          >
            {badgeIcon}
            <span className="sm:hidden font-bold">{confidenceMobileLabel}</span>
            <span className="hidden sm:inline font-bold tracking-tight">{confidenceFullLabel}</span>
          </div>

          {isRepealed && (
            <div
              className="h-9 sm:h-10 px-3 flex items-center gap-1.5 rounded-xl bg-warning-start/15 border border-warning-start/30 text-warning-start text-[11px] font-bold shrink-0"
              title={t('lawArticle.repealedTitle', 'Ky ligj është shfuqizuar')}
            >
              <AlertTriangle size={13} />
              <span className="hidden sm:inline">{t('lawArticle.repealedBadge', 'SHFUQIZUAR')}</span>
            </div>
          )}
        </div>

        <div className="md:hidden shrink-0">
          {!chatVisible ? (
            <button
              onClick={onStartAudit}
              disabled={isSummarizing}
              className="h-9 px-3 flex items-center gap-1.5 rounded-xl text-xs font-semibold shadow-sm bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer active:scale-95 transition-all"
            >
              {isSummarizing ? <Loader2 size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
              <span>
                {isSummarizing
                  ? t('lawArticle.analyzingShort', 'Analizon...')
                  : t('lawArticle.auditShort', 'Auditimi')}
              </span>
            </button>
          ) : (
            <button
              onClick={onCloseAuditor}
              className="h-9 px-3 flex items-center gap-1.5 rounded-xl text-xs font-semibold shadow-sm bg-surface border border-main text-text-primary hover:text-danger-start cursor-pointer active:scale-95 transition-all"
            >
              <X size={13} />
              <span>{t('lawArticle.close', 'Mbyll')}</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between sm:justify-center gap-1.5 sm:gap-2 w-full md:w-auto">
        {prevArticleNum !== null ? (
          <button
            type="button"
            onClick={() => onNavigateToArticle(prevArticleNum)}
            className="h-9 sm:h-10 px-2.5 sm:px-3.5 flex items-center justify-center rounded-xl text-xs font-semibold bg-surface border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm cursor-pointer shrink-0 gap-1"
            title={t('lawArticle.prevArticle', 'Neni i Mëparshëm')}
          >
            <ChevronLeft size={15} className="text-primary-start" />
            <span className="hidden sm:inline">
              {prevArticleNum === '0'
                ? t('lawArticle.preamble', 'Preambula')
                : `${t('lawArticle.article', 'Neni')} ${prevArticleNum}`}
            </span>
          </button>
        ) : (
          <div className="w-8 sm:w-10 opacity-0 pointer-events-none" />
        )}

        <form
          onSubmit={onJumpSubmit}
          className="relative flex-1 sm:flex-initial min-w-[120px] max-w-[200px] sm:max-w-none"
        >
          <Search
            size={13}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none"
          />
          <input
            type="text"
            placeholder={t('lawArticle.jumpPlaceholder', 'Neni (p.sh. 390)...')}
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
            title={t('lawArticle.nextArticle', 'Neni i Ardhshëm')}
          >
            <span className="hidden sm:inline">{`${t('lawArticle.article', 'Neni')} ${nextArticleNum}`}</span>
            <ChevronRight size={15} className="text-primary-start" />
          </button>
        ) : (
          <div className="w-8 sm:w-10 opacity-0 pointer-events-none" />
        )}
      </div>

      <div className="hidden md:flex items-center shrink-0">
        {!chatVisible ? (
          <button
            onClick={onStartAudit}
            disabled={isSummarizing}
            className="h-10 px-4 flex items-center gap-2 rounded-xl text-xs font-semibold transition-all shadow-sm hover-lift bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer"
          >
            {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
            <span>
              {isSummarizing
                ? t('lawArticle.analyzing', 'Duke Analizuar...')
                : t('lawArticle.auditBtn', 'Auditimi Ligjor')}
            </span>
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

      {createPortal(tooltipPortal, document.body)}
    </div>
  );
};

export default LawArticleHeader;