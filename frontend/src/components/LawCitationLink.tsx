// FILE: src/components/LawCitationLink.tsx
// PHOENIX PROTOCOL - IN-PLACE LAW ARTICLE VIEWER V18.1 (ZERO REDIRECTION • INSTANT JUMPING)
// 100% COMPLETE CODE • OPENS PDF MODAL IN-PLACE • HARD PINNED TOOLTIP • ZERO TS WARNINGS

import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, ShieldCheck, CheckCircle2, X, Loader2, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService, API_V1_URL } from '../services/api';
import FileViewerModal from './FileViewerModal';

export interface LawCitationLinkProps {
  lawTitle: string;
  articleNum: string;
  fullMatch: string;
  targetUrl?: string;
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
  page?: number;
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
  const { t } = useTranslation();

  const [sourceInfo, setSourceInfo] = useState<SourceInfo | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfPageNumber, setPdfPageNumber] = useState<number>(1);
  const [pdfFilename, setPdfFilename] = useState<string>('Ligji_Zyrtar.pdf');

  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [coords, setCoords] = useState({
    top: 0,
    desktopLeft: 0,
    arrowLeftPx: 50,
    isFlippedBelow: false,
    isMobile: false,
  });
  const containerRef = useRef<HTMLSpanElement>(null);

  const cleanDisplayLabel = (fullMatch || `${lawTitle} - Neni ${articleNum}`)
    .replace(/^\[+|\]+$/g, '')
    .trim();

  const updateCoordinates = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const isMobile = viewportWidth < 768;

      const idealCenter = rect.left + rect.width / 2;

      let arrowPx: number;
      let desktopLeft = 0;

      if (isMobile) {
        const tooltipBoxLeft = Math.max(12, (viewportWidth - Math.min(viewportWidth - 24, 360)) / 2);
        arrowPx = Math.max(20, Math.min(rect.left + rect.width / 2 - tooltipBoxLeft, Math.min(viewportWidth - 24, 360) - 20));
      } else {
        const tooltipWidth = 360;
        const margin = 16;
        desktopLeft = Math.max(tooltipWidth / 2 + margin, Math.min(idealCenter, viewportWidth - tooltipWidth / 2 - margin));
        arrowPx = Math.max(20, Math.min(idealCenter - (desktopLeft - tooltipWidth / 2), tooltipWidth - 20));
      }

      const estimatedHeight = 240;
      const isFlippedBelow = rect.top < (estimatedHeight + 20);
      const computedTop = isFlippedBelow ? (rect.bottom + 8) : (rect.top - 8);

      setCoords({
        top: computedTop,
        desktopLeft,
        arrowLeftPx: arrowPx,
        isFlippedBelow,
        isMobile,
      });
    }
  };

  const fetchSourceInfo = async () => {
    if (sourceInfo) return;
    try {
      const cleanArt = (articleNum || '').replace(/\D+/g, '') || articleNum;
      const response = await apiService.getLawArticle(lawTitle, cleanArt);
      if (response && response.source_info) {
        setSourceInfo(response.source_info);
      }
    } catch {
      // Hilët në heshtje
    }
  };

  const handleOpen = () => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
      fetchSourceInfo();
    }, 120);
  };

  const handleClose = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  useEffect(() => {
    if (!showTooltip) return;
    const handleOutsideClick = (e: TouchEvent | MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowTooltip(false);
      }
    };
    window.addEventListener('touchstart', handleOutsideClick);
    window.addEventListener('click', handleOutsideClick);
    return () => {
      window.removeEventListener('touchstart', handleOutsideClick);
      window.removeEventListener('click', handleOutsideClick);
    };
  }, [showTooltip]);

  // HAPJA E MENJËHERSHME E PDF-SË NË VEND (OPSIONI A)
  const handleDirectOpenPdf = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowTooltip(false);

    if (isLoadingPdf) return;
    setIsLoadingPdf(true);

    try {
      const cleanArt = (articleNum || '').replace(/\D+/g, '') || articleNum;
      const res = await apiService.getLawArticle(lawTitle, cleanArt);

      const pageNum = res.page || res.page_number || 1;
      const targetFile = res.source || `${lawTitle}.pdf`;

      setPdfPageNumber(pageNum);
      setPdfFilename(targetFile);

      const fullUrl = `${API_V1_URL}/laws/pdf/${encodeURIComponent(targetFile)}`;
      setPdfUrl(fullUrl);
      setShowPdfModal(true);

    } catch (err) {
      if (targetUrl) {
        window.open(targetUrl, '_blank');
      }
    } finally {
      setIsLoadingPdf(false);
    }
  };

  const tooltipContent = (
    <AnimatePresence>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: coords.isFlippedBelow ? -8 : 8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: coords.isFlippedBelow ? -8 : 8, scale: 0.96 }}
          transition={{ duration: 0.12 }}
          className={`fixed p-3.5 sm:p-4 bg-white dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 border-2 border-emerald-500/60 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[999999] pointer-events-auto ring-1 ring-black/10 dark:ring-white/10 ${
            coords.isMobile
              ? 'left-3 right-3 mx-auto max-w-[360px] w-[calc(100vw-24px)]'
              : 'w-[360px]'
          }`}
          style={{
            top: `${coords.top}px`,
            left: coords.isMobile ? '12px' : `${coords.desktopLeft}px`,
            right: coords.isMobile ? '12px' : 'auto',
            transform: coords.isMobile
              ? (coords.isFlippedBelow ? 'translateY(0%)' : 'translateY(-100%)')
              : (coords.isFlippedBelow ? 'translate(-50%, 0%)' : 'translate(-50%, -100%)'),
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1.5 font-black text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
              <ShieldCheck size={15} />
              <span>Verifikim Faktik në Server</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <CheckCircle2 size={10} />
                <span>100% ZYRTAR</span>
              </span>
              {coords.isMobile && (
                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-200"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          {/* Titulli i Ligjit & Neni */}
          <div className="text-xs sm:text-sm font-black text-slate-900 dark:text-white mb-1.5 leading-snug">
            {sourceInfo?.matched_law || lawTitle} • Neni {sourceInfo?.matched_article || articleNum}
          </div>

          {/* Të Dhënat Reale */}
          <div className="space-y-1 text-[11px] font-sans bg-slate-50 dark:bg-slate-900/90 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 mb-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">Burimi në Server:</span>
              <strong className="truncate max-w-[180px] font-mono text-[10px]" title={sourceInfo?.source_file}>
                {sourceInfo?.source_file || 'Gazeta Zyrtare e Kosovës'}
              </strong>
            </div>
            {sourceInfo?.page && (
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400">Vendi në Dokument:</span>
                <strong className="text-emerald-600 dark:text-emerald-400 font-bold">Faqja {sourceInfo.page}</strong>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">Veprimi:</span>
              <strong className="text-emerald-600 dark:text-emerald-400">Hapje e Menjëhershme në PDF ✓</strong>
            </div>
          </div>

          {/* Udhëzimi me 1-Klikim */}
          <div className="mt-2 flex items-center justify-between text-[10.5px] text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-1.5">
            <span>Kliko për të hapur ligjin origjinal</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-0.5">
              Hap PDF <ExternalLink size={10} />
            </span>
          </div>

          {/* Shigjeta adaptive */}
          <div
            className={`absolute border-[7px] border-transparent pointer-events-none ${
              coords.isFlippedBelow 
                ? 'bottom-full -mb-[1px] border-b-white dark:border-b-[#0b0f19]' 
                : 'top-full -mt-[1px] border-t-white dark:border-t-[#0b0f19]'
            }`}
            style={{
              left: `${coords.arrowLeftPx}px`,
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <>
      <span
        ref={containerRef}
        className={`inline-flex items-center align-baseline mx-0.5 my-0.5 max-w-full ${className}`}
        onMouseEnter={handleOpen}
        onMouseLeave={handleClose}
      >
        <button
          type="button"
          onClick={handleDirectOpenPdf}
          disabled={isLoadingPdf}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/25 text-primary-start font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full cursor-pointer focus:outline-none"
        >
          {isLoadingPdf ? (
            <Loader2 size={13} className="animate-spin text-primary-start" />
          ) : (
            <Scale size={13} className="shrink-0 opacity-80" />
          )}
          <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanDisplayLabel}</span>
        </button>

        {createPortal(tooltipContent, document.body)}
      </span>

      {/* Dritarja Modale In-Place e PDF-së */}
      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: pdfFilename,
            article_number: articleNum,
            title: lawTitle,
            page_number: pdfPageNumber,
            page: pdfPageNumber,
            mime_type: 'application/pdf',
          }}
          initialPage={pdfPageNumber}
          directUrl={pdfUrl}
          isAuth={true}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </>
  );
};

export default LawCitationLink;