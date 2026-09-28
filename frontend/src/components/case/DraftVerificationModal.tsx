// FILE: src/components/case/DraftVerificationModal.tsx
// PHOENIX PROTOCOL - DRAFT VERIFICATION MODAL V4.0
// V4.0: PROFESSIONAL REDESIGN —
//       - Header i thjeshtuar: hequr score-gauge rrethore, hequr pills me ngjyra.
//       - Metadata line: vetëm tekst me ndarës · (Data · Nene · Prec · Rezultati).
//       - Trupi i raportit me serif (Georgia), statuse si linja jo kuti.
//       - Print CSS për eksport PDF.
//       - Modulet e ekstraktuara: report/typography, report/preprocess,
//         report/ReportComponents.
// V3.10: REWRITE REMOVED.
// V3.9: PROGRESS FIX.
// V3.8: COMBINED HEADER.
// V3.7: COLOR UNIFIED.

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2, Loader2, Maximize2, Minimize2,
  Trash2, ZoomIn, ZoomOut, Lock, ShieldCheck,
  RotateCcw, Sparkles, AlertCircle,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {
  caseAnalysisService,
  type VerifyDocType,
  type ScoreBreakdown,
} from '../../services/caseAnalysisService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';

// Modulet e reja të ekstraktuara
import {
  FONT_LEVELS,
  REPORT_FONT,
  getScoreStyle,
  READINESS_STYLES,
  formatShortDate,
} from './report/typography';
import {
  preprocessReport,
  markdownToPlainText,
  markdownToWordHtml,
} from './report/preprocess';
import { buildReportComponents } from './report/ReportComponents';

// ───────────────────────────────────────────────────────────────────────────
// TYPES
// ───────────────────────────────────────────────────────────────────────────

export interface VerifyProgress {
  isGenerating: boolean;
  percent: number;
  label: string;
}

interface DraftVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  documentId: string;
  documentName: string;
  docType: string;
  docTypeLabel: string;
  onProgressChange?: (progress: VerifyProgress) => void;
}

type LoadPhase = 'loading-cache' | 'has-cache' | 'generating' | 'ready' | 'error';

// ───────────────────────────────────────────────────────────────────────────
// COMPONENT
// ───────────────────────────────────────────────────────────────────────────

const DraftVerificationModal: React.FC<DraftVerificationModalProps> = ({
  isOpen, onClose, caseId, documentId, documentName, docType, docTypeLabel, onProgressChange,
}) => {
  const [phase, setPhase] = useState<LoadPhase>('loading-cache');
  const [reportContent, setReportContent] = useState<string>('');
  const [lastBuiltAt, setLastBuiltAt] = useState<string | null>(null);
  const [reportSource, setReportSource] = useState<'fresh' | 'saved' | null>(null);
  const [readiness, setReadiness] = useState<string>('');

  const [score, setScore] = useState<number | null>(null);
  const [scoreBreakdown, setScoreBreakdown] = useState<ScoreBreakdown | null>(null);
  const [statsData, setStatsData] = useState<Record<string, any>>({});

  const [showScoreTooltip, setShowScoreTooltip] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(1);

  const abortRef = useRef<AbortController | null>(null);

  const activeFont = FONT_LEVELS[fontLevelIndex];
  const reportComponents = useMemo(() => buildReportComponents(), []);

  const title = 'Verifiko Draftin';
  const subtitle = useMemo(() => `${docTypeLabel} • ${documentName}`, [docTypeLabel, documentName]);

  const processedContent = useMemo(() => preprocessReport(reportContent), [reportContent]);
  const linkedContent = useMemo(
    () => (processedContent ? autoLinkLegalCitations(processedContent) : ''),
    [processedContent]
  );

  const scoreStyle = score !== null ? getScoreStyle(score) : null;
  const readinessStyle =
    READINESS_STYLES[(readiness || '').toUpperCase()] || READINESS_STYLES.UNKNOWN;

  const emitProgress = useCallback((isGenerating: boolean, percent: number, label: string) => {
    if (onProgressChange) onProgressChange({ isGenerating, percent, label });
  }, [onProgressChange]);

  // ═══════════════════════════════════════════════════════════════════════
  // RUN VERIFICATION (i njëjti si V3.10)
  // ═══════════════════════════════════════════════════════════════════════
  const runVerification = useCallback(async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setPhase('generating');
    setErrorMessage('');
    setReportContent('');
    setReportSource(null);
    setReadiness('');
    setScore(null);
    setScoreBreakdown(null);
    setStatsData({});
    setLastBuiltAt(null);

    emitProgress(true, 0, 'Fillimi i verifikimit...');

    const total = 6;
    let started = 0;
    let completed = 0;

    const calculatePercent = (): number => {
      const startedPct = (started / total) * 70;
      const completedPct = (completed / total) * 30;
      return Math.min(99, Math.round(startedPct + completedPct));
    };

    try {
      for await (const evt of caseAnalysisService.streamDraftVerification(
        caseId, documentId, docType as VerifyDocType,
      )) {
        if (ctrl.signal.aborted) break;

        const evtType = evt.event;

        if (evtType === 'step_started') {
          const label = evt.step_title || evt.step_key || 'Duke përpunuar...';
          emitProgress(true, calculatePercent(), label);
          continue;
        }

        if (evtType === 'section_started') {
          const titleTxt = evt.section_title || evt.section_key || '';
          started++;
          emitProgress(true, calculatePercent(), `Seksioni: ${titleTxt}`);
          continue;
        }

        if (evtType === 'section_completed') {
          completed++;
          emitProgress(true, calculatePercent(), `Përfundoi ${completed}/${total}`);
          continue;
        }

        if (evtType === 'completed' && evt.result) {
          const r = evt.result;
          setReportContent(r.full_report || '');
          setLastBuiltAt(r.built_at || new Date().toISOString());
          setReportSource('fresh');
          setReadiness(r.readiness || '');
          setScore(typeof r.score === 'number' ? r.score : null);
          setScoreBreakdown(r.score_breakdown || null);
          setStatsData(r.stats || {});
          setPhase('ready');
          emitProgress(false, 100, 'Përfundoi');
          continue;
        }

        if (evtType === 'error') {
          throw new Error(evt.message || 'Gabim gjatë verifikimit.');
        }
      }

      setPhase((stillPhase) => {
        if (stillPhase === 'generating') {
          setErrorMessage('Procesi përfundoi pa raport final.');
          emitProgress(false, 0, '');
          return 'error';
        }
        return stillPhase;
      });

    } catch (err: any) {
      if (err?.name === 'AbortError') {
        emitProgress(false, 0, '');
        return;
      }
      console.error('[DraftVerificationModal V4.0] Gabim SSE:', err);
      setErrorMessage(err?.message || 'Gabim gjatë verifikimit.');
      setPhase('error');
      emitProgress(false, 0, '');
    }
  }, [caseId, documentId, docType, emitProgress]);

  // ═══════════════════════════════════════════════════════════════════════
  // LIFECYCLE
  // ═══════════════════════════════════════════════════════════════════════
  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;

    setPhase('loading-cache');
    setReportContent('');
    setLastBuiltAt(null);
    setReportSource(null);
    setReadiness('');
    setScore(null);
    setScoreBreakdown(null);
    setStatsData({});
    setErrorMessage('');

    (async () => {
      try {
        const data = await caseAnalysisService.getDraftVerification(
          caseId, documentId, docType as VerifyDocType,
        );

        if (cancelled) return;

        if (data.has_verification && data.verification?.full_report) {
          setReportContent(data.verification.full_report);
          setLastBuiltAt(data.verification.built_at);
          setReadiness(data.verification.readiness || '');
          setScore(typeof data.verification.score === 'number' ? data.verification.score : null);
          setScoreBreakdown(data.verification.score_breakdown || null);
          setStatsData(data.verification.stats || {});
          setReportSource('saved');
          setPhase('has-cache');
          emitProgress(false, 100, '');
        } else {
          runVerification();
        }
      } catch (err: any) {
        if (cancelled) return;
        console.warn('[DraftVerificationModal V4.0] Leximi i ruajtur dështoi:', err);
        runVerification();
      }
    })();

    return () => {
      cancelled = true;
      abortRef.current?.abort();
      emitProgress(false, 0, '');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, caseId, documentId, docType]);

  useEffect(() => {
    return () => {
      emitProgress(false, 0, '');
    };
  }, [emitProgress]);

  useEffect(() => {
    if (!isOpen) {
      abortRef.current?.abort();
      abortRef.current = null;
      setCopied(false);
      setIsFullscreen(false);
      setShowScoreTooltip(false);
      emitProgress(false, 0, '');
    }
  }, [isOpen, emitProgress]);

  useEffect(() => {
    if (!isOpen) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || phase === 'generating') return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [isOpen, phase]);

  // ═══════════════════════════════════════════════════════════════════════
  // HANDLERS
  // ═══════════════════════════════════════════════════════════════════════
  const handleClearContent = async () => {
    if (!reportContent || isPurging) return;
    const confirmed = window.confirm(
      `A jeni i sigurt që dëshironi të fshini raportin e verifikimit për "${documentName}"?\n\nKy veprim fshin vetëm raportin e këtij dokumenti.`
    );
    if (!confirmed) return;

    setIsPurging(true);
    try {
      await caseAnalysisService.clearDraftVerification(caseId, documentId);
      setReportContent('');
      setLastBuiltAt(null);
      setReportSource(null);
      setReadiness('');
      setScore(null);
      setScoreBreakdown(null);
      setStatsData({});
      setPhase('ready');
    } catch (err) {
      console.error('[DraftVerificationModal V4.0] Fshirja dështoi:', err);
      alert('Fshirja e raportit në server dështoi.');
    } finally {
      setIsPurging(false);
    }
  };

  const handleCopy = async () => {
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
  };

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER GUARDS
  // ═══════════════════════════════════════════════════════════════════════
  if (!isOpen) return null;
  if (phase === 'loading-cache') return null;
  if (phase === 'generating' && !reportContent) return null;

  const hasStats = score !== null || Object.keys(statsData).length > 0;
  const showStatsRow = Boolean(reportContent) && hasStats;

  // Metadata segments (tekst, jo pills)
  const metaSegments: string[] = [];
  if (statsData.articles_total) {
    metaSegments.push(`${statsData.articles_verified || 0}/${statsData.articles_total} nene`);
  }
  if (typeof statsData.precedents_found === 'number') {
    metaSegments.push(`${statsData.precedents_found} precedent${statsData.precedents_found === 1 ? '' : 'ë'}`);
  }
  if (typeof statsData.formal_pct === 'number') {
    metaSegments.push(`${Math.round(statsData.formal_pct)}% formal`);
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[250] p-2 sm:p-4 md:p-6 select-none">
        {/* Print CSS */}
        <style>{`
          @media print {
            .print-hide { display: none !important; }
            .fast-draft-verify,
            .fast-draft-verify * {
              background: #fff !important;
              color: #000 !important;
              box-shadow: none !important;
            }
            .fast-draft-verify {
              padding: 0 !important;
              max-height: none !important;
              overflow: visible !important;
            }
            .fast-draft-verify p,
            .fast-draft-verify li,
            .fast-draft-verify blockquote,
            .fast-draft-verify td {
              font-family: Georgia, serif !important;
              font-size: 11pt !important;
              line-height: 1.5 !important;
            }
            .fast-draft-verify h1,
            .fast-draft-verify h2,
            .fast-draft-verify h3,
            .fast-draft-verify h4 {
              font-family: Georgia, serif !important;
              color: #000 !important;
            }
            .fast-draft-verify hr {
              border-top: 1px solid #999 !important;
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
              HEADER — V4.0 PROFESIONAL (pa cockpit)
          ═══════════════════════════════════════════════════════════════ */}
          <div className="shrink-0 border-b border-main/60 pb-3 print-hide">
            {/* Rreshti 1: Titull + kontrollat */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className="w-8 h-8 bg-primary-start/10 text-primary-start rounded-lg flex items-center justify-center border border-primary-start/20 shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-xs sm:text-sm font-bold text-text-primary tracking-tight truncate">
                    {title}
                  </h3>
                  <p className="text-[10px] sm:text-[11px] text-text-muted truncate mt-0.5">
                    {subtitle}
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
                    title="Fshi raportin">
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

            {/* Rreshti 2: Metadata line — tekst i qetë me · ndarës */}
            {showStatsRow && (
              <div className="mt-2.5 flex items-center flex-wrap gap-x-3 gap-y-1 text-[10px] sm:text-[11px] font-mono text-text-muted tabular-nums">
                <span className="whitespace-nowrap">
                  <span className="opacity-70">{reportSource === 'fresh' ? 'Gjeneruar' : 'Ruajtur'}</span>{' '}
                  {formatShortDate(lastBuiltAt)}
                </span>

                {metaSegments.length > 0 && (
                  <>
                    <span className="opacity-40">·</span>
                    <span className="whitespace-nowrap">{metaSegments.join('  ·  ')}</span>
                  </>
                )}

                {score !== null && scoreStyle && (
                  <span
                    className={`flex items-center gap-1 whitespace-nowrap cursor-help ${scoreStyle.text}`}
                    onMouseEnter={() => setShowScoreTooltip(true)}
                    onMouseLeave={() => setShowScoreTooltip(false)}
                  >
                    <span className="opacity-60">·</span>
                    <span>Rezultati</span>
                    <span className="font-bold">{score}/100</span>
                    <AnimatePresence>
                      {showScoreTooltip && scoreBreakdown && (
                        <motion.span
                          initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
                          transition={{ duration: 0.12 }}
                          className="absolute top-full left-0 mt-2 z-30 w-[220px] p-3 bg-card border border-main rounded-md shadow-2xl pointer-events-none"
                        >
                          <span className="block text-[9px] font-sans font-bold uppercase tracking-widest text-text-muted mb-2">
                            Struktura e pikëve
                          </span>
                          <span className="block space-y-2 text-[10px] font-sans">
                            <span className="flex items-center justify-between">
                              <span className="text-text-muted">Plotësia formale</span>
                              <span className="font-bold text-text-primary tabular-nums">{Math.round(scoreBreakdown.formal)}%</span>
                            </span>
                            <span className="flex items-center justify-between">
                              <span className="text-text-muted">Cilësia ligjore</span>
                              <span className="font-bold text-text-primary tabular-nums">{Math.round(scoreBreakdown.legal)}%</span>
                            </span>
                            <span className="flex items-center justify-between">
                              <span className="text-text-muted">Gatishmëria</span>
                              <span className="font-bold text-text-primary tabular-nums">{scoreBreakdown.readiness}%</span>
                            </span>
                          </span>
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </span>
                )}

                {readinessStyle && reportContent && (
                  <span className="ml-auto flex items-center gap-1.5 whitespace-nowrap">
                    <span className="text-text-muted opacity-70">Gatishmëria</span>
                    <span className={`font-sans font-bold uppercase tracking-wide ${readinessStyle.color}`}>
                      {readinessStyle.label}
                    </span>
                  </span>
                )}

                <button type="button" onClick={runVerification} disabled={isPurging}
                  className={`h-6 px-2 rounded-md border border-main/60 hover:border-primary-start/50 hover:text-primary-start text-text-muted font-sans font-medium text-[10px] transition-colors flex items-center gap-1 disabled:opacity-50 cursor-pointer shrink-0 ${readinessStyle && reportContent ? '' : 'ml-auto'}`}
                  title="Rigjenero">
                  <RotateCcw size={10} />
                  <span className="hidden sm:inline">Rigjenero</span>
                </button>
              </div>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════════════
              BODY
          ═══════════════════════════════════════════════════════════════ */}
          <div className="flex-1 overflow-y-auto custom-finance-scroll p-3 sm:p-6 my-2 bg-surface/20 rounded-xl sm:rounded-2xl border border-main/60 text-text-primary select-text relative flex flex-col">
            <style>{`
              .fast-draft-verify p,
              .fast-draft-verify li,
              .fast-draft-verify blockquote {
                font-family: ${REPORT_FONT.serif} !important;
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .fast-draft-verify h1,
              .fast-draft-verify h2,
              .fast-draft-verify h3,
              .fast-draft-verify h4 {
                font-family: ${REPORT_FONT.serif} !important;
              }
            `}</style>

            {errorMessage && (
              <div className="mb-4 p-3 sm:p-4 rounded-lg border border-rose-500/30 bg-rose-500/5 flex items-start gap-3 shrink-0">
                <AlertCircle size={16} className="text-rose-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-xs font-bold text-rose-500 mb-1">Gabim</p>
                  <p className="text-[11px] text-text-secondary">{errorMessage}</p>
                </div>
              </div>
            )}

            {!reportContent && !errorMessage && (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <ShieldCheck size={28} />
                </div>
                <div>
                  <h4 className="text-base font-bold text-text-primary">Nuk ka raport verifikimi</h4>
                  <p className="text-xs text-text-muted max-w-lg mt-1">Klikoni "Verifiko Tani" për të gjeneruar një raport të ri.</p>
                </div>
                <button type="button" onClick={runVerification}
                  className="mt-2 h-10 px-5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer shadow-md hover-lift">
                  <Sparkles size={14} />
                  <span>Verifiko Tani</span>
                </button>
              </div>
            )}

            {reportContent && (
              <div className="fast-draft-verify markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={reportComponents as any}>
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
                <span className="hidden lg:inline">Raporti i verifikimit është ruajtur veçmas</span>
                <span className="lg:hidden">I ruajtur</span>
              </div>
            )}

            <div className="flex flex-row items-center gap-1.5 sm:gap-2 ml-auto w-full sm:w-auto justify-end">
              <button type="button" onClick={handleCopy} disabled={!reportContent}
                className="h-8 sm:h-9 px-2.5 sm:px-4 rounded-lg sm:rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] uppercase tracking-wider shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shrink-0">
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

export default DraftVerificationModal;