// FILE: src/components/case/DraftVerificationModal.tsx
// PHOENIX PROTOCOL - DRAFT VERIFICATION MODAL V3.10
// V3.10: REWRITE REMOVED — Hequr butoni "Rishkruaj Dokumentin", importi
//        DocumentRewriteModal, importi PenLine, state isRewriteOpen dhe
//        të gjitha referencat. Escape handler tani mbyll gjithmonë modalin.
// V3.9: PROGRESS FIX —
//       - Progress tani llogaritet me weighted formula (70% started + 30% completed)
//         duke marrë parasysh që 6 seksionet xhirojnë PARALEL.
//       - Cleanup on unmount: emitProgress(false, 0, '') për të pastruar state.
//       - U hoq referenca e mbetur formatAuditDate/ALBANIAN_MONTHS.
// V3.8: COMBINED HEADER — Header + Banner + Stats bashkuar.
// V3.7: COLOR UNIFIED — primary-start.

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2, Loader2, Maximize2, Minimize2,
  Trash2, ZoomIn, ZoomOut, Lock, ShieldCheck,
  RotateCcw, Calendar, Sparkles, AlertCircle,
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
import { PrecedentCitationLink } from '../PrecedentCitationLink';

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

const formatShortDate = (isoDate?: string | Date | null): string => {
  if (!isoDate) return '';
  try {
    const d = typeof isoDate === 'string' ? new Date(isoDate) : isoDate;
    if (isNaN(d.getTime())) return '';
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear().toString().slice(-2);
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${day}.${month}.${year}, ${hours}:${minutes}`;
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
  high: { ring: 'stroke-emerald-500', text: 'text-emerald-500', bg: 'bg-emerald-500/5', border: 'border-emerald-500/25', label: 'Shkëlqyeshëm' },
  mid:  { ring: 'stroke-amber-500',   text: 'text-amber-500',   bg: 'bg-amber-500/5',   border: 'border-amber-500/25',   label: 'Mirë' },
  low:  { ring: 'stroke-rose-500',    text: 'text-rose-500',    bg: 'bg-rose-500/5',    border: 'border-rose-500/25',    label: 'Dobët' },
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
// MARKDOWN → PLAIN TEXT
// ───────────────────────────────────────────────────────────────────────────

const stripInlineMarkdown = (text: string): string => {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
};

const markdownToPlainText = (markdown: string): string => {
  if (!markdown) return '';
  const lines = markdown.split(/\r?\n/);
  const out: string[] = [];
  let consecutiveBlanks = 0;

  const pushBlank = () => {
    if (consecutiveBlanks < 1) {
      out.push('');
      consecutiveBlanks++;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { pushBlank(); continue; }
    consecutiveBlanks = 0;

    if (/^(---|---|\*\*\*|___)$/.test(line)) { out.push('─'.repeat(60)); continue; }

    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      const lvl = h[1].length;
      const text = stripInlineMarkdown(h[2]).trim();
      if (lvl === 1) {
        out.push(''); out.push(text.toUpperCase());
        out.push('═'.repeat(Math.min(60, Math.max(20, text.length))));
      } else if (lvl === 2) {
        out.push(''); out.push(text.toUpperCase());
        out.push('─'.repeat(Math.min(60, Math.max(20, text.length))));
      } else if (lvl === 3) {
        out.push(''); out.push(`◆ ${text}`);
      } else {
        out.push(''); out.push(`▸ ${text}`);
      }
      continue;
    }

    if (line.startsWith('>')) {
      out.push(`    "${stripInlineMarkdown(line.replace(/^>\s?/, ''))}"`);
      continue;
    }

    const bullet = line.match(/^([•\-\*])\s+(.+)$/);
    if (bullet) { out.push(`  • ${stripInlineMarkdown(bullet[2])}`); continue; }

    const num = line.match(/^(\d+)\.\s+(.+)$/);
    if (num) { out.push(`  ${num[1]}. ${stripInlineMarkdown(num[2])}`); continue; }

    out.push(stripInlineMarkdown(line));
  }

  while (out.length > 0 && out[0] === '') out.shift();
  while (out.length > 0 && out[out.length - 1] === '') out.pop();
  return out.join('\n');
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
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, `<code style="background-color: ${WORD_CODE_BG}; padding: 2px 4px; font-family: Consolas, monospace; font-size: 10pt;">$1</code>`);
  };

  const flushList = () => {
    if (inList) { htmlOutput.push(inList === 'ul' ? '</ul>' : '</ol>'); inList = null; }
  };

  const flushBlockquote = () => {
    if (inBlockquote) {
      htmlOutput.push(`<blockquote style="border-left: 4px solid ${WORD_BLOCKQUOTE_BORDER}; margin: 10px 0; padding: 8px 16px; background-color: ${WORD_BLOCKQUOTE_BG}; color: ${WORD_BLOCKQUOTE_TEXT}; font-style: italic; font-family: Calibri, Arial, sans-serif;">${blockquoteLines.map(formatInline).join('<br>')}</blockquote>`);
      blockquoteLines = []; inBlockquote = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

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

    if (line.startsWith('>')) { flushList(); inBlockquote = true; blockquoteLines.push(line.replace(/^>\s?/, '')); continue; }
    else if (inBlockquote) { flushBlockquote(); }

    const bulletMatch = line.match(/^([•\-\*])\s+(.+)$/);
    if (bulletMatch) {
      if (inList !== 'ul') { flushList(); htmlOutput.push('<ul style="margin: 6px 0 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">'); inList = 'ul'; }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: ${WORD_BODY_COLOR}; font-size: 11pt;">${formatInline(bulletMatch[2])}</li>`);
      continue;
    }

    const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      if (inList !== 'ol') { flushList(); htmlOutput.push('<ol style="margin: 6px 6px 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">'); inList = 'ol'; }
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
      <div className="mt-2 mb-4 sm:mb-6 pb-4 sm:pb-5 border-b-2 border-primary-start/30">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-2xl bg-primary-start/15 border border-primary-start/30 flex items-center justify-center shrink-0">
            <ShieldCheck size={18} className="text-primary-start sm:hidden" />
            <ShieldCheck size={22} className="text-primary-start hidden sm:block" />
          </div>
          <h1 className="text-base sm:text-2xl font-black text-text-primary tracking-tight">
            {text.replace(/^RAPORT VERIFIKIMI\s*—\s*/, '')}
          </h1>
        </div>
        <p className="text-[10px] sm:text-[11px] text-text-muted uppercase tracking-widest font-bold mt-2 ml-12 sm:ml-14">
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
        <h2 className="flex items-center gap-2 sm:gap-3 mt-6 sm:mt-8 mb-3 sm:mb-4 pb-2 sm:pb-3 border-b border-main">
          <span className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-primary-start text-white flex items-center justify-center font-black text-xs sm:text-sm shrink-0 shadow-sm">
            {match[1]}
          </span>
          <span className="text-sm sm:text-lg font-black text-text-primary tracking-tight uppercase">{match[2]}</span>
        </h2>
      );
    }
    return (
      <h2 className="text-sm sm:text-lg font-black text-text-primary mt-6 sm:mt-8 mb-3 sm:mb-4 pb-2 sm:pb-3 border-b border-main uppercase tracking-tight">
        {children}
      </h2>
    );
  },

  h3: ({ children }: any) => {
    const text = String(children);
    const match = text.match(/^([A-Z])\.\s+(.+)$/);
    if (match) {
      return (
        <h3 className="flex items-center gap-2 sm:gap-2.5 mt-4 sm:mt-5 mb-2.5 sm:mb-3">
          <span className="w-1 h-4 sm:h-5 rounded-full bg-primary-start shrink-0" />
          <span className="text-[13px] sm:text-base font-bold text-text-primary">
            <span className="text-primary-start mr-1">{match[1]}.</span>{match[2]}
          </span>
        </h3>
      );
    }
    return (
      <h3 className="flex items-center gap-2 sm:gap-2.5 mt-4 sm:mt-5 mb-2.5 sm:mb-3">
        <span className="w-1 h-4 sm:h-5 rounded-full bg-primary-start shrink-0" />
        <span className="text-[13px] sm:text-base font-bold text-text-primary">{children}</span>
      </h3>
    );
  },

  h4: ({ children }: any) => (
    <h4 className="text-[13px] sm:text-sm font-bold text-text-primary mt-3 sm:mt-4 mb-2 pl-3 border-l-2 border-primary-start/40">{children}</h4>
  ),

  p: ({ children }: any) => (
    <p className="text-[13px] sm:text-sm leading-relaxed text-text-primary mb-2.5 sm:mb-3">{children}</p>
  ),

  ul: ({ children }: any) => (<ul className="list-none pl-0 mb-2.5 sm:mb-3 space-y-1.5">{children}</ul>),

  ol: ({ children }: any) => (
    <ol className="list-decimal pl-5 sm:pl-6 mb-2.5 sm:mb-3 space-y-1.5 text-[13px] sm:text-sm text-text-primary">{children}</ol>
  ),

  li: ({ children }: any) => {
    const firstText = Array.isArray(children) ? String(children[0] || '') : String(children || '');
    const trimmed = firstText.trim();

    if (trimmed.startsWith('✅')) {
      return (
        <li className="flex items-start gap-2 p-2 sm:p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-[13px] sm:text-sm">
          <span className="text-emerald-500 font-bold shrink-0 leading-relaxed">✓</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children) ? [String(children[0]).replace('✅', '').trim(), ...children.slice(1)] : String(children).replace('✅', '').trim()}
          </span>
        </li>
      );
    }

    if (trimmed.startsWith('❌')) {
      return (
        <li className="flex items-start gap-2 p-2 sm:p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-[13px] sm:text-sm">
          <span className="text-rose-500 font-bold shrink-0 leading-relaxed">✗</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children) ? [String(children[0]).replace('❌', '').trim(), ...children.slice(1)] : String(children).replace('❌', '').trim()}
          </span>
        </li>
      );
    }

    if (trimmed.startsWith('⚠️')) {
      return (
        <li className="flex items-start gap-2 p-2 sm:p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 text-[13px] sm:text-sm">
          <span className="text-amber-500 font-bold shrink-0 leading-relaxed">!</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children) ? [String(children[0]).replace('⚠️', '').trim(), ...children.slice(1)] : String(children).replace('⚠️', '').trim()}
          </span>
        </li>
      );
    }

    if (trimmed.startsWith('💡')) {
      return (
        <li className="flex items-start gap-2 p-2 sm:p-2.5 rounded-lg bg-sky-500/5 border border-sky-500/20 text-[13px] sm:text-sm">
          <span className="text-sky-500 font-bold shrink-0 leading-relaxed">?</span>
          <span className="flex-1 leading-relaxed text-text-primary">
            {Array.isArray(children) ? [String(children[0]).replace('💡', '').trim(), ...children.slice(1)] : String(children).replace('💡', '').trim()}
          </span>
        </li>
      );
    }

    return (
      <li className="flex items-start gap-2 sm:gap-2.5 pl-1 text-[13px] sm:text-sm leading-relaxed text-text-primary">
        <span className="w-1.5 h-1.5 rounded-full bg-primary-start/60 mt-2 shrink-0" />
        <span className="flex-1">{children}</span>
      </li>
    );
  },

  strong: ({ children }: any) => (<strong className="font-bold text-text-primary">{children}</strong>),
  em: ({ children }: any) => (<em className="italic text-text-secondary">{children}</em>),

  code: ({ children }: any) => (
    <code className="px-1.5 py-0.5 rounded bg-canvas border border-main font-mono text-[10px] sm:text-[11px] text-primary-start font-semibold">{children}</code>
  ),

  hr: () => (
    <div className="my-5 sm:my-7 flex items-center justify-center">
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary-start/40 to-transparent" />
      <div className="mx-3 w-1.5 h-1.5 rounded-full bg-primary-start/60" />
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary-start/40 to-transparent" />
    </div>
  ),

  blockquote: ({ children }: any) => (
    <blockquote className="my-3 sm:my-4 pl-3 sm:pl-4 py-2.5 sm:py-3 pr-3 border-l-4 border-primary-start/50 bg-primary-start/5 rounded-r-lg">
      <div className="text-[13px] sm:text-sm italic text-text-secondary leading-relaxed">{children}</div>
    </blockquote>
  ),

  a: ({ children, href }: any) => {
    const hrefStr = typeof href === 'string' ? href : '';
    if (hrefStr.includes('/laws/article')) {
      return (<LawCitationLink lawTitle="" articleNum="" fullMatch={String(children)} targetUrl={hrefStr} />);
    }
    if (hrefStr.includes('/laws/search')) {
      return (<PrecedentCitationLink caseNumber={String(children)} />);
    }
    return (
      <a href={hrefStr} className="text-primary-start hover:text-primary-end underline underline-offset-2 transition-colors font-medium" target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  },

  table: ({ children }: any) => (
    <div className="overflow-x-auto my-3 sm:my-4 rounded-xl border border-main">
      <table className="min-w-full text-xs">{children}</table>
    </div>
  ),

  thead: ({ children }: any) => (<thead className="bg-canvas/60">{children}</thead>),

  th: ({ children }: any) => (
    <th className="px-2 sm:px-3 py-1.5 sm:py-2 text-left font-bold text-text-primary border-b border-main text-[11px] sm:text-xs">{children}</th>
  ),

  td: ({ children }: any) => (
    <td className="px-2 sm:px-3 py-1.5 sm:py-2 border-b border-main/60 text-text-primary text-[11px] sm:text-xs">{children}</td>
  ),
});

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

  const emitProgress = useCallback((isGenerating: boolean, percent: number, label: string) => {
    if (onProgressChange) onProgressChange({ isGenerating, percent, label });
  }, [onProgressChange]);

  // ═══════════════════════════════════════════════════════════════════════
  // V3.9 FIX: Run verification me progress të saktë
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

    // V3.9: Ndajmë totalin në 6 seksione, por llogaritim weighted
    const total = 6;
    let started = 0;      // Seksione që kanë filluar
    let completed = 0;    // Seksione që kanë përfunduar

    // V3.9: Formula — 70% e progresit bazuar në "started", 30% në "completed".
    // Arsyeja: 6 seksionet xhirojnë PARALEL. Nëse llogaritim vetëm "completed",
    // progresi mbetet 0% derisa të përfundojë i pari (ndodh vonë).
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
      console.error('[DraftVerificationModal V3.10] Gabim SSE:', err);
      setErrorMessage(err?.message || 'Gabim gjatë verifikimit.');
      setPhase('error');
      emitProgress(false, 0, '');
    }
  }, [caseId, documentId, docType, emitProgress]);

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
        console.warn('[DraftVerificationModal V3.10] Leximi i ruajtur dështoi:', err);
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

  // ═══════════════════════════════════════════════════════════════════════
  // V3.9 FIX: Cleanup kur komponenti UNMOUNTOHET (hequr nga parent).
  // Kjo parandalon state stale në CaseViewPage (isVerifyGenerating=true
  // mbetet i bllokuar nëse modali hiqet nga JSX).
  // ═══════════════════════════════════════════════════════════════════════
  useEffect(() => {
    return () => {
      // Reset parent progress state kur modali zhduket
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
      console.error('[DraftVerificationModal V3.10] Fshirja dështoi:', err);
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

  const readinessStyle = (() => {
    const r = (readiness || '').toUpperCase();
    if (r === 'READY') return { bg: 'bg-emerald-500/15', border: 'border-emerald-500/40', text: 'text-emerald-500', label: 'GATI' };
    if (r === 'NEEDS WORK') return { bg: 'bg-amber-500/15', border: 'border-amber-500/40', text: 'text-amber-500', label: 'KËRKON PUNË' };
    if (r === 'INCOMPLETE') return { bg: 'bg-rose-500/15', border: 'border-rose-500/40', text: 'text-rose-500', label: 'I PËRPLOTË' };
    return { bg: 'bg-slate-500/15', border: 'border-slate-500/40', text: 'text-slate-500', label: 'I PANJOHUR' };
  })();

  if (!isOpen) return null;
  if (phase === 'loading-cache') return null;
  if (phase === 'generating' && !reportContent) return null;

  const hasStats = score !== null || Object.keys(statsData).length > 0;
  const showStatsRow = Boolean(reportContent) && hasStats;

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
              : 'h-[96vh] sm:h-[92vh] max-w-5xl max-h-[880px] rounded-2xl sm:rounded-3xl border border-main'
          } p-2.5 sm:p-4 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
        >
          {/* COMBINED HEADER */}
          <div className="shrink-0 border-b border-main pb-2 sm:pb-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-primary-start/15 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/30 shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                    <h3 className="text-xs sm:text-sm font-black text-text-primary uppercase tracking-tight truncate">{title}</h3>
                    {readinessStyle.label && reportContent && (
                      <span className={`px-1.5 sm:px-2 py-0.5 rounded-md text-[8px] sm:text-[9px] font-black uppercase tracking-wider border ${readinessStyle.bg} ${readinessStyle.border} ${readinessStyle.text}`}>
                        {readinessStyle.label}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] sm:text-[11px] text-text-muted font-medium truncate mt-0.5 font-mono">{subtitle}</p>
                </div>
              </div>

              <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
                <div className="hidden sm:flex items-center bg-surface border border-main rounded-lg p-0.5">
                  <button type="button" onClick={() => setFontLevelIndex((p) => Math.max(0, p - 1))} disabled={fontLevelIndex <= 0}
                    className="px-1.5 py-0.5 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-md hover:bg-hover cursor-pointer" title="Zvogëlo">
                    <ZoomOut size={12} />
                  </button>
                  <span className="px-1 text-[10px] font-mono font-bold text-primary-start min-w-[28px] text-center">{activeFont.label}</span>
                  <button type="button" onClick={() => setFontLevelIndex((p) => Math.min(FONT_LEVELS.length - 1, p + 1))} disabled={fontLevelIndex >= FONT_LEVELS.length - 1}
                    className="px-1.5 py-0.5 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-md hover:bg-hover cursor-pointer" title="Zmadho">
                    <ZoomIn size={12} />
                  </button>
                </div>

                {reportContent && (
                  <button type="button" onClick={handleClearContent} disabled={isPurging}
                    className="p-1.5 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-lg transition-colors cursor-pointer disabled:opacity-40"
                    title="Fshi raportin">
                    {isPurging ? <Loader2 size={14} className="animate-spin text-danger-start" /> : <Trash2 size={14} />}
                  </button>
                )}

                <button type="button" onClick={() => setIsFullscreen(!isFullscreen)}
                  className="hidden sm:flex p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-lg transition-colors cursor-pointer"
                  title={isFullscreen ? 'Zvogëlo' : 'Zmadho'}>
                  {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>

                <button type="button" onClick={onClose}
                  className="p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-lg transition-colors cursor-pointer" title="Mbyll">
                  <X size={16} />
                </button>
              </div>
            </div>

            {showStatsRow && scoreStyle && (
              <div className="mt-2 flex items-center gap-1.5 sm:gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <div className="flex items-center gap-1 text-[10px] sm:text-[11px] text-text-muted font-mono shrink-0 pr-1.5 sm:pr-2 border-r border-main">
                  <Calendar size={11} className="text-primary-start shrink-0" />
                  <span className="hidden sm:inline">{reportSource === 'fresh' ? 'Gjeneruar' : 'Ruajtur'}</span>
                  <span className="whitespace-nowrap">{formatShortDate(lastBuiltAt)}</span>
                </div>

                {score !== null && (
                  <div
                    className={`relative flex items-center gap-1.5 px-2 py-1 rounded-lg ${scoreStyle.bg} border ${scoreStyle.border} cursor-help shrink-0`}
                    onMouseEnter={() => setShowScoreTooltip(true)}
                    onMouseLeave={() => setShowScoreTooltip(false)}
                  >
                    <div className="relative w-6 h-6 shrink-0">
                      <svg className="w-6 h-6 -rotate-90" viewBox="0 0 44 44">
                        <circle cx="22" cy="22" r="18" stroke="currentColor" strokeWidth="5" fill="none" className="text-canvas/60" />
                        <circle cx="22" cy="22" r="18" stroke="currentColor" strokeWidth="5" fill="none" strokeLinecap="round"
                          strokeDasharray={2 * Math.PI * 18} strokeDashoffset={(2 * Math.PI * 18) * (1 - score / 100)}
                          className={`${scoreStyle.ring} transition-all duration-700`} />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className={`text-[9px] font-black ${scoreStyle.text} leading-none tabular-nums`}>{score}</span>
                      </div>
                    </div>
                    <span className={`text-[10px] font-bold ${scoreStyle.text} whitespace-nowrap hidden sm:inline`}>{scoreStyle.label}</span>

                    <AnimatePresence>
                      {showScoreTooltip && scoreBreakdown && (
                        <motion.div
                          initial={{ opacity: 0, y: 4, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 4, scale: 0.96 }} transition={{ duration: 0.12 }}
                          className="absolute top-full left-0 mt-1.5 z-30 w-[220px] p-3 bg-card border-2 border-primary-start/40 rounded-xl shadow-2xl pointer-events-none">
                          <p className="text-[9px] font-black uppercase tracking-widest text-primary-start mb-2">Struktura e pikëve</p>
                          <div className="space-y-1.5 text-[10px]">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-text-muted">Plotësia formale</span>
                              <span className="font-black text-text-primary tabular-nums">{Math.round(scoreBreakdown.formal)}%</span>
                            </div>
                            <div className="h-1 rounded-full bg-canvas overflow-hidden">
                              <div className="h-full bg-primary-start rounded-full transition-all duration-500" style={{ width: `${Math.min(100, scoreBreakdown.formal)}%` }} />
                            </div>
                            <div className="flex items-center justify-between gap-2 pt-1">
                              <span className="text-text-muted">Cilësia ligjore</span>
                              <span className="font-black text-text-primary tabular-nums">{Math.round(scoreBreakdown.legal)}%</span>
                            </div>
                            <div className="h-1 rounded-full bg-canvas overflow-hidden">
                              <div className="h-full bg-primary-start rounded-full transition-all duration-500" style={{ width: `${Math.min(100, scoreBreakdown.legal)}%` }} />
                            </div>
                            <div className="flex items-center justify-between gap-2 pt-1">
                              <span className="text-text-muted">Gatishmëria</span>
                              <span className="font-black text-text-primary tabular-nums">{scoreBreakdown.readiness}%</span>
                            </div>
                            <div className="h-1 rounded-full bg-canvas overflow-hidden">
                              <div className="h-full bg-primary-start rounded-full transition-all duration-500" style={{ width: `${Math.min(100, scoreBreakdown.readiness)}%` }} />
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {typeof statsData.articles_total === 'number' && (
                  <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-canvas/60 border border-main shrink-0">
                    <span className="text-[8px] uppercase tracking-widest font-bold text-text-muted whitespace-nowrap hidden sm:inline">Nenet</span>
                    <span className="text-[10px] font-black text-text-primary tabular-nums">
                      {statsData.articles_verified || 0}<span className="text-text-muted font-medium">/{statsData.articles_total || 0}</span>
                    </span>
                  </div>
                )}

                {typeof statsData.precedents_found === 'number' && (
                  <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-canvas/60 border border-main shrink-0">
                    <span className="text-[8px] uppercase tracking-widest font-bold text-text-muted whitespace-nowrap hidden sm:inline">Prec.</span>
                    <span className="text-[10px] font-black text-text-primary tabular-nums">{statsData.precedents_found}</span>
                  </div>
                )}

                {typeof statsData.formal_pct === 'number' && (
                  <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-canvas/60 border border-main shrink-0">
                    <span className="text-[8px] uppercase tracking-widest font-bold text-text-muted whitespace-nowrap hidden sm:inline">Plotësia</span>
                    <span className="text-[10px] font-black text-text-primary tabular-nums">{Math.round(statsData.formal_pct)}%</span>
                  </div>
                )}

                {typeof statsData.legal_pct === 'number' && (
                  <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-canvas/60 border border-main shrink-0">
                    <span className="text-[8px] uppercase tracking-widest font-bold text-text-muted whitespace-nowrap hidden sm:inline">Cilësia</span>
                    <span className="text-[10px] font-black text-text-primary tabular-nums">{Math.round(statsData.legal_pct)}%</span>
                  </div>
                )}

                <button type="button" onClick={runVerification} disabled={isPurging}
                  className="ml-auto h-6 px-2 sm:px-2.5 rounded-lg bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[10px] uppercase tracking-wider transition-all flex items-center gap-1 disabled:opacity-50 cursor-pointer shrink-0 shadow-sm"
                  title="Rigjenero">
                  <RotateCcw size={10} />
                  <span className="hidden sm:inline">Rigjenero</span>
                </button>
              </div>
            )}
          </div>

          {/* BODY */}
          <div className="flex-1 overflow-y-auto custom-finance-scroll p-2.5 sm:p-4 my-2 bg-surface/30 rounded-xl sm:rounded-2xl border border-main text-text-primary select-text relative flex flex-col">
            <style>{`
              .fast-draft-verify p, .fast-draft-verify li {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
            `}</style>

            {errorMessage && (
              <div className="mb-4 p-3 sm:p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 flex items-start gap-3 shrink-0">
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

          {/* FOOTER */}
          <div className="flex flex-row items-center justify-between pt-2 border-t border-main gap-1.5 sm:gap-3 shrink-0">
            {reportContent && (
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-main text-text-muted text-[10px] sm:text-xs font-medium shrink-0">
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