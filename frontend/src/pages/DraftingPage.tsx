// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V10.8 (SCROLLBAR FIX)
// 1. FIXED: Double scrollbars removed. "Udhëzimet" now has a single, internal scrollbar.
// 2. FIXED: Textarea fills the available vertical space (h-full) instead of auto-resizing.
// 3. RETAINED: Custom dark/blue scrollbar styling.
// 4. RETAINED: All functional logic and mobile responsiveness.

import React, { useState, useEffect, useMemo } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { Case } from '../data/types'; 
import { useAuth } from '../context/AuthContext';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, Sparkles, RotateCcw, Trash2, Briefcase, ChevronDown, LayoutTemplate,
  FileCheck, Lock, BrainCircuit, Archive } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- CUSTOM SCROLLBAR STYLES ---
const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: rgba(17, 24, 39, 0.5); /* Dark background */
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(59, 130, 246, 0.5); /* Primary Blue transparent */
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(59, 130, 246, 0.8); /* Primary Blue solid on hover */
  }
  /* For Firefox */
  .custom-scrollbar {
    scrollbar-width: thin;
    scrollbar-color: rgba(59, 130, 246, 0.5) rgba(17, 24, 39, 0.5);
  }
`;

type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

type TemplateType = 
  | 'generic' | 'padi' | 'pergjigje' | 'kunderpadi' | 'ankese' | 'prapësim' 
  | 'nda' | 'mou' | 'shareholders' | 'sla' 
  | 'employment_contract' | 'termination_notice' | 'warning_letter' 
  | 'terms_conditions' | 'privacy_policy' 
  | 'lease_agreement' | 'sales_purchase' 
  | 'power_of_attorney';

interface DraftingJobState {
  status: JobStatus | null;
  result: string | null;
  error: string | null;
  characterCount?: number;
}

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-1">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
    </span>
);

const DraftResultRenderer: React.FC<{ text: string }> = ({ text }) => {
    return (
        <div className="bg-white text-black min-h-[1123px] w-full p-6 sm:p-16 shadow-2xl mx-auto rounded-sm ring-1 ring-gray-200 overflow-x-hidden">
             <div className="markdown-content text-[11.5pt] leading-[1.7] font-serif select-text text-gray-900 break-words">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    components={{
                        p: ({node, ...props}) => {
                            const content = String(props.children);
                            if (content.includes('gjeneruar nga AI')) {
                                return <p className="mt-12 pt-4 border-t border-gray-100 text-[9pt] italic text-gray-400 text-center" {...props} />;
                            }
                            return <p className="mb-5 text-justify" {...props} />;
                        },
                        strong: ({node, ...props}) => <span className="font-bold text-black tracking-tight" {...props} />,
                        h1: ({node, ...props}) => <h1 className="text-base sm:text-lg font-bold text-black mt-2 mb-8 text-center uppercase tracking-normal border-b-2 border-black pb-2 leading-tight" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-[12pt] font-bold text-black mt-8 mb-4 uppercase border-b border-gray-200 pb-1" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-[11.5pt] font-bold text-black mt-6 mb-2 underline decoration-1 underline-offset-4" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc ml-6 sm:ml-8 mb-5 space-y-2" {...props} />,
                        ol: ({node, ...props}) => <ol className="list-decimal ml-6 sm:ml-8 mb-5 space-y-2" {...props} />,
                        blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-300 pl-4 sm:pl-6 py-2 my-6 italic bg-gray-50 text-gray-700 rounded-sm" {...props} />,
                        hr: () => <hr className="my-10 border-gray-200" />,
                        a: ({href, children}) => {
                            if (href?.startsWith('doc://')) {
                                return (<span className="inline-flex items-center gap-1 bg-blue-50 text-blue-800 border border-blue-100 px-2 py-0.5 rounded-[2px] text-[10px] font-bold tracking-wide mx-0.5 no-underline font-sans align-middle uppercase"><FileCheck size={10} />{children}</span>);
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
  useTranslation(); 
  const { user } = useAuth();
  
  const [context, setContext] = useState(() => localStorage.getItem('drafting_context') || '');
  const [currentJob, setCurrentJob] = useState<DraftingJobState>({ status: null, result: null, error: null });
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  useEffect(() => { if (!isPro) { setSelectedCaseId(undefined); setSelectedTemplate('generic'); } }, [isPro]);
  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { const fetchCases = async () => { try { const res = await apiService.getCases(); setCases(res || []); } catch (e) { console.error(e); } }; fetchCases(); }, []);

  const getCaseDisplayName = (c: Case) => c.title || c.case_name || `Rasti #${c.id.substring(0, 8)}`;

  const handleAutofillCase = async (caseId: string) => {
    const caseData = cases.find(c => c.id === caseId);
    if (!caseData) return;
    let autofillText = `Përmbledhje e Rastit: ${caseData.title || caseData.case_number}\n\nKlienti: ${caseData.client?.name || 'N/A'}`;
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
          setCurrentJob(prev => ({ ...prev, result: accumulatedText }));
      }
      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));
    } catch (error: any) {
      setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: error.message || "Gabim!" }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveToArchive = async () => {
    if (!currentJob.result) return;
    setSaving(true);
    try {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const fileName = `draft-${selectedTemplate}-${Date.now()}.txt`;
      const file = new File([blob], fileName, { type: 'text/plain' });
      await apiService.uploadArchiveItem(file, fileName, 'DRAFT', selectedCaseId);
      setSaveSuccess("U arkivua!");
    } catch (err: any) {
      alert("Gabim!");
    } finally {
      setSaving(false);
    }
  };

  const handleCopyResult = async () => { if (currentJob.result) { await navigator.clipboard.writeText(currentJob.result); alert("Kopjuar!"); } };
  const handleDownloadResult = () => { if (currentJob.result) { const blob = new Blob([currentJob.result], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `draft-${Date.now()}.txt`; a.click(); } };
  const handleClearResult = () => { if (window.confirm("A jeni të sigurt?")) { setCurrentJob({ status: null, result: null, error: null }); setSaveSuccess(null); } };

  const getStatusDisplay = () => {
    switch(currentJob.status) {
      case 'COMPLETED': return { text: "Përfunduar", color: 'text-green-400', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED': return { text: "Dështoi", color: 'text-red-400', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING': return { text: "Duke u hartuar", color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default: return { text: "Rezultati", color: 'text-white', icon: <Sparkles className="h-5 w-5 text-gray-500" /> };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8 flex flex-col h-full overflow-hidden">
      <style>{scrollbarStyles}</style>
      
      {/* HEADER */}
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3">
            <PenTool className="text-primary-start" />Hartimi AI
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 overflow-y-auto lg:overflow-hidden custom-scrollbar">
        {/* INPUT PANEL */}
        <div className="glass-panel flex flex-col h-auto lg:h-[600px] p-4 sm:p-6 rounded-2xl shadow-2xl border border-white/10 shrink-0">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2 flex-shrink-0">
                <FileText className="text-primary-start" size={20} />Konfigurimi
            </h3>
            <form onSubmit={(e) => { e.preventDefault(); runDraftingStream(); }} className="flex flex-col flex-1 gap-4 min-h-0">
                <div className="flex flex-col sm:flex-row gap-4 flex-shrink-0">
                    <div className='flex-1 min-w-0'>
                        <div className="flex items-center justify-between mb-1">
                            <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-wider">Rasti</label>
                            {!isPro && <span className="flex items-center gap-1 text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20"><Lock size={10} /> PRO</span>}
                        </div>
                        <div className="relative">
                            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select 
                                value={selectedCaseId || ''} 
                                onChange={(e) => {
                                    const val = e.target.value || undefined;
                                    setSelectedCaseId(val);
                                    if(val) handleAutofillCase(val); 
                                }} 
                                disabled={isSubmitting || !isPro} 
                                className="glass-input w-full pl-10 pr-10 py-3 appearance-none rounded-xl text-sm"
                            >
                                <option value="" className="bg-gray-900">Pa Kontekst</option>
                                {isPro && cases.map(c => (<option key={c.id} value={String(c.id)} className="bg-gray-900">{getCaseDisplayName(c)}</option>))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                    <div className='flex-1 min-w-0'>
                        <div className="flex items-center justify-between mb-1">
                            <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-wider">Lloji i Dokumentit</label>
                            {!isPro && <span className="flex items-center gap-1 text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20"><Lock size={10} /> PRO</span>}
                        </div>
                        <div className="relative">
                            <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value as TemplateType)} disabled={isSubmitting || !isPro} className="glass-input w-full pl-10 pr-10 py-3 appearance-none rounded-xl text-sm">
                                <option value="generic" className="bg-gray-900 font-bold">Hartim i Lirë</option>
                                <optgroup label="Litigim" className="bg-gray-900 italic text-gray-400">
                                    <option value="padi">Padi</option>
                                    <option value="pergjigje">Përgjigje</option>
                                    <option value="kunderpadi">Kundërpadi</option>
                                    <option value="ankese">Ankesë</option>
                                </optgroup>
                                <optgroup label="Korporative" className="bg-gray-900 italic text-gray-400">
                                    <option value="nda">NDA</option>
                                    <option value="mou">MoU</option>
                                    <option value="employment_contract">Kontratë Pune</option>
                                </optgroup>
                                <optgroup label="Punësim" className="bg-gray-900 italic text-gray-400">
                                    <option value="employment_contract">Kontratë Pune</option>
                                    <option value="termination_notice">Njoftim Shkëputje</option>
                                    <option value="warning_letter">Vërejtje me shkrim</option>
                                </optgroup>
                                <optgroup label="Pronësi" className="bg-gray-900 italic text-gray-400">
                                    <option value="lease_agreement">Kontratë Qiraje</option>
                                    <option value="sales_purchase">Kontratë Shitblerje</option>
                                </optgroup>
                                <optgroup label="Dixhitale" className="bg-gray-900 italic text-gray-400">
                                    <option value="terms_conditions">Kushtet e Përdorimit</option>
                                    <option value="privacy_policy">Politika e Privatësisë</option>
                                </optgroup>
                                <optgroup label="Administrative" className="bg-gray-900 italic text-gray-400">
                                    <option value="power_of_attorney">Autorizim (Prokurë)</option>
                                </optgroup>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                </div>

                <div className="flex-1 flex flex-col min-h-0">
                    <label className="block text-[10px] font-medium text-gray-400 mb-1 uppercase tracking-wider">Udhëzimet</label>
                    <div className="flex-1 h-full relative">
                        <textarea 
                            value={context} 
                            onChange={(e) => setContext(e.target.value)} 
                            placeholder="Shkruani detajet..." 
                            className="glass-input w-full h-full p-4 rounded-xl resize-none text-sm leading-relaxed border border-white/5 bg-transparent focus:ring-1 focus:ring-primary-start/50 outline-none custom-scrollbar absolute inset-0" 
                            disabled={isSubmitting} 
                        />
                    </div>
                </div>

                <button type="submit" disabled={isSubmitting || !context.trim()} className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white font-bold rounded-xl shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 active:scale-95 shrink-0 transition-all">
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  Gjenero Dokumentin
                </button>
            </form>
        </div>

        {/* RESULT PANEL */}
        <div className="flex flex-col h-auto lg:h-[600px] rounded-2xl overflow-hidden shadow-2xl bg-[#12141c] border border-white/10 shrink-0">
            <div className="flex justify-between items-center p-4 bg-black/40 border-b border-white/5 flex-shrink-0">
                <div className="flex items-center gap-3">
                   <div className={`${statusDisplay.color} p-2 bg-white/5 rounded-lg`}>{statusDisplay.icon}</div>
                   <div>
                        <h3 className="text-white text-sm font-semibold leading-none">{statusDisplay.text}</h3>
                   </div>
                </div>
                <div className="flex gap-1 sm:gap-2">
                    <button onClick={runDraftingStream} disabled={!currentJob.result || isSubmitting} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30" title="Rigjenero"><RotateCcw size={16}/></button>
                    <button onClick={handleSaveToArchive} disabled={!currentJob.result || saving} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-primary-start disabled:opacity-30" title="Arkivo">
                        {saving ? <RefreshCw className="animate-spin" size={16}/> : <Archive size={16}/>}
                    </button>
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30" title="Kopjo"><Copy size={16}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30" title="Shkarko"><Download size={16}/></button>
                    <button onClick={handleClearResult} disabled={!currentJob.result && !currentJob.error} className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg disabled:opacity-30 border border-red-500/10" title="Fshi"><Trash2 size={16}/></button>
                </div>
            </div>

            <div className="flex-1 bg-[#0f1117] overflow-y-auto p-4 sm:p-10 relative min-h-0 custom-scrollbar">
                <div className="max-w-full mx-auto">
                    {currentJob.error && (<div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6 text-xs text-red-300 flex items-center gap-3"><AlertCircle size={16} />{currentJob.error}</div>)}
                    {saveSuccess && (<div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 mb-6 text-xs text-green-300 flex items-center gap-3"><CheckCircle size={16} />{saveSuccess}</div>)}
                    
                    <AnimatePresence mode="wait">
                        {currentJob.result ? (
                            <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="pb-8">
                                <DraftResultRenderer text={currentJob.result} />
                            </motion.div>
                        ) : (
                            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 flex flex-col items-center justify-center text-center px-4 py-20">
                                {isSubmitting ? (
                                    <div className="flex flex-col items-center">
                                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg mb-4">
                                            <BrainCircuit className="w-6 h-6 text-white animate-pulse" />
                                        </div>
                                        <div className="text-white font-medium flex items-center gap-2">
                                            Duke u hartuar...<ThinkingDots />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="opacity-20 flex flex-col items-center">
                                        <FileText className="w-12 h-12 text-gray-600 mb-4" />
                                        <p className="text-gray-400 text-sm font-medium">Rezultati do të shfaqet këtu</p>
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;