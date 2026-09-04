// FILE: frontend/src/components/case/CaseAnalysisModal.tsx
// PHOENIX PROTOCOL - EXECUTIVE MASTER FORENSIC REPORT MODAL V5.1 (ZERO-WARNING CLEAN TYPESCRIPT BUILD)

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileSearch, X, Copy, Save, CheckCircle2, 
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut
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
  onDeleteAnalysis?: () => Promise<void> | void;
}

const FONT_LEVELS = [
  { label: '85%', base: 14, h1: 20, h2: 17, h3: 15, line: 1.6 },
  { label: '100%', base: 15.5, h1: 22, h2: 18.5, h3: 16.5, line: 1.7 },
  { label: '115%', base: 17.5, h1: 25, h2: 21, h3: 18.5, line: 1.8 }, // Default Komod
  { label: '130%', base: 19.5, h1: 28, h2: 23, h3: 20.5, line: 1.85 },
  { label: '150%', base: 22, h1: 31, h2: 26, h3: 23, line: 1.9 }
];

// Funksion pastrimi: Heq rreshtat e statusit dhe bllokun e sugjerimeve të brendshme
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
  onDeleteAnalysis,
}) => {
  const [copied, setCopied] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Zgjedhja e madhësisë së fontit me memorizim në LocalStorage (Default: Level 2 = 115% / 17.5px)
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 2;
    } catch {
      return 2;
    }
  });

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  if (!isOpen) return null;

  const pristineDocument = sanitizeReportDocument(analysisText);
  const autoLinkedContent = autoLinkLegalCitations(pristineDocument);

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
      await apiService.archiveForensicReport(
        caseId,
        `Raporti Forenzik: ${caseTitle}`,
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
    if (!window.confirm("A jeni i sigurt që doni të fshini këtë analizë nga baza e të dhënave (Cascade Wipeout) për ta rigjeneruar nga e para?")) {
      return;
    }

    setIsDeleting(true);
    try {
      await apiService.clearChatHistory(caseId);
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
      <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[250] p-2 sm:p-4 md:p-6 select-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 15 }}
          className={`glass-panel w-full ${
            isFullscreen ? 'h-full max-h-screen rounded-none' : 'max-w-6xl h-[92vh] max-h-[950px] rounded-3xl'
          } p-5 sm:p-7 shadow-2xl border border-main bg-card flex flex-col transition-all duration-200`}
          style={{ backgroundColor: 'var(--bg-card, #ffffff)' }}
        >
          {/* Header Ekzekutiv */}
          <div className="flex items-center justify-between pb-4 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/20 shrink-0 shadow-xs">
                <FileSearch size={20} />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                  Raporti i Plotë Forenzik i Lëndës
                </h3>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {caseTitle} — {clientName}
                </p>
              </div>
            </div>

            {/* Butonat e Kontrollit në Header: Font Resizer + Kosh + Fullscreen + Mbyllje */}
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Kontrolluesi Interaktiv i Madhësisë së Fontit */}
              <div className="flex items-center bg-surface border border-main rounded-xl p-0.5 mr-1 text-xs shadow-inner">
                <button
                  type="button"
                  onClick={handleDecreaseFont}
                  disabled={fontLevelIndex <= 0}
                  className="px-2.5 py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-lg hover:bg-hover transition-colors font-bold flex items-center gap-0.5 cursor-pointer"
                  title="Zvogëlo Madhësinë e Tekstit (A-)"
                >
                  <ZoomOut size={13} />
                  <span>A-</span>
                </button>
                <button
                  type="button"
                  onClick={handleResetFont}
                  className="px-2 py-1 text-[11px] font-mono font-bold text-primary-start hover:text-primary-end rounded-lg hover:bg-hover transition-colors cursor-pointer"
                  title="Rivendos në Madhësinë Komode (115%)"
                >
                  {activeFont.label}
                </button>
                <button
                  type="button"
                  onClick={handleIncreaseFont}
                  disabled={fontLevelIndex >= FONT_LEVELS.length - 1}
                  className="px-2.5 py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-lg hover:bg-hover transition-colors font-bold flex items-center gap-0.5 cursor-pointer"
                  title="Zmadho Madhësinë e Tekstit (A+)"
                >
                  <span>A+</span>
                  <ZoomIn size={13} />
                </button>
              </div>

              <button
                type="button"
                onClick={handleDeleteAnalysis}
                disabled={isDeleting}
                className="p-2 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-xl transition-colors cursor-pointer"
                title="Fshi Analizën (Cascade Wipeout)"
              >
                {isDeleting ? <Loader2 size={16} className="animate-spin text-rose-500" /> : <Trash2 size={16} />}
              </button>

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title={isFullscreen ? "Zvogëlo" : "Zmadho Ekranin"}
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

          {/* Trupi i Dokumentit me Shkallëzim Dinamik të Fontit */}
          <div className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-8 mt-3 bg-surface/40 rounded-2xl border border-main text-text-primary shadow-inner select-text">
            {/* Scoped CSS për rregullim të saktë të madhësisë në të gjithë raportin */}
            <style>{`
              .dynamic-forensic-report p,
              .dynamic-forensic-report li,
              .dynamic-forensic-report td,
              .dynamic-forensic-report span:not(.lucide) {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .dynamic-forensic-report h1 {
                font-size: ${activeFont.h1}px !important;
                line-height: 1.3 !important;
                margin-top: 1.4em !important;
                margin-bottom: 0.6em !important;
              }
              .dynamic-forensic-report h2 {
                font-size: ${activeFont.h2}px !important;
                line-height: 1.35 !important;
                margin-top: 1.2em !important;
                margin-bottom: 0.5em !important;
              }
              .dynamic-forensic-report h3 {
                font-size: ${activeFont.h3}px !important;
                line-height: 1.4 !important;
                margin-top: 1em !important;
                margin-bottom: 0.4em !important;
              }
              .dynamic-forensic-report th {
                font-size: ${Math.max(12, activeFont.base - 2)}px !important;
              }
            `}</style>

            <div className="markdown-content dynamic-forensic-report prose prose-slate dark:prose-invert max-w-none text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {autoLinkedContent}
              </ReactMarkdown>
            </div>
          </div>

          {/* Veprimet Ekzekutive */}
          <div className="flex items-center justify-between pt-4 mt-3 border-t border-main gap-3 shrink-0">
            <button
              type="button"
              onClick={handleArchive}
              disabled={isArchiving || !pristineDocument}
              className="h-10 px-5 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-primary-start flex items-center gap-2 transition-all shadow-sm disabled:opacity-40 cursor-pointer"
            >
              {isArchiving ? (
                <Loader2 size={15} className="animate-spin" />
              ) : archiveSuccess ? (
                <CheckCircle2 size={15} className="text-status-success" />
              ) : (
                <Save size={15} />
              )}
              {archiveSuccess ? 'U ruajt në Arkiv!' : 'Ruaj në Arkiv'}
            </button>

            <button
              type="button"
              onClick={handleCopy}
              disabled={!pristineDocument}
              className="h-10 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center gap-2 disabled:opacity-40 cursor-pointer"
            >
              <Copy size={14} /> {copied ? 'U Kopjua Raporti!' : 'Kopjo Raportin'}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CaseAnalysisModal;