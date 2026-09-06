// FILE: frontend/src/components/case/StandardDocumentAuditModal.tsx
// PHOENIX PROTOCOL - UNIFIED FAST DOCUMENT AUDIT MODAL V4.0 (TRUE ATOMIC MONGODB CASCADE WIPEOUT)
// ZERO TS WARNINGS • POWERED BY FAST MODEL (GPT-4O-MINI) • TOTAL PURGE SYNC • 100% COMPLETE CODE

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, X, Copy, CheckCircle2, 
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown, Sparkles, Lock
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface StandardDocumentAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  documentId: string;
  documentName: string;
  clientName?: string;
}

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 }
];

export const StandardDocumentAuditModal: React.FC<StandardDocumentAuditModalProps> = ({
  isOpen,
  onClose,
  caseId,
  documentId,
  documentName,
  clientName = 'Klienti',
}) => {
  const [reportContent, setReportContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(1);
  const activeFont = FONT_LEVELS[fontLevelIndex];
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  // Leximi i pasqyrës ekzistuese nga MongoDB (0ms Cache)
  useEffect(() => {
    if (isOpen && caseId && documentId) {
      apiService.getDocuments(caseId)
        .then((docs: any[]) => {
          const currentDoc = (docs || []).find((d: any) => String(d.id || d._id) === String(documentId));
          const savedAudit = currentDoc?.latest_analysis || currentDoc?.latest_forensic_audit || currentDoc?.standard_analysis || '';
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
  }, [isOpen, caseId, documentId]);

  // Auto-scroll gjatë kohës që gjenerohet teksti i ri
  useEffect(() => {
    if (!isUserScrolledUpRef.current && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [reportContent, isLoading]);

  // Gjenerimi i shpejtë dhe ekonomik me GPT-4o-Mini (FAST Mode)
  const handleGenerateAudit = useCallback(async () => {
    if (!caseId || !documentId || isLoading || isPurging) return;

    setIsLoading(true);
    setReportContent('');
    isUserScrolledUpRef.current = false;

    const fastPrompt = `[ANALIZË STANDARDE E SHKRESËS — PËRMBLEDHJE EKZEKUTIVE]
Dokumenti: "${documentName}"
DETYRË: Kryej analizën e qartë, praktike dhe koncize të kësaj shkrese për përdorim të shpejtë ligjor:
1. IDENTITETI DHE LLOJI I SHKRESËS: Çfarë akti është, organi lëshues/nxjerrës, data dhe palët e përfshira.
2. PËRMBLEDHJA E THELBISË: Çfarë kërkohet, vendoset ose pretendohet në këtë shkresë.
3. BAZA KRYESORE LIGJORE: Dispozitat dhe nenet kryesore të legjislacionit të Kosovës që përmenden ose zbatohen.
4. VLERËSIMI PROCEDURAL & AFATET: Rreziqet e menjëhershme, afatet ligjore prekluzive dhe hapat e rekomanduar.
Rregull: Përgjigju qartë, pa vonesa, në gjuhë standarde juridike shqipe.`;

    try {
      const stream = apiService.sendChatMessageStream(
        caseId,
        fastPrompt,
        [documentId],
        'ks',
        'FAST',
        'document',
        false
      );

      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setReportContent(accumulated);
      }
    } catch (err: any) {
      console.error("Standard Doc Audit Error:", err);
      alert("Ndodhi një gabim gjatë pasqyrës së shkresës.");
    } finally {
      setIsLoading(false);
    }
  }, [caseId, documentId, documentName, isLoading, isPurging]);

  // TOTAL CASCADE WIPEOUT: Asgjësim atomik me $unset në MongoDB Atlas
  const handleClearContent = async () => {
    if (!reportContent || !caseId || !documentId || isPurging) return;
    const confirmWipe = window.confirm("A jeni i sigurt që dëshironi të asgjësoni plotësisht pasqyrën e kësaj shkrese nga serveri (Total Cascade Wipeout)?");
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await apiService.axiosInstance.post(`/cases/${caseId}/documents/${documentId}/clear-audit`);
      setReportContent('');
    } catch (err) {
      console.error("Could not purge document audit on MongoDB:", err);
      alert("Dështoi asgjësimi i pasqyrës së shkresës në server.");
    } finally {
      setIsPurging(false);
    }
  };

  const handleCopy = () => {
    if (!reportContent) return;
    navigator.clipboard.writeText(reportContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
              : 'h-[92vh] max-w-4xl max-h-[850px] rounded-2xl sm:rounded-3xl border border-main'
          } p-4 sm:p-6 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-primary-start/15 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                    Pasqyra e Shkresës
                  </h3>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[10px] font-bold font-mono uppercase">
                    E Shpejtë • GPT-4o
                  </span>
                </div>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {documentName} • {clientName}
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

              {/* Trash: TOTAL CASCADE WIPEOUT NË MONGODB ATLAS */}
              {reportContent && (
                <button
                  type="button"
                  onClick={handleClearContent}
                  disabled={isPurging}
                  className="p-2 text-text-muted hover:text-rose-500 hover:bg-rose-500/10 rounded-xl transition-colors cursor-pointer"
                  title="Asgjëso përfundimisht nga MongoDB Atlas (Total Wipeout)"
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
              .fast-doc-audit p, .fast-doc-audit li {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .fast-doc-audit h1, .fast-doc-audit h2, .fast-doc-audit h3 {
                color: var(--text-primary);
                font-weight: 800;
                margin-top: 1em;
                margin-bottom: 0.4em;
              }
            `}</style>

            {!reportContent && !isLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <Sparkles size={28} />
                </div>
                <div>
                  <h4 className="text-base font-bold text-text-primary">Pasqyra Ligjore e Shkresës</h4>
                  <p className="text-xs text-text-muted max-w-md mt-1">
                    Gjeneroni një analizë të shpejtë dhe të qartë të këtij dokumenti me identifikimin e neneve dhe afateve thelbësore.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateAudit}
                  disabled={isPurging}
                  className="px-6 py-3 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-md flex items-center gap-2 cursor-pointer transition-all hover-lift disabled:opacity-50"
                >
                  <Sparkles size={14} />
                  <span>Gjenero Pasqyrën e Shkresës</span>
                </button>
              </div>
            ) : isLoading && !reportContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto space-y-3">
                <Loader2 className="w-9 h-9 animate-spin text-primary-start" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Duke analizuar shkresën me shpejtësi...
                </p>
              </div>
            ) : (
              <div className="markdown-content fast-doc-audit prose prose-slate dark:prose-invert max-w-none text-text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {autoLinkLegalCitations(reportContent)}
                </ReactMarkdown>
              </div>
            )}

            {/* Butoni Lundrues për lëvizje në fund të raportit */}
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

          {/* Bottom Actions me Mbrojtje Anti-Abuzim */}
          <div className="flex items-center justify-between pt-3 border-t border-main gap-3 shrink-0">
            {reportContent && !isLoading && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium" title="Shkresa është analizuar tashmë">
                <Lock size={12} className="text-text-muted" />
                <span className="hidden sm:inline">Shkresa është e analizuar (Pastrojeni me kosh për ta asgjësuar nga serveri)</span>
                <span className="sm:hidden">E analizuar</span>
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
                <span>{copied ? 'U Kopjua!' : 'Kopjo Përmbledhjen'}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default StandardDocumentAuditModal;