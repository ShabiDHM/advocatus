// FILE: frontend/src/components/case/CaseDossierAuditModal.tsx
// PHOENIX PROTOCOL - CASE DOSSIER AUDIT MODAL V6.2.1
// V6.2.1: HEQUR "Në Fund" button — nuk nevojitet, scrollbar mjafton.
// V6.2: STATS PANEL me gjetje ✅/❌/⚠️/💡.
// V6.1.5: LAW CITATION LINK.

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2,
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, Lock, Scale, Folder,
  ShieldCheck, RotateCcw, Calendar, Sparkles, AlertTriangle, XCircle, TrendingUp,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { LawCitationLink } from '../LawCitationLink';

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

interface DerivedStats {
  countOK: number;
  countX: number;
  countWarn: number;
  countSug: number;
  readiness: string;
}

function deriveStats(content: string): DerivedStats {
  if (!content) {
    return { countOK: 0, countX: 0, countWarn: 0, countSug: 0, readiness: 'I PANJOHUR' };
  }
  const countOK = (content.match(/✅/g) || []).length;
  const countX = (content.match(/❌/g) || []).length;
  const countWarn = (content.match(/⚠️/g) || []).length;
  const countSug = (content.match(/💡/g) || []).length;

  let readiness = 'I PANJOHUR';
  if (/GATI|READY/i.test(content)) readiness = 'GATI';
  if (/KËRKON PUNË|NEEDS WORK/i.test(content)) readiness = 'KËRKON PUNË';
  if (/I PËRPLOTË|INCOMPLETE/i.test(content)) readiness = 'I PËRPLOTË';

  return { countOK, countX, countWarn, countSug, readiness };
}

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
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 },
];

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
            {text.replace(/^RAPORT\s*—\s*/, '').replace(/^RAPORT VERIFIKIMI\s*—\s*/, '')}
          </h1>
        </div>
        <p className="text-[11px] text-text-muted uppercase tracking-widest font-bold mt-2 ml-14">
          Raport Auditimi
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
// MARKDOWN → DOCX HTML
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

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Raport</title>
    <style>body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: ${WORD_BODY_COLOR}; }</style>
    </head><body>${htmlOutput.join('\n')}</body></html>`.trim();
};

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
  const reportComponents = useMemo(() => buildReportComponents(), []);

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
        console.warn('[CaseDossierAuditModal V6.2.1] Ngarkimi i raportit të ruajtur dështoi:', err);
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

  const handleCopy = async () => {
    if (!reportContent) return;

    const processed = preprocessReport(reportContent);
    const htmlContent = markdownToWordHtml(processed);
    const plainContent = processed;

    try {
      if (navigator.clipboard && window.ClipboardItem) {
        const clipboardItem = new ClipboardItem({
          'text/html': new Blob([htmlContent], { type: 'text/html' }),
          'text/plain': new Blob([plainContent], { type: 'text/plain' }),
        });
        await navigator.clipboard.write([clipboardItem]);
      } else {
        throw new Error();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      await navigator.clipboard.writeText(plainContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen) return null;

  const showReportBanner = Boolean(reportContent.trim())
    && (reportSource === 'cache' || reportSource === 'saved');

  const processedContent = preprocessReport(reportContent);
  const linkedContent = processedContent ? autoLinkLegalCitations(processedContent) : '';

  const hasDerivedStats = derivedStats.countOK + derivedStats.countX + derivedStats.countWarn > 0;

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
          {/* HEADER */}
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-emerald-500/15 text-emerald-500 rounded-2xl flex items-center justify-center border border-emerald-500/30 shrink-0">
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
                <span className="px-1.5 text-[10px] font-mono font-bold text-emerald-500">
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
                  className="p-2 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-xl transition-colors cursor-pointer disabled:opacity-40"
                  title={isSingleDoc ? "Fshi raportin e këtij dokumenti" : "Fshi raportin e rastit"}
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

          {/* BANNER */}
          {showReportBanner && (
            <div className="mt-3 p-3 sm:p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/25 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0">
              <div className="flex items-start gap-2.5 min-w-0 flex-1">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0">
                  <Calendar size={15} className="text-emerald-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs sm:text-sm font-bold text-text-primary">
                    {reportSource === 'cache'
                      ? 'Ky raport është shfaqur nga memoria e serverit'
                      : 'Ky raport është ruajtur më parë'}
                  </p>
                  <p className="text-[11px] sm:text-xs text-text-muted mt-0.5">
                    {reportSource === 'cache'
                      ? 'Klikoni "Rigjenero" për ta krijuar nga e para'
                      : <>Gjeneruar më <span className="font-mono font-semibold text-text-secondary">{formatAuditDate(lastAuditedAt)}</span></>}
                  </p>
                </div>
              </div>
              {onRegenerate && (
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={isPurging}
                  className="h-9 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-500/90 text-white font-bold text-[11px] uppercase tracking-wider transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shrink-0 shadow-sm hover-lift"
                  title="Rigjenero nga e para"
                >
                  <RotateCcw size={13} />
                  <span>Rigjenero</span>
                </button>
              )}
            </div>
          )}

          {/* STATS PANEL */}
          {reportContent && hasDerivedStats && (
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 shrink-0">
              <div className="p-2.5 rounded-xl bg-emerald-500/5 border border-emerald-500/25 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <CheckCircle2 size={11} className="text-emerald-500 shrink-0" />
                  <p className="text-[9px] uppercase tracking-widest font-bold text-emerald-500/80 truncate">
                    Gjetje OK
                  </p>
                </div>
                <p className="text-sm font-black text-emerald-500 tabular-nums leading-tight">
                  {derivedStats.countOK}
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-rose-500/5 border border-rose-500/25 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <XCircle size={11} className="text-rose-500 shrink-0" />
                  <p className="text-[9px] uppercase tracking-widest font-bold text-rose-500/80 truncate">
                    Gabime
                  </p>
                </div>
                <p className="text-sm font-black text-rose-500 tabular-nums leading-tight">
                  {derivedStats.countX}
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-amber-500/5 border border-amber-500/25 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <AlertTriangle size={11} className="text-amber-500 shrink-0" />
                  <p className="text-[9px] uppercase tracking-widest font-bold text-amber-500/80 truncate">
                    Kujdes
                  </p>
                </div>
                <p className="text-sm font-black text-amber-500 tabular-nums leading-tight">
                  {derivedStats.countWarn}
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-sky-500/5 border border-sky-500/25 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <TrendingUp size={11} className="text-sky-500 shrink-0" />
                  <p className="text-[9px] uppercase tracking-widest text-sky-500/80 truncate">
                    Sugjerime
                  </p>
                </div>
                <p className="text-sm font-black text-sky-500 tabular-nums leading-tight">
                  {derivedStats.countSug}
                </p>
              </div>
            </div>
          )}

          {/* BODY */}
          <div
            className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 my-2 bg-surface/30 rounded-2xl border border-main text-text-primary select-text relative flex flex-col"
          >
            <style>{`
              .fast-case-dossier-audit p, .fast-case-dossier-audit li {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
            `}</style>

            {isLoadingFromServer ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <Loader2 className="w-10 h-10 animate-spin text-emerald-500" />
                <p className="text-sm text-text-muted">Duke lexuar raportin e ruajtur...</p>
              </div>
            ) : !reportContent ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
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
                    className="mt-2 h-10 px-5 rounded-xl bg-emerald-500 hover:bg-emerald-500/90 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer shadow-md hover-lift"
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

          {/* FOOTER */}
          <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
            {reportContent && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium">
                <Lock size={12} className="text-text-muted" />
                <span className="hidden sm:inline">
                  {isSingleDoc
                    ? 'Raporti i dokumentit është ruajtur veçmas'
                    : 'Raporti i rastit është ruajtur'}
                </span>
                <span className="sm:hidden">I ruajtur</span>
              </div>
            )}

            <div className="ml-auto flex items-center gap-2">
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
  );
};

export default CaseDossierAuditModal;