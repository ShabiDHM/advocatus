// FILE: frontend/src/components/case/CaseDossierAuditModal.tsx
// PHOENIX PROTOCOL - CASE DOSSIER AUDIT MODAL V5.0
// V5.0: SERVER FETCH — kur hapet pa `preGeneratedReport`, lexon raportin e ruajtur
//       nga GET /cases/{id}/audit. Loading + error handling. "Analizo" buton në
//       empty state. Banner "saved" me timestamp.
// V4.0.1: Hequr useCallback, isSaving state.
// V4.0.0: Modal bëhet VETËM viewer.

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2,
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown, Lock, Scale, Folder,
  ShieldCheck, RotateCcw, Calendar, Sparkles
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

const WORD_CODE_BG = '#f1f5f9';
const WORD_BLOCKQUOTE_BORDER = '#2563eb';
const WORD_BLOCKQUOTE_BG = '#f8fafc';
const WORD_BLOCKQUOTE_TEXT = '#334155';
const WORD_HR_COLOR = '#cbd5e1';
const WORD_HEADING_COLOR = '#0f172a';
const WORD_BODY_COLOR = '#1e293b';

const ALBANIAN_MONTHS = [
  'Janar', 'Shkurt', 'Mars', 'Prill', 'Maj', 'Qershor',
  'Korrik', 'Gusht', 'Shtator', 'Tetor', 'Nëntor', 'Dhjetor',
];

const formatAuditDate = (isoDate: string | Date | undefined | null): string => {
  if (!isoDate) return '';
  try {
    const d = typeof isoDate === 'string' ? new Date(isoDate) : isoDate;
    if (isNaN(d.getTime())) return '';
    const day = d.getDate().toString().padStart(2, '0');
    const month = ALBANIAN_MONTHS[d.getMonth()];
    const year = d.getFullYear();
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${day} ${month} ${year}, ${hours}:${minutes}`;
  } catch {
    return '';
  }
};

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

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 }
];

const markdownToWordHtml = (markdown: string): string => {
  const lines = markdown.split(/\r?\n/);
  const htmlOutput: string[] = [];
  let inList: 'ul' | 'ol' | null = null;
  let inBlockquote = false;
  let blockquoteLines: string[] = [];

  const formatInline = (text: string): string => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, `<code style="background-color: ${WORD_CODE_BG}; padding: 2px 4px; font-family: Consolas, monospace; font-size: 10pt;">$1</code>`);
  };

  const flushList = () => {
    if (inList) {
      htmlOutput.push(inList === 'ul' ? '</ul>' : '</ol>');
      inList = null;
    }
  };

  const flushBlockquote = () => {
    if (inBlockquote) {
      htmlOutput.push(`<blockquote style="border-left: 4px solid ${WORD_BLOCKQUOTE_BORDER}; margin: 10px 0; padding: 8px 16px; background-color: ${WORD_BLOCKQUOTE_BG}; color: ${WORD_BLOCKQUOTE_TEXT}; font-style: italic; font-family: Calibri, Arial, sans-serif;">${blockquoteLines.map(formatInline).join('<br>')}</blockquote>`);
      blockquoteLines = [];
      inBlockquote = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (/^(---|---|\*\*\*|___)$/.test(line)) {
      flushList();
      flushBlockquote();
      htmlOutput.push(`<hr style="border: 0; border-top: 1px solid ${WORD_HR_COLOR}; margin: 16px 0;" />`);
      continue;
    }

    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushList();
      flushBlockquote();
      const level = hMatch[1].length;
      const text = formatInline(hMatch[2]);
      const fontSize = level === 1 ? '16pt' : level === 2 ? '14pt' : '12pt';
      htmlOutput.push(`<h${level} style="font-size: ${fontSize}; font-family: Calibri, Arial, sans-serif; font-weight: bold; color: ${WORD_HEADING_COLOR}; margin-top: 14px; margin-bottom: 6px;">${text}</h${level}>`);
      continue;
    }

    if (line.startsWith('>')) {
      flushList();
      inBlockquote = true;
      blockquoteLines.push(line.replace(/^>\s?/, ''));
      continue;
    } else if (inBlockquote) {
      flushBlockquote();
    }

    const bulletMatch = line.match(/^([•\-\*])\s+(.+)$/);
    if (bulletMatch) {
      if (inList !== 'ul') {
        flushList();
        htmlOutput.push('<ul style="margin: 6px 0 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">');
        inList = 'ul';
      }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: ${WORD_BODY_COLOR}; font-size: 11pt;">${formatInline(bulletMatch[2])}</li>`);
      continue;
    }

    const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      if (inList !== 'ol') {
        flushList();
        htmlOutput.push('<ol style="margin: 6px 0 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">');
        inList = 'ol';
      }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: ${WORD_BODY_COLOR}; font-size: 11pt;">${formatInline(numMatch[2])}</li>`);
      continue;
    }

    flushList();
    if (line.length === 0) continue;

    htmlOutput.push(`<p style="margin: 6px 0; font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: ${WORD_BODY_COLOR};">${formatInline(line)}</p>`);
  }

  flushList();
  flushBlockquote();

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Raport</title>
      <style>
        body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: ${WORD_BODY_COLOR}; }
      </style>
    </head>
    <body>
      ${htmlOutput.join('\n')}
    </body>
    </html>
  `.trim();
};

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
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);

  // V5.0: Server fetch state
  const [isLoadingFromServer, setIsLoadingFromServer] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [lastAuditedAt, setLastAuditedAt] = useState<string | null>(null);
  const [reportSource, setReportSource] = useState<'fresh' | 'cache' | 'saved' | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const fetchAbortRef = useRef<boolean>(false);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(1);
  const activeFont = FONT_LEVELS[fontLevelIndex];
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

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

  // ═══════════════════════════════════════════════════════════════════════════
  // V5.0: LOAD STRATEGY
  //   1. Nëse `preGeneratedReport` → përdor direkt (nga analiza e re)
  //   2. Përndryshe → fetch nga server (GET /audit)
  // ═══════════════════════════════════════════════════════════════════════════
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

    // Fetch from server
    setIsLoadingFromServer(true);
    setLoadError(null);
    setReportContent('');

    apiService.getCaseDossierAudit(caseId)
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
        console.warn('[CaseDossierAuditModal V5.0] Failed to load saved report:', err);
        setLoadError('Dështoi ngarkimi i raportit të ruajtur.');
      })
      .finally(() => {
        if (fetchAbortRef.current) return;
        setIsLoadingFromServer(false);
      });

    return () => {
      fetchAbortRef.current = true;
    };
  }, [isOpen, preGeneratedReport, preGeneratedSource, caseId]);

  // Reset kur mbyllet
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

  const handleClearContent = async () => {
    if (!reportContent || !caseId || isPurging) return;
    const confirmWipe = window.confirm("A jeni i sigurt që dëshironi të asgjësoni plotësisht raportin nga serveri?");
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await apiService.clearCaseDossierAudit(caseId);
      setReportContent('');
      setLastAuditedAt(null);
      setReportSource(null);
    } catch (err) {
      console.error("Purge error:", err);
      alert("Dështoi asgjësimi i raportit në server.");
    } finally {
      setIsPurging(false);
    }
  };

  const handleRegenerate = () => {
    if (onRegenerate) {
      onRegenerate();
    }
  };

  const handleCopy = async () => {
    if (!reportContent) return;
    const htmlContent = markdownToWordHtml(reportContent);

    try {
      if (navigator.clipboard && window.ClipboardItem) {
        const clipboardItem = new ClipboardItem({
          'text/html': new Blob([htmlContent], { type: 'text/html' }),
          'text/plain': new Blob([reportContent], { type: 'text/plain' }),
        });
        await navigator.clipboard.write([clipboardItem]);
      } else {
        throw new Error();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      await navigator.clipboard.writeText(reportContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    setShowScrollBottomBtn(distanceFromBottom > 80);
  };

  const scrollToBottom = () => {
    scrollContainerRef.current?.scrollTo({ top: scrollContainerRef.current.scrollHeight, behavior: 'smooth' });
    setShowScrollBottomBtn(false);
  };

  if (!isOpen) return null;

  const showReportBanner = Boolean(reportContent.trim())
    && (reportSource === 'cache' || reportSource === 'saved');

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[250] p-2 sm:p-4 md:p-6 select-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 10 }}
          className={`glass-panel w-full ${
            isFullscreen
              ? 'h-full max-h-screen rounded-none border-0'
              : 'h-[92vh] max-w-5xl max-h-[880px] rounded-2xl sm:rounded-3xl border border-main'
          } p-4 sm:p-6 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-primary-start/15 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0">
                {effectiveScope === 'document' ? <ShieldCheck className="w-5 h-5" /> : <Folder className="w-5 h-5" />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                    {reportTitle}
                  </h3>
                </div>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {headerSubtitle}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <div className="flex items-center bg-surface border border-main rounded-xl p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => setFontLevelIndex(prev => Math.max(0, prev - 1))}
                  disabled={fontLevelIndex <= 0}
                  className="px-2 py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-lg hover:bg-hover font-bold cursor-pointer"
                  title="Zvogëlo"
                >
                  <ZoomOut size={13} />
                </button>
                <span className="px-1.5 text-[10px] font-mono font-bold text-primary-start">
                  {activeFont.label}
                </span>
                <button
                  type="button"
                  onClick={() => setFontLevelIndex(prev => Math.min(FONT_LEVELS.length - 1, prev + 1))}
                  disabled={fontLevelIndex >= FONT_LEVELS.length - 1}
                  className="px-2 py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-lg hover:bg-hover font-bold cursor-pointer"
                  title="Zmadho"
                >
                  <ZoomIn size={13} />
                </button>
              </div>

              {reportContent && (
                <button
                  type="button"
                  onClick={handleClearContent}
                  disabled={isPurging}
                  className="p-2 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-xl transition-colors cursor-pointer"
                  title="Fshi raportin nga serveri"
                >
                  {isPurging ? <Loader2 size={16} className="animate-spin text-danger-start" /> : <Trash2 size={16} />}
                </button>
              )}

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="hidden sm:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title={isFullscreen ? "Zvogëlo" : "Zmadho"}
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

          {/* BANNER — cache/saved */}
          {showReportBanner && (
            <div className="mt-3 p-3 sm:p-4 rounded-xl bg-primary-start/5 border border-primary-start/25 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0">
              <div className="flex items-start gap-2.5 min-w-0 flex-1">
                <div className="w-8 h-8 rounded-lg bg-primary-start/15 flex items-center justify-center shrink-0">
                  <Calendar size={15} className="text-primary-start" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs sm:text-sm font-bold text-text-primary">
                    {reportSource === 'cache'
                      ? 'Ky raport është shfaqur nga cache e serverit'
                      : 'Ky raport është ruajtur më parë'}
                  </p>
                  <p className="text-[11px] sm:text-xs text-text-muted mt-0.5">
                    {reportSource === 'cache'
                      ? 'Kliko "Rianalizo" për të gjeneruar nga e para'
                      : <>Gjeneruar më <span className="font-mono font-semibold text-text-secondary">{formatAuditDate(lastAuditedAt)}</span></>}
                  </p>
                </div>
              </div>
              {onRegenerate && (
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={isPurging}
                  className="h-9 px-4 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] uppercase tracking-wider transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shrink-0 shadow-sm hover-lift"
                  title="Rianalizo nga e para — injoron cache-në"
                >
                  <RotateCcw size={13} />
                  <span>Rianalizo</span>
                </button>
              )}
            </div>
          )}

          {/* Body */}
          <div
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 my-2 bg-surface/30 rounded-2xl border border-main text-text-primary select-text relative flex flex-col"
          >
            <style>{`
              .fast-case-dossier-audit p, .fast-case-dossier-audit li {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .fast-case-dossier-audit h1, .fast-case-dossier-audit h2, .fast-case-dossier-audit h3 {
                color: var(--text-primary);
                font-weight: 800;
                margin-top: 1em;
                margin-bottom: 0.4em;
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
              <div className="markdown-content fast-case-dossier-audit prose prose-slate dark:prose-invert max-w-none text-text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {autoLinkLegalCitations(reportContent)}
                </ReactMarkdown>
              </div>
            )}

            {showScrollBottomBtn && (
              <button
                type="button"
                onClick={scrollToBottom}
                className="sticky bottom-2 right-2 ml-auto z-20 px-3 py-1.5 bg-text-primary text-text-inverse text-[11px] font-bold rounded-full shadow-lg border border-border-strong flex items-center gap-1 cursor-pointer"
              >
                <span>Te Fundi</span>
                <ArrowDown size={12} className="animate-bounce" />
              </button>
            )}
          </div>

          {/* Bottom Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
            {reportContent && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium">
                <Lock size={12} className="text-text-muted" />
                <span className="hidden sm:inline">Raporti është ruajtur (Përdorni koshin për ta asgjësuar)</span>
                <span className="sm:hidden">E ruajtur</span>
              </div>
            )}

            <div className="ml-auto flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopy}
                disabled={!reportContent}
                className="h-9 px-5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center gap-2 disabled:opacity-40 cursor-pointer"
              >
                {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                <span>{copied ? 'U Kopjua!' : 'Kopjo për Word'}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CaseDossierAuditModal;