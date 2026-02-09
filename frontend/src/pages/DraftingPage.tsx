// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V8.3 (SOKRATI BRANDING SYNC)
// 1. BRANDING: Synchronized "Thinking" state with ChatPanel.
// 2. FIX: Implemented logic to replace thinking state immediately with real content.
// 3. UI: Touch-optimized controls and Pro Gatekeeper fully intact.

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { Case } from '../data/types'; 
import { useAuth } from '../context/AuthContext';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, Sparkles, RotateCcw, Trash2, Briefcase, ChevronDown, LayoutTemplate,
  FileCheck, Lock, BrainCircuit
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
type TemplateType = 'generic' | 'padi' | 'pergjigje' | 'kunderpadi' | 'kontrate';

interface DraftingJobState {
  status: JobStatus | null;
  result: string | null;
  error: string | null;
}

// --- SUB-COMPONENTS ---

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-1">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
    </span>
);

const AutoResizeTextarea: React.FC<{ 
    value: string; onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void; 
    placeholder?: string; disabled?: boolean; className?: string; minHeight?: number; maxHeight?: number;
}> = ({ value, onChange, placeholder, disabled, className, minHeight = 150, maxHeight = 500 }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; 
            textareaRef.current.style.height = `${Math.min(Math.max(textareaRef.current.scrollHeight, minHeight), maxHeight)}px`;
        }
    }, [value, minHeight, maxHeight]);
    return <textarea ref={textareaRef} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled} className={className} />;
};

const DraftResultRenderer: React.FC<{ text: string }> = ({ text }) => {
    return (
        <div className="markdown-content text-gray-300 text-sm leading-8 font-serif select-text">
             <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                    p: ({node, ...props}) => <p className="mb-6 last:mb-0 text-justify text-gray-200" {...props} />,
                    strong: ({node, ...props}) => <span className="font-bold text-white" {...props} />,
                    h1: ({node, ...props}) => <h1 className="text-2xl font-bold text-white mt-8 mb-6 pb-2 border-b-2 border-white/10 uppercase tracking-widest text-center" {...props} />,
                    h2: ({node, ...props}) => <h2 className="text-xl font-bold text-white mt-6 mb-4 border-b border-white/5 pb-1" {...props} />,
                    h3: ({node, ...props}) => <h3 className="text-lg font-bold text-primary-start mt-4 mb-2 uppercase tracking-wide" {...props} />,
                    blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-accent-start pl-4 py-2 my-6 bg-white/5 italic text-gray-300 rounded-r-lg" {...props} />,
                    a: ({href, children}) => {
                        if (href?.startsWith('doc://')) {
                            return (<span className="inline-flex items-center gap-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-1.5 py-0.5 rounded-[4px] text-xs font-bold tracking-wide mx-0.5 no-underline font-sans not-italic"><FileCheck size={10} />{children}</span>);
                        }
                        return <span className="text-blue-400 font-bold mx-0.5">{children}</span>;
                    },
                }} >{text}</ReactMarkdown>
        </div>
    );
};

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  
  const [context, setContext] = useState(() => localStorage.getItem('drafting_context') || '');
  const [currentJob, setCurrentJob] = useState<DraftingJobState>({ status: null, result: null, error: null });
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  useEffect(() => { if (!isPro) { setSelectedCaseId(undefined); setSelectedTemplate('generic'); } }, [isPro]);
  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { const fetchCases = async () => { try { const res = await apiService.getCases(); setCases(res || []); } catch (e) { console.error(e); } }; fetchCases(); }, []);

  const getCaseDisplayName = (c: Case) => c.title || c.case_name || `Rasti #${c.id.substring(0, 8)}`;

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    
    let accumulatedText = "";

    try {
      const stream = apiService.draftLegalDocumentStream({
          user_prompt: context.trim(),
          document_type: isPro ? selectedTemplate : 'generic',
          case_id: isPro ? selectedCaseId : undefined,
          use_library: isPro && !!selectedCaseId
      });

      for await (const chunk of stream) {
          accumulatedText += chunk;
          setCurrentJob(prev => ({
              ...prev,
              result: accumulatedText
          }));
      }

      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));

    } catch (error: any) {
      console.error("Drafting stream failed:", error);
      setCurrentJob(prev => ({ 
          ...prev, 
          status: 'FAILED', 
          error: error.message || t('drafting.errorStartJob') 
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyResult = async () => { if (currentJob.result) { await navigator.clipboard.writeText(currentJob.result); alert(t('general.copied')); } };
  const handleDownloadResult = () => { if (currentJob.result) { const blob = new Blob([currentJob.result], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `draft-${Date.now()}.txt`; a.click(); } };
  const handleClearResult = () => { if (window.confirm(t('drafting.confirmClear'))) { setCurrentJob({ status: null, result: null, error: null }); } };

  const getStatusDisplay = () => {
    switch(currentJob.status) {
      case 'COMPLETED': return { text: t('drafting.statusCompleted'), color: 'text-green-400', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED': return { text: t('drafting.statusFailed'), color: 'text-red-400', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING': return { text: t('drafting.statusWorking'), color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default: return { text: t('drafting.statusResult'), color: 'text-white', icon: <Sparkles className="h-5 w-5 text-gray-500" /> };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col h-full">
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3"><PenTool className="text-primary-start" />{t('drafting.title')}</h1>
        <p className="text-gray-400 text-sm">{t('drafting.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[700px]">
        {/* INPUT PANEL */}
        <div className="glass-panel flex flex-col h-[500px] lg:h-full p-6 rounded-2xl overflow-hidden shadow-2xl">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2"><FileText className="text-primary-start" size={20} />{t('drafting.configuration')}</h3>
            <form onSubmit={(e) => { e.preventDefault(); runDraftingStream(); }} className="flex flex-col flex-1 gap-4 min-h-0">
                <div className="flex flex-col sm:flex-row gap-4 flex-shrink-0">
                    <div className='flex-1 min-w-0'>
                        <div className="flex items-center justify-between mb-1">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider">{t('drafting.caseLabel')}</label>
                            {!isPro && <span className="flex items-center gap-1 text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20"><Lock size={10} /> PRO</span>}
                        </div>
                        <div className="relative">
                            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select value={selectedCaseId || ''} onChange={(e) => setSelectedCaseId(e.target.value || undefined)} disabled={isSubmitting || !isPro} className={`glass-input w-full pl-10 pr-10 py-3 appearance-none rounded-xl ${!isPro ? 'opacity-50 cursor-not-allowed' : ''}`}>
                                <option value="" className="bg-gray-900">{t('drafting.noCaseSelected')}</option>
                                {isPro && cases.map(c => (<option key={c.id} value={String(c.id)} className="bg-gray-900">{getCaseDisplayName(c)}</option>))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                    <div className='flex-1 min-w-0'>
                        <div className="flex items-center justify-between mb-1">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider">{t('drafting.templateLabel')}</label>
                            {!isPro && <span className="flex items-center gap-1 text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20"><Lock size={10} /> PRO</span>}
                        </div>
                        <div className="relative">
                            <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value as TemplateType)} disabled={isSubmitting || !isPro} className={`glass-input w-full pl-10 pr-10 py-3 appearance-none rounded-xl ${!isPro ? 'opacity-50 cursor-not-allowed' : ''}`}>
                                <option value="generic" className="bg-gray-900">{t('drafting.templateGeneric')}</option>
                                {isPro && (
                                    <>
                                        <option value="padi" className="bg-gray-900">{t('drafting.templatePadi')}</option>
                                        <option value="pergjigje" className="bg-gray-900">{t('drafting.templatePergjigje')}</option>
                                        <option value="kunderpadi" className="bg-gray-900">{t('drafting.templateKunderpadi')}</option>
                                        <option value="kontrate" className="bg-gray-900">{t('drafting.templateKontrate')}</option>
                                    </>
                                )}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                </div>

                <div className="flex-1 flex flex-col min-h-0">
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.instructionsLabel')}</label>
                    <AutoResizeTextarea value={context} onChange={(e) => setContext(e.target.value)} placeholder={t('drafting.promptPlaceholder')} className="glass-input w-full p-4 rounded-xl resize-none text-sm leading-relaxed overflow-y-auto custom-scrollbar flex-1" disabled={isSubmitting} />
                </div>

                <button type="submit" disabled={isSubmitting || !context.trim()} className="w-full py-3 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 active:scale-95">
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  {t('drafting.generateBtn')}
                </button>
            </form>
        </div>

        {/* RESULT PANEL */}
        <div className="glass-panel flex flex-col h-[600px] lg:h-full p-6 rounded-2xl overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/5 flex-shrink-0">
                <h3 className="text-white font-semibold flex items-center gap-2">{statusDisplay.icon}<span className={statusDisplay.color}>{statusDisplay.text}</span></h3>
                <div className="flex gap-2">
                    <button onClick={runDraftingStream} disabled={!currentJob.result || isSubmitting} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors"><RotateCcw size={18}/></button>
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors"><Copy size={18}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors"><Download size={18}/></button>
                    <button onClick={handleClearResult} disabled={!currentJob.result && !currentJob.error} className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg disabled:opacity-30 transition-colors border border-red-500/20"><Trash2 size={18}/></button>
                </div>
            </div>
            {currentJob.error && (<div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4 text-sm text-red-300 flex items-center gap-2 flex-shrink-0"><AlertCircle size={16} />{currentJob.error}</div>)}
            <div className="flex-1 bg-black/20 rounded-xl border border-white/5 p-4 overflow-y-auto custom-scrollbar relative min-h-0">
                {currentJob.result ? (
                    <DraftResultRenderer text={currentJob.result} />
                ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
                        {isSubmitting ? (
                            <AnimatePresence>
                                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                                    <div className="w-12 h-12 rounded-full bg-primary-start flex items-center justify-center shadow-[0_0_20px_rgba(37,99,235,0.4)] mb-4">
                                        <BrainCircuit className="w-6 h-6 text-white" />
                                    </div>
                                    <div className="text-blue-400 font-bold text-sm flex items-center gap-1">
                                        Sokrati duke menduar<ThinkingDots />
                                    </div>
                                </motion.div>
                            </AnimatePresence>
                        ) : (
                            <div className="opacity-50">
                                <FileText className="w-16 h-16 mb-4 mx-auto text-gray-600" />
                                <p className="text-gray-600 text-sm font-medium">{t('drafting.emptyState')}</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;