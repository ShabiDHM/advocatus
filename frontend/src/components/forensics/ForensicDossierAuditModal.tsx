// FILE: frontend/src/components/forensics/ForensicDossierAuditModal.tsx
// PHOENIX PROTOCOL - FORENSIC DOSSIER AUDIT MODAL V2.0 (HOLISTIC-STRATEGIC DOCTRINE)
// ZERO TS WARNINGS • SUPREME COURT ADVISOR ANALOGY • DOSSIER-LEVEL PERSISTENCE • 100% COMPLETE CODE

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Copy, CheckCircle2,
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown, Sparkles, Lock, ShieldCheck, Folder
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { forensicDeskService } from '../../services/forensicDeskService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface ForensicDossierAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseName?: string;
  clientName?: string;
  documentCount?: number;
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
      <title>Doktrina Forenzike e Fashikullit</title>
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

export const ForensicDossierAuditModal: React.FC<ForensicDossierAuditModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseName = 'Fashikulli Forenzik',
  clientName = 'Klienti',
  documentCount = 0,
}) => {
  const [reportContent, setReportContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(1);
  const activeFont = FONT_LEVELS[fontLevelIndex];
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  // Leximi i pasqyrës ekzistuese nga MongoDB (0ms Cache) — rifreskohet në çdo hapje
  useEffect(() => {
    if (isOpen && caseId) {
      setIsLoading(false);
      forensicDeskService.getForensicDossier(caseId)
        .then((dossier: any) => {
          const savedAudit = dossier?.latest_dossier_analysis || '';
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

  // Auto-scroll gjatë gjenerimit
  useEffect(() => {
    if (!isUserScrolledUpRef.current && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [reportContent, isLoading]);

  // DOKTRINA FORENZIKE E FASHIKULLIT — OPINION HOLISTIK-STRAteGJIK
  const handleGenerateAudit = useCallback(async () => {
    if (!caseId || isLoading || isPurging || isSaving) return;

    setIsLoading(true);
    setReportContent('');
    isUserScrolledUpRef.current = false;

    const auditPrompt = `[DOKTRINA FORENZIKE E FASHIKULLIT TË PLOTË]
Lënda Forenzike: "${caseName}" | Klienti: "${clientName}" | Shkresat e Administruara: ${documentCount}

TI JE NJË KËSHILLTAR I LARTË I GJYKATËS SUPREME TË KOSOVËS me përvojë dekadash në procedurën civile, penale dhe administrative. Klienti ka kaluar nëpër disa instanca gjyqësore dhe vjen para teje për një OPINION TË PRERË STRATEGJIK mbi të gjithë fashikullin.

DETYRA JOTE: Lexo dhe analizo TË GJITHA ${documentCount} SHKRESAT e fashikullit si një tërësi koherente. NUK je duke verifikuar nene individuale në një akt të vetëm — je duke dhënë një doktrinë forenzike mbi historikun e plotë dhe pozicionin ligjor aktual të klientit.

Përgjigju me këtë strukturë të prerë:

### 1. PËRMBLEDHJA E RASTIT DHE HISTORIKU PROCEDURAL
* Çfarë ka ndodhur deri tani në këtë fashikull (nga të gjitha instancat).
* Rindërtimi kronologjik i ngjarjeve dhe akteve kryesore (data, akte, palë, organe).
* Palët, rolet e tyre procedurale dhe pozicionet në secilën fazë të procedurës.

### 2. KONTRADIKTAT THELBËSORE DHE MOSPËRPUTHJET FAKTIKE
* Kontradiktat mes deklaratave, provave dhe akteve të ndryshme të fashikullit.
* Mospërputhjet kronologjike, alibitë dhe versionet e kundërta të palëve.
* Pikat konkrete ku tregimi faktik nuk qëndron ose ku pala kundërshtare ka dobësi.

### 3. SHKELJET PROCEDURALE DHE REFERENCAT LIGJORE TË PROBLEMATIKE
* Shkeljet thelbësore procedurale gjatë ecurisë së çështjes (nëse ka), me përshkrim se ku dhe si kanë ndodhur.
* Referencat ligjore të pasakta, të shfuqizuara ose të keqzbatuara në aktet e fashikullit.
* RREGULL I HEKURT: NUK lejohet rishkrimi, zëvendësimi apo korrigjimi automatik i neneve. Për çdo referencë të problematik, paraqit: (a) referencën siç është cituar dhe në cilën shkresë, (b) referencën e saktë në fuqi si REKOMANDIM i veçantë, (c) arsyen e problemit.
* Pasojat e mundshme të këtyre shkeljeve për vlefshmërinë e akteve dhe mundësitë e shfrytëzimit të tyre në favor të klientit.

### 4. VLERËSIMI STRATEGJIK I POZICIONIT LIGJOR
* Pozicioni i përgjithshëm i klientit në këtë fazë të procedurës.
* Pikat e forta dhe dobësitë provuese të fashikullit në tërësi.
* Mundësitë dhe rreziqet e hapave të mundshëm proceduralë.
* Precedentët e Gjykatës Supreme dhe Kushtetuese që mund të shfrytëzohen në favor (vetëm ato që ekzistojnë vërtetë, pa sajim).

### 5. REKOMANDIMI PËRFUNDIMTAR DHE HAPI I ARDHSHËM
* Opinioni i prerë i ekspertit (si këshilltar i Gjykatës Supreme) mbi rrugën më të mirë.
* Hapi konkret procedural që duhet ndërmarrë TANI.
* Afatet ligjore të sakta dhe strategjia taktike për fazën e ardhshme.

Rregull i Hekurt: Përgjigju me gjuhë zyrtare gjyqësore, me pika hierarkike të strukturuara, si një OPINION I PRERË profesionale. Mos kopjo shkresat fjalë për fjalë, por nxirr thelbin e tyre. Pa tabela të fryra dhe pa formalitete të tepërta hyrëse.`;

    try {
      const contextHeader = `Lënda Forenzike: ${caseName} - ${clientName}. FASHIKULLI I PLOTË (${documentCount} shkresa të administruara). Vula: AKTIVE`;

      const stream = await forensicDeskService.streamForensicChat(
        caseId,
        auditPrompt,
        contextHeader
      );

      const reader = stream.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;
        setReportContent(accumulated);
      }

      // 🔒 PERSISTENCE: Ruajtja e detyruar në MongoDB pas përfundimit të transmetimit
      const finalContent = accumulated.trim();
      if (finalContent.length > 0) {
        setIsSaving(true);
        try {
          await forensicDeskService.saveForensicDossierAudit(caseId, finalContent);
        } catch (saveErr) {
          console.error("Forensic Dossier Audit Persist Error:", saveErr);
          alert("Doktrina u gjenerua por nuk mund të ruhej në server. Kontrolloni lidhjen dhe provoni përsëri.");
        } finally {
          setIsSaving(false);
        }
      }
    } catch (err: any) {
      console.error("Forensic Dossier Audit Error:", err);
      alert("Ndodhi një gabim gjatë gjenerimit të doktrinës forenzike të fashikullit.");
    } finally {
      setIsLoading(false);
    }
  }, [caseId, caseName, clientName, documentCount, isLoading, isPurging, isSaving]);

  // TOTAL CASCADE WIPEOUT në MongoDB
  const handleClearContent = async () => {
    if (!reportContent || !caseId || isPurging) return;
    const confirmWipe = window.confirm("A jeni i sigurt që dëshironi të asgjësoni plotësisht doktrinën forenzike të fashikullit nga serveri (Total Cascade Wipeout)?");
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await forensicDeskService.clearForensicDossierAudit(caseId);
      setReportContent('');
    } catch (err) {
      console.error("Could not purge forensic dossier audit on MongoDB:", err);
      alert("Dështoi asgjësimi i doktrinës forenzike të fashikullit në server.");
    } finally {
      setIsPurging(false);
    }
  };

  // KOPJIMI I PASTËR DHE I FORMOSHËM PËR MICROSOFT WORD
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
          {/* Header */}
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-primary-start/15 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0">
                <Folder className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                    Doktrina Forenzike e Fashikullit
                  </h3>
                </div>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {caseName} • {clientName} • {documentCount} shkresa
                </p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Font Size */}
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

              {/* Trash */}
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

              {/* Fullscreen */}
              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="hidden sm:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title={isFullscreen ? "Zvogëlo" : "Zmadho"}
              >
                {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>

              {/* Close */}
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

          {/* Body */}
          <div
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 my-2 bg-surface/30 rounded-2xl border border-main text-text-primary select-text relative flex flex-col"
          >
            <style>{`
              .fast-forensic-dossier-audit p, .fast-forensic-dossier-audit li {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .fast-forensic-dossier-audit h1, .fast-forensic-dossier-audit h2, .fast-forensic-dossier-audit h3 {
                color: var(--text-primary);
                font-weight: 800;
                margin-top: 1em;
                margin-bottom: 0.4em;
              }
            `}</style>

            {!reportContent && !isLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <ShieldCheck size={28} />
                </div>
                <div>
                  <h4 className="text-base font-bold text-text-primary">Doktrina Forenzike e Fashikullit</h4>
                  <p className="text-xs text-text-muted max-w-lg mt-1">
                    Merrni një <strong className="text-text-primary">opinion të prerë strategjik</strong> mbi historikun e plotë të këtij fashikulli me <strong className="text-text-primary">{documentCount} shkresa</strong> — si një këshilltar i Gjykatës Supreme: çfarë ka ndodhur, kontradiktat, shkeljet, pozicioni ligjor dhe hapi i ardhshëm konkret.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateAudit}
                  disabled={isPurging || isSaving}
                  className="px-6 py-3 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-md flex items-center gap-2 cursor-pointer transition-all hover-lift disabled:opacity-50"
                >
                  <Sparkles size={14} />
                  <span>Fillo Doktrinën Forenzike</span>
                </button>
              </div>
            ) : isLoading && !reportContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto space-y-3">
                <Loader2 className="w-9 h-9 animate-spin text-primary-start" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Duke analizuar fashikullin si një tërësi koherente...
                </p>
              </div>
            ) : (
              <div className="markdown-content fast-forensic-dossier-audit prose prose-slate dark:prose-invert max-w-none text-text-primary">
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

          {/* Bottom Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
            {reportContent && !isLoading && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium" title="Fashikulli është audituar tashmë">
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

export default ForensicDossierAuditModal;