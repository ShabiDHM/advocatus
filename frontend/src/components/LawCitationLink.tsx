// FILE: src/components/LawCitationLink.tsx
// PHOENIX PROTOCOL - SOLID OPAQUE INLINE LAW CITATION LINK V11.0 (RESPONSIVE WRAP & ZERO OVERFLOW)

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale } from 'lucide-react';
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
        return 'border-t-emerald-500';
      case 'MEDIUM':
        return 'border-t-amber-500';
      case 'LOW':
      case 'LOWEST':
        return 'border-t-rose-500';
      default:
        return 'border-t-primary-start';
    }
  };

  const tooltipContent = (
    <AnimatePresence>
      {showTooltip && sourceInfo && (
        <motion.div
          initial={{ opacity: 0, y: 4, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.98 }}
          transition={{ duration: 0.12 }}
          className={`absolute w-72 sm:w-84 p-4 border border-main border-t-2 ${getBorderColorClass(
            sourceInfo.confidence?.level || 'UNKNOWN'
          )} rounded-2xl shadow-2xl z-[9999] text-left font-sans text-xs bg-surface text-text-primary pointer-events-none opacity-100`}
          style={{
            top: `${coords.top - 8}px`,
            left: `${coords.tooltipLeft}px`,
            transform: 'translate(-50%, -100%)',
            backgroundColor: 'var(--bg-surface, #1e222b)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 10px 20px -10px rgba(0, 0, 0, 0.4)',
          }}
        >
          <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-main">
            <div className="flex items-center gap-1.5 font-bold text-xs text-primary-start uppercase tracking-wider">
              <Scale size={14} className="shrink-0" />
              <span>{sourceInfo.confidence?.label || 'E verifikuar'}</span>
            </div>
            {sourceInfo.confidence?.score !== undefined && sourceInfo.confidence.score > 0 && (
              <span className="text-[10px] font-bold text-text-secondary">
                {Math.round(sourceInfo.confidence.score * 100)}% përputhje
              </span>
            )}
          </div>

          <div className="font-bold text-xs text-text-primary leading-snug mb-1">
            {sourceInfo.matched_law || lawTitle}
          </div>

          <div className="text-xs font-bold text-primary-start mb-2">
            Neni {sourceInfo.matched_article || articleNum}
          </div>

          <div className="text-[11px] text-text-secondary border-t border-main pt-2 mt-1 leading-relaxed">
            {sourceInfo.verification_hint || 'Baza ligjore e Kosovës korrespondon me kërkimin.'}
          </div>

          <div
            className="absolute top-full -translate-x-1/2 -mt-[1px] border-[7px] border-transparent pointer-events-none"
            style={{
              borderTopColor: 'var(--bg-surface, #1e222b)',
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
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/25 text-primary-start font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full"
        title={`Verifiko Nenin ${articleNum} të ${lawTitle}`}
      >
        <Scale size={11} className="shrink-0 opacity-80" />
        <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanDisplayLabel}</span>
      </Link>

      {createPortal(tooltipContent, document.body)}
    </span>
  );
};

export default LawCitationLink;