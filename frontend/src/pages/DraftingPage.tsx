// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V6.4 (CLEAN UI)
// 1. CLEANUP: Removed all visible prompts/constraints. Input box starts empty.
// 2. LOGIC: Sends 'document_type' to backend so the brain handles the rules.

import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { Case } from '../data/types'; 
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, Sparkles, RotateCcw, Trash2, Briefcase, ChevronDown, LayoutTemplate
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'SUCCESS' | 'FAILED' | 'FAILURE';
type TemplateType = 'generic' | 'padi' | 'pergjigje' | 'kunderpadi' | 'kontrate';

interface DraftingJobState {
  jobId: string | null;
  status: JobStatus | null;
  result: string | null;
  error: string | null;
}

// --- AUTO RESIZE TEXTAREA ---
interface AutoResizeTextareaProps {
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    placeholder?: string;
    disabled?: boolean;
    className?: string;
    minHeight?: number;
    maxHeight?: number;
}

const AutoResizeTextarea: React.FC<AutoResizeTextareaProps> = ({ 
    value, onChange, placeholder, disabled, className, minHeight = 150, maxHeight = 500 
}) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; 
            const scrollHeight = textareaRef.current.scrollHeight;
            const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
            textareaRef.current.style.height = `${newHeight}px`;
            textareaRef.current.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
        }
    }, [value, minHeight, maxHeight]);
    return (
        <textarea ref={textareaRef} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled} className={`${className} transition-all duration-200 ease-in-out`} style={{ minHeight: `${minHeight}px` }} />
    );
};

// --- STREAMING MARKDOWN ---
const StreamedMarkdown: React.FC<{ text: string, isNew: boolean, onComplete: () => void }> = ({ text, isNew, onComplete }) => {
    const [displayedText, setDisplayedText] = useState(isNew ? "" : text);
    useEffect(() => {
        if (!isNew) { setDisplayedText(text); return; }
        setDisplayedText(""); 
        let index = 0; const speed = 5; 
        const intervalId = setInterval(() => {
            setDisplayedText((prev) => {
                if (index >= text.length) { clearInterval(intervalId); onComplete(); return text; }
                const nextChar = text.charAt(index); index++; return prev + nextChar;
            });
        }, speed);
        return () => clearInterval(intervalId);
    }, [text, isNew, onComplete]);

    return (
        <div className="markdown-content text-gray-300 text-sm leading-relaxed">
             <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                    p: ({node, ...props}) => <p className="mb-4 last:mb-0 text-justify" {...props} />,
                    strong: ({node, ...props}) => <span className="font-bold text-amber-100" {...props} />,
                    em: ({node, ...props}) => <span className="italic text-gray-400" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-2 my-3 marker:text-primary-500" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal pl-5 space-y-2 my-3 marker:text-primary-500" {...props} />,
                    li: ({node, ...props}) => <li className="pl-1" {...props} />,
                    h1: ({node, ...props}) => <h1 className="text-xl font-bold text-white mt-6 mb-4 border-b border-white/10 pb-2 uppercase tracking-wide text-center" {...props} />,
                    h2: ({node, ...props}) => <h2 className="text-lg font-bold text-white mt-5 mb-3" {...props} />,
                    h3: ({node, ...props}) => <h3 className="text-base font-bold text-gray-200 mt-4 mb-2" {...props} />,
                    blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary-500 pl-4 py-2 my-4 bg-white/5 italic text-gray-400" {...props} />,
                    code: ({node, ...props}) => <code className="bg-black/40 px-1.5 py-0.5 rounded text-xs font-mono text-pink-300" {...props} />,
                    table: ({node, ...props}) => <div className="overflow-x-auto my-4"><table className="min-w-full border-collapse border border-white/10 text-xs" {...props} /></div>,
                    th: ({node, ...props}) => <th className="border border-white/10 px-3 py-2 bg-white/5 font-bold text-left" {...props} />,
                    td: ({node, ...props}) => <td className="border border-white/10 px-3 py-2" {...props} />,
                }} >{displayedText}</ReactMarkdown>
        </div>
    );
};

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const [context, setContext] = useState(() => localStorage.getItem('drafting_context') || '');
  const [currentJob, setCurrentJob] = useState<DraftingJobState>(() => {
      const savedJob = localStorage.getItem('drafting_job');
      return savedJob ? JSON.parse(savedJob) : { jobId: null, status: null, result: null, error: null };
  });
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isResultNew, setIsResultNew] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);

  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { localStorage.setItem('drafting_job', JSON.stringify(currentJob)); }, [currentJob]);
  useEffect(() => { const fetchCases = async () => { try { const userCases = await apiService.getCases(); if (Array.isArray(userCases)) setCases(userCases); else setCases([]); } catch (error) { console.error("DraftingPage: Failed to fetch cases:", error); } }; fetchCases(); }, []);
  useEffect(() => { return () => { if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current); }; }, []);

  const getCaseDisplayName = (c: Case) => {
    if (c.title && c.title.trim().length > 0) return c.title;
    if (c.case_name && c.case_name.trim().length > 0) return c.case_name;
    if (c.case_number) return `Rasti: ${c.case_number}`;
    return `Rasti #${c.id.substring(0, 8)}...`;
  };

  const startPolling = (jobId: string) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    pollingIntervalRef.current = window.setInterval(async () => {
      try {
        const statusResponse = await apiService.getDraftingJobStatus(jobId);
        const newStatus = statusResponse.status as JobStatus; 
        setCurrentJob(prev => ({ ...prev, status: newStatus }));
        if (newStatus === 'COMPLETED' || newStatus === 'SUCCESS') {
          try {
            const resultResponse = await apiService.getDraftingJobResult(jobId);
            const finalResult = resultResponse.document_text || resultResponse.result_text || "";
            setIsResultNew(true); 
            setCurrentJob(prev => ({ ...prev, status: 'COMPLETED', result: finalResult, error: null }));
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
            setIsSubmitting(false);
          } catch (error) {
            setCurrentJob(prev => ({ ...prev, error: t('drafting.errorFetchResult'), status: 'FAILED' }));
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
            setIsSubmitting(false);
          }
        } else if (newStatus === 'FAILED' || newStatus === 'FAILURE') {
          setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: statusResponse.error || t('drafting.errorJobFailed'), result: null }));
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsSubmitting(false);
        }
      } catch (error) { console.warn("Polling error:", error); }
    }, 2000);
  };

  const runDraftingJob = async () => {
    if (!context.trim()) return;
    setIsSubmitting(true);
    setCurrentJob({ jobId: null, status: 'PENDING', result: null, error: null });
    setIsResultNew(false);
    try {
      // PHOENIX FIX: Passing 'document_type' to backend so it knows which hidden template to use
      const jobResponse = await apiService.initiateDraftingJob({ 
          user_prompt: context.trim(), 
          context: context.trim(), 
          case_id: selectedCaseId, 
          use_library: !!selectedCaseId,
          document_type: selectedTemplate // <-- CRITICAL: Sends 'padi', 'kontrate', etc.
      });
      setCurrentJob({ jobId: jobResponse.job_id, status: 'PENDING', result: null, error: null });
      startPolling(jobResponse.job_id);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || t('drafting.errorStartJob');
      setCurrentJob(prev => ({ ...prev, error: errorMessage, status: 'FAILED' }));
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); runDraftingJob(); };
  const handleCopyResult = async () => { if (currentJob.result) { await navigator.clipboard.writeText(currentJob.result); alert(t('general.copied')); } };
  const handleDownloadResult = () => { if (currentJob.result) { const blob = new Blob([currentJob.result], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `draft-${new Date().getTime()}.txt`; document.body.appendChild(a); a.click(); document.body.removeChild(a); } };
  const handleClearResult = () => { if (window.confirm(t('drafting.confirmClear'))) { if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current); setCurrentJob({ jobId: null, status: null, result: null, error: null }); setIsResultNew(false); } };

  const getStatusDisplay = () => {
    switch(currentJob.status) {
      case 'COMPLETED': case 'SUCCESS': return { text: t('drafting.statusCompleted'), color: 'text-green-400', icon: <CheckCircle className="h-5 w-5 text-green-400" /> };
      case 'FAILED': case 'FAILURE': return { text: t('drafting.statusFailed'), color: 'text-red-400', icon: <AlertCircle className="h-5 w-5 text-red-400" /> };
      case 'PROCESSING': case 'PENDING': return { text: t('drafting.statusWorking'), color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse text-yellow-400" /> };
      default: return { text: t('drafting.statusResult'), color: 'text-white', icon: <Sparkles className="h-5 w-5 text-gray-500" /> };
    }
  };
  const statusDisplay = getStatusDisplay();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-[calc(100vh-theme(spacing.20))] h-auto flex flex-col">
      <style>{` .custom-textarea-scroll::-webkit-scrollbar { width: 8px; } .custom-textarea-scroll::-webkit-scrollbar-track { background: transparent; } .custom-textarea-scroll::-webkit-scrollbar-thumb { background-color: rgba(255, 255, 255, 0.2); border-radius: 4px; } .custom-textarea-scroll::-webkit-scrollbar-thumb:hover { background-color: rgba(255, 255, 255, 0.3); } `}</style>
      
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3"><PenTool className="text-primary-500" />{t('drafting.title')}</h1>
        <p className="text-gray-400 text-sm">{t('drafting.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[600px] flex-1">
        
        {/* INPUT PANEL */}
        <div className="flex flex-col h-[500px] lg:h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl overflow-hidden">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2 flex-shrink-0"><FileText className="text-primary-400" size={20} />{t('drafting.configuration')}</h3>
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4 min-h-0">
                <div className="flex flex-col sm:flex-row gap-4 flex-shrink-0">
                    <div className='flex-1 min-w-0'>
                        <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.caseLabel')}</label>
                        <div className="relative">
                            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select value={selectedCaseId || ''} onChange={(e) => setSelectedCaseId(e.target.value || undefined)} disabled={isSubmitting} className="w-full bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none text-sm pl-10 pr-10 py-3 appearance-none transition-colors cursor-pointer truncate">
                                <option value="" className="bg-gray-900 text-gray-400">{t('drafting.noCaseSelected')}</option>
                                {cases.length > 0 ? ( cases.map(c => (<option key={c.id} value={String(c.id)} className="bg-gray-900 text-white">{getCaseDisplayName(c)}</option>)) ) : ( <option value="" disabled className="bg-gray-900 text-gray-500 italic">{t('drafting.noCasesFound')}</option> )}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                    <div className='flex-1 min-w-0'>
                        <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.templateLabel')}</label>
                        <div className="relative">
                            <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value as TemplateType)} disabled={isSubmitting} className="w-full bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none text-sm pl-10 pr-10 py-3 appearance-none transition-colors cursor-pointer">
                                <option value="generic" className="bg-gray-900 text-gray-400">{t('drafting.templateGeneric')}</option>
                                <option value="padi" className="bg-gray-900 text-white">{t('drafting.templatePadi')}</option>
                                <option value="pergjigje" className="bg-gray-900 text-white">{t('drafting.templatePergjigje')}</option>
                                <option value="kunderpadi" className="bg-gray-900 text-white">{t('drafting.templateKunderpadi')}</option>
                                <option value="kontrate" className="bg-gray-900 text-white">{t('drafting.templateKontrate')}</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                </div>

                <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider flex-shrink-0">{t('drafting.instructionsLabel')}</label>
                    <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                        <AutoResizeTextarea value={context} onChange={(e) => setContext(e.target.value)} placeholder={t('drafting.promptPlaceholder')} className="w-full p-4 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none resize-none text-sm leading-relaxed custom-textarea-scroll custom-scrollbar" disabled={isSubmitting} minHeight={150} maxHeight={500} />
                    </div>
                </div>

                <button type="submit" disabled={isSubmitting || !context.trim()} className="w-full py-3 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-2 flex-shrink-0">
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  {t('drafting.generateBtn')}
                </button>
            </form>
        </div>

        {/* RESULT PANEL */}
        <div className="flex flex-col h-[500px] lg:h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl overflow-hidden">
            <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/5 flex-shrink-0">
                <h3 className="text-white font-semibold flex items-center gap-2">{statusDisplay.icon}<span className={statusDisplay.color}>{statusDisplay.text}</span></h3>
                <div className="flex gap-2">
                    <button onClick={runDraftingJob} disabled={!currentJob.result || isSubmitting} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.regenerate')}><RotateCcw size={18}/></button>
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.copyTitle')}><Copy size={18}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.downloadTitle')}><Download size={18}/></button>
                    <button onClick={handleClearResult} disabled={!currentJob.result && !currentJob.error} className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg disabled:opacity-30 transition-colors border border-red-500/20" title={t('drafting.clearTitle')}><Trash2 size={18}/></button>
                </div>
            </div>
            {currentJob.error && (<div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4 text-sm text-red-300 flex items-center gap-2 flex-shrink-0"><AlertCircle size={16} />{currentJob.error}</div>)}
            <div className="flex-1 bg-black/50 rounded-xl border border-white/5 p-4 overflow-y-auto custom-scrollbar relative min-h-0">
                {currentJob.result ? (<StreamedMarkdown text={currentJob.result} isNew={isResultNew} onComplete={() => setIsResultNew(false)} />) : (<div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600 opacity-50">{isSubmitting || (currentJob.status === 'PENDING' || currentJob.status === 'PROCESSING') ? (<><RefreshCw className="w-12 h-12 animate-spin mb-4 text-primary-500" /><p>{t('drafting.generatingMessage')}</p></>) : (<><FileText className="w-16 h-16 mb-4" /><p>{t('drafting.emptyState')}</p></>)}</div>)}
            </div>
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;