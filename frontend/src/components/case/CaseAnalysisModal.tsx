// FILE: frontend/src/components/case/CaseAnalysisModal.tsx
// PHOENIX PROTOCOL - DEDICATED MASTER FORENSIC ANALYSIS MODAL V1.1 (CLEAN IMPORTS & 0 TS WARNINGS)

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileSearch, X, Copy, Download, Save, CheckCircle2, 
  Loader2, Maximize2, Minimize2 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface CaseAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle?: string;
  clientName?: string;
  clientPosition?: string;
}

export const CaseAnalysisModal: React.FC<CaseAnalysisModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseTitle = 'Lënda Ligjore',
  clientName = 'Klienti',
  clientPosition = 'DEFENDANT',
}) => {
  const [analysisText, setAnalysisText] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  useEffect(() => {
    if (!isOpen || !caseId) return;

    if (analysisText.length > 50) return;

    let isMounted = true;
    const runForensicAnalysis = async () => {
      setIsLoading(true);
      setAnalysisText('');
      try {
        const prompt = "ANALIZO RASTIN — Gjenero raportin e plotë forenzik të gjithë fashikullit me të gjitha seksionet: analiza e thellë forenzike, matrica e provave, identifikimi i aktorëve, baza statutore, opinioni i gjyqtarit suprem, llogaritja e dëmeve me kamatë 8% dhe plani i veprimit.";
        const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
        
        let accumulated = '';
        for await (const chunk of stream) {
          if (!isMounted) break;
          accumulated += chunk;
          setAnalysisText(accumulated);
          
          if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
          }
        }
      } catch (err) {
        console.error("Master Forensic Stream Failed:", err);
        if (isMounted) {
          setAnalysisText((prev) => prev + "\n\n[Gabim: Shërbimi i analizës forenzike u ndërpre. Ju lutem provoni përsëri.]");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    runForensicAnalysis();

    return () => {
      isMounted = false;
    };
  }, [isOpen, caseId]);

  if (!isOpen) return null;

  const autoLinkedContent = autoLinkLegalCitations(analysisText);

  const handleCopy = () => {
    navigator.clipboard.writeText(analysisText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadTxt = () => {
    const element = document.createElement("a");
    const file = new Blob([analysisText], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `Raporti_Forenzik_${caseTitle.replace(/[^a-zA-Z0-9]/g, '_')}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleArchive = async () => {
    if (!caseId || !analysisText) return;
    setIsArchiving(true);
    setArchiveSuccess(false);
    try {
      await apiService.archiveForensicReport(
        caseId,
        `Raporti Forenzik: ${caseTitle}`,
        analysisText
      );
      setArchiveSuccess(true);
      setTimeout(() => setArchiveSuccess(false), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dështoi ruajtja në arkiv.");
    } finally {
      setIsArchiving(false);
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
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/20 shrink-0 shadow-xs">
                <FileSearch size={20} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                    Raporti i Plotë Forenzik i Lëndës
                  </h3>
                  <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-md bg-primary-start/10 text-primary-start border border-primary-start/20 font-mono">
                    {clientPosition}
                  </span>
                </div>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5">
                  {caseTitle} — {clientName}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
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

          {/* Scanner Progress Banner */}
          {isLoading && (
            <div className="mt-3 px-4 py-2.5 bg-primary-start/10 border border-primary-start/20 rounded-xl flex items-center justify-between gap-3 shrink-0 animate-pulse">
              <div className="flex items-center gap-2 text-xs font-bold text-primary-start">
                <Loader2 size={14} className="animate-spin shrink-0" />
                <span>Sokrati duke skanuar provat, shkeljet dhe bazën statutore në kohë reale...</span>
              </div>
              <span className="text-[10px] font-mono text-primary-start/80 uppercase font-black tracking-wider">
                Analizë e Thellë
              </span>
            </div>
          )}

          {/* Body */}
          <div 
            ref={scrollRef}
            className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 mt-3 bg-surface/50 rounded-2xl border border-main text-text-primary shadow-inner select-text"
          >
            {analysisText.trim().length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 gap-3">
                <Loader2 size={32} className="animate-spin text-primary-start" />
                <p className="text-xs font-bold text-text-secondary">Duke ngarkuar fashikullin dhe filluar analizën forenzike...</p>
              </div>
            ) : (
              <div className="markdown-content prose prose-slate dark:prose-invert max-w-none prose-sm leading-relaxed text-text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {autoLinkedContent}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex flex-wrap items-center justify-between pt-4 mt-3 border-t border-main gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownloadTxt}
                disabled={isLoading || !analysisText}
                className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-40 cursor-pointer"
              >
                <Download size={14} /> Shkarko TXT
              </button>

              <button
                type="button"
                onClick={handleArchive}
                disabled={isArchiving || isLoading || !analysisText}
                className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-primary-start flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-40 cursor-pointer"
              >
                {isArchiving ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : archiveSuccess ? (
                  <CheckCircle2 size={14} className="text-status-success" />
                ) : (
                  <Save size={14} />
                )}
                {archiveSuccess ? 'U ruajt!' : 'Ruaj në Arkiv'}
              </button>
            </div>

            <button
              type="button"
              onClick={handleCopy}
              disabled={isLoading || !analysisText}
              className="h-9 px-5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer"
            >
              <Copy size={13} /> {copied ? 'U Kopjua!' : 'Kopjo Raportin'}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CaseAnalysisModal;