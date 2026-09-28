// FILE: frontend/src/components/case/CaseDossierAuditModal.tsx
// PHOENIX PROTOCOL - CASE DOSSIER AUDIT MODAL V7.0
// V7.0: PROFESSIONAL REDESIGN — i njëjti stil si DraftVerificationModal V4.1:
//       - Header i thjeshtuar (pa cockpit, pa 4-box stats).
//       - Metadata line me · ndarës.
//       - Trupi me serif (Georgia) + status si linja.
//       - Ripërdorim i moduleve report/typography, report/preprocess,
//         report/ReportComponents (parameterized me h1Label="Raport Auditimi").
//       - Print CSS për eksport PDF.
// V6.4: TIMEZONE FIX — formatAuditDate (Europe/Belgrade).
// V6.3: COLOR UNIFIED.
// V6.2.1: HEQUR "Në Fund" button.
// V6.2: STATS PANEL.
// V6.1.5: LAW CITATION LINK.

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2, Loader2, Maximize2, Minimize2,
  Trash2, ZoomIn, ZoomOut, Lock, Scale, Folder,
  ShieldCheck, RotateCcw, Calendar, Sparkles,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';

// Modulet e përbashkëta të raportit
import {
  FONT_LEVELS,
  REPORT_FONT,
  READINESS_STYLES,
  STATUS_MARK,
} from './report/typography';
import {
  preprocessReport,
  markdownToPlainText,
  markdownToWordHtml,
} from './report/preprocess';
import { buildReportComponents } from './report/ReportComponents';

// ───────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ───────────────────────────────────────────────────────────────────────────

const ALBANIAN_MONTHS = [
  'Janar', 'Shkurt', 'Mars', 'Prill', 'Maj', 'Qershor',
  'Korrik', 'Gusht', 'Shtator', 'Tetor', 'Nëntor', 'Dhjetor',
];

// V6.4: Timezone-aware formatim (Europe/Belgrade)
const formatAuditDate = (isoDate: string | Date | undefined | null): string => {
  if (!isoDate) return '';
  try {
    let dateStr = typeof isoDate === 'string' ? isoDate : isoDate.toISOString();
    if (!/[Zz]$/.test(dateStr) && !/[+-]\d{2}:?\d{2}$/.test(dateStr)) {
      dateStr += 'Z';
    }
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';

    const formatter = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Europe/Belgrade',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    const parts = formatter.formatToParts(d);
    const get = (t: string) => parts.find(p => p.type === t)?.value || '';
    const day = get('day');
    const monthNum = parseInt(get('month'), 10);
    const year = get('year');
    const hour = get('hour');
    const minute = get('minute');
    const month = ALBANIAN_MONTHS[monthNum - 1] || '';

    return `${day} ${month} ${year}, ${hour}:${minute}`;
  } catch {
    return '';
  }
};

// ───────────────────────────────────────────────────────────────────────────
// STATS DERIVATION
// ───────────────────────────────────────────────────────────────────────────

interface DerivedStats {
  countOK: number;
  countX: number;
  countWarn: number;
  countSug: number;
  readiness: string;
}

const deriveStats = (rawMarkdown: string): DerivedStats => {
  if (!rawMarkdown) {
    return { countOK: 0, countX: 0, countWarn: 0, countSug: 0, readiness: 'I PANJOHUR' };
  }

  // Numëro marker-at tipografikë pas preprocess
  const processed = preprocessReport(rawMarkdown);
  const countOK = (processed.match(new RegExp(STATUS_MARK.ok, 'g')) || []).length;
  const countX = (processed.match(new RegExp(STATUS_MARK.fail, 'g')) || []).length;
  const countWarn = (processed.match(new RegExp(STATUS_MARK.warn, 'g')) || []).length;
  const countSug = (processed.match(new RegExp(STATUS_MARK.hint, 'g')) || []).length;

  let readiness = 'I PANJOHUR';
  if (/GATI|READY/i.test(rawMarkdown)) readiness = 'GATI';
  if (/KËRKON PUNË|NEEDS WORK/i.test(rawMarkdown)) readiness = 'KËRKON PUNË';
  if (/I PËRPLOTË|INCOMPLETE/i.test(rawMarkdown)) readiness = 'I PËRPLOTË';

  return { countOK, countX, countWarn, countSug, readiness };
};

// ───────────────────────────────────────────────────────────────────────────
// TYPES
// ───────────────────────────────────────────────────────────────────────────

interface CaseDossierAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseName?: string;
  clientName?: string;
  documentCount?: number;
  documentIds?: string[];
  documentNames?: string[];
  preGeneratedReport?: string | null;
  preGeneratedSource?: 'fresh' | 'cache' | 'saved';
  onRegenerate?: () => void;
}

// ───────────────────────────────────────────────────────────────────────────
// COMPONENT
// ───────────────────────────────────────────────────────────────────────────

export const CaseDossierAuditModal: React.FC<CaseDossierAuditModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseName = 'Lënda',
  clientName = 'Klienti',
  documentCount = 0,
  documentIds,
  documentNames,
  preGeneratedReport = null,
  preGeneratedSource,
  onRegenerate,
}) => {
  const [reportContent, setReportContent] = useState<string>('');
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const [isLoadingFromServer, setIsLoadingFromServer] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [lastAuditedAt, setLastAuditedAt] = useState<string | null>(null);
  const [reportSource, setReportSource] = useState<'fresh' | 'cache' | 'saved' | null>(null);

  const fetchAbortRef = useRef<boolean>(false);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(1);
  const activeFont = FONT_LEVELS[fontLevelIndex];

  // Report components me label audit
  const reportComponents = useMemo(
    () => buildReportComponents({ h1Label: 'Raport Auditimi' }),
    []
  );

  const isSingleDoc = Boolean(documentIds && documentIds.length > 0);
  const singleDocName = isSingleDoc && documentNames && documentNames.length > 0
    ? documentNames[0]
    : null;

  const effectiveScope = isSingleDoc ? 'document' : 'case';

  const reportTitle = effectiveScope === 'document'
    ? 'Verifikimi i Dokumentit'
    : 'Doktrina e Rastit';

  const headerSubtitle = isSingleDoc
    ? `${singleDocName || 'Dokument i vetëm'} • ${clientName}`
    : `${caseName} • ${clientName} • ${documentCount} shkresa`;

  const derivedStats = useMemo(() => deriveStats(reportContent), [reportContent]);

  const readinessStyle =
    READINESS_STYLES[(derivedStats.readiness || '').toUpperCase()] || READINESS_STYLES.UNKNOWN;

  // ── LOAD ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;

    fetchAbortRef.current = false;

    if (preGeneratedReport) {
      setReportContent(preGeneratedReport);
      setLastAuditedAt(new Date().toISOString());
      setReportSource(preGeneratedSource || 'fresh');
      setIsLoadingFromServer(false);
      setLoadError(null);
      return;
    }

    setIsLoadingFromServer(true);
    setLoadError(null);
    setReportContent('');

    apiService.getCaseDossierAudit(caseId, documentIds)
      .then((data) => {
        if (fetchAbortRef.current) return;
        if (data.has_audit && data.content) {
          setReportContent(data.content);
          setLastAuditedAt(data.audited_at);
          setReportSource('saved');
        }
      })
      .catch((err) => {
        if (fetchAbortRef.current) return;
        console.warn('[CaseDossierAuditModal V7.0] Ngarkimi i raportit të ruajtur dështoi:', err);
        setLoadError('Ngarkimi i raportit të ruajtur dështoi.');
      })
      .finally(() => {
        if (fetchAbortRef.current) return;
        setIsLoadingFromServer(false);
      });

    return () => {
      fetchAbortRef.current = true;
    };
  }, [isOpen, preGeneratedReport, preGeneratedSource, caseId, documentIds]);

  // ── Reset kur mbyllet ───────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) {
      setReportContent('');
      setLastAuditedAt(null);
      setReportSource(null);
      setCopied(false);
      setIsFullscreen(false);
      setIsLoadingFromServer(false);
      setLoadError(null);
    }
  }, [isOpen]);

  // ── ESC ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [isOpen, onClose]);

  // ── CLEAR CONTENT ───────────────────────────────────────────────────────
  const handleClearContent = async () => {
    if (!reportContent || !caseId || isPurging) return;

    const confirmWipe = window.confirm(
      isSingleDoc
        ? `A jeni i sigurt që dëshironi të fshini raportin e dokumentit "${singleDocName || 'i panjohur'}"?\n\nRaportet e dokumenteve të tjera dhe doktrina e rastit NUK preken.`
        : `A jeni i sigurt që dëshironi të fshini raportin e rastit?\n\nKy veprim do të fshijë:\n- Doktrinën e rastit\n- TË GJITHA raportet e dokumenteve\n- Ekstraktimet, cross-references dhe findings`
    );
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await apiService.clearCaseDossierAudit(caseId, documentIds);
      setReportContent('');
      setLastAuditedAt(null);
      setReportSource(null);
    } catch (err) {
      console.error("Fshirja dështoi:", err);
      alert("Fshirja e raportit në server dështoi.");
    } finally {
      setIsPurging(false);
    }
  };

  const handleRegenerate = () => {
    if (onRegenerate) onRegenerate();
  };

  const handleCopy = useCallback(async () => {
    if (!reportContent) return;

    const processed = preprocessReport(reportContent);
    const htmlContent = markdownToWordHtml(processed);
    const plainContent = markdownToPlainText(processed);

    try {
      if (navigator.clipboard && (window as any).ClipboardItem) {
        const item = new (window as any).ClipboardItem({
          'text/html': new Blob([htmlContent], { type: 'text/html' }),
          'text/plain': new Blob([plainContent], { type: 'text/plain' }),
        });
        await navigator.clipboard.write([item]);
      } else {
        await navigator.clipboard.writeText(plainContent);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      await navigator.clipboard.writeText(plainContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [reportContent]);

  if (!isOpen) return null;

  const processedContent = preprocessReport(reportContent);
  const linkedContent = processedContent ? autoLinkLegalCitations(processedContent) : '';

  const hasStats = derivedStats.countOK + derivedStats.countX + derivedStats.countWarn + derivedStats.countSug > 0;
  const showStatsRow = Boolean(reportContent) && hasStats;

  // Ndërto metadata segments
  const metaSegments: string[] = [];
  if (derivedStats.countOK > 0) metaSegments.push(`${derivedStats.countOK} gjetje OK`);
  if (derivedStats.countX > 0)   metaSegments.push(`${derivedStats.countX} gabime`);
  if (derivedStats.countWarn > 0) metaSegments.push(`${derivedStats.countWarn} kujdes`);
  if (derivedStats.countSug > 0) metaSegments.push(`${derivedStats.countSug} sugjerime`);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[250] p-2 sm:p-4 md:p-6 select-none">
        {/* Print CSS */}
        <style>{`
          @media print {
            .print-hide { display: none !important; }
            .fast-case-dossier-audit,
            .fast-case-dossier-audit * {
              background: #fff !important;
              color: #000 !important;
              box-shadow: none !important;
            }
            .fast-case-dossier-audit {
              padding: 0 !important;
              max-height: none !important;
              overflow: visible !important;
            }
            .fast-case-dossier-audit p,
            .fast-case-dossier-audit li,
            .fast-case-dossier-audit blockquote,
            .fast-case-dossier-audit td {
              font-family: Georgia, serif !important;
              font-size: 11pt !important;
              line-height: 1.5 !important;
            }
          }
        `}</style>

        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 10 }}
          className={`glass-panel w-full ${
            isFullscreen
              ? 'h-full max-h-screen rounded-none border-0'
              : 'h-[96vh] sm:h-[92vh] max-w-5xl max-h-[880px] rounded-2xl sm:rounded-3xl border border-main'
          } p-2.5 sm:p-4 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
        >
          {/* ═══════════════════════════════════════════════════════════════
              HEADER — V7.0 PROFESIONAL
          ═══════════════════════════════════════════════════════════════ */}
          <div className="shrink-0 border-b border-main/60 pb-3 print-hide">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className="w-8 h-8 bg-primary-start/10 text-primary-start rounded-lg flex items-center justify-center border border-primary-start/20 shrink-0">
                  {effectiveScope === 'document' ? <ShieldCheck className="w-4 h-4" /> : <Folder className="w-4 h-4" />}
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-xs sm:text-sm font-bold text-text-primary tracking-tight truncate">
                    {reportTitle}
                  </h3>
                  <p className="text-[10px] sm:text-[11px] text-text-muted truncate mt-0.5">
                    {headerSubtitle}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
                <div className="hidden sm:flex items-center bg-surface border border-main/60 rounded-md p-0.5">
                  <button type="button" onClick={() => setFontLevelIndex((p) => Math.max(0, p - 1))} disabled={fontLevelIndex <= 0}
                    className="px-1.5 py-0.5 text-text-muted hover:text-text-primary disabled:opacity-30 rounded hover:bg-hover cursor-pointer" title="Zvogëlo">
                    <ZoomOut size={12} />
                  </button>
                  <span className="px-1 text-[10px] font-mono font-bold text-text-muted min-w-[28px] text-center">{activeFont.label}</span>
                  <button type="button" onClick={() => setFontLevelIndex((p) => Math.min(FONT_LEVELS.length - 1, p + 1))} disabled={fontLevelIndex >= FONT_LEVELS.length - 1}
                    className="px-1.5 py-0.5 text-text-muted hover:text-text-primary disabled:opacity-30 rounded hover:bg-hover cursor-pointer" title="Zmadho">
                    <ZoomIn size={12} />
                  </button>
                </div>

                {reportContent && (
                  <button type="button" onClick={handleClearContent} disabled={isPurging}
                    className="p-1.5 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-md transition-colors cursor-pointer disabled:opacity-40"
                    title={isSingleDoc ? "Fshi raportin e këtij dokumenti" : "Fshi raportin e rastit"}>
                    {isPurging ? <Loader2 size={14} className="animate-spin text-danger-start" /> : <Trash2 size={14} />}
                  </button>
                )}

                <button type="button" onClick={() => setIsFullscreen(!isFullscreen)}
                  className="hidden sm:flex p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-md transition-colors cursor-pointer"
                  title={isFullscreen ? 'Zvogëlo' : 'Zmadho'}>
                  {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>

                <button type="button" onClick={onClose}
                  className="p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-md transition-colors cursor-pointer" title="Mbyll">
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Metadata line */}
            {showStatsRow && (
              <div className="mt-2.5 flex items-center flex-wrap gap-x-3 gap-y-1 text-[10px] sm:text-[11px] font-mono text-text-muted tabular-nums">
                {lastAuditedAt && (
                  <span className="whitespace-nowrap">
                    <span className="opacity-70">{reportSource === 'fresh' ? 'Gjeneruar' : reportSource === 'cache' ? 'Nga cache' : 'Ruajtur'}</span>{' '}
                    {formatAuditDate(lastAuditedAt)}
                  </span>
                )}

                {metaSegments.length > 0 && (
                  <>
                    <span className="opacity-40">·</span>
                    <span className="whitespace-nowrap">{metaSegments.join('  ·  ')}</span>
                  </>
                )}

                {reportContent && derivedStats.readiness && (
                  <span className="ml-auto flex items-center gap-1.5 whitespace-nowrap">
                    <span className="text-text-muted opacity-70">Gatishmëria</span>
                    <span className={`font-sans font-bold uppercase tracking-wide ${readinessStyle.color}`}>
                      {readinessStyle.label}
                    </span>
                  </span>
                )}

                {onRegenerate && (
                  <button type="button" onClick={handleRegenerate} disabled={isPurging}
                    className={`h-6 px-2 rounded-md border border-main/60 hover:border-primary-start/50 hover:text-primary-start text-text-muted font-sans font-medium text-[10px] transition-colors flex items-center gap-1 disabled:opacity-50 cursor-pointer shrink-0 ${reportContent && derivedStats.readiness ? '' : 'ml-auto'}`}
                    title="Rigjenero">
                    <RotateCcw size={10} />
                    <span className="hidden sm:inline">Rigjenero</span>
                  </button>
                )}
              </div>
            )}

            {/* Banner për cache/saved (V7.0: minimal) */}
            {reportContent && (reportSource === 'cache' || reportSource === 'saved') && (
              <div className="mt-2 flex items-center gap-2 text-[10px] sm:text-[11px] text-text-muted">
                <Calendar size={11} className="text-primary-start shrink-0" />
                <span>
                  {reportSource === 'cache'
                    ? 'Ky raport është shfaqur nga memoria e serverit.'
                    : 'Ky raport është ruajtur më parë.'}
                </span>
              </div>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════════════
              BODY
          ═══════════════════════════════════════════════════════════════ */}
          <div className="flex-1 overflow-y-auto custom-finance-scroll p-3 sm:p-6 my-2 bg-surface/20 rounded-xl sm:rounded-2xl border border-main/60 text-text-primary select-text relative flex flex-col">
            <style>{`
              .fast-case-dossier-audit p,
              .fast-case-dossier-audit li,
              .fast-case-dossier-audit blockquote {
                font-family: ${REPORT_FONT.serif} !important;
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .fast-case-dossier-audit h1,
              .fast-case-dossier-audit h2,
              .fast-case-dossier-audit h3,
              .fast-case-dossier-audit h4 {
                font-family: ${REPORT_FONT.serif} !important;
              }
            `}</style>

            {isLoadingFromServer ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <Loader2 className="w-10 h-10 animate-spin text-primary-start" />
                <p className="text-sm text-text-muted">Duke lexuar raportin e ruajtur...</p>
              </div>
            ) : !reportContent ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  {effectiveScope === 'document' ? <ShieldCheck size={28} /> : <Scale size={28} />}
                </div>
                <div>
                  <h4 className="text-base font-bold text-text-primary">{reportTitle}</h4>
                  <p className="text-xs text-text-muted max-w-lg mt-1">
                    {loadError
                      ? loadError
                      : isSingleDoc
                        ? `Nuk ka raport të ruajtur për dokumentin "${singleDocName || ''}". Klikoni "Analizo" për të gjeneruar një të re.`
                        : 'Nuk ka raport të ruajtur për këtë fashikull. Klikoni "Analizo" për të gjeneruar një të re.'}
                  </p>
                </div>
                {onRegenerate && (
                  <button
                    type="button"
                    onClick={handleRegenerate}
                    className="mt-2 h-10 px-5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer shadow-md hover-lift"
                  >
                    <Sparkles size={14} />
                    <span>Analizo {effectiveScope === 'document' ? 'Dokumentin' : 'Rastin'}</span>
                  </button>
                )}
              </div>
            ) : (
              <div className="fast-case-dossier-audit markdown-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={reportComponents as any}
                >
                  {linkedContent}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════════════
              FOOTER
          ═══════════════════════════════════════════════════════════════ */}
          <div className="flex flex-row items-center justify-between pt-2 border-t border-main/60 gap-1.5 sm:gap-3 shrink-0 print-hide">
            {reportContent && (
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface border border-main/60 text-text-muted text-[10px] sm:text-xs font-medium shrink-0">
                <Lock size={11} className="text-text-muted" />
                <span className="hidden lg:inline">
                  {isSingleDoc
                    ? 'Raporti i dokumentit është ruajtur veçmas'
                    : 'Raporti i rastit është ruajtur'}
                </span>
                <span className="lg:hidden">I ruajtur</span>
              </div>
            )}

            <div className="flex flex-row items-center gap-1.5 sm:gap-2 ml-auto w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={handleCopy}
                disabled={!reportContent}
                className="h-8 sm:h-9 px-2.5 sm:px-4 rounded-lg sm:rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] uppercase tracking-wider shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shrink-0"
              >
                {copied ? <CheckCircle2 size={13} /> : <Copy size={13} />}
                <span className="hidden lg:inline">{copied ? 'U Kopjua!' : 'Kopjo për Dokument'}</span>
                <span className="hidden sm:inline lg:hidden">{copied ? 'U Kopjua!' : 'Kopjo'}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CaseDossierAuditModal;