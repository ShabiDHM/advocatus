// FILE: src/components/case/DocumentRewriteModal.tsx
// PHOENIX PROTOCOL - DOCUMENT REWRITE MODAL V1.5
// V1.5: FULLSCREEN WIDTH — Kur isFullscreen, dokumenti zgjerohet sipas
//       dritares (maxWidth: min(1400px, 100%)) në vend të 794px (A4).
//       Modal normal mbetet me pamje A4 klasike.
// V1.4: ZOOM CONTROLS — butona [−] 100% [+] në header + keyboard shortcuts
//       (Ctrl +/-/0). Aplikohet me CSS zoom në wrapper A4, me scroll natyral.
//       Body wrapper kalon në `overflow-auto` për të lejuar horizontal scroll.
// V1.3.1: FIX CONTRAST — A4 me CSS scoped që detyron ngjyrën e errët
//         (#0f172a) për të gjithë elementët, duke anashkaluar dark mode
//         dhe prose classes nga parent-i.
// V1.3: MULTI-DEVICE LOAD.
// V1.2: CLICKABLE CITATIONS.

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2, Loader2, Maximize2, Minimize2,
  RefreshCw, AlertCircle, Download, Printer,
  Sparkles, ShieldCheck, ShieldAlert, AlertTriangle,
  ZoomIn, ZoomOut,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {
  caseAnalysisService,
  type VerifyDocType,
  type DraftRewriteResult,
} from '../../services/caseAnalysisService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { LawCitationLink } from '../LawCitationLink';
import { PrecedentCitationLink } from '../PrecedentCitationLink';

// ───────────────────────────────────────────────────────────────────────────
// TYPES
// ───────────────────────────────────────────────────────────────────────────

interface DocumentRewriteModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  documentId: string;
  documentName: string;
  docType: string;
  docTypeLabel: string;
}

type LoadPhase = 'idle' | 'loading-saved' | 'generating' | 'ready' | 'error';

interface ValidationIssue {
  type: string;
  type_label: string;
  value: string;
  context: string;
  severity: 'high' | 'medium' | 'low';
}

// ───────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ───────────────────────────────────────────────────────────────────────────

const ZOOM_MIN = 50;
const ZOOM_MAX = 200;
const ZOOM_STEP = 10;
const ZOOM_DEFAULT = 100;

// ───────────────────────────────────────────────────────────────────────────
// STYLES
// ───────────────────────────────────────────────────────────────────────────

const A4_STYLE = {
  width: '100%',
  maxWidth: '794px',
  minHeight: '1123px',
  padding: '80px 60px',
  background: '#ffffff',
  color: '#0f172a',
  fontFamily: '"Times New Roman", Times, Georgia, serif',
  fontSize: '14px',
  lineHeight: '1.75',
} as const;

const VALIDATION_STYLES = {
  clean: {
    bg: 'bg-emerald-500/5',
    border: 'border-emerald-500/30',
    text: 'text-emerald-500',
    icon: ShieldCheck,
    label: 'Zero Halucinacione',
    message: 'Dokumenti i rishkruar përmban vetëm elementet e origjinalit.',
  },
  warning: {
    bg: 'bg-amber-500/5',
    border: 'border-amber-500/30',
    text: 'text-amber-500',
    icon: AlertTriangle,
    label: 'Kërkohet Verifikim Manual',
    message: 'U identifikuan elemente të reja me rrezik të mesëm. Kontrolloji para dorëzimit.',
  },
  danger: {
    bg: 'bg-rose-500/5',
    border: 'border-rose-500/30',
    text: 'text-rose-500',
    icon: ShieldAlert,
    label: 'Halucinacione të Mundshme',
    message: 'U identifikuan elemente KRITIKE që nuk ekzistojnë në origjinal. NUK DORËZO para verifikimit!',
  },
} as const;

// ───────────────────────────────────────────────────────────────────────────
// COMPONENT
// ───────────────────────────────────────────────────────────────────────────

const DocumentRewriteModal: React.FC<DocumentRewriteModalProps> = ({
  isOpen,
  onClose,
  caseId,
  documentId,
  documentName,
  docType,
  docTypeLabel,
}) => {
  const [phase, setPhase] = useState<LoadPhase>('idle');
  const [result, setResult] = useState<DraftRewriteResult | null>(null);
  const [progressLabel, setProgressLabel] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showValidationDetails, setShowValidationDetails] = useState<boolean>(false);
  const [zoomLevel, setZoomLevel] = useState<number>(ZOOM_DEFAULT);

  const abortRef = useRef<AbortController | null>(null);
  const hasInitializedRef = useRef<boolean>(false);

  const content = result?.content || '';
  const validation = result?.validation;

  const linkedContent = useMemo(
    () => (content ? autoLinkLegalCitations(content) : ''),
    [content]
  );

  const a4Components = useMemo(() => buildA4Components(), []);

  // ── ZOOM HANDLERS ──
  const handleZoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(ZOOM_MAX, prev + ZOOM_STEP));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(ZOOM_MIN, prev - ZOOM_STEP));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoomLevel(ZOOM_DEFAULT);
  }, []);

  // ── GENERATE / REGENERATE ──
  const runRewrite = useCallback(async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setPhase('generating');
    setErrorMessage('');
    setResult(null);
    setProgressLabel('Duke lexuar draftin dhe rekomandimet...');
    setShowValidationDetails(false);

    try {
      for await (const evt of caseAnalysisService.streamDraftRewrite(
        caseId,
        documentId,
        docType as VerifyDocType,
      )) {
        if (ctrl.signal.aborted) break;

        const evtType = evt.event;

        if (evtType === 'step_started') {
          setProgressLabel(evt.step_title || evt.step_key || 'Duke përpunuar...');
          continue;
        }

        if (evtType === 'chunk_completed') {
          const idx = evt.chunk_index || 0;
          const total = evt.total_chunks || 0;
          setProgressLabel(`Përfundoi pjesa ${idx}/${total}`);
          continue;
        }

        if (evtType === 'validation_completed') {
          setProgressLabel('Duke verifikuar për halucinacione...');
          continue;
        }

        if (evtType === 'completed' && evt.result) {
          const r = evt.result;

          if (r.status === 'error') {
            setErrorMessage(r.error_message || 'Rishkrimi dështoi.');
            setPhase('error');
            setProgressLabel('');
            continue;
          }

          setResult(r as DraftRewriteResult);
          setPhase('ready');
          setProgressLabel('Përfundoi');
          continue;
        }

        if (evtType === 'error') {
          throw new Error(evt.message || 'Gabim gjatë rishkrimit.');
        }
      }

      setPhase((stillPhase) => {
        if (stillPhase === 'generating') {
          setErrorMessage('Procesi përfundoi pa dokument final.');
          setProgressLabel('');
          return 'error';
        }
        return stillPhase;
      });

    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      console.error('[DocumentRewriteModal V1.5] SSE error:', err);
      setErrorMessage(err?.message || 'Gabim gjatë rishkrimit.');
      setPhase('error');
      setProgressLabel('');
    }
  }, [caseId, documentId, docType]);

  // ── INIT: LOAD SAVED FIRST, THEN AUTO-GENERATE ──
  useEffect(() => {
    if (!isOpen) {
      hasInitializedRef.current = false;
      abortRef.current?.abort();
      return;
    }
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    let cancelled = false;
    setPhase('loading-saved');
    setErrorMessage('');
    setResult(null);
    setProgressLabel('Duke lexuar dokumentin e ruajtur...');

    (async () => {
      try {
        const res = await caseAnalysisService.getSavedRewrite(
          caseId,
          documentId,
          docType as VerifyDocType,
        );

        if (cancelled) return;

        if (res.has_rewrite && res.rewrite?.content) {
          setResult(res.rewrite as DraftRewriteResult);
          setPhase('ready');
          setProgressLabel('');
          return;
        }

        runRewrite();
      } catch (err: any) {
        if (cancelled) return;
        console.warn('[DocumentRewriteModal V1.5] Load saved failed:', err);
        runRewrite();
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, caseId, documentId, docType]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ── KEYBOARD SHORTCUTS: Esc close + Ctrl +/-/0 zoom ──
  useEffect(() => {
    if (!isOpen) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      // Zoom shortcuts (Ctrl or Cmd)
      if (e.ctrlKey || e.metaKey) {
        if (e.key === '=' || e.key === '+') {
          e.preventDefault();
          setZoomLevel((prev) => Math.min(ZOOM_MAX, prev + ZOOM_STEP));
        } else if (e.key === '-' || e.key === '_') {
          e.preventDefault();
          setZoomLevel((prev) => Math.max(ZOOM_MIN, prev - ZOOM_STEP));
        } else if (e.key === '0') {
          e.preventDefault();
          setZoomLevel(ZOOM_DEFAULT);
        }
      }
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [isOpen]);

  const handleCopy = useCallback(async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      alert('Kopjimi dështoi. Provo manualisht (Ctrl+C).');
    }
  }, [content]);

  const handleDownload = useCallback(() => {
    if (!content) return;
    const safeName = (documentName || 'dokument')
      .replace(/[^\w\d.-]+/g, '_')
      .replace(/\.\w+$/, '');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rishkruar_${safeName}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, [content, documentName]);

  const handlePrint = useCallback(() => {
    if (!content) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Bllokuesi i pop-up-eve e bllokoi printimin. Lejo pop-up-et dhe provo përsëri.');
      return;
    }

    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${docTypeLabel} — ${documentName}</title>
  <style>
    @page { size: A4; margin: 20mm; }
    body {
      font-family: "Times New Roman", Times, Georgia, serif;
      font-size: 12pt;
      line-height: 1.6;
      color: #000;
      margin: 0;
    }
    h1 { font-size: 16pt; font-weight: bold; text-align: center; margin: 0 0 8pt; text-transform: uppercase; color: #000; }
    h2 { font-size: 14pt; font-weight: bold; margin: 16pt 0 6pt; color: #000; }
    h3 { font-size: 12pt; font-weight: bold; margin: 12pt 0 4pt; color: #000; }
    h4 { font-size: 11pt; font-weight: bold; margin: 10pt 0 4pt; color: #000; }
    h5 { font-size: 10pt; font-weight: bold; margin: 8pt 0 4pt; color: #000; }
    p { margin: 0 0 8pt; text-align: justify; color: #000; }
    ul, ol { margin: 6pt 0 8pt 24pt; }
    li { margin-bottom: 4pt; color: #000; }
    strong { font-weight: bold; color: #000; }
    em { font-style: italic; }
    hr { border: none; border-top: 1px solid #999; margin: 12pt 0; }
    blockquote { border-left: 3px solid #999; padding-left: 12pt; margin: 8pt 0; font-style: italic; }
    code { background: #f1f5f9; padding: 1pt 3pt; font-family: "Courier New", monospace; font-size: 10pt; }
    a { color: #000; text-decoration: none; }
    table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
    th, td { border: 1px solid #999; padding: 4pt 6pt; text-align: left; font-size: 11pt; color: #000; }
  </style>
</head>
<body>
${markdownToPrintHtml(content)}
</body>
</html>`;

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();

    setTimeout(() => {
      printWindow.focus();
      printWindow.print();
    }, 300);
  }, [content, documentName, docTypeLabel]);

  if (!isOpen) return null;

  const showDocument = phase === 'ready' && content;
  const showLoadingSaved = phase === 'loading-saved';
  const showProgress = phase === 'generating';
  const showError = phase === 'error';

  const validationSeverity = validation?.severity || 'clean';
  const validationStyle = VALIDATION_STYLES[validationSeverity as keyof typeof VALIDATION_STYLES]
    || VALIDATION_STYLES.clean;
  const ValidationIcon = validationStyle.icon;
  const issues: ValidationIssue[] = validation?.issues || [];

  const zoomFactor = zoomLevel / 100;
  const canZoomOut = zoomLevel > ZOOM_MIN;
  const canZoomIn = zoomLevel < ZOOM_MAX;

  // V1.5: Dynamic maxWidth — fullscreen zgjeron dokumentin sipas dritares
  const a4StyleDynamic = {
    ...A4_STYLE,
    maxWidth: isFullscreen ? 'min(1400px, 100%)' : A4_STYLE.maxWidth,
    zoom: zoomFactor,
  } as React.CSSProperties;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/90 backdrop-blur-md flex items-center justify-center z-[260] p-2 sm:p-4 md:p-6 select-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 10 }}
          className={`glass-panel w-full ${
            isFullscreen
              ? 'h-full max-h-screen rounded-none border-0'
              : 'h-[94vh] max-w-6xl max-h-[950px] rounded-2xl sm:rounded-3xl border border-main'
          } p-4 sm:p-5 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
        >
          {/* HEADER */}
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-primary-start/15 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0">
                <Sparkles className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                    Rishkruaj Dokumentin
                  </h3>
                  {showDocument && (
                    <>
                      <span className="px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-wider border bg-emerald-500/15 border-emerald-500/40 text-emerald-500">
                        GATI
                      </span>
                      {validation && (
                        <span className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-wider border flex items-center gap-1 ${validationStyle.bg} ${validationStyle.border} ${validationStyle.text}`}>
                          <ValidationIcon size={9} />
                          {validationSeverity === 'clean' ? 'SAFE' : validationSeverity === 'warning' ? 'KONTR.' : 'RREZIK'}
                        </span>
                      )}
                    </>
                  )}
                </div>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {docTypeLabel} • {documentName}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {showDocument && (
                <>
                  {/* V1.4: ZOOM CONTROLS */}
                  <div
                    className="hidden sm:flex items-center h-8 rounded-lg border border-main bg-surface overflow-hidden"
                    role="group"
                    aria-label="Zoom kontrolli"
                  >
                    <button
                      type="button"
                      onClick={handleZoomOut}
                      disabled={!canZoomOut}
                      className="h-full px-2 text-text-secondary hover:text-primary-start hover:bg-hover transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Zvogëlo tekstin (Ctrl −)"
                      aria-label="Zvogëlo"
                    >
                      <ZoomOut size={13} />
                    </button>
                    <button
                      type="button"
                      onClick={handleZoomReset}
                      className="h-full px-2 min-w-[44px] text-center text-[11px] font-bold text-text-secondary hover:text-primary-start hover:bg-hover transition-all cursor-pointer tabular-nums"
                      title="Rivendos zoom (Ctrl 0)"
                      aria-label="Rivendos zoom"
                    >
                      {zoomLevel}%
                    </button>
                    <button
                      type="button"
                      onClick={handleZoomIn}
                      disabled={!canZoomIn}
                      className="h-full px-2 text-text-secondary hover:text-primary-start hover:bg-hover transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Zmadho tekstin (Ctrl +)"
                      aria-label="Zmadho"
                    >
                      <ZoomIn size={13} />
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={handlePrint}
                    className="hidden sm:flex h-8 px-3 rounded-lg border border-main bg-surface hover:bg-hover text-text-secondary hover:text-primary-start items-center gap-1.5 transition-all cursor-pointer"
                    title="Printo dokumentin"
                  >
                    <Printer size={13} />
                    <span className="text-[11px] font-bold hidden md:inline">Printo</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleDownload}
                    className="hidden sm:flex h-8 px-3 rounded-lg border border-main bg-surface hover:bg-hover text-text-secondary hover:text-primary-start items-center gap-1.5 transition-all cursor-pointer"
                    title="Shkarko si .txt"
                  >
                    <Download size={13} />
                    <span className="text-[11px] font-bold hidden md:inline">Shkarko</span>
                  </button>

                  <button
                    type="button"
                    onClick={runRewrite}
                    className="hidden sm:flex h-8 px-3 rounded-lg border border-main bg-surface hover:bg-hover text-text-secondary hover:text-emerald-500 items-center gap-1.5 transition-all cursor-pointer"
                    title="Rishkruaj nga e para"
                  >
                    <RefreshCw size={13} />
                    <span className="text-[11px] font-bold hidden md:inline">Rishkruaj</span>
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="hidden sm:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title={isFullscreen ? 'Zvogëlo' : 'Zmadho'}
              >
                {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>

              <button
                type="button"
                onClick={onClose}
                className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title="Mbyll"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* LOADING SAVED */}
          {showLoadingSaved && (
            <div className="mt-3 p-4 rounded-xl bg-canvas/40 border border-main flex items-center gap-3 shrink-0">
              <Loader2 size={16} className="text-primary-start animate-spin shrink-0" />
              <span className="text-xs font-bold text-text-primary">
                Duke lexuar dokumentin e ruajtur...
              </span>
            </div>
          )}

          {/* PROGRESS */}
          {showProgress && (
            <div className="mt-3 p-4 sm:p-5 rounded-xl bg-primary-start/5 border border-primary-start/25 shrink-0">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-9 h-9 rounded-xl bg-primary-start/15 flex items-center justify-center shrink-0">
                  <Loader2 size={18} className="text-primary-start animate-spin" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs sm:text-sm font-bold text-text-primary truncate">
                    {progressLabel || 'Duke rishkruar dokumentin...'}
                  </p>
                  <p className="text-[10px] text-text-muted mt-0.5">
                    Duke inkorporuar rekomandimet • 70-95 sekonda
                  </p>
                </div>
              </div>

              <div className="h-2 bg-canvas rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-start to-primary-end rounded-full animate-pulse"
                  style={{ width: '65%' }}
                />
              </div>
            </div>
          )}

          {/* ERROR */}
          {showError && (
            <div className="mt-3 p-4 rounded-xl bg-rose-500/5 border border-rose-500/25 shrink-0">
              <div className="flex items-start gap-3">
                <AlertCircle size={18} className="text-rose-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-xs font-bold text-rose-500 mb-1">Rishkrimi dështoi</p>
                  <p className="text-xs text-text-secondary">{errorMessage}</p>
                  <button
                    type="button"
                    onClick={runRewrite}
                    className="mt-3 h-8 px-4 rounded-lg bg-rose-500 hover:bg-rose-500/90 text-white font-bold text-[11px] uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <RefreshCw size={12} />
                    <span>Provo Përsëri</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* VALIDATION PANEL */}
          {showDocument && validation && (
            <div className={`mt-3 rounded-xl border ${validationStyle.bg} ${validationStyle.border} shrink-0 overflow-hidden`}>
              <div className="flex items-start gap-3 p-3 sm:p-4">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${validationStyle.bg} border ${validationStyle.border}`}>
                  <ValidationIcon size={16} className={validationStyle.text} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="min-w-0">
                      <p className={`text-xs sm:text-sm font-black ${validationStyle.text}`}>
                        {validationStyle.label}
                      </p>
                      <p className="text-[11px] text-text-secondary mt-0.5">
                        {validationStyle.message}
                      </p>
                    </div>

                    {issues.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowValidationDetails((v) => !v)}
                        className={`h-7 px-3 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer border ${validationStyle.border} ${validationStyle.text} hover:brightness-110`}
                      >
                        {showValidationDetails ? 'Fshih' : `Shfaq ${issues.length} detaje`}
                      </button>
                    )}
                  </div>

                  {validation.stats && (
                    <div className="mt-2 flex items-center gap-3 text-[10px] text-text-muted font-mono flex-wrap">
                      {validation.stats.dates_new > 0 && <span>📅 +{validation.stats.dates_new} data</span>}
                      {validation.stats.articles_new > 0 && <span>⚖️ +{validation.stats.articles_new} nene</span>}
                      {validation.stats.cases_new > 0 && <span>📋 +{validation.stats.cases_new} lëndë</span>}
                      {validation.stats.amounts_new > 0 && <span>💰 +{validation.stats.amounts_new} shuma</span>}
                      {validation.stats.laws_new > 0 && <span>📖 +{validation.stats.laws_new} ligje</span>}
                      {validation.total_issues === 0 && (
                        <span className="text-emerald-500">✓ 100% konsistent me origjinalin</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <AnimatePresence>
                {showValidationDetails && issues.length > 0 && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`border-t ${validationStyle.border} overflow-hidden`}
                  >
                    <div className="p-3 sm:p-4 space-y-2 max-h-[200px] overflow-y-auto">
                      {issues.map((issue, idx) => (
                        <div
                          key={idx}
                          className={`p-2.5 rounded-lg border ${
                            issue.severity === 'high'
                              ? 'bg-rose-500/5 border-rose-500/30'
                              : 'bg-amber-500/5 border-amber-500/30'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded ${
                              issue.severity === 'high'
                                ? 'bg-rose-500/20 text-rose-500'
                                : 'bg-amber-500/20 text-amber-500'
                            }`}>
                              {issue.severity === 'high' ? 'KRITIKE' : 'MESME'}
                            </span>
                            <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
                              {issue.type_label}
                            </span>
                          </div>
                          <p className="text-xs font-black text-text-primary mb-1">
                            {issue.value}
                          </p>
                          {issue.context && (
                            <p className="text-[10px] text-text-muted font-mono leading-relaxed">
                              {issue.context}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* BODY — A4 */}
          {/* V1.4: overflow-auto (jo vetëm -y) për të lejuar scroll horizontal kur zoom > 100% */}
          <div
            className="flex-1 overflow-auto my-2 bg-canvas/40 rounded-2xl border border-main"
            style={{ scrollbarGutter: 'stable' }}
          >
            {showDocument && (
              <div className="flex justify-center py-6 px-4 min-w-fit">
                {/* V1.3.1: Wrapper class për scoped CSS */}
                {/* V1.4: zoom CSS property — shkallëzon layout-in natyralisht */}
                {/* V1.5: maxWidth dinamik — në fullscreen zgjerohet sipas dritares */}
                <div
                  className="a4-document-wrapper shadow-[0_8px_40px_rgba(0,0,0,0.4)] rounded-sm"
                  style={a4StyleDynamic}
                >
                  {/* V1.3.1: CSS scoped — force color për çdo element */}
                  <style>{`
                    .a4-document-wrapper,
                    .a4-document-wrapper * {
                      color: #0f172a !important;
                    }
                    .a4-document-wrapper h1,
                    .a4-document-wrapper h2,
                    .a4-document-wrapper h3,
                    .a4-document-wrapper h4,
                    .a4-document-wrapper h5,
                    .a4-document-wrapper h6 {
                      color: #000000 !important;
                    }
                    .a4-document-wrapper strong,
                    .a4-document-wrapper b {
                      color: #000000 !important;
                      font-weight: 700 !important;
                    }
                    .a4-document-wrapper blockquote,
                    .a4-document-wrapper em,
                    .a4-document-wrapper i {
                      color: #334155 !important;
                    }
                    .a4-document-wrapper a {
                      color: #0f172a !important;
                      text-decoration: underline !important;
                    }
                  `}</style>

                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={a4Components as any}
                  >
                    {linkedContent}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {(showProgress || showLoadingSaved) && (
              <div className="flex items-center justify-center h-full min-h-[400px] p-12">
                <div className="text-center space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center mx-auto">
                    <Sparkles size={32} className="animate-pulse" />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-text-primary">
                      {showLoadingSaved
                        ? 'Duke lexuar dokumentin e ruajtur...'
                        : 'Duke rishkruar dokumentin...'}
                    </h4>
                    <p className="text-xs text-text-muted max-w-md mt-1">
                      {showLoadingSaved
                        ? 'Kontrollojmë nëse ekziston një version i ruajtur.'
                        : 'Drafti po riorganizohet me strukturë profesionale dhe rekomandimet e verifikimit.'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* FOOTER */}
          <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
            {showDocument && result && (
              <div className="flex items-center gap-3 text-[10px] text-text-muted font-mono">
                <span>{result.content_chars?.toLocaleString()} karaktere</span>
                <span className="hidden sm:inline">•</span>
                <span className="hidden sm:inline">{result.duration_sec?.toFixed(1)}s</span>
                {result.chunks_total && (
                  <>
                    <span className="hidden sm:inline">•</span>
                    <span className="hidden sm:inline">{result.chunks_total} chunks</span>
                  </>
                )}
              </div>
            )}

            <div className="ml-auto flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopy}
                disabled={!showDocument}
                className="h-9 px-5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center gap-2 disabled:opacity-40 cursor-pointer"
              >
                {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                <span>{copied ? 'U Kopjua!' : 'Kopjo Dokumentin'}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

// ───────────────────────────────────────────────────────────────────────────
// HELPERS
// ───────────────────────────────────────────────────────────────────────────

const buildA4Components = () => ({
  h1: ({ children }: any) => (
    <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#000000', textAlign: 'center', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '24px', marginTop: '0' }}>
      {children}
    </h1>
  ),
  h2: ({ children }: any) => (
    <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#000000', textTransform: 'uppercase', marginTop: '28px', marginBottom: '12px', borderBottom: '1px solid #cbd5e1', paddingBottom: '4px' }}>
      {children}
    </h2>
  ),
  h3: ({ children }: any) => (
    <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#000000', marginTop: '18px', marginBottom: '8px' }}>
      {children}
    </h3>
  ),
  h4: ({ children }: any) => (
    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#000000', marginTop: '14px', marginBottom: '6px' }}>
      {children}
    </h4>
  ),
  h5: ({ children }: any) => (
    <h5 style={{ fontSize: '12.5px', fontWeight: 700, color: '#000000', marginTop: '10px', marginBottom: '5px' }}>
      {children}
    </h5>
  ),
  p: ({ children }: any) => (
    <p style={{ color: '#0f172a', marginBottom: '12px', textAlign: 'justify' }}>
      {children}
    </p>
  ),
  ul: ({ children }: any) => (
    <ul style={{ marginLeft: '24px', marginBottom: '12px' }}>{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol style={{ marginLeft: '24px', marginBottom: '12px' }}>{children}</ol>
  ),
  li: ({ children }: any) => (
    <li style={{ color: '#0f172a', marginBottom: '4px' }}>{children}</li>
  ),
  strong: ({ children }: any) => (
    <strong style={{ color: '#000000', fontWeight: 700 }}>{children}</strong>
  ),
  em: ({ children }: any) => (
    <em style={{ color: '#334155', fontStyle: 'italic' }}>{children}</em>
  ),
  hr: () => (
    <hr style={{ border: 'none', borderTop: '1px solid #94a3b8', margin: '20px 0' }} />
  ),
  blockquote: ({ children }: any) => (
    <blockquote style={{ borderLeft: '3px solid #94a3b8', paddingLeft: '14px', margin: '14px 0', fontStyle: 'italic', color: '#334155' }}>
      {children}
    </blockquote>
  ),
  code: ({ children }: any) => (
    <code style={{ background: '#f1f5f9', padding: '2px 5px', fontFamily: '"Courier New", monospace', fontSize: '12px', borderRadius: '3px', color: '#0f172a' }}>
      {children}
    </code>
  ),

  a: ({ children, href }: any) => {
    const hrefStr = typeof href === 'string' ? href : '';

    if (hrefStr.includes('/laws/article')) {
      return (
        <LawCitationLink
          lawTitle=""
          articleNum=""
          fullMatch={String(children)}
          targetUrl={hrefStr}
        />
      );
    }

    if (hrefStr.includes('/laws/search')) {
      return (
        <PrecedentCitationLink caseNumber={String(children)} />
      );
    }

    return (
      <a
        href={hrefStr}
        style={{ color: '#0f172a', textDecoration: 'underline' }}
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    );
  },

  table: ({ children }: any) => (
    <table style={{ width: '100%', borderCollapse: 'collapse', margin: '14px 0' }}>{children}</table>
  ),
  th: ({ children }: any) => (
    <th style={{ border: '1px solid #94a3b8', padding: '6px 10px', textAlign: 'left', fontWeight: 700, background: '#f1f5f9', color: '#000000' }}>
      {children}
    </th>
  ),
  td: ({ children }: any) => (
    <td style={{ border: '1px solid #94a3b8', padding: '6px 10px', textAlign: 'left', color: '#0f172a' }}>
      {children}
    </td>
  ),
});

function markdownToPrintHtml(markdown: string): string {
  const lines = markdown.split(/\r?\n/);
  const html: string[] = [];
  let inList: 'ul' | 'ol' | null = null;
  let inBlockquote = false;
  let bqLines: string[] = [];

  const inline = (text: string): string => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  };

  const flushList = () => {
    if (inList) {
      html.push(inList === 'ul' ? '</ul>' : '</ol>');
      inList = null;
    }
  };

  const flushBq = () => {
    if (inBlockquote) {
      html.push(`<blockquote>${bqLines.map(inline).join('<br>')}</blockquote>`);
      bqLines = [];
      inBlockquote = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();

    if (/^(---|---|\*\*\*|___)$/.test(line)) {
      flushList(); flushBq();
      html.push('<hr />');
      continue;
    }

    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      flushList(); flushBq();
      const lvl = h[1].length;
      html.push(`<h${lvl}>${inline(h[2])}</h${lvl}>`);
      continue;
    }

    if (line.startsWith('>')) {
      flushList();
      inBlockquote = true;
      bqLines.push(line.replace(/^>\s?/, ''));
      continue;
    } else if (inBlockquote) {
      flushBq();
    }

    const bullet = line.match(/^([•\-\*])\s+(.+)$/);
    if (bullet) {
      if (inList !== 'ul') {
        flushList();
        html.push('<ul>');
        inList = 'ul';
      }
      html.push(`<li>${inline(bullet[2])}</li>`);
      continue;
    }

    const num = line.match(/^(\d+)\.\s+(.+)$/);
    if (num) {
      if (inList !== 'ol') {
        flushList();
        html.push('<ol>');
        inList = 'ol';
      }
      html.push(`<li>${inline(num[2])}</li>`);
      continue;
    }

    flushList();
    if (!line) continue;
    html.push(`<p>${inline(line)}</p>`);
  }

  flushList(); flushBq();
  return html.join('\n');
}

export default DocumentRewriteModal;