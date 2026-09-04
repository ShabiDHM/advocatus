// FILE: frontend/src/components/case/CaseAnalysisModal.tsx
// PHOENIX PROTOCOL - EXECUTIVE MASTER FORENSIC REPORT MODAL V4.0 (CASCADE WIPEOUT HEADER BUTTON)

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileSearch, X, Copy, Save, CheckCircle2, 
  Loader2, Maximize2, Minimize2, Trash2 
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

// Funksion pastrimi: Heq rreshtat e debugut "Pjesa 1/9..." dhe "Sugjerime:" nga raporti ekzekutiv
const sanitizeReportDocument = (rawText: string): string => {
  if (!rawText) return '';
  
  let text = rawText;
  
  // Heq rreshtat e statusit të analizës
  text = text.replace(/📋\s*Duke\s+analizuar[^\n]*\n?/gi, '');
  text = text.replace(/✅\s*Pjesa\s+\d+\/\d+\s+u\s+analizua\.?\s*/gi, '');
  text = text.replace(/🔗\s*Duke\s+përmbledhur[^\n]*\n?/gi, '');
  
  // Heq bllokun e sugjerimeve të chatit nga ky modal
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

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  if (!isOpen) return null;

  const pristineDocument = sanitizeReportDocument(analysisText);
  const autoLinkedContent = autoLinkLegalCitations(pristineDocument);

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

  // 🧹 CASCADE WIPEOUT BUTONI I KOSHIT NË HEADER
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
            isFullscreen ? 'h-full max-h-screen rounded-none' : 'max-w-5xl h-[90vh] max-h-[900px] rounded-3xl'
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

            {/* Butonat e Kontrollit në Header: Kosh (Wipeout) + Fullscreen + Mbyllje */}
            <div className="flex items-center gap-1.5 shrink-0">
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
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Trupi i Dokumentit - Formatim Gjyqësor i Pastër */}
          <div className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-8 mt-3 bg-surface/40 rounded-2xl border border-main text-text-primary shadow-inner select-text">
            <div className="markdown-content prose prose-slate dark:prose-invert max-w-none prose-sm sm:prose-base leading-relaxed text-text-primary">
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
              className="h-9 px-4 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-primary-start flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-40 cursor-pointer"
            >
              {isArchiving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : archiveSuccess ? (
                <CheckCircle2 size={14} className="text-status-success" />
              ) : (
                <Save size={14} />
              )}
              {archiveSuccess ? 'U ruajt në Arkiv!' : 'Ruaj në Arkiv'}
            </button>

            <button
              type="button"
              onClick={handleCopy}
              disabled={!pristineDocument}
              className="h-9 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer"
            >
              <Copy size={13} /> {copied ? 'U Kopjua Raporti!' : 'Kopjo Raportin'}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CaseAnalysisModal;