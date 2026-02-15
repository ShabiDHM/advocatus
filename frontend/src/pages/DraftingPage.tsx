// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V9.5 (CLEAN HEADER ACTIONS)
// 1. REMOVED: "Save to Case" button and logic.
// 2. MOVED: "Save to Archive" to the top action bar.
// 3. IMPROVED: Consistent button styling in the Result header.
// 4. RETAINED: Professional A4 Legal Document rendering.

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { Case } from '../data/types'; 
import { useAuth } from '../context/AuthContext';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, Sparkles, RotateCcw, Trash2, Briefcase, ChevronDown, LayoutTemplate,
  FileCheck, Lock, BrainCircuit, Archive, FilePlus, Printer} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
type TemplateType = 'generic' | 'padi' | 'pergjigje' | 'kunderpadi' | 'kontrate';

interface DraftingJobState {
  status: JobStatus | null;
  result: string | null;
  error: string | null;
  characterCount?: number;
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
        <div className="bg-white text-black min-h-[1123px] w-full p-12 sm:p-20 shadow-2xl mx-auto rounded-sm ring-1 ring-gray-200">
             <div className="markdown-content text-[11pt] leading-[1.6] font-serif select-text text-gray-900">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    components={{
                        p: ({node, ...props}) => <p className="mb-4 text-justify" {...props} />,
                        strong: ({node, ...props}) => <span className="font-bold text-black" {...props} />,
                        h1: ({node, ...props}) => <h1 className="text-xl font-bold text-black mt-4 mb-6 pb-2 border-b border-black uppercase tracking-tight text-center" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-lg font-bold text-black mt-6 mb-3 border-b border-gray-200 pb-1" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-md font-bold text-black mt-4 mb-2 uppercase" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc ml-6 mb-4 space-y-1" {...props} />,
                        ol: ({node, ...props}) => <ol className="list-decimal ml-6 mb-4 space-y-1" {...props} />,
                        blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-black pl-4 py-1 my-4 italic bg-gray-50 rounded-sm" {...props} />,
                        hr: () => <hr className="my-8 border-gray-300" />,
                        a: ({href, children}) => {
                            if (href?.startsWith('doc://')) {
                                return (<span className="inline-flex items-center gap-1 bg-gray-100 text-black border border-gray-300 px-1.5 py-0.5 rounded-[2px] text-[10px] font-bold tracking-wide mx-0.5 no-underline font-sans align-middle"><FileCheck size={10} />{children}</span>);
                            }
                            return <span className="text-black underline font-bold">{children}</span>;
                        },
                    }} 
                >
                    {text}
                </ReactMarkdown>
             </div>
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
  const [, setShowTemplateInfo] = useState(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  useEffect(() => { if (!isPro) { setSelectedCaseId(undefined); setSelectedTemplate('generic'); } }, [isPro]);
  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { const fetchCases = async () => { try { const res = await apiService.getCases(); setCases(res || []); } catch (e) { console.error(e); } }; fetchCases(); }, []);

  const getCaseDisplayName = (c: Case) => c.title || c.case_name || `Rasti #${c.id.substring(0, 8)}`;

  const handleAutofillCase = async () => {
    if (!selectedCaseId) return;
    const caseData = cases.find(c => c.id === selectedCaseId);
    if (!caseData) return;

    let autofillText = t('drafting.autofillPrompt', { caseTitle: caseData.title || caseData.case_number });
    if (caseData.client) {
      autofillText += `\n\n${t('drafting.clientLabel', 'Klienti')}: ${caseData.client.name || 'N/A'}`;
      if (caseData.client.email) autofillText += `\nEmail: ${caseData.client.email}`;
      if (caseData.client.phone) autofillText += `\nTel: ${caseData.client.phone}`;
    }
    setContext(prev => prev ? prev + '\n\n' + autofillText : autofillText);
  };

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setSaveSuccess(null);
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
          setCurrentJob(prev => ({ ...prev, result: accumulatedText, characterCount: accumulatedText.length }));
      }
      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));
    } catch (error: any) {
      console.error("Drafting stream failed:", error);
      setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: error.message || t('drafting.errorStartJob') }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveToArchive = async () => {
    if (!currentJob.result) return;
    setSaving(true);
    setSaveSuccess(null);
    try {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const fileName = `draft-${selectedTemplate}-${Date.now()}.txt`;
      const file = new File([blob], fileName, { type: 'text/plain' });
      await apiService.uploadArchiveItem(file, fileName, 'DRAFT', selectedCaseId);
      setSaveSuccess(t('drafting.savedToArchive'));
    } catch (err: any) {
      alert(err.message || t('drafting.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleCopyResult = async () => { if (currentJob.result) { await navigator.clipboard.writeText(currentJob.result); alert(t('general.copied')); } };
  const handleDownloadResult = () => { if (currentJob.result) { const blob = new Blob([currentJob.result], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `draft-${Date.now()}.txt`; a.click(); } };
  const handleClearResult = () => { if (window.confirm(t('drafting.confirmClear'))) { setCurrentJob({ status: null, result: null, error: null }); setSaveSuccess(null); } };

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
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col h-screen max-h-screen overflow-hidden">
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3"><PenTool className="text-primary-start" />{t('drafting.title')}</h1>
        <p className="text-gray-400 text-sm">{t('drafting.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
        {/* INPUT PANEL */}
        <div className="lg:col-span-4 glass-panel flex flex-col p-6 rounded-2xl shadow-2xl overflow-hidden border border-white/10">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2 flex-shrink-0"><FileText className="text-primary-start" size={20} />{t('drafting.configuration')}</h3>
            <form onSubmit={(e) => { e.preventDefault(); runDraftingStream(); }} className="flex flex-col flex-1 gap-4 min-h-0">
                <div className="space-y-4 flex-shrink-0">
                    <div>
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
                        {selectedCaseId && isPro && (
                            <button type="button" onClick={handleAutofillCase} className="mt-1 text-xs text-primary-start hover:text-primary-end transition-colors flex items-center gap-1">
                                <FilePlus size={12} /> {t('drafting.autofill')}
                            </button>
                        )}
                    </div>
                    <div>
                        <div className="flex items-center justify-between mb-1">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider">{t('drafting.templateLabel')}</label>
                            {!isPro && <span className="flex items-center gap-1 text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20"><Lock size={10} /> PRO</span>}
                        </div>
                        <div className="relative">
                            <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select 
                                value={selectedTemplate} 
                                onChange={(e) => {
                                    const val = e.target.value as TemplateType;
                                    setSelectedTemplate(val);
                                    setShowTemplateInfo(true);
                                }} 
                                onFocus={() => setShowTemplateInfo(true)}
                                onBlur={() => setTimeout(() => setShowTemplateInfo(false), 200)}
                                disabled={isSubmitting || !isPro} 
                                className={`glass-input w-full pl-10 pr-10 py-3 appearance-none rounded-xl ${!isPro ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
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
                    <AutoResizeTextarea 
                        value={context} 
                        onChange={(e) => setContext(e.target.value)} 
                        placeholder={t('drafting.promptPlaceholder')} 
                        className="glass-input w-full p-4 rounded-xl resize-none text-sm leading-relaxed overflow-y-auto custom-scrollbar flex-1 border border-white/5" 
                        disabled={isSubmitting} 
                    />
                </div>

                <button type="submit" disabled={isSubmitting || !context.trim()} className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 active:scale-[0.98] flex-shrink-0">
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  {t('drafting.generateBtn')}
                </button>
            </form>
        </div>

        {/* RESULT PANEL */}
        <div className="lg:col-span-8 flex flex-col h-full rounded-2xl overflow-hidden shadow-2xl bg-[#12141c] border border-white/5">
            <div className="flex justify-between items-center p-4 bg-black/40 border-b border-white/5 flex-shrink-0">
                <div className="flex items-center gap-3">
                   <div className={`${statusDisplay.color} p-2 bg-white/5 rounded-lg`}>{statusDisplay.icon}</div>
                   <div>
                        <h3 className="text-white text-sm font-semibold leading-none mb-1">{statusDisplay.text}</h3>
                        <p className="text-[10px] text-gray-500 uppercase tracking-widest">{t('drafting.legalPreview') || 'Professional Legal Draft'}</p>
                   </div>
                </div>
                <div className="flex gap-2">
                    <button onClick={runDraftingStream} disabled={!currentJob.result || isSubmitting} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-all" title={t('drafting.regenerate')}><RotateCcw size={18}/></button>
                    <button onClick={handleSaveToArchive} disabled={!currentJob.result || saving} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-secondary-start disabled:opacity-30 transition-all" title={t('drafting.saveToArchive')}>
                        {saving ? <RefreshCw className="animate-spin" size={18}/> : <Archive size={18}/>}
                    </button>
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-all" title={t('general.copy')}><Copy size={18}/></button>
                    <button onClick={() => window.print()} disabled={!currentJob.result} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-all" title={t('general.print')}><Printer size={18}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-all" title={t('general.download')}><Download size={18}/></button>
                    <button onClick={handleClearResult} disabled={!currentJob.result && !currentJob.error} className="p-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg disabled:opacity-30 transition-all border border-red-500/20" title={t('general.clear')}><Trash2 size={18}/></button>
                </div>
            </div>

            <div className="flex-1 bg-[#0f1117] overflow-y-auto custom-scrollbar p-8 sm:p-12 relative min-h-0">
                <div className="max-w-[850px] mx-auto">
                    {currentJob.error && (<div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6 text-sm text-red-300 flex items-center gap-3"><AlertCircle size={20} />{currentJob.error}</div>)}
                    {saveSuccess && (<div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 mb-6 text-sm text-green-300 flex items-center gap-3"><CheckCircle size={20} />{saveSuccess}</div>)}
                    
                    {currentJob.result ? (
                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="pb-12">
                            <DraftResultRenderer text={currentJob.result} />
                        </motion.div>
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
                            {isSubmitting ? (
                                <AnimatePresence>
                                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center">
                                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-[0_0_30px_rgba(37,99,235,0.4)] mb-6">
                                            <BrainCircuit className="w-8 h-8 text-white animate-pulse" />
                                        </div>
                                        <div className="text-xl text-white font-bold flex items-center gap-2">
                                            {t('drafting.thinking')}<ThinkingDots />
                                        </div>
                                        {currentJob.characterCount && (
                                            <p className="text-sm text-gray-500 mt-3 font-mono">Generating: {currentJob.characterCount} chars...</p>
                                        )}
                                    </motion.div>
                                </AnimatePresence>
                            ) : (
                                <div className="opacity-20 flex flex-col items-center">
                                    <div className="w-24 h-24 border-2 border-dashed border-gray-600 rounded-full flex items-center justify-center mb-6">
                                        <FileText className="w-10 h-10 text-gray-600" />
                                    </div>
                                    <p className="text-gray-400 text-lg font-medium">{t('drafting.emptyState')}</p>
                                    <p className="text-gray-600 text-sm mt-2 max-w-xs">{t('drafting.emptyHint') || 'Provide instructions on the left to start drafting your legal document.'}</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;