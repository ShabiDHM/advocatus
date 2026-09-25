// FILE: src/components/case/DraftVerificationModal.tsx
// PHOENIX PROTOCOL - DRAFT VERIFICATION MODAL V3.2
// V3.2: BUTONI "Rishkruaj Dokumentin" në footer → hap DocumentRewriteModal.
// V3.1.2: HEQUR "Në Fund" button.
// V3.1.1: SCORE TOOLTIP breakdown.
// V3.1: SCORE RING + STATS PANEL.

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2, Loader2, Maximize2, Minimize2,
  Trash2, ZoomIn, ZoomOut, Lock, ShieldCheck,
  RotateCcw, Calendar, Sparkles, AlertCircle, PenLine,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {
  caseAnalysisService,
  type VerifyDocType,
  type ScoreBreakdown,
} from '../../services/caseAnalysisService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { LawCitationLink } from '../LawCitationLink';
import DocumentRewriteModal from './DocumentRewriteModal';

// ───────────────────────────────────────────────────────────────────────────
// KONSTANTE
// ───────────────────────────────────────────────────────────────────────────

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

const formatAuditDate = (isoDate?: string | Date | null): string => {
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

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 },
];

const SCORE_STYLES = {
  high: {
    ring: 'stroke-emerald-500',
    text: 'text-emerald-500',
    bg: 'bg-emerald-500/5',
    border: 'border-emerald-500/25',
    label: 'Shkëlqyeshëm',
  },
  mid: {
    ring: 'stroke-amber-500',
    text: 'text-amber-500',
    bg: 'bg-amber-500/5',
    border: 'border-amber-500/25',
    label: 'Mirë',
  },
  low: {
    ring: 'stroke-rose-500',
    text: 'text-rose-500',
    bg: 'bg-rose-500/5',
    border: 'border-rose-500/25',
    label: 'Dobët',
  },
};

const getScoreStyle = (score: number) => {
  if (score >= 85) return SCORE_STYLES.high;
  if (score >= 60) return SCORE_STYLES.mid;
  return SCORE_STYLES.low;
};

// ───────────────────────────────────────────────────────────────────────────
// PREPROCESS
// ───────────────────────────────────────────────────────────────────────────

const preprocessReport = (markdown: string): string => {
  if (!markdown) return '';
  return markdown
    .replace(/\[OK\]/g, '✅')
    .replace(/\[X\]/g, '❌')
    .replace(/\[!\]/g, '⚠️')
    .replace(/\[\?\]/g, '💡')
    .replace(/\*\*File:\*\*/g, '**Dokumenti:**')
    .replace(/\*\*File\*\*/g, '**Dokumenti**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*NEEDS WORK\*\*/g, '**Gatishmëria:** **KËRKON PUNË**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*READY\*\*/g, '**Gatishmëria:** **GATI**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*INCOMPLETE\*\*/g, '**Gatishmëria:** **I PËRPLOTË**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*UNKNOWN\*\*/g, '**Gatishmëria:** **I PANJOHUR**')
    .replace(/\bNEEDS WORK\b/g, 'KËRKON PUNË')
    .replace(/\bINCOMPLETE\b/g, 'I PËRPLOTË')
    .replace(/\bUNKNOWN\b/g, 'I PANJOHUR')
    .replace(/🛑\s*/g, '⛔ ')
    .replace(/⚠️ SUGJERIM/g, '💡 **SUGJERIM**')
    .replace(/ℹ️\s*/g, 'ℹ️  ');
};

// ───────────────────────────────────────────────────────────────────────────
// MARKDOWN → WORD HTML
// ───────────────────────────────────────────────────────────────────────────

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
      flushList(); flushBlockquote();
      htmlOutput.push(`<hr style="border: 0; border-top: 1px solid ${WORD_HR_COLOR}; margin: 16px 0;" />`);
      continue;
    }

    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushList(); flushBlockquote();
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
        htmlOutput.push('<ol style="margin: 6px 6px 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">');
        inList = 'ol';
      }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: ${WORD_BODY_COLOR}; font-size: 11pt;">${formatInline(numMatch[2])}</li>`);
      continue;
    }

    flushList();
    if (line.length === 0) continue;
    htmlOutput.push(`<p style="margin: 6px 0; font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: ${WORD_BODY_COLOR};">${formatInline(line)}</p>`);
  }

  flushList(); flushBlockquote();

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Raport Verifikimi</title>
    <style>body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: ${WORD_BODY_COLOR}; }</style>
    </head><body>${htmlOutput.join('\n')}</body></html>`.trim();
};

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
// CUSTOM MARKDOWN COMPONENTS
// ───────────────────────────────────────────────────────────────────────────

const buildReportComponents = () => ({
  h1: ({ children }: any) => {
    const text = String(children);
    return (
      <div className="mt-2 mb-6 pb-5 border-b-2 border-emerald-500/30">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0">
            <ShieldCheck size={22} className="text-emerald-500" />
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-text-primary tracking-tight">
            {text.replace(/^RAPORT VERIFIKIMI\s*—\s*/, '')}
          </h1>
        </div>
        <p className="text-[11px] text-text-muted uppercase tracking-widest font-bold mt-2 ml-14">
          Raport Verifikimi
        </p>
      </div>
    );
  },

  h2: ({ children }: any) => {
    const text = String(children);
    const match = text.match(/^(\d+)\.\s+(.+)$/);
    if (match) {
      return (
        <h2 className="flex items-center gap-3 mt-8 mb-4 pb-3 border-b border-main">
          <span className="w-9 h-9 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-black text-sm shrink-0 shadow-sm">
            {match[1]}
          </span>
          <span className="text-base sm:text-lg font-black text-text-primary tracking-tight uppercase">
            {match[2]}
          </span>
        </h2>
      );
    }
    return (
      <h2 className="text-base sm:text-lg font-black text-text-primary mt-8 mb-4 pb-3 border-b border-main uppercase tracking-tight">
        {children}
      </h2>
    );
  },

  h3: ({ children }: any) => {
    const text = String(children);
    const match = text.match(/^([A-Z])\.\s+(.+)$/);
    if (match) {
      return (
        <h3 className="flex items-center gap-2.5 mt-5 mb-3">
          <span className="w-1 h-5 rounded-full bg-emerald-500 shrink-0" />
          <span className="text-sm sm:text-base font-bold text-text-primary">
            <span className="text-emerald-500 mr-1">{match[1]}.</span>
            {match[2]}
          </span>
        </h3>
      );
    }
    return (
      <h3 className="flex items-center gap-2.5 mt-5 mb-3">
        <span className="w-1 h-5 rounded-full bg-emerald-500 shrink-0" />
        <span className="text-sm sm:text-base font-bold text-text-primary">{children}</span>
      </h3>
    );
  },

  h4: ({ children }: any) => (
    <h4 className="text-sm font-bold text-text-primary mt-4 mb-2 pl-3 border-l-2 border-emerald-500/40">
      {children}
    </h4>
  ),

  p: ({ children }: any) => (
    <p className="text-xs sm:text-sm leading-relaxed text-text-primary mb-3">
      {children}
    </p>
  ),

  ul: ({ children }: any) => (
    <ul className="list-none pl-0 mb-3 space-y-1.5">
      {children}
    </ul>
  ),

  ol: ({ children }: any) => (
    <ol className="list-decimal pl-6 mb-3 space-y-1.5 text-xs sm:text-sm text-text-primary">
      {children}
    </ol>
  ),

  li: ({ children }: any) => {
    const firstText = Array.isArray(children)
      ? String(children[0] || '')
      : String(children || '');
    const trimmed = firstText.trim();

    if (trimmed.startsWith('✅')) {
      return (
        <li className="flex items-start gap-2 p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs sm:text-sm">
          <span className="text-emerald-500 font-bold shrink-0 leading-relaxed">✓</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children)
              ? [String(children[0]).replace('✅', '').trim(), ...children.slice(1)]
              : String(children).replace('✅', '').trim()}
          </span>
        </li>
      );
    }

    if (trimmed.startsWith('❌')) {
      return (
        <li className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs sm:text-sm">
          <span className="text-rose-500 font-bold shrink-0 leading-relaxed">✗</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children)
              ? [String(children[0]).replace('❌', '').trim(), ...children.slice(1)]
              : String(children).replace('❌', '').trim()}
          </span>
        </li>
      );
    }

    if (trimmed.startsWith('⚠️')) {
      return (
        <li className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs sm:text-sm">
          <span className="text-amber-500 font-bold shrink-0 leading-relaxed">!</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children)
              ? [String(children[0]).replace('⚠️', '').trim(), ...children.slice(1)]
              : String(children).replace('⚠️', '').trim()}
          </span>
        </li>
      );
    }

    if (trimmed.startsWith('💡')) {
      return (
        <li className="flex items-start gap-2 p-2.5 rounded-lg bg-sky-500/5 border border-sky-500/20 text-xs sm:text-sm">
          <span className="text-sky-500 font-bold shrink-0 leading-relaxed">?</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children)
              ? [String(children[0]).replace('💡', '').trim(), ...children.slice(1)]
              : String(children).replace('💡', '').trim()}
          </span>
        </li>
      );
    }

    return (
      <li className="flex items-start gap-2.5 pl-1 text-xs sm:text-sm leading-relaxed text-text-primary">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60 mt-2 shrink-0" />
        <span className="flex-1">{children}</span>
      </li>
    );
  },

  strong: ({ children }: any) => (
    <strong className="font-bold text-text-primary">{children}</strong>
  ),

  em: ({ children }: any) => (
    <em className="italic text-text-secondary">{children}</em>
  ),

  code: ({ children }: any) => (
    <code className="px-1.5 py-0.5 rounded bg-canvas border border-main font-mono text-[11px] text-emerald-500 font-semibold">
      {children}
    </code>
  ),

  hr: () => (
    <div className="my-7 flex items-center justify-center">
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />
      <div className="mx-3 w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />
    </div>
  ),

  blockquote: ({ children }: any) => (
    <blockquote className="my-4 pl-4 py-3 pr-3 border-l-4 border-emerald-500/50 bg-emerald-500/5 rounded-r-lg">
      <div className="text-xs sm:text-sm italic text-text-secondary leading-relaxed">
        {children}
      </div>
    </blockquote>
  ),

  a: ({ children, href }: any) => {
    const isArticleLink = typeof href === 'string' && href.includes('/laws/article');

    if (isArticleLink) {
      return (
        <LawCitationLink
          lawTitle=""
          articleNum=""
          fullMatch={String(children)}
          targetUrl={href}
        />
      );
    }

    return (
      <a
        href={href}
        className="text-primary-start hover:text-primary-end underline underline-offset-2 transition-colors font-medium"
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    );
  },

  table: ({ children }: any) => (
    <div className="overflow-x-auto my-4 rounded-xl border border-main">
      <table className="min-w-full text-xs">
        {children}
      </table>
    </div>
  ),

  thead: ({ children }: any) => (
    <thead className="bg-canvas/60">{children}</thead>
  ),

  th: ({ children }: any) => (
    <th className="px-3 py-2 text-left font-bold text-text-primary border-b border-main">
      {children}
    </th>
  ),

  td: ({ children }: any) => (
    <td className="px-3 py-2 border-b border-main/60 text-text-primary">
      {children}
    </td>
  ),
});

// ───────────────────────────────────────────────────────────────────────────
// COMPONENT
// ───────────────────────────────────────────────────────────────────────────

const DraftVerificationModal: React.FC<DraftVerificationModalProps> = ({
  isOpen,
  onClose,
  caseId,
  documentId,
  documentName,
  docType,
  docTypeLabel,
  onProgressChange,
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

  // V3.2: Rewrite modal
  const [isRewriteOpen, setIsRewriteOpen] = useState<boolean>(false);

  const abortRef = useRef<AbortController | null>(null);

  const activeFont = FONT_LEVELS[fontLevelIndex];
  const reportComponents = useMemo(() => buildReportComponents(), []);

  const title = 'Verifiko Draftin';
  const subtitle = useMemo(
    () => `${docTypeLabel} • ${documentName}`,
    [docTypeLabel, documentName]
  );

  const processedContent = useMemo(() => preprocessReport(reportContent), [reportContent]);
  const linkedContent = useMemo(
    () => (processedContent ? autoLinkLegalCitations(processedContent) : ''),
    [processedContent]
  );

  const scoreStyle = score !== null ? getScoreStyle(score) : null;

  const emitProgress = useCallback((isGenerating: boolean, percent: number, label: string) => {
    if (onProgressChange) {
      onProgressChange({ isGenerating, percent, label });
    }
  }, [onProgressChange]);

  // ── RUN VERIFICATION ────────────────────────────────────────────────────
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

    let completed = 0;
    const total = 6;

    try {
      for await (const evt of caseAnalysisService.streamDraftVerification(
        caseId,
        documentId,
        docType as VerifyDocType,
      )) {
        if (ctrl.signal.aborted) break;

        const evtType = evt.event;

        if (evtType === 'step_started') {
          const label = evt.step_title || evt.step_key || 'Duke përpunuar...';
          emitProgress(true, Math.round((completed / total) * 100), label);
          continue;
        }

        if (evtType === 'section_started') {
          const titleTxt = evt.section_title || evt.section_key || '';
          emitProgress(true, Math.round((completed / total) * 100), `Seksioni: ${titleTxt}`);
          continue;
        }

        if (evtType === 'section_completed') {
          completed++;
          emitProgress(true, Math.round((completed / total) * 100), 'Vazhdon...');
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
      console.error('[DraftVerificationModal V3.2] Gabim SSE:', err);
      setErrorMessage(err?.message || 'Gabim gjatë verifikimit.');
      setPhase('error');
      emitProgress(false, 0, '');
    }
  }, [caseId, documentId, docType, emitProgress]);

  // ── LOAD FLOW ───────────────────────────────────────────────────────────
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
    setIsRewriteOpen(false);

    (async () => {
      try {
        const data = await caseAnalysisService.getDraftVerification(
          caseId,
          documentId,
          docType as VerifyDocType,
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
        console.warn('[DraftVerificationModal V3.2] Leximi i ruajtur dështoi:', err);
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

  // ── RESET ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) {
      abortRef.current?.abort();
      abortRef.current = null;
      setCopied(false);
      setIsFullscreen(false);
      setShowScoreTooltip(false);
      setIsRewriteOpen(false);
      emitProgress(false, 0, '');
    }
  }, [isOpen, emitProgress]);

  // ── ESC ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isRewriteOpen) onClose();
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [isOpen, onClose, isRewriteOpen]);

  // ── BLLOK SCROLL BODY ───────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen || phase === 'generating') return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [isOpen, phase]);

  // ── DELETE ──────────────────────────────────────────────────────────────
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
      console.error('[DraftVerificationModal V3.2] Fshirja dështoi:', err);
      alert('Fshirja e raportit në server dështoi.');
    } finally {
      setIsPurging(false);
    }
  };

  // ── COPY ────────────────────────────────────────────────────────────────
  const handleCopy = async () => {
    if (!reportContent) return;

    const processed = preprocessReport(reportContent);
    const htmlContent = markdownToWordHtml(processed);
    const plainContent = processed;

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

  // ── READINESS BADGE ─────────────────────────────────────────────────────
  const readinessStyle = (() => {
    const r = (readiness || '').toUpperCase();
    if (r === 'READY') return { bg: 'bg-emerald-500/15', border: 'border-emerald-500/40', text: 'text-emerald-500', label: 'GATI' };
    if (r === 'NEEDS WORK') return { bg: 'bg-amber-500/15', border: 'border-amber-500/40', text: 'text-amber-500', label: 'KËRKON PUNË' };
    if (r === 'INCOMPLETE') return { bg: 'bg-rose-500/15', border: 'border-rose-500/40', text: 'text-rose-500', label: 'I PËRPLOTË' };
    return { bg: 'bg-slate-500/15', border: 'border-slate-500/40', text: 'text-slate-500', label: 'I PANJOHUR' };
  })();

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════

  if (!isOpen) return null;
  if (phase === 'loading-cache') return null;
  if (phase === 'generating' && !reportContent) return null;

  const showReportBanner = Boolean(reportContent.trim());
  const hasStats = score !== null || Object.keys(statsData).length > 0;

  return (
    <>
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
            {/* HEADER */}
            <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-10 h-10 bg-emerald-500/15 text-emerald-500 rounded-2xl flex items-center justify-center border border-emerald-500/30 shrink-0">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                      {title}
                    </h3>
                    {readinessStyle.label && reportContent && (
                      <span className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-wider border ${readinessStyle.bg} ${readinessStyle.border} ${readinessStyle.text}`}>
                        {readinessStyle.label}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                    {subtitle}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <div className="flex items-center bg-surface border border-main rounded-xl p-0.5 text-xs">
                  <button
                    type="button"
                    onClick={() => setFontLevelIndex((p) => Math.max(0, p - 1))}
                    disabled={fontLevelIndex <= 0}
                    className="px-2 py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-lg hover:bg-hover font-bold cursor-pointer"
                    title="Zvogëlo"
                  >
                    <ZoomOut size={13} />
                  </button>
                  <span className="px-1.5 text-[10px] font-mono font-bold text-emerald-500">
                    {activeFont.label}
                  </span>
                  <button
                    type="button"
                    onClick={() => setFontLevelIndex((p) => Math.min(FONT_LEVELS.length - 1, p + 1))}
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
                    className="p-2 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-xl transition-colors cursor-pointer disabled:opacity-40"
                    title="Fshi raportin e verifikimit"
                  >
                    {isPurging ? (
                      <Loader2 size={16} className="animate-spin text-danger-start" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
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

            {/* BANNER */}
            {showReportBanner && reportContent && (
              <div className="mt-3 p-3 sm:p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/25 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0">
                <div className="flex items-start gap-2.5 min-w-0 flex-1">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0">
                    <Calendar size={15} className="text-emerald-500" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs sm:text-sm font-bold text-text-primary">
                      {reportSource === 'fresh'
                        ? 'Raporti u gjenerua me sukses'
                        : 'Ky raport është ruajtur më parë'}
                    </p>
                    <p className="text-[11px] sm:text-xs text-text-muted mt-0.5">
                      Gjeneruar më{' '}
                      <span className="font-mono font-semibold text-text-secondary">
                        {formatAuditDate(lastBuiltAt)}
                      </span>
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={runVerification}
                  disabled={isPurging}
                  className="h-9 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-500/90 text-white font-bold text-[11px] uppercase tracking-wider transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shrink-0 shadow-sm hover-lift"
                  title="Rigjenero raportin nga e para"
                >
                  <RotateCcw size={13} />
                  <span>Rigjenero</span>
                </button>
              </div>
            )}

            {/* SCORE + STATS PANEL */}
            {reportContent && hasStats && scoreStyle && (
              <div className="mt-3 grid grid-cols-2 sm:grid-cols-5 gap-2 shrink-0">
                {score !== null && (
                  <div
                    className={`col-span-2 sm:col-span-1 relative flex items-center gap-2.5 p-2.5 rounded-xl ${scoreStyle.bg} border ${scoreStyle.border} cursor-help`}
                    onMouseEnter={() => setShowScoreTooltip(true)}
                    onMouseLeave={() => setShowScoreTooltip(false)}
                  >
                    <div className="relative w-11 h-11 shrink-0">
                      <svg className="w-11 h-11 -rotate-90" viewBox="0 0 44 44">
                        <circle
                          cx="22" cy="22" r="18"
                          stroke="currentColor" strokeWidth="3" fill="none"
                          className="text-canvas/60"
                        />
                        <circle
                          cx="22" cy="22" r="18"
                          stroke="currentColor" strokeWidth="3" fill="none"
                          strokeLinecap="round"
                          strokeDasharray={2 * Math.PI * 18}
                          strokeDashoffset={(2 * Math.PI * 18) * (1 - score / 100)}
                          className={`${scoreStyle.ring} transition-all duration-700`}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className={`text-sm font-black ${scoreStyle.text} leading-none tabular-nums`}>
                          {score}
                        </span>
                      </div>
                    </div>
                    <div className="min-w-0">
                      <p className="text-[9px] uppercase tracking-widest font-bold text-text-muted">Pikët</p>
                      <p className={`text-[11px] font-bold ${scoreStyle.text} truncate`}>
                        {scoreStyle.label}
                      </p>
                    </div>

                    <AnimatePresence>
                      {showScoreTooltip && scoreBreakdown && (
                        <motion.div
                          initial={{ opacity: 0, y: 4, scale: 0.96 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 4, scale: 0.96 }}
                          transition={{ duration: 0.12 }}
                          className="absolute top-full left-0 mt-1.5 z-30 w-[220px] p-3 bg-card border-2 border-emerald-500/40 rounded-xl shadow-2xl pointer-events-none"
                        >
                          <p className="text-[9px] font-black uppercase tracking-widest text-emerald-500 mb-2">
                            Struktura e pikëve
                          </p>
                          <div className="space-y-1.5 text-[10px]">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-text-muted">Plotësia formale</span>
                              <span className="font-black text-text-primary tabular-nums">
                                {Math.round(scoreBreakdown.formal)}%
                              </span>
                            </div>
                            <div className="h-1 rounded-full bg-canvas overflow-hidden">
                              <div
                                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                                style={{ width: `${Math.min(100, scoreBreakdown.formal)}%` }}
                              />
                            </div>

                            <div className="flex items-center justify-between gap-2 pt-1">
                              <span className="text-text-muted">Cilësia ligjore</span>
                              <span className="font-black text-text-primary tabular-nums">
                                {Math.round(scoreBreakdown.legal)}%
                              </span>
                            </div>
                            <div className="h-1 rounded-full bg-canvas overflow-hidden">
                              <div
                                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                                style={{ width: `${Math.min(100, scoreBreakdown.legal)}%` }}
                              />
                            </div>

                            <div className="flex items-center justify-between gap-2 pt-1">
                              <span className="text-text-muted">Gatishmëria</span>
                              <span className="font-black text-text-primary tabular-nums">
                                {scoreBreakdown.readiness}%
                              </span>
                            </div>
                            <div className="h-1 rounded-full bg-canvas overflow-hidden">
                              <div
                                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                                style={{ width: `${Math.min(100, scoreBreakdown.readiness)}%` }}
                              />
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {typeof statsData.articles_total === 'number' && (
                  <div className="p-2.5 rounded-xl bg-canvas/60 border border-main min-w-0">
                    <p className="text-[9px] uppercase tracking-widest font-bold text-text-muted truncate">
                      Nenet
                    </p>
                    <p className="text-sm font-black text-text-primary tabular-nums leading-tight">
                      {statsData.articles_verified || 0}
                      <span className="text-text-muted font-medium text-xs">
                        /{statsData.articles_total || 0}
                      </span>
                    </p>
                  </div>
                )}

                {typeof statsData.precedents_found === 'number' && (
                  <div className="p-2.5 rounded-xl bg-canvas/60 border border-main min-w-0">
                    <p className="text-[9px] uppercase tracking-widest font-bold text-text-muted truncate">
                      Precedentë
                    </p>
                    <p className="text-sm font-black text-text-primary tabular-nums leading-tight">
                      {statsData.precedents_found}
                    </p>
                  </div>
                )}

                {typeof statsData.formal_pct === 'number' && (
                  <div className="p-2.5 rounded-xl bg-canvas/60 border border-main min-w-0">
                    <p className="text-[9px] uppercase tracking-widest font-bold text-text-muted truncate">
                      Plotësia
                    </p>
                    <p className="text-sm font-black text-text-primary tabular-nums leading-tight">
                      {Math.round(statsData.formal_pct)}%
                    </p>
                  </div>
                )}

                {typeof statsData.legal_pct === 'number' && (
                  <div className="p-2.5 rounded-xl bg-canvas/60 border border-main min-w-0">
                    <p className="text-[9px] uppercase tracking-widest font-bold text-text-muted truncate">
                      Cilësia
                    </p>
                    <p className="text-sm font-black text-text-primary tabular-nums leading-tight">
                      {Math.round(statsData.legal_pct)}%
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* BODY */}
            <div
              className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 my-2 bg-surface/30 rounded-2xl border border-main text-text-primary select-text relative flex flex-col"
            >
              <style>{`
                .fast-draft-verify p, .fast-draft-verify li {
                  font-size: ${activeFont.base}px !important;
                  line-height: ${activeFont.line} !important;
                }
              `}</style>

              {errorMessage && (
                <div className="mb-4 p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 flex items-start gap-3 shrink-0">
                  <AlertCircle size={18} className="text-rose-500 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-xs font-bold text-rose-500 mb-1">Gabim</p>
                    <p className="text-xs text-text-secondary">{errorMessage}</p>
                  </div>
                </div>
              )}

              {!reportContent && !errorMessage && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                    <ShieldCheck size={28} />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-text-primary">
                      Nuk ka raport verifikimi
                    </h4>
                    <p className="text-xs text-text-muted max-w-lg mt-1">
                      Klikoni "Verifiko Tani" për të gjeneruar një raport të ri.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={runVerification}
                    className="mt-2 h-10 px-5 rounded-xl bg-emerald-500 hover:bg-emerald-500/90 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer shadow-md hover-lift"
                  >
                    <Sparkles size={14} />
                    <span>Verifiko Tani</span>
                  </button>
                </div>
              )}

              {reportContent && (
                <div className="fast-draft-verify markdown-content">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={reportComponents as any}
                  >
                    {linkedContent}
                  </ReactMarkdown>
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
              {reportContent && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium">
                  <Lock size={12} className="text-text-muted" />
                  <span className="hidden sm:inline">Raporti i verifikimit është ruajtur veçmas</span>
                  <span className="sm:hidden">I ruajtur</span>
                </div>
              )}

              <div className="ml-auto flex items-center gap-2">
                {/* V3.2: Butoni "Rishkruaj Dokumentin" */}
                {reportContent && (
                  <button
                    type="button"
                    onClick={() => setIsRewriteOpen(true)}
                    className="h-9 px-5 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white font-bold text-xs uppercase tracking-wider shadow-md transition-all flex items-center gap-2 cursor-pointer"
                    title="Rishkruaj dokumentin me rekomandimet"
                  >
                    <PenLine size={14} />
                    <span>Rishkruaj Dokumentin</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={handleCopy}
                  disabled={!reportContent}
                  className="h-9 px-5 rounded-xl bg-emerald-500 hover:bg-emerald-500/90 text-white font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center gap-2 disabled:opacity-40 cursor-pointer"
                >
                  {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                  <span>{copied ? 'U Kopjua!' : 'Kopjo për Dokument'}</span>
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </AnimatePresence>

      {/* V3.2: Rewrite Modal */}
      <DocumentRewriteModal
        isOpen={isRewriteOpen}
        onClose={() => setIsRewriteOpen(false)}
        caseId={caseId}
        documentId={documentId}
        documentName={documentName}
        docType={docType}
        docTypeLabel={docTypeLabel}
      />
    </>
  );
};

export default DraftVerificationModal;