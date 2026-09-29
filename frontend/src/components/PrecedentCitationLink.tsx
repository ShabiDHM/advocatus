// FILE: src/components/PrecedentCitationLink.tsx
// PHOENIX PROTOCOL - PRECEDENT CITATION VIEWER V23.1
//
// V23.1: FIX terma teknike në anglisht → shqip.
//   - Përdoret `getMatchTypeLabel()` për `case_number_exact` → "Përputhje e saktë"
//   - Përdoret `getConfidenceLevelLabel()` për `HIGH` → "E lartë"
//   - Tooltip shfaq të gjitha etiketat në shqip
//
// V23.0: KONSISTENT ME V208.4 /case-page.
// V22.1: FIX TS6133.
// V22.0: ZERO FAKE VERIFICATION.

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Gavel, ExternalLink, Loader2, X, AlertTriangle, HelpCircle, Loader,
  ShieldCheck, Info,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService, API_V1_URL } from '../services/api';
import FileViewerModal from './FileViewerModal';
import { getMatchTypeLabel, getConfidenceLevelLabel } from '../utils/lawLabels';

export interface PrecedentCitationLinkProps {
  caseNumber: string;
  className?: string;
}

type PrecedentStatus =
  | 'idle'
  | 'loading'
  | 'verified_exact'
  | 'verified_regex'
  | 'reference_only'
  | 'unverified'
  | 'error';

interface CasePageSourceInfo {
  match_type: string;
  confidence: {
    level: string;
    score: number;
  };
  is_reference_only: boolean;
}

interface CasePageResponse {
  page: number | null;
  page_number: number | null;
  law_title: string;
  found: boolean;
  source_info?: CasePageSourceInfo | null;
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
  const [pdfPageNumber, setPdfPageNumber] = useState<number | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>('Aktgjykim_Suprem.pdf');

  const [status, setStatus] = useState<PrecedentStatus>('idle');
  const [caseInfo, setCaseInfo] = useState<CasePageResponse | null>(null);

  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sourceAbortRef = useRef<AbortController | null>(null);
  const pdfAbortRef = useRef<AbortController | null>(null);

  const [coords, setCoords] = useState({
    top: 0,
    desktopLeft: 0,
    arrowLeftPx: 50,
    isFlippedBelow: false,
    isMobile: false,
  });
  const containerRef = useRef<HTMLSpanElement>(null);

  const cleanLabel = useMemo(
    () => caseNumber.replace(/^\[+|\]+$/g, '').trim(),
    [caseNumber],
  );

  const updateCoordinates = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const isMobile = viewportWidth < 768;

      const idealCenter = rect.left + rect.width / 2;

      let arrowPx: number;
      let desktopLeft = 0;

      if (isMobile) {
        const tooltipBoxLeft = Math.max(
          12,
          (viewportWidth - Math.min(viewportWidth - 24, 390)) / 2,
        );
        arrowPx = Math.max(
          20,
          Math.min(
            idealCenter - tooltipBoxLeft,
            Math.min(viewportWidth - 24, 390) - 20,
          ),
        );
      } else {
        const tooltipWidth = 390;
        const margin = 16;
        desktopLeft = Math.max(
          tooltipWidth / 2 + margin,
          Math.min(idealCenter, viewportWidth - tooltipWidth / 2 - margin),
        );
        arrowPx = Math.max(
          20,
          Math.min(idealCenter - (desktopLeft - tooltipWidth / 2), tooltipWidth - 20),
        );
      }

      const estimatedHeight = 220;
      const isFlippedBelow = rect.top < estimatedHeight + 20;
      const computedTop = isFlippedBelow ? rect.bottom + 8 : rect.top - 8;

      setCoords({
        top: computedTop,
        desktopLeft,
        arrowLeftPx: arrowPx,
        isFlippedBelow,
        isMobile,
      });
    }
  }, []);

  const fetchCaseInfo = useCallback(async () => {
    if (
      status === 'verified_exact' ||
      status === 'verified_regex' ||
      status === 'reference_only' ||
      status === 'unverified'
    ) {
      return;
    }

    sourceAbortRef.current?.abort();
    const controller = new AbortController();
    sourceAbortRef.current = controller;

    setStatus('loading');

    try {
      const res = await apiService.axiosInstance.get<CasePageResponse>(
        '/laws/case-page',
        {
          params: { law_title: cleanLabel },
          signal: controller.signal,
        },
      );

      if (controller.signal.aborted) return;

      const data = res.data;
      setCaseInfo(data || null);

      if (!data || data.found !== true) {
        setStatus('unverified');
        return;
      }

      const matchType = data.source_info?.match_type || 'unknown';
      const isRefOnly = data.source_info?.is_reference_only === true;

      if (isRefOnly) {
        setStatus('reference_only');
        return;
      }

      if (matchType === 'case_number_exact' || matchType === 'case_number_regex') {
        setStatus('verified_exact');
        return;
      }

      if (matchType === 'law_title_exact' || matchType === 'law_title_regex') {
        setStatus('verified_regex');
        return;
      }

      setStatus('verified_regex');
    } catch (err: any) {
      if (err?.name === 'CanceledError' || err?.name === 'AbortError') return;
      if (!controller.signal.aborted) {
        console.error('[PrecedentCitationLink] Fetch error:', err);
        setStatus('error');
      }
    }
  }, [cleanLabel, status]);

  const handleOpen = useCallback(() => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
      fetchCaseInfo();
    }, 100);
  }, [updateCoordinates, fetchCaseInfo]);

  const handleClose = useCallback(() => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  }, []);

  useEffect(() => {
    return () => {
      if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
      sourceAbortRef.current?.abort();
      pdfAbortRef.current?.abort();
    };
  }, []);

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

    pdfAbortRef.current?.abort();
    const controller = new AbortController();
    pdfAbortRef.current = controller;

    try {
      const res = await apiService.axiosInstance.get<CasePageResponse>(
        '/laws/case-page',
        {
          params: { law_title: cleanLabel },
          signal: controller.signal,
        },
      );

      if (controller.signal.aborted) return;

      const data = res.data;

      const rawPage = data?.page ?? data?.page_number ?? null;
      const pageNum =
        typeof rawPage === 'number' && rawPage > 0
          ? rawPage
          : rawPage !== null
            ? parseInt(String(rawPage), 10) || null
            : null;

      let targetFile = data?.law_title || cleanLabel;
      if (!targetFile.toLowerCase().endsWith('.pdf')) {
        targetFile = `${targetFile}.pdf`;
      }

      setPdfPageNumber(pageNum);
      setPdfFilename(targetFile);

      const fullUrl = `${API_V1_URL}/laws/caselaw/pdf/${encodeURIComponent(targetFile)}`;
      setPdfUrl(fullUrl);
      setShowPdfModal(true);
    } catch (err: any) {
      if (err?.name === 'CanceledError' || err?.name === 'AbortError') return;

      const fallbackFile = cleanLabel.toLowerCase().endsWith('.pdf')
        ? cleanLabel
        : `${cleanLabel}.pdf`;
      setPdfFilename(fallbackFile);
      setPdfPageNumber(null);
      setPdfUrl(`${API_V1_URL}/laws/caselaw/pdf/${encodeURIComponent(fallbackFile)}`);
      setShowPdfModal(true);
    } finally {
      if (!controller.signal.aborted) setIsLoadingPdf(false);
    }
  };

  const statusConfig = useMemo(() => {
    switch (status) {
      case 'idle':
        return {
          icon: <HelpCircle size={15} />,
          label: t('precedentCitation.statusIdle', 'Kliko për verifikim'),
          badge: t('precedentCitation.statusIdleShort', 'I PAVERIFIKUAR'),
          color: 'text-text-muted',
          bgColor: 'bg-surface',
          borderColor: 'border-main',
          hint: t(
            'precedentCitation.idleHint',
            'Kliko për të kontrolluar nëse ky aktgjykim ekziston në arkivën zyrtare.',
          ),
        };
      case 'loading':
        return {
          icon: <Loader size={15} className="animate-spin" />,
          label: t('precedentCitation.statusLoading', 'Duke kontrolluar arkivën...'),
          badge: t('precedentCitation.statusLoadingShort', 'DUKE NGARKUAR'),
          color: 'text-primary-start',
          bgColor: 'bg-primary-start/10',
          borderColor: 'border-primary-start/30',
          hint: t('precedentCitation.loadingHint', 'Po kontrollojmë arkivën...'),
        };
      case 'verified_exact':
        return {
          icon: <ShieldCheck size={15} />,
          label: t('precedentCitation.statusVerifiedExact', 'Gjetur me numër të saktë lënde'),
          badge: t('precedentCitation.statusVerifiedExactShort', 'VERIFIKUAR'),
          color: 'text-success-start',
          bgColor: 'bg-success-start/10',
          borderColor: 'border-success-start/30',
          hint: t(
            'precedentCitation.verifiedExactHint',
            'Numri i lëndës përputhet saktësisht me një vendim në arkivë.',
          ),
        };
      case 'verified_regex':
        return {
          icon: <ShieldCheck size={15} />,
          label: t('precedentCitation.statusVerifiedRegex', 'Gjetur në arkivë'),
          badge: t('precedentCitation.statusVerifiedRegexShort', 'VERIFIKUAR'),
          color: 'text-success-start',
          bgColor: 'bg-success-start/10',
          borderColor: 'border-success-start/30',
          hint: t(
            'precedentCitation.verifiedRegexHint',
            'Gjetur me përputhje të pjesshme të numrit ose titullit.',
          ),
        };
      case 'reference_only':
        return {
          icon: <Info size={15} />,
          label: t('precedentCitation.statusReferenceOnly', 'Vetëm referencë në një dokument'),
          badge: t('precedentCitation.statusReferenceOnlyShort', 'REFERENCË'),
          color: 'text-warning-start',
          bgColor: 'bg-warning-start/10',
          borderColor: 'border-warning-start/30',
          hint: t(
            'precedentCitation.referenceOnlyHint',
            'Ky numër lënde përmendet në tekstin e një dokumenti tjetër, por nuk është gjetur si vendim i veçantë në arkivë.',
          ),
        };
      case 'unverified':
        return {
          icon: <AlertTriangle size={15} />,
          label: t('precedentCitation.statusUnverified', 'Nuk u gjet në arkivë'),
          badge: t('precedentCitation.statusUnverifiedShort', 'I PAVERIFIKUAR'),
          color: 'text-warning-start',
          bgColor: 'bg-warning-start/10',
          borderColor: 'border-warning-start/30',
          hint: t(
            'precedentCitation.unverifiedHint',
            'Ky aktgjykim nuk u gjet në arkivën zyrtare. Kontrollo numrin e lëndës ose provo manualisht.',
          ),
        };
      case 'error':
        return {
          icon: <AlertTriangle size={15} />,
          label: t('precedentCitation.statusError', 'Verifikimi dështoi'),
          badge: t('precedentCitation.statusErrorShort', 'GABIM'),
          color: 'text-danger-start',
          bgColor: 'bg-danger-start/10',
          borderColor: 'border-danger-start/30',
          hint: t(
            'precedentCitation.errorHint',
            'Verifikimi dështoi për shkak të rrjetit. Provo përsëri më vonë.',
          ),
        };
    }
  }, [status, t]);

  const buttonStyle = useMemo(() => {
    switch (status) {
      case 'verified_exact':
      case 'verified_regex':
        return 'bg-success-start/10 hover:bg-success-start/20 border-success-start/30 text-success-start';
      case 'reference_only':
        return 'bg-primary-start/10 hover:bg-primary-start/20 border-primary-start/30 text-primary-start';
      case 'unverified':
      case 'error':
        return 'bg-warning-start/10 hover:bg-warning-start/20 border-warning-start/30 text-warning-start';
      case 'loading':
        return 'bg-primary-start/10 hover:bg-primary-start/20 border-primary-start/30 text-primary-start';
      default:
        return 'bg-warning-start/10 hover:bg-warning-start/20 border-warning-start/30 text-warning-start';
    }
  }, [status]);

  const buttonIcon = useMemo(() => {
    if (isLoadingPdf) {
      return <Loader2 size={13} className="animate-spin shrink-0" />;
    }
    switch (status) {
      case 'verified_exact':
      case 'verified_regex':
        return <ShieldCheck size={13} className="shrink-0 opacity-90" />;
      case 'reference_only':
        return <Info size={13} className="shrink-0 opacity-90" />;
      case 'unverified':
      case 'error':
        return <AlertTriangle size={13} className="shrink-0 opacity-90" />;
      case 'loading':
        return <Loader size={13} className="animate-spin shrink-0 opacity-90" />;
      default:
        return <Gavel size={13} className="shrink-0 opacity-90" />;
    }
  }, [status, isLoadingPdf]);

  // V23.1: Përkthim i termave teknike
  const matchTypeLabel = useMemo(
    () => getMatchTypeLabel(caseInfo?.source_info?.match_type, t),
    [caseInfo?.source_info?.match_type, t],
  );

  const confidenceLevelLabel = useMemo(
    () => getConfidenceLevelLabel(caseInfo?.source_info?.confidence?.level, t),
    [caseInfo?.source_info?.confidence?.level, t],
  );

  const tooltipContent = (
    <AnimatePresence>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: coords.isFlippedBelow ? -8 : 8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: coords.isFlippedBelow ? -8 : 8, scale: 0.96 }}
          transition={{ duration: 0.12 }}
          className={`fixed p-3.5 sm:p-4 bg-card text-text-primary border-2 rounded-2xl shadow-2xl z-[999999] pointer-events-auto ${statusConfig.borderColor} ${
            coords.isMobile
              ? 'left-3 right-3 mx-auto max-w-[390px] w-[calc(100vw-24px)]'
              : 'w-[390px]'
          }`}
          style={{
            top: `${coords.top}px`,
            left: coords.isMobile ? '12px' : `${coords.desktopLeft}px`,
            right: coords.isMobile ? '12px' : 'auto',
            transform: coords.isMobile
              ? coords.isFlippedBelow
                ? 'translateY(0%)'
                : 'translateY(-100%)'
              : coords.isFlippedBelow
                ? 'translate(-50%, 0%)'
                : 'translate(-50%, -100%)',
          }}
        >
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-main">
            <div
              className={`flex items-center gap-1.5 font-black text-xs uppercase tracking-wider ${statusConfig.color}`}
            >
              {statusConfig.icon}
              <span>{statusConfig.label}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className={`px-2 py-0.5 rounded-md font-mono text-[10px] font-bold ${statusConfig.bgColor} ${statusConfig.color} border ${statusConfig.borderColor}`}
              >
                {statusConfig.badge}
              </span>
              {coords.isMobile && (
                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1 rounded-md text-text-muted hover:text-text-primary"
                  aria-label={t('general.close', 'Mbyll')}
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          <div className="text-xs sm:text-sm font-black text-text-primary mb-1.5 leading-snug">
            {t('precedentCitation.caseLabel', 'Vendimi')}: {cleanLabel}
          </div>

          {(status === 'verified_exact' ||
            status === 'verified_regex' ||
            status === 'reference_only' ||
            status === 'unverified') &&
            caseInfo && (
              <div className="space-y-1 text-xs text-text-secondary font-sans bg-surface/80 p-2 rounded-xl border border-main mb-1.5">
                {caseInfo.law_title && (
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-text-muted font-medium shrink-0">
                      {t('precedentCitation.sourceFile', 'Dokumenti')}:
                    </span>
                    <strong
                      className="truncate max-w-[220px] font-mono text-[10px] text-right"
                      title={caseInfo.law_title}
                    >
                      {caseInfo.law_title}
                    </strong>
                  </div>
                )}

                {caseInfo.page != null && caseInfo.page > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted font-medium">
                      {t('precedentCitation.pageInDoc', 'Faqja')}:
                    </span>
                    <strong className={statusConfig.color}>
                      {t('lawArticle.page', 'Faqja')} {caseInfo.page}
                    </strong>
                  </div>
                )}

                {/* V23.1: Match type në shqip */}
                {caseInfo.source_info?.match_type && (
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted font-medium">
                      {t('precedentCitation.matchType', 'Lloj përputhje')}:
                    </span>
                    <strong className="text-text-primary">
                      {matchTypeLabel}
                    </strong>
                  </div>
                )}

                {/* V23.1: Confidence level në shqip */}
                {caseInfo.source_info?.confidence?.level && (
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted font-medium">
                      {t('precedentCitation.confidenceLevel', 'Besueshmëri')}:
                    </span>
                    <strong className={statusConfig.color}>
                      {confidenceLevelLabel}
                      {typeof caseInfo.source_info.confidence.score === 'number' &&
                        caseInfo.source_info.confidence.score > 0 && (
                          <span className="ml-1 text-[10px] font-mono opacity-70">
                            ({Math.round(caseInfo.source_info.confidence.score * 100)}%)
                          </span>
                        )}
                    </strong>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span className="text-text-muted font-medium">
                    {t('precedentCitation.status', 'Statusi')}:
                  </span>
                  <strong className={statusConfig.color}>
                    {caseInfo.found
                      ? t('precedentCitation.found', 'Gjetur në arkivë')
                      : t('precedentCitation.notFound', 'Nuk u gjet')}
                  </strong>
                </div>
              </div>
            )}

          <div
            className={`text-[11px] leading-relaxed border-t border-main/50 pt-1.5 mt-1.5 ${
              status === 'idle'
                ? 'text-text-muted'
                : status === 'loading'
                  ? 'text-primary-start flex items-center gap-1.5'
                  : status === 'reference_only'
                    ? 'text-warning-start'
                    : status === 'error'
                      ? 'text-danger-start'
                      : status === 'unverified'
                        ? 'text-warning-start'
                        : 'text-text-muted'
            }`}
          >
            {status === 'loading' && <Loader size={11} className="animate-spin" />}
            {statusConfig.hint}
          </div>

          <div className="mt-2 flex items-center justify-between text-[10.5px] text-text-muted border-t border-main pt-1.5">
            <span>
              {t('precedentCitation.clickToOpen', 'Kliko për të hapur aktgjykimin')}
            </span>
            <span className={`font-bold flex items-center gap-0.5 ${statusConfig.color}`}>
              {t('precedentCitation.openPdf', 'Hap PDF')} <ExternalLink size={10} />
            </span>
          </div>

          <div
            className={`absolute border-[7px] border-transparent pointer-events-none ${
              coords.isFlippedBelow
                ? 'bottom-full -mb-[1px] border-b-card'
                : 'top-full -mt-[1px] border-t-card'
            }`}
            style={{ left: `${coords.arrowLeftPx}px` }}
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
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full cursor-pointer focus:outline-none ${buttonStyle}`}
        >
          {buttonIcon}
          <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanLabel}</span>
        </button>

        {createPortal(tooltipContent, document.body)}
      </span>

      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: pdfFilename,
            title: cleanLabel,
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          initialPage={pdfPageNumber ?? undefined}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </>
  );
};

export default PrecedentCitationLink;