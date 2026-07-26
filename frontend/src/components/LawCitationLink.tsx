// FILE: src/components/LawCitationLink.tsx
// PHOENIX PROTOCOL - LAW CITATION LINK V1.2 (REMOVED OLD TITLE TOOLTIP)

import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, Eye } from 'lucide-react';
import { apiService } from '../services/api';

export interface LawCitationLinkProps {
  /** The full law title (e.g., "Ligji Nr. 03/L-006") */
  lawTitle: string;
  /** The article number (e.g., "92") */
  articleNum: string;
  /** The full match text to display (e.g., "Ligjit Nr. 03/L-006, Neni 92") */
  fullMatch: string;
  /** The target URL for navigation */
  targetUrl: string;
  /** Optional className for styling */
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

/**
 * LawCitationLink Component
 * 
 * Displays a clickable law citation with:
 * - Confidence badge (✅ Verified / ⚠️ Needs verification)
 * - Tooltip with full source information on hover
 * - Lazy loading of source_info
 * 
 * Used in: Chat, Analysis Modal, Draft, Search Results, PDF Generation
 */
export const LawCitationLink: React.FC<LawCitationLinkProps> = ({
  lawTitle,
  articleNum,
  fullMatch,
  targetUrl,
  className = '',
}) => {
  console.log('🔥🔥🔥 LawCitationLink is RENDERING!', lawTitle); // ← Debug log

  const [sourceInfo, setSourceInfo] = useState<SourceInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch source_info from the backend
  const fetchSourceInfo = async () => {
    if (sourceInfo || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.getLawArticle(lawTitle, articleNum);
      setSourceInfo(response.source_info || null);
    } catch (err) {
      console.error('Failed to fetch source info:', err);
      setError('Nuk mund të verifikohej burimi.');
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
    }, 300);
  };

  const handleMouseLeave = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  // Determine confidence badge
  const confidenceLevel = sourceInfo?.confidence?.level || 'UNKNOWN';
  const confidenceLabel = sourceInfo?.confidence?.label || 'Verifiko';

  const getBadgeColor = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-success-start/20 text-success-start border-success-start/30';
      case 'MEDIUM':
        return 'bg-warning-start/20 text-warning-start border-warning-start/30';
      case 'LOW':
      case 'LOWEST':
        return 'bg-danger-start/20 text-danger-start border-danger-start/30';
      default:
        return 'bg-text-muted/10 text-text-muted border-text-muted/20';
    }
  };

  const getBadgeIcon = (level: string) => {
    switch (level) {
      case 'HIGH':
        return '✅';
      case 'MEDIUM':
        return '🔍';
      case 'LOW':
      case 'LOWEST':
        return '⚠️';
      default:
        return '📋';
    }
  };

  return (
    <span
      className={`relative inline-flex items-center gap-1 group align-middle ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Citation Link - NO title attribute here! */}
      <Link
        to={targetUrl}
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-bold transition-all shadow-sm hover:shadow-md hover:scale-[1.02] bg-primary-start/10 text-primary-start border border-primary-start/30 hover:bg-primary-start/20 mx-1 align-middle"
      >
        <Scale size={11} className="text-primary-start shrink-0" />
        <span>{fullMatch}</span>
        <Eye size={11} className="opacity-70 ml-0.5 shrink-0" />
      </Link>

      {/* Confidence Badge - shown when source_info is available */}
      {sourceInfo && (
        <span
          className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider border ${getBadgeColor(
            confidenceLevel
          )} shrink-0`}
        >
          <span>{getBadgeIcon(confidenceLevel)}</span>
          <span className="hidden sm:inline">{confidenceLabel}</span>
        </span>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <span className="w-3 h-3 border-2 border-primary-start border-t-transparent rounded-full spinner-robust shrink-0" />
      )}

      {/* Error indicator */}
      {error && !isLoading && (
        <span className="text-[8px] text-danger-start font-black uppercase tracking-widest shrink-0">
          ⚠️ Gabim
        </span>
      )}

      {/* Tooltip with full source info */}
      <AnimatePresence>
        {showTooltip && sourceInfo && (
          <motion.div
            initial={{ opacity: 0, y: 5, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 5, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-surface border border-main rounded-xl shadow-2xl z-[300] text-left pointer-events-none"
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-base">{sourceInfo.confidence?.icon || '📋'}</span>
              <span className="font-bold text-xs text-text-primary">
                {sourceInfo.confidence?.label || 'Verifiko'}
              </span>
              {sourceInfo.confidence?.score !== undefined &&
                sourceInfo.confidence.score > 0 && (
                  <span className="ml-auto text-[9px] text-text-muted font-bold uppercase tracking-widest">
                    {Math.round(sourceInfo.confidence.score * 100)}% përputhje
                  </span>
                )}
            </div>

            <div className="text-[10px] text-text-secondary leading-relaxed space-y-1">
              <div className="font-medium text-text-primary text-[11px]">
                {sourceInfo.matched_law || lawTitle}
              </div>
              <div className="text-text-muted text-[9px]">
                Neni {sourceInfo.matched_article || articleNum}
              </div>

              {sourceInfo.was_mapped && sourceInfo.mapped_from && (
                <div className="mt-1 text-warning-start text-[9px] font-medium">
                  📌 Kërkuar si: <span className="font-bold">{sourceInfo.mapped_from}</span>
                </div>
              )}

              {sourceInfo.multiple_matches &&
                sourceInfo.matching_laws?.length > 0 && (
                  <div className="mt-1 text-danger-start text-[9px] font-medium">
                    ⚠️ Ky nen ekziston në {sourceInfo.matching_laws.length} ligje të ndryshme
                  </div>
                )}

              <div className="mt-1.5 text-[9px] text-text-muted border-t border-main/50 pt-1.5 italic">
                {sourceInfo.verification_hint || 'Verifikoni me burimin zyrtar.'}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Spinner styles for loading indicator */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spinner-robust {
          animation: spin 1s linear infinite !important;
        }
      `}</style>
    </span>
  );
};

export default LawCitationLink;