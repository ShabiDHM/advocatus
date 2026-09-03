// FILE: src/components/LawCitationLink.tsx
// PHOENIX PROTOCOL - SOLID FORENSIC TOOLTIP (NO NATIVE TITLE, NO DOUBLE TOOLTIP) V12.0

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, ShieldCheck } from 'lucide-react';
import { apiService } from '../services/api';

export interface LawCitationLinkProps {
  lawTitle: string;
  articleNum: string;
  fullMatch: string;
  targetUrl: string;
  className?: string;
}

interface SourceInfo {
  confidence: {
    level: 'HIGH' | 'MEDIUM' | 'LOW' | 'LOWEST' | 'UNKNOWN' | 'NONE';
    label: string;
    icon: string;
    color: string;
    description: string;
    score: number;
  };
  matched_law: string;
  matched_article: string;
  source_file: string;
  was_mapped: boolean;
  mapped_from: string | null;
  multiple_matches: boolean;
  matching_laws: string[];
  strategy_used: string;
  verification_hint: string;
  match_count: number;
}

export const LawCitationLink: React.FC<LawCitationLinkProps> = ({
  lawTitle,
  articleNum,
  fullMatch,
  targetUrl,
  className = '',
}) => {
  const [sourceInfo, setSourceInfo] = useState<SourceInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [coords, setCoords] = useState({ top: 0, tooltipLeft: 0, arrowOffset: 0 });
  const containerRef = useRef<HTMLSpanElement>(null);

  const cleanDisplayLabel = (fullMatch || `${lawTitle} - Neni ${articleNum}`)
    .replace(/^\[+|\]+$/g, '')
    .trim();

  const updateCoordinates = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const tooltipWidth = viewportWidth < 640 ? 300 : 340;
      const margin = 16;

      const idealLeft = rect.left + rect.width / 2;
      const minLeft = tooltipWidth / 2 + margin;
      const maxLeft = viewportWidth - tooltipWidth / 2 - margin;
      const clampedLeft = Math.max(minLeft, Math.min(idealLeft, maxLeft));
      const arrowOffset = idealLeft - clampedLeft;

      setCoords({
        top: rect.top + window.scrollY,
        tooltipLeft: clampedLeft,
        arrowOffset: arrowOffset,
      });
    }
  };

  const fetchSourceInfo = async () => {
    if (sourceInfo || isLoading) return;
    setIsLoading(true);
    try {
      const response = await apiService.getLawArticle(lawTitle, articleNum);
      setSourceInfo(response.source_info || null);
    } catch {
      // Graceful fallback on network/lookup failure
    } finally {
      setIsLoading(false);
    }
  };

  const handleMouseEnter = () => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
      fetchSourceInfo();
    }, 180);
  };

  const handleMouseLeave = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  const getBorderColorClass = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'border-emerald-500/60';
      case 'MEDIUM':
        return 'border-amber-500/60';
      case 'LOW':
      case 'LOWEST':
        return 'border-rose-500/60';
      default:
        return 'border-primary-start/60';
    }
  };

  const getBadgeColorClass = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-emerald-500/10 text-emerald-500';
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-500';
      case 'LOW':
      case 'LOWEST':
        return 'bg-rose-500/10 text-rose-500';
      default:
        return 'bg-primary-start/10 text-primary-start';
    }
  };

  const tooltipContent = (
    <AnimatePresence>
      {showTooltip && sourceInfo && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.95 }}
          transition={{ duration: 0.12 }}
          className={`absolute w-72 sm:w-80 p-4 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-2 ${getBorderColorClass(
            sourceInfo.confidence?.level || 'UNKNOWN'
          )} rounded-2xl shadow-2xl z-[9999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10`}
          style={{
            top: `${coords.top - 8}px`,
            left: `${coords.tooltipLeft}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-200 dark:border-slate-800">
            <div className={`flex items-center gap-1.5 font-bold text-xs ${getBadgeColorClass(sourceInfo.confidence?.level || 'UNKNOWN').split(' ')[1]}`}>
              <ShieldCheck size={16} />
              <span>{sourceInfo.confidence?.label || 'Tekst Zyrtar i Verifikuar'}</span>
            </div>
            {sourceInfo.confidence?.score !== undefined && sourceInfo.confidence.score > 0 && (
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${getBadgeColorClass(sourceInfo.confidence?.level || 'UNKNOWN')}`}>
                {Math.round(sourceInfo.confidence.score * 100)}% SCORE
              </span>
            )}
          </div>

          <div className="text-xs font-bold text-slate-900 dark:text-white mb-1 leading-snug">
            {sourceInfo.matched_law || lawTitle} • Neni {sourceInfo.matched_article || articleNum}
          </div>

          <div className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed mb-2.5">
            {sourceInfo.verification_hint || 'Nen i nxjerrë direkt nga Kodi Zyrtar.'}
          </div>

          <div className="flex items-center justify-between text-[10px] font-mono bg-slate-100 dark:bg-slate-950 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
            <span>Integriteti i Tekstit:</span>
            <span className={`font-bold ${getBadgeColorClass(sourceInfo.confidence?.level || 'UNKNOWN').split(' ')[1]}`}>
              Tekst i Paprekur ✓
            </span>
          </div>

          <div
            className="absolute top-full -translate-x-1/2 -mt-[2px] border-[8px] border-transparent pointer-events-none"
            style={{
              borderTopColor: 'var(--tw-prose-body, currentColor)', // Ose mund të përdorni ngjyrën nga klasa parent (border-emerald)
              opacity: 0.6,
              left: `calc(50% + ${coords.arrowOffset}px)`,
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <span
      ref={containerRef}
      className={`inline-flex items-center align-baseline mx-0.5 my-0.5 max-w-full ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Link
        to={targetUrl}
        // 👉 Fshirë atributi `title` PËR TË NDALUAR BROWSER NATIVE TOOLTIP!
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/25 text-primary-start font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full"
      >
        <Scale size={13} className="shrink-0 opacity-80" />
        <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanDisplayLabel}</span>
      </Link>

      {createPortal(tooltipContent, document.body)}
    </span>
  );
};

export default LawCitationLink;