// FILE: frontend/src/components/case/StandardCaseAnalysisModal.tsx
// PHOENIX PROTOCOL - UNIFIED FAST CASE ANALYSIS MODAL V5.0 (TRUE ATOMIC MONGODB CASCADE WIPEOUT)
// ZERO TS WARNINGS • POWERED BY FAST MODEL (GPT-4O-MINI) • TOTAL PURGE SYNC • 100% COMPLETE CODE

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Briefcase, X, Copy, CheckCircle2, 
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown, RefreshCw, Sparkles, Lock, AlertCircle
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface StandardCaseAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle?: string;
  clientName?: string;
  isAnalysisDirty?: boolean;
}

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 }
];

export const StandardCaseAnalysisModal: React.FC<StandardCaseAnalysisModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseTitle = 'Lënda Ligjore',
  clientName = 'Klienti',
  isAnalysisDirty = false,
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

  // Ngarkimi i pasqyrës ekzistuese të lëndës (0ms Cache)
  useEffect(() => {
    if (isOpen && caseId) {
      apiService.getCaseDetails(caseId)
        .then((details: any) => {
          const savedSummary = details?.latest_deep_analysis || details?.latest_analysis || details?.standard_summary || '';
          if (savedSummary && typeof savedSummary === 'string' && savedSummary.trim().length > 50) {
            setReportContent(savedSummary);
          } else {
            setReportContent('');
          }
        })
        .catch(() => {
          setReportContent('');
        });
    }
  }, [isOpen, caseId]);

  // Auto-scroll gjatë kohës që gjenerohet teksti i ri
  useEffect(() => {
    if (!isUserScrolledUpRef.current && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [reportContent, isLoading]);

  // Gjenerimi i shpejtë dhe ekonomik i të gjithë fashikullit me GPT-4o-Mini
  const handleGenerateAnalysis = useCallback(async () => {
    if (!caseId || isLoading || isPurging) return;

    setIsLoading(true);
    setReportContent('');
    isUserScrolledUpRef.current = false;

    const fastPrompt = `[ANALIZË STANDARDE E RASTIT — PËRMBLEDHJE EKZEKUTIVE E LËNDËS]
Lënda: "${caseTitle}" | Klienti: "${clientName}"
DETYRË: Kryej analizën e qartë, praktike dhe të unifikuar të të GJITHË fashikullit të lëndës (me të gjitha shkresat e administruara së bashku) për përdorim të shpejtë ligjor:
1. PASAPORTA E LËNDËS DHE PALËT: Gjendja procedurale, natyra e mosmarrëveshjes, roli i palëve dhe organi kompetent.
2. KRONOLOGJIA DHE FAKTET KRYESORE: Rindërtimi thelbësor i fakteve dhe ngjarjeve kryesore nga të gjitha shkresat e dosjes.
3. BAZA KRYESORE NORMATIVE: Nenet dhe ligjet themelore pozitive të Kosovës (LPK, KPK, LMD, etj.) që rregullojnë këtë rast.
4. VLERËSIMI I RREZIQEVE DHE HAPAT E ARDHSHËM: Vlerësimi objektiv i pozitës së klientit dhe veprimet e rekomanduara me afatet përkatëse.
Rregull: Përgjigju qartë, në mënyrë të unifikuar për të gjithë lëndën, me gjuhë standarde juridike shqipe.`;

    try {
      const stream = apiService.sendChatMessageStream(
        caseId,
        fastPrompt,
        undefined,
        'ks',
        'FAST',
        'automatic',
        false
      );

      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setReportContent(accumulated);
      }
    } catch (err: any) {
      console.error("Standard Case Analysis Error:", err);
      alert("Ndodhi një gabim gjatë pasqyrës së lëndës.");
    } finally {
      setIsLoading(false);
    }
  }, [caseId, caseTitle, clientName, isLoading, isPurging]);

  // TOTAL CASCADE WIPEOUT: Asgjësim i përhershëm në MongoDB Atlas
  const handleClearContent = async () => {
    if (!reportContent || !caseId || isPurging) return;
    const confirmWipe = window.confirm("A jeni i sigurt që dëshironi të asgjësoni plotësisht pasqyrën e lëndës nga serveri (Total Cascade Wipeout)?");
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await apiService.axiosInstance.post(`/cases/${caseId}/analysis/clear`);
      setReportContent('');
    } catch (err) {
      console.error("Could not purge case analysis on MongoDB:", err);
      alert("Dështoi asgjësimi i analizës në server.");
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

  // Mbrojtja Anti-Abuzim: Zhbllokohet vetëm nëse është bosh ose nëse fashikulli ka ndryshuar
  const isActionAllowed = !reportContent || isAnalysisDirty;

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
          {/* Header Bar */}
          <div className="flex items-center justify-between pb-3.5 border-b border-main shrink-0 gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 bg-primary-start/15 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0">
                <Briefcase className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                    Pasqyra e Rastit
                  </h3>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[10px] font-bold font-mono uppercase">
                    E Shpejtë • GPT-4o
                  </span>
                  {isAnalysisDirty && reportContent && (
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[10px] font-bold uppercase flex items-center gap-1">
                      <AlertCircle size={10} /> Fashikull i Përditësuar
                    </span>
                  )}
                </div>
                <p className="text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {caseTitle} • {clientName}
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

              {/* Trash: TOTAL CASCADE WIPEOUT NË MONGODB */}
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

          {/* Body Content */}
          <div 
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 my-2 bg-surface/30 rounded-2xl border border-main text-text-primary select-text relative flex flex-col"
          >
            <style>{`
              .fast-case-audit p, .fast-case-audit li {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .fast-case-audit h1, .fast-case-audit h2, .fast-case-audit h3 {
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
                  <h4 className="text-base font-bold text-text-primary">Pasqyra Ekzekutive e Rastit</h4>
                  <p className="text-xs text-text-muted max-w-md mt-1">
                    Gjeneroni një analizë të shpejtë të gjithë fashikullit të lëndës me pikat kyçe faktike dhe procedurale nga të gjitha shkresat.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateAnalysis}
                  className="px-6 py-3 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-md flex items-center gap-2 cursor-pointer transition-all hover-lift"
                >
                  <Sparkles size={14} />
                  <span>Gjenero Pasqyrën e Rastit</span>
                </button>
              </div>
            ) : isLoading && !reportContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto space-y-3">
                <Loader2 className="w-9 h-9 animate-spin text-primary-start" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Duke analizuar fashikullin e lëndës me shpejtësi...
                </p>
              </div>
            ) : (
              <div className="markdown-content fast-case-audit prose prose-slate dark:prose-invert max-w-none text-text-primary">
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
              <div className="flex items-center gap-2">
                {isActionAllowed ? (
                  <button
                    type="button"
                    onClick={handleGenerateAnalysis}
                    className="h-9 px-3.5 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 rounded-xl text-xs font-bold text-primary-start flex items-center gap-1.5 cursor-pointer transition-all"
                    title="Përditëso analizën pasi ka shkresa të reja në lëndë"
                  >
                    <RefreshCw size={12} />
                    <span>Përditëso Analizën</span>
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface border border-main text-text-muted text-xs font-medium" title="Fashikulli nuk ka ndryshuar">
                    <Lock size={12} className="text-text-muted" />
                    <span className="hidden sm:inline">Analiza është e përditësuar (Shtoni ose hiqni një shkresë për ri-analizim)</span>
                    <span className="sm:hidden">E përditësuar</span>
                  </div>
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
                <span>{copied ? 'U Kopjua!' : 'Kopjo Pasqyrën e Rastit'}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default StandardCaseAnalysisModal;