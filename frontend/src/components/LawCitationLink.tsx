// FILE: src/components/LawCitationLink.tsx
// PHOENIX PROTOCOL - IN-PLACE LAW ARTICLE VIEWER V23.0
//
// V23.0: STATUS I RI 'external' për traktate ndërkombëtare.
//   - Kur backend kthen is_external: true → badge blu 🌐 "Traktat ndërkombëtar"
//   - Tooltip shfaq emrin kanonik + referencë ndaj Nenit 22 të Kushtetutës
//   - Dallimi: verified (gjelbër) ≠ external (blu) ≠ unverified (verdhë)
//
// V22.2: FIX terma teknike → shqip.
// V22.1: FIX TS6133.
// V22.0: ZERO FAKE VERIFICATION.

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Scale, ShieldCheck, X, Loader2,
  AlertTriangle, HelpCircle, Loader, Globe,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService, API_V1_URL } from '../services/api';
import FileViewerModal from './FileViewerModal';
import { getMatchTypeLabel } from '../utils/lawLabels';
import type { SourceInfo } from './law/lawArticleTypes';

export interface LawCitationLinkProps {
  lawTitle: string;
  articleNum: string;
  fullMatch: string;
  targetUrl?: string;
  className?: string;
}

type CitationStatus =
  | 'idle'
  | 'loading'
  | 'verified'
  | 'external'         // V23.0: traktat ndërkombëtar (KEDNJ/OKB/Hagë)
  | 'unverified'
  | 'repealed'
  | 'error';

interface ExternalInfo {
  id: string;
  canonical_name: string;
  short_name: string;
  category: string;
  constitutional_basis: string;
  note: string;
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
  const [externalInfo, setExternalInfo] = useState<ExternalInfo | null>(null);
  const [status, setStatus] = useState<CitationStatus>('idle');
  const [showTooltip, setShowTooltip] = useState(false);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfPageNumber, setPdfPageNumber] = useState<number | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>('Ligji_Zyrtar.pdf');

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

  const resolvedParams = useMemo(() => {
    let lTitle = lawTitle || '';
    let aNum = articleNum || '';

    if (targetUrl) {
      try {
        const url = new URL(targetUrl, window.location.origin);
        const qLaw = url.searchParams.get('lawTitle');
        const qArt = url.searchParams.get('articleNumber');
        if (qLaw) lTitle = qLaw;
        if (qArt) aNum = qArt;
      } catch {
        // URL e pavlefshme
      }
    }

    if (!aNum) {
      const matchNum = (fullMatch || lawTitle).match(/\d+/);
      if (matchNum) aNum = matchNum[0];
    }

    return {
      lawTitle: lTitle.trim() || 'Ligji',
      articleNum: aNum.trim() || '1',
    };
  }, [lawTitle, articleNum, targetUrl, fullMatch]);

  const cleanDisplayLabel = (
    fullMatch || `${resolvedParams.lawTitle} - Neni ${resolvedParams.articleNum}`
  )
    .replace(/^\[+|\]+$/g, '')
    .trim();

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
          (viewportWidth - Math.min(viewportWidth - 24, 380)) / 2,
        );
        arrowPx = Math.max(
          20,
          Math.min(
            rect.left + rect.width / 2 - tooltipBoxLeft,
            Math.min(viewportWidth - 24, 380) - 20,
          ),
        );
      } else {
        const tooltipWidth = 380;
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

      const estimatedHeight = 260;
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

  const fetchSourceInfo = useCallback(async () => {
    if (
      status === 'verified' ||
      status === 'repealed' ||
      status === 'unverified' ||
      status === 'external'
    ) {
      return;
    }

    sourceAbortRef.current?.abort();
    const controller = new AbortController();
    sourceAbortRef.current = controller;

    setStatus('loading');

    try {
      const cleanArt =
        resolvedParams.articleNum.replace(/\D+/g, '') || resolvedParams.articleNum;
      const response = await apiService.getLawArticle(resolvedParams.lawTitle, cleanArt);

      if (controller.signal.aborted) return;

      // V23.0: Kontrollo external PARA repealed
      if (response && response.is_external === true) {
        setExternalInfo({
          id: response.external_source_id || '',
          canonical_name: response.law_title || '',
          short_name: response.external_short_name || '',
          category: response.external_category || 'international_treaty',
          constitutional_basis: response.source || '',
          note: response.text || '',
        });
        if (response.source_info) setSourceInfo(response.source_info);
        setStatus('external');
        return;
      }

      if (response && response.is_repealed === true) {
        setSourceInfo(response.source_info ?? null);
        setStatus('repealed');
        return;
      }

      if (response && response.source_info) {
        const level = response.source_info.confidence?.level;
        setSourceInfo(response.source_info);

        if (level === 'HIGH' || level === 'MEDIUM') {
          setStatus('verified');
        } else {
          setStatus('unverified');
        }
        return;
      }

      setStatus('unverified');
    } catch {
      if (!controller.signal.aborted) {
        setStatus('error');
      }
    }
  }, [status, resolvedParams.lawTitle, resolvedParams.articleNum]);

  const handleOpen = useCallback(() => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
      fetchSourceInfo();
    }, 120);
  }, [updateCoordinates, fetchSourceInfo]);

  const handleClose = useCallback(() => {
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = null;
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

    // V23.0: Traktatet eksterne NUK kanë PDF në serverin e Kosovës
    if (status === 'external') {
      // Hap referencën në një tab të re
      if (externalInfo?.constitutional_basis) {
        // Nuk ka URL — trego alert me info
        alert(
          `🌐 ${externalInfo.canonical_name}\n\n` +
          `${externalInfo.note}\n\n` +
          `Referenca kushtetuese: ${externalInfo.constitutional_basis}`
        );
      }
      return;
    }

    setIsLoadingPdf(true);

    pdfAbortRef.current?.abort();
    const controller = new AbortController();
    pdfAbortRef.current = controller;

    try {
      const cleanArt =
        resolvedParams.articleNum.replace(/\D+/g, '') || resolvedParams.articleNum;
      const res = await apiService.getLawArticle(resolvedParams.lawTitle, cleanArt);

      if (controller.signal.aborted) return;

      const rawPage = res.page ?? res.page_number ?? null;
      const pageNum =
        typeof rawPage === 'number' && rawPage > 0
          ? rawPage
          : rawPage !== null
            ? parseInt(String(rawPage), 10) || null
            : null;

      const targetFile = res.source || `${resolvedParams.lawTitle}.pdf`;

      setPdfPageNumber(pageNum);
      setPdfFilename(targetFile);

      const fullUrl = `${API_V1_URL}/laws/pdf/${encodeURIComponent(targetFile)}`;
      setPdfUrl(fullUrl);
      setShowPdfModal(true);
    } catch {
      if (targetUrl) {
        window.open(targetUrl, '_blank');
      }
    } finally {
      if (!controller.signal.aborted) setIsLoadingPdf(false);
    }
  };

  const statusConfig = useMemo(() => {
    switch (status) {
      case 'idle':
        return {
          icon: <HelpCircle size={15} />,
          label: t('lawCitation.statusIdle', 'Kliko për verifikim'),
          badge: t('lawCitation.statusIdleShort', 'I PAVERIFIKUAR'),
          color: 'text-text-muted',
          bgColor: 'bg-surface',
          borderColor: 'border-main',
          hint: t(
            'lawCitation.idleHint',
            'Kliko butonin për të verifikuar në bazën ligjore. Asnjë pretendim verifikimi bëhet pa të dhëna reale.',
          ),
        };
      case 'loading':
        return {
          icon: <Loader size={15} className="animate-spin" />,
          label: t('lawCitation.statusLoading', 'Duke verifikuar...'),
          badge: t('lawCitation.statusLoadingShort', 'DUKE NGARKUAR'),
          color: 'text-primary-start',
          bgColor: 'bg-primary-start/10',
          borderColor: 'border-primary-start/30',
          hint: t('lawCitation.loadingHint', 'Po kontrollojmë bazën ligjore...'),
        };
      case 'verified':
        return {
          icon: <ShieldCheck size={15} />,
          label: t('lawCitation.statusVerified', 'Verifikuar në bazën ligjore'),
          badge: t('lawCitation.statusVerifiedShort', 'VERIFIKUAR'),
          color: 'text-success-start',
          bgColor: 'bg-success-start/10',
          borderColor: 'border-success-start/30',
          hint: null,
        };
      case 'external':
        // V23.0: Traktat ndërkombëtar
        return {
          icon: <Globe size={15} />,
          label: t(
            'lawCitation.statusExternal',
            'Traktat ndërkombëtar (Neni 22 i Kushtetutës)',
          ),
          badge: t('lawCitation.statusExternalShort', 'NDËRKOMBËTAR'),
          color: 'text-info-start',
          bgColor: 'bg-info-start/10',
          borderColor: 'border-info-start/30',
          hint: t(
            'lawCitation.externalHint',
            'Ky burim zbatohet drejtpërdrejt në Kosovë sipas Nenit 22 të Kushtetutës. Nuk verifikohet në bazën e ligjeve kosovare sepse është traktat ndërkombëtar.',
          ),
        };
      case 'unverified':
        return {
          icon: <AlertTriangle size={15} />,
          label: t('lawCitation.statusUnverified', 'Nuk u verifikua — konsulto manualisht'),
          badge: t('lawCitation.statusUnverifiedShort', 'I PAVERIFIKUAR'),
          color: 'text-warning-start',
          bgColor: 'bg-warning-start/10',
          borderColor: 'border-warning-start/30',
          hint: t(
            'lawCitation.unverifiedHint',
            'Nuk mund të konfirmohej në bazën ligjore. Konsulto manualisht.',
          ),
        };
      case 'repealed':
        return {
          icon: <AlertTriangle size={15} />,
          label: t('lawCitation.statusRepealed', 'Ky ligj është shfuqizuar'),
          badge: t('lawCitation.statusRepealedShort', 'SHFUQIZUAR'),
          color: 'text-warning-start',
          bgColor: 'bg-warning-start/10',
          borderColor: 'border-warning-start/30',
          hint: t(
            'lawCitation.repealedHint',
            'Ky ligj është shfuqizuar. Konsulto ligjin zëvendësues.',
          ),
        };
      case 'error':
        return {
          icon: <AlertTriangle size={15} />,
          label: t('lawCitation.statusError', 'Verifikimi dështoi'),
          badge: t('lawCitation.statusErrorShort', 'GABIM'),
          color: 'text-danger-start',
          bgColor: 'bg-danger-start/10',
          borderColor: 'border-danger-start/30',
          hint: t(
            'lawCitation.errorHint',
            'Nuk mund të verifikohej. Kontrollo lidhjen ose provo përsëri.',
          ),
        };
    }
  }, [status, t]);

  const matchTypeLabel = useMemo(
    () => getMatchTypeLabel(sourceInfo?.title_match_type, t),
    [sourceInfo?.title_match_type, t],
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
              ? 'left-3 right-3 mx-auto max-w-[380px] w-[calc(100vw-24px)]'
              : 'w-[380px]'
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
          <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-main">
            <div
              className={`flex items-center gap-1.5 font-black text-xs uppercase tracking-wider ${statusConfig.color}`}
            >
              {statusConfig.icon}
              <span>{statusConfig.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-md font-bold ${statusConfig.bgColor} ${statusConfig.color} border ${statusConfig.borderColor}`}
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

          {/* V23.0: Titulli */}
          <div className="text-xs sm:text-sm font-black text-text-primary mb-1.5 leading-snug">
            {status === 'external' && externalInfo
              ? externalInfo.canonical_name
              : sourceInfo?.matched_law
                ? sourceInfo.matched_law
                : resolvedParams.lawTitle}
            {' • '}
            {t('lawArticle.article', 'Neni')}{' '}
            {sourceInfo?.matched_article || resolvedParams.articleNum}
          </div>

          {/* V23.0: External info block */}
          {status === 'external' && externalInfo && (
            <div className="space-y-1.5 text-[11px] font-sans bg-info-start/5 p-2.5 rounded-xl border border-info-start/20 text-text-secondary mb-1.5">
              <div className="flex items-center justify-between">
                <span className="text-text-muted">
                  {t('lawCitation.category', 'Kategoria')}:
                </span>
                <strong className="text-info-start">
                  🌐 {t('lawCitation.internationalTreaty', 'Traktat ndërkombëtar')}
                </strong>
              </div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-text-muted shrink-0">
                  {t('lawCitation.constitutionalBasis', 'Baza kushtetuese')}:
                </span>
                <strong className="text-right text-text-primary">
                  {externalInfo.constitutional_basis}
                </strong>
              </div>
              {externalInfo.note && (
                <div className="text-[10px] text-text-muted italic leading-relaxed pt-1 border-t border-info-start/20">
                  {externalInfo.note}
                </div>
              )}
            </div>
          )}

          {/* Verified / Unverified / Repealed — info block i vjetër */}
          {(status === 'verified' || status === 'repealed' || status === 'unverified') && (
            <div className="space-y-1 text-[11px] font-sans bg-surface/90 p-2 rounded-xl border border-main text-text-secondary mb-1.5">
              {sourceInfo?.source_file ? (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">
                    {t('lawCitation.sourceFile', 'Burimi')}:
                  </span>
                  <strong
                    className="truncate max-w-[180px] font-mono text-[10px]"
                    title={sourceInfo.source_file}
                  >
                    {sourceInfo.source_file}
                  </strong>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">
                    {t('lawCitation.sourceFile', 'Burimi')}:
                  </span>
                  <strong className="text-text-muted italic">
                    {t('lawCitation.sourceUnknown', 'i panjohur')}
                  </strong>
                </div>
              )}

              {sourceInfo?.page != null && sourceInfo.page > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">
                    {t('lawCitation.pageInDoc', 'Faqja')}:
                  </span>
                  <strong className={statusConfig.color}>
                    {t('lawArticle.page', 'Faqja')} {sourceInfo.page}
                  </strong>
                </div>
              )}

              {sourceInfo?.title_match_type && (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">
                    {t('lawCitation.matchType', 'Lloj përputhje')}:
                  </span>
                  <strong className="text-text-primary">{matchTypeLabel}</strong>
                </div>
              )}
            </div>
          )}

          {/* Hint (i përbashkët) */}
          {statusConfig.hint && (
            <div
              className={`text-[11px] leading-relaxed border-t border-main/50 pt-1.5 mt-1.5 ${
                status === 'idle'
                  ? 'text-text-muted'
                  : status === 'loading'
                    ? 'text-primary-start flex items-center gap-1.5'
                    : status === 'external'
                      ? 'text-info-start'
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
          )}

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

  const buttonStyle = useMemo(() => {
    switch (status) {
      case 'verified':
        return 'bg-success-start/10 hover:bg-success-start/20 border-success-start/25 text-success-start';
      case 'external':
        // V23.0: Bluja për traktate ndërkombëtare
        return 'bg-info-start/10 hover:bg-info-start/20 border-info-start/30 text-info-start';
      case 'repealed':
      case 'unverified':
        return 'bg-warning-start/10 hover:bg-warning-start/20 border-warning-start/25 text-warning-start';
      case 'error':
        return 'bg-danger-start/10 hover:bg-danger-start/20 border-danger-start/25 text-danger-start';
      case 'loading':
        return 'bg-primary-start/10 hover:bg-primary-start/20 border-primary-start/25 text-primary-start';
      default:
        return 'bg-primary-start/10 hover:bg-primary-start/20 border-primary-start/25 text-primary-start';
    }
  }, [status]);

  const buttonIcon = useMemo(() => {
    if (isLoadingPdf) {
      return <Loader2 size={13} className="animate-spin shrink-0" />;
    }
    switch (status) {
      case 'verified':
        return <ShieldCheck size={13} className="shrink-0 opacity-80" />;
      case 'external':
        return <Globe size={13} className="shrink-0 opacity-90" />;
      case 'repealed':
      case 'unverified':
        return <AlertTriangle size={13} className="shrink-0 opacity-80" />;
      case 'error':
        return <AlertTriangle size={13} className="shrink-0 opacity-80" />;
      case 'loading':
        return <Loader size={13} className="animate-spin shrink-0 opacity-80" />;
      default:
        return <Scale size={13} className="shrink-0 opacity-80" />;
    }
  }, [status, isLoadingPdf]);

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
          <span className="truncate max-w-[260px] sm:max-w-[340px]">
            {cleanDisplayLabel}
          </span>
        </button>

        {createPortal(tooltipContent, document.body)}
      </span>

      {/* PDF modal vetëm për statute (jo external) */}
      {showPdfModal && pdfUrl && status !== 'external' && (
        <FileViewerModal
          documentData={{
            file_name: pdfFilename,
            article_number: resolvedParams.articleNum,
            title: resolvedParams.lawTitle,
            page_number: pdfPageNumber,
            page: pdfPageNumber,
            mime_type: 'application/pdf',
          }}
          initialPage={pdfPageNumber ?? undefined}
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