// FILE: src/components/PrecedentCitationLink.tsx
// PHOENIX PROTOCOL - DIRECT IN-PLACE PRECEDENT VIEWER V18.0 (ZERO REDIRECTIONS • INSTANT MODAL)
// 100% COMPLETE CODE • OPENS EXACT PDF PAGE ON TOP OF CHAT • ZERO CONTEXT LOSS

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Gavel, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService, API_V1_URL } from '../services/api';
import FileViewerModal from './FileViewerModal';

export interface PrecedentCitationLinkProps {
  caseNumber: string;
  className?: string;
}

export const PrecedentCitationLink: React.FC<PrecedentCitationLinkProps> = ({
  caseNumber,
  className = '',
}) => {
  const { t } = useTranslation();
  const [showTooltip, setShowTooltip] = useState(false);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfPageNumber, setPdfPageNumber] = useState<number>(1);
  const [pdfFilename, setPdfFilename] = useState<string>('Aktgjykim_Suprem.pdf');

  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [coords, setCoords] = useState({
    top: 0,
    left: 0,
    arrowLeft: 0,
    isFlippedBelow: false,
  });
  const containerRef = useRef<HTMLSpanElement>(null);

  const cleanLabel = caseNumber.replace(/^\[+|\]+$/g, '').trim();

  const updateCoordinates = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const tooltipWidth = Math.min(viewportWidth - 32, viewportWidth < 640 ? 320 : 400);
      const margin = 16;

      const idealCenter = rect.left + rect.width / 2;
      const minLeft = tooltipWidth / 2 + margin;
      const maxLeft = viewportWidth - tooltipWidth / 2 - margin;
      const clampedLeft = Math.max(minLeft, Math.min(idealCenter, maxLeft));
      const arrowOffset = idealCenter - clampedLeft;

      const estimatedTooltipHeight = 220;
      const isFlippedBelow = rect.top < (estimatedTooltipHeight + 20);
      const computedTop = isFlippedBelow ? (rect.bottom + 10) : (rect.top - 10);

      setCoords({
        top: computedTop,
        left: clampedLeft,
        arrowLeft: arrowOffset,
        isFlippedBelow,
      });
    }
  };

  const handleMouseEnter = () => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
    }, 150);
  };

  const handleMouseLeave = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  // HAPJA E DREJTPËRDREJTË E PDF-SË PA BRAKTISUR FAQEN E BISEDËS
  const handleDirectOpenPdf = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowTooltip(false);

    if (isLoadingPdf) return;
    setIsLoadingPdf(true);

    try {
      // 1. Pyet serverin për faqen e saktë dhe emrin zyrtar të skedarit
      const res = await apiService.axiosInstance.get('/laws/case-page', {
        params: { law_title: cleanLabel }
      });

      const pageNum = res.data?.page || res.data?.page_number || 1;
      let targetFile = res.data?.law_title || cleanLabel;
      if (!targetFile.toLowerCase().endsWith('.pdf')) {
        targetFile = `${targetFile}.pdf`;
      }

      setPdfPageNumber(pageNum);
      setPdfFilename(targetFile);

      // 2. Ndërton URL-në e drejtpërdrejtë për hapjen e shpejtë të PDF-së
      const fullUrl = `${API_V1_URL}/laws/caselaw/pdf/${encodeURIComponent(targetFile)}`;
      setPdfUrl(fullUrl);
      setShowPdfModal(true);

    } catch (err) {
      // Fallback nëse serveri nuk kthen faqe specifike: hap PDF-në me emrin bazë
      const fallbackFile = cleanLabel.toLowerCase().endsWith('.pdf') ? cleanLabel : `${cleanLabel}.pdf`;
      setPdfFilename(fallbackFile);
      setPdfPageNumber(1);
      setPdfUrl(`${API_V1_URL}/laws/caselaw/pdf/${encodeURIComponent(fallbackFile)}`);
      setShowPdfModal(true);
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
          className="fixed w-[320px] sm:w-[400px] p-4 sm:p-5 bg-white dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 border-2 border-amber-500/50 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[999999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10"
          style={{
            top: `${coords.top}px`,
            left: `${coords.left}px`,
            transform: coords.isFlippedBelow ? 'translate(-50%, 0%)' : 'translate(-50%, -100%)',
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-black text-xs uppercase tracking-wider">
              <Gavel size={16} />
              <span>Gjykata Supreme e Kosovës</span>
            </div>
            <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 font-mono text-[10px] font-bold">
              PRECEDENT GJYQËSOR
            </span>
          </div>

          {/* Numri Zyrtar */}
          <div className="text-sm sm:text-base font-black text-slate-900 dark:text-white mb-2 leading-snug">
            Vendimi: {cleanLabel}
          </div>

          {/* Të Dhënat Reale */}
          <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300 font-sans bg-slate-50 dark:bg-slate-900/80 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 font-medium">Instanca:</span>
              <strong>Kolegji i Gjykatës Supreme</strong>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 font-medium">Burimi:</span>
              <strong className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                <FileText size={12} />
                Dokument Zyrtar i Arkivuar (PDF)
              </strong>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 font-medium">Veprimi:</span>
              <strong className="text-emerald-600 dark:text-emerald-400">Hapje e Menjëhershme në Ekran ✓</strong>
            </div>
          </div>

          {/* Udhëzimi me 1-Klikim */}
          <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-2">
            <span>Kliko për të hapur aktgjykimin në modal</span>
            <span className="text-amber-500 font-bold flex items-center gap-0.5">
              Hap Këtu <ExternalLink size={10} />
            </span>
          </div>

          {/* Shigjeta inteligjente */}
          <div
            className={`absolute -translate-x-1/2 border-[8px] border-transparent pointer-events-none ${
              coords.isFlippedBelow 
                ? 'bottom-full -mb-[1px] border-b-white dark:border-b-[#0b0f19]' 
                : 'top-full -mt-[1px] border-t-white dark:border-t-[#0b0f19]'
            }`}
            style={{
              left: `calc(50% + ${coords.arrowLeft}px)`,
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
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <button
          type="button"
          onClick={handleDirectOpenPdf}
          disabled={isLoadingPdf}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-600 dark:text-amber-400 font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full cursor-pointer focus:outline-none"
        >
          {isLoadingPdf ? (
            <Loader2 size={13} className="animate-spin text-amber-500" />
          ) : (
            <Gavel size={13} className="shrink-0 opacity-90" />
          )}
          <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanLabel}</span>
        </button>

        {createPortal(tooltipContent, document.body)}
      </span>

      {/* Dritarja Modale e Menjëhershme që hapet drejtpërdrejt pa lëvizur nga faqja */}
      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: pdfFilename,
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          initialPage={pdfPageNumber}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </>
  );
};

export default PrecedentCitationLink;