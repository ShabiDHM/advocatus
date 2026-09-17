// FILE: frontend/src/components/case/CaseDossierAuditModal.tsx
// PHOENIX PROTOCOL - CASE DOSSIER AUDIT MODAL V2.5
// V2.5: document_ids prop — analiza e një dokumenti ose fashikulli.

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2,
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown, Sparkles, Lock, Scale, Folder,
  FileSearch, GitBranch, FileText, CheckCircle
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface CaseDossierAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseName?: string;
  clientName?: string;
  documentCount?: number;
  documentIds?: string[];
  documentNames?: string[];
}

type PhaseKey = 'extraction' | 'cross_reference' | 'synthesis' | 'idle';

interface PhaseInfo {
  key: PhaseKey;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const PHASES: PhaseInfo[] = [
  {
    key: 'extraction',
    label: 'Ekstraktimi',
    description: 'Duke lexuar dhe strukturuar dokumentet',
    icon: <FileSearch size={14} />,
  },
  {
    key: 'cross_reference',
    label: 'Lidhjet',
    description: 'Duke gjetur referencat midis shkresave',
    icon: <GitBranch size={14} />,
  },
  {
    key: 'synthesis',
    label: 'Sinteza',
    description: 'Duke hartuar doktrinën përfundimtare',
    icon: <FileText size={14} />,
  },
];

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
      .replace(/`([^`]+)`/g, '<code style="background-color: #f1f5f9; padding: 2px 4px; font-family: Consolas, monospace; font-size: 10pt;">$1</code>');
  };

  const flushList = () => {
    if (inList) {
      htmlOutput.push(inList === 'ul' ? '</ul>' : '</ol>');
      inList = null;
    }
  };

  const flushBlockquote = () => {
    if (inBlockquote) {
      htmlOutput.push(`<blockquote style="border-left: 4px solid #2563eb; margin: 10px 0; padding: 8px 16px; background-color: #f8fafc; color: #334155; font-style: italic; font-family: Calibri, Arial, sans-serif;">${blockquoteLines.map(formatInline).join('<br>')}</blockquote>`);
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
      htmlOutput.push('<hr style="border: 0; border-top: 1px solid #cbd5e1; margin: 16px 0;" />');
      continue;
    }

    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushList();
      flushBlockquote();
      const level = hMatch[1].length;
      const text = formatInline(hMatch[2]);
      const fontSize = level === 1 ? '16pt' : level === 2 ? '14pt' : '12pt';
      htmlOutput.push(`<h${level} style="font-size: ${fontSize}; font-family: Calibri, Arial, sans-serif; font-weight: bold; color: #0f172a; margin-top: 14px; margin-bottom: 6px;">${text}</h${level}>`);
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
      htmlOutput.push(`<li style="margin-bottom: 4px; color: #1e293b; font-size: 11pt;">${formatInline(bulletMatch[2])}</li>`);
      continue;
    }

    const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      if (inList !== 'ol') {
        flushList();
        htmlOutput.push('<ol style="margin: 6px 0 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">');
        inList = 'ol';
      }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: #1e293b; font-size: 11pt;">${formatInline(numMatch[2])}</li>`);
      continue;
    }

    flushList();
    if (line.length === 0) continue;

    htmlOutput.push(`<p style="margin: 6px 0; font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1e293b;">${formatInline(line)}</p>`);
  }

  flushList();
  flushBlockquote();

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Doktrina e Fashikullit</title>
      <style>
        body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1e293b; }
      </style>
    </head>
    <body>
      ${htmlOutput.join('\n')}
    </body>
    </html>
  `.trim();
};

const TYPEWRITER_DURATION_MS = 2000;
const TYPEWRITER_TICKS = 50;

const applyTypewriter = async (
  fullText: string,
  onUpdate: (s: string) => void,
  isCancelled: () => boolean,
): Promise<void> => {
  const totalChars = fullText.length;
  if (totalChars === 0) return;

  const chunkSize = Math.max(1, Math.ceil(totalChars / TYPEWRITER_TICKS));
  const intervalMs = TYPEWRITER_DURATION_MS / TYPEWRITER_TICKS;

  for (let i = 1; i <= TYPEWRITER_TICKS; i++) {
    if (isCancelled()) return;
    const end = Math.min(i * chunkSize, totalChars);
    onUpdate(fullText.slice(0, end));
    if (end >= totalChars) break;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  onUpdate(fullText);
};

export const CaseDossierAuditModal: React.FC<CaseDossierAuditModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseName = 'Fashikulli i Lëndës',
  clientName = 'Klienti',
  documentCount = 0,
  documentIds,
  documentNames,
}) => {
  const [reportContent, setReportContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);

  const [currentPhase, setCurrentPhase] = useState<PhaseKey>('idle');
  const [phaseLabel, setPhaseLabel] = useState<string>('');
  const [progressDetail, setProgressDetail] = useState<string>('');
  const [completedPhases, setCompletedPhases] = useState<PhaseKey[]>([]);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  const hasReceivedChunksRef = useRef<boolean>(false);
  const accumulatedRef = useRef<string>('');
  const currentSectionTitleRef = useRef<string>('');
  const generationIdRef = useRef<number>(0);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(1);
  const activeFont = FONT_LEVELS[fontLevelIndex];
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  const isSingleDoc = Boolean(documentIds && documentIds.length > 0);
  const singleDocName = isSingleDoc && documentNames && documentNames.length > 0
    ? documentNames[0]
    : null;

  const reportTitle = isSingleDoc
    ? (singleDocName ? `Doktrina e Dokumentit` : 'Doktrina e Dokumentit')
    : 'Doktrina e Fashikullit';

  const headerSubtitle = isSingleDoc
    ? `${singleDocName || 'Dokument i vetëm'} • ${clientName}`
    : `${caseName} • ${clientName} • ${documentCount} shkresa`;

  const actionButtonLabel = isSingleDoc
    ? 'Fillo Analizën e Dokumentit'
    : 'Fillo Doktrinën e Fashikullit';

  const emptyStateDescription = isSingleDoc
    ? 'Merrni një opinion të prerë strategjik mbi këtë dokument të vetëm. Analiza strukturohet në 6 seksione me streaming real-time.'
    : `Merrni një opinion të prerë strategjik mbi historikun e plotë të këtij fashikulli me ${documentCount} shkresa — çfarë ka ndodhur, kontradiktat, shkeljet, pozicioni ligjor dhe hapi i ardhshëm konkret.`;

  useEffect(() => {
    if (isOpen && caseId) {
      setIsLoading(false);
      apiService.getCaseDetails(caseId)
        .then((details: any) => {
          const savedAudit = details?.latest_dossier_analysis || '';
          if (savedAudit && typeof savedAudit === 'string' && savedAudit.trim().length > 50) {
            setReportContent(savedAudit);
          } else {
            setReportContent('');
          }
        })
        .catch(() => {
          setReportContent('');
        });
    }
  }, [isOpen, caseId]);

  useEffect(() => {
    if (isOpen) {
      setCurrentPhase('idle');
      setPhaseLabel('');
      setProgressDetail('');
      setCompletedPhases([]);
      hasReceivedChunksRef.current = false;
      accumulatedRef.current = '';
      currentSectionTitleRef.current = '';
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isUserScrolledUpRef.current && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [reportContent, isLoading]);

  const handleGenerateAudit = useCallback(async () => {
    if (!caseId || isLoading || isPurging || isSaving) return;

    const generationId = ++generationIdRef.current;
    const isCancelled = () => generationIdRef.current !== generationId;

    setIsLoading(true);
    setReportContent('');
    setCurrentPhase('extraction');
    setPhaseLabel('Fillo...');
    setProgressDetail('');
    setCompletedPhases([]);
    hasReceivedChunksRef.current = false;
    accumulatedRef.current = '';
    currentSectionTitleRef.current = '';
    isUserScrolledUpRef.current = false;

    try {
      const stream = apiService.streamCaseAnalysis(caseId, false, documentIds);

      for await (const evt of stream) {
        if (isCancelled()) break;
        const evtType = evt.event;

        if (evtType === 'start') {
          setPhaseLabel(`Lënda: ${evt.case_title || caseName}`);
          continue;
        }

        if (evtType === 'phase_started') {
          setCurrentPhase(evt.phase as PhaseKey);
          const phaseCfg = PHASES.find(p => p.key === evt.phase);
          setPhaseLabel(phaseCfg ? `${phaseCfg.label}...` : evt.phase || '');
          setProgressDetail('');
          continue;
        }

        if (evtType === 'phase_completed') {
          setCompletedPhases(prev => [...prev, evt.phase as PhaseKey]);
          continue;
        }

        if (evtType === 'phase_skipped') {
          setCompletedPhases(prev => [...prev, evt.phase as PhaseKey]);
          continue;
        }

        if (evtType === 'document_started') {
          setPhaseLabel(`Ekstraktimi: ${evt.file_name} (${(evt.index || 0) + 1}/${evt.total_documents || 0})`);
          continue;
        }
        if (evtType === 'document_completed') {
          setProgressDetail(`✓ ${evt.file_name} — ${evt.stats?.total_entities || 0} entitete`);
          continue;
        }
        if (evtType === 'document_skipped') {
          setProgressDetail(`⏭️ ${evt.file_name} (cache)`);
          continue;
        }
        if (evtType === 'document_failed') {
          setProgressDetail(`✗ ${evt.file_name}: ${evt.error || 'unknown'}`);
          continue;
        }

        if (evtType === 'section_started') {
          const title = evt.section_title || evt.section_key || '';
          setPhaseLabel(`Sinteza: ${title}`);
          currentSectionTitleRef.current = title;
          accumulatedRef.current += `\n\n# ${title}\n\n`;
          setReportContent(accumulatedRef.current);
          continue;
        }

        if (evtType === 'section_chunk') {
          const chunk = evt.chunk || '';
          if (chunk) {
            hasReceivedChunksRef.current = true;
            accumulatedRef.current += chunk;
            setReportContent(accumulatedRef.current);
          }
          continue;
        }

        if (evtType === 'section_completed') {
          setProgressDetail(`✓ ${evt.section_title} (${evt.content_length || 0} chars)`);
          continue;
        }

        if (evtType === 'report_ready') {
          const content = evt.content || '';
          const fromCache = evt.from_cache === true;

          if (fromCache && content.trim() && !hasReceivedChunksRef.current) {
            setPhaseLabel('Duke shfaqur doktrinën...');
            await applyTypewriter(
              content,
              (partial) => {
                if (!isCancelled()) setReportContent(partial);
              },
              isCancelled,
            );
            accumulatedRef.current = content;
          }
          continue;
        }

        if (evtType === 'complete') {
          setCurrentPhase('idle');
          setPhaseLabel('Doktrina u përfundua');
          setProgressDetail('');
          break;
        }

        if (evtType === 'error') {
          console.error('[SSE Error]', evt);
          setProgressDetail(`⚠️ ${evt.message || 'Gabim në server'}`);
          continue;
        }
      }

      if (isCancelled()) return;

      const finalMarkdown = accumulatedRef.current.trim();
      if (finalMarkdown) {
        setIsSaving(true);
        try {
          await apiService.saveCaseDossierAudit(caseId, finalMarkdown);
        } catch (saveErr) {
          console.error("Case Dossier Audit Persist Error:", saveErr);
          alert("Doktrina u gjenerua por nuk mund të ruhej në server.");
        } finally {
          setIsSaving(false);
        }
      }
    } catch (err: any) {
      if (isCancelled()) return;
      console.error("Case Dossier Audit Error:", err);
      setProgressDetail(`⚠️ ${err?.message || 'Gabim i panjohur'}`);
      alert(err?.message || 'Ndodhi një gabim gjatë gjenerimit të doktrinës.');
    } finally {
      if (!isCancelled()) {
        setIsLoading(false);
        setCurrentPhase('idle');
      }
    }
  }, [caseId, caseName, isLoading, isPurging, isSaving, documentIds]);

  const handleClearContent = async () => {
    if (!reportContent || !caseId || isPurging) return;
    const confirmWipe = window.confirm("A jeni i sigurt që dëshironi të asgjësoni plotësisht doktrinën e fashikullit nga serveri (Total Cascade Wipeout)?");
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await apiService.clearCaseDossierAudit(caseId);
      setReportContent('');
      setCompletedPhases([]);
      setCurrentPhase('idle');
      accumulatedRef.current = '';
    } catch (err) {
      console.error("Could not purge case dossier audit on MongoDB:", err);
      alert("Dështoi asgjësimi i doktrinës së fashikullit në server.");
    } finally {
      setIsPurging(false);
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
    isUserScrolledUpRef.current = false;
    setShowScrollBottomBtn(false);
  };

  if (!isOpen) return null;

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
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-primary-start/15 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0">
                {isSingleDoc ? <FileText className="w-5 h-5" /> : <Folder className="w-5 h-5" />}
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
                  className="p-2 text-text-muted hover:text-rose-500 hover:bg-rose-500/10 rounded-xl transition-colors cursor-pointer"
                  title="Fshi doktrinën nga serveri (Total Wipeout)"
                >
                  {isPurging ? <Loader2 size={16} className="animate-spin text-rose-500" /> : <Trash2 size={16} />}
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

          {isLoading && (
            <div className="pt-3 pb-1 shrink-0">
              <div className="flex items-center justify-between gap-2 mb-2">
                {PHASES.map((phase) => {
                  const isActive = currentPhase === phase.key;
                  const isCompleted = completedPhases.includes(phase.key);
                  return (
                    <div
                      key={phase.key}
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] sm:text-xs font-bold uppercase tracking-wider transition-all ${
                        isCompleted
                          ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                          : isActive
                          ? 'bg-primary-start/15 text-primary-start border border-primary-start/30 animate-pulse'
                          : 'bg-surface text-text-muted border border-main'
                      }`}
                    >
                      {isCompleted ? <CheckCircle size={12} /> : isActive ? <Loader2 size={12} className="animate-spin" /> : phase.icon}
                      <span className="hidden sm:inline">{phase.label}</span>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-2 text-[10px] sm:text-xs font-medium text-text-muted">
                <Loader2 size={11} className="animate-spin text-primary-start shrink-0" />
                <span className="truncate">{phaseLabel}</span>
              </div>
              {progressDetail && (
                <div className="text-[10px] text-text-muted/70 truncate mt-0.5 font-mono pl-4">
                  {progressDetail}
                </div>
              )}
            </div>
          )}

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

            {!reportContent && !isLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <Scale size={28} />
                </div>
                <div>
                  <h4 className="text-base font-bold text-text-primary">{reportTitle}</h4>
                  <p className="text-xs text-text-muted max-w-lg mt-1">
                    {emptyStateDescription}
                  </p>
                  <p className="text-[10px] text-text-muted/70 mt-2 font-mono">
                    Analiza zhvillohet në 3 faza: Ekstraktimi → Lidhjet → Sinteza
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateAudit}
                  disabled={isPurging || isSaving}
                  className="px-6 py-3 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-md flex items-center gap-2 cursor-pointer transition-all hover-lift disabled:opacity-50"
                >
                  <Sparkles size={14} />
                  <span>{actionButtonLabel}</span>
                </button>
              </div>
            ) : isLoading && !reportContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto space-y-3">
                <Loader2 className="w-9 h-9 animate-spin text-primary-start" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  {isSingleDoc
                    ? 'Duke analizuar dokumentin...'
                    : 'Duke analizuar fashikullin si një tërësi koherente...'}
                </p>
                <p className="text-[10px] text-text-muted font-mono max-w-md text-center">
                  Kjo mund të zgjasë disa minuta për dokumente të mëdhenj. Ju lutem mos mbyllni dritaren.
                </p>
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
                className="sticky bottom-2 right-2 ml-auto z-20 px-3 py-1.5 bg-slate-900 text-white text-[11px] font-bold rounded-full shadow-lg border border-slate-700 flex items-center gap-1 cursor-pointer"
              >
                <span>Te Fundi</span>
                <ArrowDown size={12} className="animate-bounce" />
              </button>
            )}
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
            {reportContent && !isLoading && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium">
                {isSaving ? (
                  <>
                    <Loader2 size={12} className="text-primary-start animate-spin" />
                    <span className="hidden sm:inline">Duke ruajtur në server...</span>
                    <span className="sm:hidden">Duke ruajtur...</span>
                  </>
                ) : (
                  <>
                    <Lock size={12} className="text-text-muted" />
                    <span className="hidden sm:inline">Doktrina është ruajtur (Përdorni koshin për ta asgjësuar nga serveri)</span>
                    <span className="sm:hidden">E ruajtur</span>
                  </>
                )}
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