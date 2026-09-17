// FILE: src/components/PrecedentCitationLink.tsx
// PHOENIX PROTOCOL - INFALLIBLE MOBILE PINNED PRECEDENT VIEWER V21.0
// V21.0: Zero hex. amber-* → warning-start, slate-* → semantic. border-b/t-card.

import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Gavel, FileText, ExternalLink, Loader2, X } from 'lucide-react';
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
    desktopLeft: 0,
    arrowLeftPx: 50,
    isFlippedBelow: false,
    isMobile: false,
  });
  const containerRef = useRef<HTMLSpanElement>(null);

  const cleanLabel = caseNumber.replace(/^\[+|\]+$/g, '').trim();

  const updateCoordinates = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const isMobile = viewportWidth < 768;

      const idealCenter = rect.left + rect.width / 2;

      let arrowPx: number;
      let desktopLeft = 0;

      if (isMobile) {
        const tooltipBoxLeft = Math.max(12, (viewportWidth - Math.min(viewportWidth - 24, 390)) / 2);
        arrowPx = Math.max(20, Math.min(idealCenter - tooltipBoxLeft, Math.min(viewportWidth - 24, 390) - 20));
      } else {
        const tooltipWidth = 390;
        const margin = 16;
        desktopLeft = Math.max(tooltipWidth / 2 + margin, Math.min(idealCenter, viewportWidth - tooltipWidth / 2 - margin));
        arrowPx = Math.max(20, Math.min(idealCenter - (desktopLeft - tooltipWidth / 2), tooltipWidth - 20));
      }

      const estimatedHeight = 220;
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

  const handleOpen = () => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
    }, 100);
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

  const handleDirectOpenPdf = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowTooltip(false);

    if (isLoadingPdf) return;
    setIsLoadingPdf(true);

    try {
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

      const fullUrl = `${API_V1_URL}/laws/caselaw/pdf/${encodeURIComponent(targetFile)}`;
      setPdfUrl(fullUrl);
      setShowPdfModal(true);

    } catch (err) {
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
          className={`fixed p-3.5 sm:p-4 bg-card text-text-primary border-2 border-warning-start/50 rounded-2xl shadow-2xl z-[999999] pointer-events-auto ${
            coords.isMobile
              ? 'left-3 right-3 mx-auto max-w-[390px] w-[calc(100vw-24px)]'
              : 'w-[390px]'
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
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-main">
            <div className="flex items-center gap-1.5 text-warning-start font-black text-xs uppercase tracking-wider">
              <Gavel size={15} />
              <span>Gjykata Supreme e Kosovës</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded-md bg-warning-start/15 text-warning-start font-mono text-[10px] font-bold">
                PRECEDENT
              </span>
              {coords.isMobile && (
                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1 rounded-md text-text-muted hover:text-text-primary"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          {/* Numri Zyrtar */}
          <div className="text-xs sm:text-sm font-black text-text-primary mb-1.5 leading-snug">
            Vendimi: {cleanLabel}
          </div>

          {/* Të Dhënat Reale */}
          <div className="space-y-1 text-xs text-text-secondary font-sans bg-surface/80 p-2 rounded-xl border border-main mb-1.5">
            <div className="flex items-center justify-between">
              <span className="text-text-muted font-medium">Instanca:</span>
              <strong>Kolegji i Gjykatës Supreme</strong>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-muted font-medium">Burimi:</span>
              <strong className="text-warning-start flex items-center gap-1">
                <FileText size={11} />
                Dokument Zyrtar i Arkivuar (PDF)
              </strong>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-muted font-medium">Veprimi:</span>
              <strong className="text-success-start">Hapje e Menjëhershme në Ekran ✓</strong>
            </div>
          </div>

          {/* Udhëzimi me 1-Klikim */}
          <div className="mt-2 flex items-center justify-between text-[10.5px] text-text-muted border-t border-main pt-1.5">
            <span>Kliko për të hapur aktgjykimin në vend</span>
            <span className="text-warning-start font-bold flex items-center gap-0.5">
              Hap Këtu <ExternalLink size={10} />
            </span>
          </div>

          {/* Shigjeta adaptive */}
          <div
            className={`absolute border-[7px] border-transparent pointer-events-none ${
              coords.isFlippedBelow 
                ? 'bottom-full -mb-[1px] border-b-card' 
                : 'top-full -mt-[1px] border-t-card'
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
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-warning-start/10 hover:bg-warning-start/20 border border-warning-start/30 text-warning-start font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full cursor-pointer focus:outline-none"
        >
          {isLoadingPdf ? (
            <Loader2 size={13} className="animate-spin text-warning-start" />
          ) : (
            <Gavel size={13} className="shrink-0 opacity-90" />
          )}
          <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanLabel}</span>
        </button>

        {createPortal(tooltipContent, document.body)}
      </span>

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