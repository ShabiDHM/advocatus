// FILE: src/components/LawCitationLink.tsx
// PHOENIX PROTOCOL - EXACT ASCII MATCH LAW CITATION LINK V4.0

import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Paperclip } from 'lucide-react';
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
  const [error, setError] = useState<string | null>(null);
  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchSourceInfo = async () => {
    if (sourceInfo || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.getLawArticle(lawTitle, articleNum);
      setSourceInfo(response.source_info || null);
    } catch {
      setError('Nuk u verifikua dot burimi.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleMouseEnter = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
    }
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
      fetchSourceInfo();
    }, 200);
  };

  const handleMouseLeave = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  const confidenceLevel = sourceInfo?.confidence?.level || 'UNKNOWN';

  const getBadgeStyle = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30';
      case 'LOW':
      case 'LOWEST':
        return 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-500/30';
    }
  };

  return (
    <span
      className={`relative inline-flex items-center gap-2 px-2.5 py-1 rounded-xl bg-surface/90 border border-main shadow-sm my-1 align-middle group cursor-pointer transition-all hover:border-primary-start/50 ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* 1. Citation Link Pill */}
      <Link
        to={targetUrl}
        className="inline-flex items-center gap-1.5 font-bold text-xs sm:text-sm text-primary-start hover:underline tracking-tight"
      >
        <Paperclip size={13} className="text-primary-start shrink-0" />
        <span>[{fullMatch}]</span>
      </Link>

      {/* 2. Right Verification Badge */}
      {sourceInfo && (
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-black uppercase tracking-wider border ${getBadgeStyle(
            confidenceLevel
          )} shrink-0 transition-all`}
        >
          <span>{sourceInfo.confidence?.icon || '✅'}</span>
          <span>{sourceInfo.confidence?.label || 'E verifikuar'}</span>
        </span>
      )}

      {/* Loading Spinner */}
      {isLoading && (
        <span className="w-3.5 h-3.5 border-2 border-primary-start border-t-transparent rounded-full animate-spin shrink-0" />
      )}

      {/* Error Badge */}
      {error && !isLoading && (
        <span className="text-[9px] text-rose-500 font-black uppercase tracking-widest shrink-0">
          ⚠️ Gabim
        </span>
      )}

      {/* 3. Executive Tooltip Card */}
      <AnimatePresence>
        {showTooltip && sourceInfo && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-2 w-[440px] max-w-[90vw] p-4 bg-surface/98 backdrop-blur-2xl border-2 border-main rounded-2xl shadow-2xl z-[500] text-left font-mono text-xs text-text-primary pointer-events-none"
          >
            {/* Row 1: Status + Score */}
            <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-main/70">
              <div className="flex items-center gap-1.5 font-bold text-xs">
                <span>{sourceInfo.confidence?.icon || '✅'}</span>
                <span className="text-text-primary uppercase tracking-wide">
                  {sourceInfo.confidence?.label || 'E verifikuar'}
                </span>
              </div>
              {sourceInfo.confidence?.score !== undefined && sourceInfo.confidence.score > 0 && (
                <span className="text-[11px] font-bold text-text-secondary">
                  {Math.round(sourceInfo.confidence.score * 100)}% përputhje
                </span>
              )}
            </div>

            {/* Row 2: Official Law Name */}
            <div className="font-bold text-xs sm:text-sm text-text-primary leading-snug mb-1 font-sans">
              {sourceInfo.matched_law || lawTitle}
            </div>

            {/* Row 3: Article Number */}
            <div className="text-xs font-bold text-primary-start mb-2">
              Neni {sourceInfo.matched_article || articleNum}
            </div>

            {/* Row 4: Search Mapping (If Mapped) */}
            {sourceInfo.was_mapped && sourceInfo.mapped_from && (
              <div className="text-[11px] text-amber-500 font-medium mb-2 flex items-center gap-1.5">
                <span>📌</span>
                <span>Kërkuar si: ({sourceInfo.mapped_from})</span>
              </div>
            )}

            {/* Multiple Matches Warning (If applicable) */}
            {sourceInfo.multiple_matches && sourceInfo.matching_laws?.length > 0 && (
              <div className="text-[11px] text-rose-500 font-medium mb-2 flex items-center gap-1.5">
                <span>⚠️</span>
                <span>Ky nen ekziston në {sourceInfo.matching_laws.length} ligje të ndryshme në bazë</span>
              </div>
            )}

            {/* Row 5: Verification Hint */}
            <div className="text-[11px] text-emerald-500 dark:text-emerald-400 font-medium border-t border-main/50 pt-2 mt-2 flex items-center gap-1.5 font-sans">
              <span>{sourceInfo.confidence?.icon || '✅'}</span>
              <span>
                {sourceInfo.verification_hint || 'Ky nen korrespondon saktësisht me kërkimin.'}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
};

export default LawCitationLink;