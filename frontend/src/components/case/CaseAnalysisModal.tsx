// FILE: frontend/src/components/case/CaseAnalysisModal.tsx
// PHOENIX PROTOCOL - EXECUTIVE MASTER FORENSIC REPORT MODAL V8.0 (SECURE ADMIN-ONLY DELETION)
// ZERO TS WARNINGS • ZERO HARDCODING • SOLID THEME-AWARE

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileSearch, X, Copy, Save, CheckCircle2, 
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface CaseAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysisText: string;
  caseId: string;
  caseTitle?: string;
  clientName?: string;
  modalHeaderTitle?: string;
  onDeleteAnalysis?: () => Promise<void> | void;
}

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 },
  { label: '150%', base: 21, h1: 29, h2: 24, h3: 21, line: 1.85 }
];

const sanitizeReportDocument = (rawText: string): string => {
  if (!rawText) return '';
  let text = rawText;
  text = text.replace(/📋\s*Duke\s+analizuar[^\n]*\n?/gi, '');
  text = text.replace(/✅\s*Pjesa\s+\d+\/\d+\s+u\s+analizua\.?\s*/gi, '');
  text = text.replace(/🔗\s*Duke\s+përmbledhur[^\n]*\n?/gi, '');
  text = text.replace(/(?:\n|^)(?:#{1,4}\s*)?Sugjerime:[\s\S]*?(?=(?:---\s*)?(?:⚖️\s*)?\*?\*?KLAUZOLË|$)/gi, '\n\n');
  return text.trim();
};

export const CaseAnalysisModal: React.FC<CaseAnalysisModalProps> = ({
  isOpen,
  onClose,
  analysisText,
  caseId,
  caseTitle = 'Lënda Ligjore',
  clientName = 'Klienti',
  modalHeaderTitle,
  onDeleteAnalysis,
}) => {
  const [copied, setCopied] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 2;
    } catch {
      return 2;
    }
  });

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  const pristineDocument = sanitizeReportDocument(analysisText);
  const autoLinkedContent = autoLinkLegalCitations(pristineDocument);

  useEffect(() => {
    if (!isOpen) return;
    const container = scrollContainerRef.current;
    if (!container) return;

    if (!isUserScrolledUpRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [analysisText, isOpen]);

  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const userScrolledUp = distanceFromBottom > 80;
    isUserScrolledUpRef.current = userScrolledUp;
    setShowScrollBottomBtn(userScrolledUp);
  };

  const scrollToBottom = () => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    isUserScrolledUpRef.current = false;
    setShowScrollBottomBtn(false);
  };

  if (!isOpen) return null;

  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleDecreaseFont = () => {
    setFontLevelIndex((prev) => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleIncreaseFont = () => {
    setFontLevelIndex((prev) => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(2);
    try { localStorage.setItem('juristi_forensic_font_size', '2'); } catch {}
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(pristineDocument);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleArchive = async () => {
    if (!caseId || !pristineDocument) return;
    setIsArchiving(true);
    setArchiveSuccess(false);
    try {
      const archiveDocTitle = modalHeaderTitle 
        ? `${modalHeaderTitle} - ${caseTitle}`
        : `Raporti Forenzik: ${caseTitle}`;

      await apiService.archiveForensicReport(
        caseId,
        archiveDocTitle,
        pristineDocument
      );
      setArchiveSuccess(true);
      setTimeout(() => setArchiveSuccess(false), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dështoi ruajtja në arkiv.");
    } finally {
      setIsArchiving(false);
    }
  };

  const handleDeleteAnalysis = async () => {
    if (!caseId) return;
    if (!window.confirm("A jeni i sigurt që doni të fshini këtë analizë nga baza e të dhënave për ta rigjeneruar nga e para?")) {
      return;
    }

    setIsDeleting(true);
    try {
      if (onDeleteAnalysis) {
        await onDeleteAnalysis();
      }
      onClose();
    } catch (err: any) {
      console.error("Failed to delete analysis:", err);
      alert("Dështoi fshirja e analizës.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center z-[250] p-0 sm:p-3 md:p-6 select-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 10 }}
          className={`glass-panel w-full ${
            isFullscreen 
              ? 'h-full max-h-screen rounded-none border-0' 
              : 'h-full sm:h-[94vh] max-w-6xl sm:max-h-[960px] rounded-none sm:rounded-3xl border-0 sm:border sm:border-main'
          } p-3 sm:p-5 md:p-7 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
          style={{ backgroundColor: 'var(--bg-card, #ffffff)' }}
        >
          {/* Header Ultra-Adaptiv */}
          <div className="flex items-center justify-between pb-3 sm:pb-4 border-b border-main shrink-0 gap-2">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-primary-start/10 text-primary-start rounded-xl sm:rounded-2xl flex items-center justify-center border border-primary-start/20 shrink-0 shadow-xs">
                <FileSearch className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-xs sm:text-sm md:text-base font-black text-text-primary uppercase tracking-tight truncate leading-tight">
                  {modalHeaderTitle || "Raporti i Plotë Forenzik"}
                </h3>
                <p className="text-[10px] sm:text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {caseTitle} <span className="opacity-60">•</span> {clientName}
                </p>
              </div>
            </div>

            {/* Kontrollet */}
            <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
              {/* Font Resizer */}
              <div className="flex items-center bg-surface border border-main rounded-lg sm:rounded-xl p-0.5 text-xs shadow-inner">
                <button
                  type="button"
                  onClick={handleDecreaseFont}
                  disabled={fontLevelIndex <= 0}
                  className="p-1 sm:px-2 sm:py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-md hover:bg-hover transition-colors font-bold flex items-center cursor-pointer"
                  title="Zvogëlo Tekstin (A-)"
                >
                  <ZoomOut className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                  <span className="hidden sm:inline ml-0.5">A-</span>
                </button>
                <button
                  type="button"
                  onClick={handleResetFont}
                  className="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-[11px] font-mono font-bold text-primary-start hover:text-primary-end rounded-md hover:bg-hover transition-colors cursor-pointer"
                  title="Rivendos Madhësinë"
                >
                  {activeFont.label}
                </button>
                <button
                  type="button"
                  onClick={handleIncreaseFont}
                  disabled={fontLevelIndex >= FONT_LEVELS.length - 1}
                  className="p-1 sm:px-2 sm:py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-md hover:bg-hover transition-colors font-bold flex items-center cursor-pointer"
                  title="Zmadho Tekstin (A+)"
                >
                  <span className="hidden sm:inline mr-0.5">A+</span>
                  <ZoomIn className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                </button>
              </div>

              {/* PHOENIX FIX: Butoni i Fshirjes shfaqet VETËM kur onDeleteAnalysis është i pranishëm (ADMIN) */}
              {onDeleteAnalysis && (
                <button
                  type="button"
                  onClick={handleDeleteAnalysis}
                  disabled={isDeleting}
                  className="p-1.5 sm:p-2 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-lg sm:rounded-xl transition-colors cursor-pointer"
                  title="Fshi Analizën"
                >
                  {isDeleting ? <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin text-rose-500" /> : <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
                </button>
              )}

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="hidden sm:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title={isFullscreen ? "Zvogëlo" : "Zmadho Ekranin"}
              >
                {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>

              <button
                type="button"
                onClick={onClose}
                className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-lg sm:rounded-xl transition-colors cursor-pointer"
                title="Mbyll"
              >
                <X className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>

          {/* Trupi i Raportit */}
          <div 
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto overflow-x-hidden custom-finance-scroll p-3 sm:p-6 md:p-8 my-2 sm:my-3 bg-surface/40 rounded-xl sm:rounded-2xl border border-main text-text-primary shadow-inner select-text relative touch-pan-y"
          >
            <style>{`
              .dynamic-forensic-report p,
              .dynamic-forensic-report li,
              .dynamic-forensic-report span:not(.lucide) {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .dynamic-forensic-report td {
                font-size: ${Math.max(11.5, activeFont.base - 1.5)}px !important;
                line-height: 1.45 !important;
                padding: 6px 8px !important;
              }
              .dynamic-forensic-report th {
                font-size: ${Math.max(11, activeFont.base - 2)}px !important;
                padding: 8px 8px !important;
              }
              .dynamic-forensic-report h1 {
                font-size: ${activeFont.h1}px !important;
                line-height: 1.25 !important;
                margin-top: 1.2em !important;
                margin-bottom: 0.5em !important;
              }
              .dynamic-forensic-report h2 {
                font-size: ${activeFont.h2}px !important;
                line-height: 1.3 !important;
                margin-top: 1.1em !important;
                margin-bottom: 0.4em !important;
              }
              .dynamic-forensic-report h3 {
                font-size: ${activeFont.h3}px !important;
                line-height: 1.35 !important;
                margin-top: 0.9em !important;
                margin-bottom: 0.3em !important;
              }
              .dynamic-forensic-report table {
                display: block !important;
                width: 100% !important;
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
                margin: 1em 0 !important;
              }
            `}</style>

            <div className="markdown-content dynamic-forensic-report prose prose-slate dark:prose-invert max-w-none text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {autoLinkedContent}
              </ReactMarkdown>
            </div>
          </div>

          {/* Butoni Lundrues për Rikthim te Fundi */}
          <AnimatePresence>
            {showScrollBottomBtn && (
              <motion.button
                initial={{ opacity: 0, y: 10, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.9 }}
                type="button"
                onClick={scrollToBottom}
                className="absolute bottom-16 sm:bottom-20 right-4 sm:right-10 z-20 px-3 py-1.5 sm:px-3.5 sm:py-2 bg-slate-900/90 hover:bg-slate-900 text-white text-[11px] sm:text-xs font-bold rounded-full shadow-2xl border border-slate-700/80 backdrop-blur-md flex items-center gap-1.5 cursor-pointer hover:border-sky-500/50 transition-all"
              >
                <span>Te Fundi</span>
                <ArrowDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 animate-bounce" />
              </motion.button>
            )}
          </AnimatePresence>

          {/* Veprimet Ekzekutive */}
          <div className="flex items-center justify-between pt-2.5 sm:pt-4 border-t border-main gap-2 sm:gap-3 shrink-0">
            <button
              type="button"
              onClick={handleArchive}
              disabled={isArchiving || !pristineDocument}
              className="flex-1 sm:flex-initial h-10 px-3 sm:px-5 bg-surface hover:bg-hover border border-main rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider text-primary-start flex items-center justify-center gap-1.5 sm:gap-2 transition-all shadow-sm disabled:opacity-40 cursor-pointer min-h-[40px]"
            >
              {isArchiving ? (
                <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
              ) : archiveSuccess ? (
                <CheckCircle2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-status-success" />
              ) : (
                <Save className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              )}
              <span className="truncate">{archiveSuccess ? 'U ruajt!' : 'Ruaj në Arkiv'}</span>
            </button>

            <button
              type="button"
              onClick={handleCopy}
              disabled={!pristineDocument}
              className="flex-1 sm:flex-initial h-10 px-4 sm:px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] sm:text-xs uppercase tracking-wider shadow-sm transition-all flex items-center justify-center gap-1.5 sm:gap-2 disabled:opacity-40 cursor-pointer min-h-[40px]"
            >
              <Copy className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> 
              <span className="truncate">{copied ? 'U Kopjua!' : 'Kopjo Raportin'}</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CaseAnalysisModal;