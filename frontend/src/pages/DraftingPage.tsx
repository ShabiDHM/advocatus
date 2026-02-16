// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V10.21 (LAWYER GRADE + TOOLTIPS)
// 1. RESTORED: All tooltips (title attributes) for UI actions.
// 2. ENHANCED: Lawyer Grade typography (Hyphenation, Centered H1, Underlined H3).
// 3. FIXED: Forced Contrast black-on-white (!important) for all document elements.
// 4. MOBILE: Dynamic margins (px-6 mobile, 2.5cm desktop) without feature loss.

import React, { useState, useEffect, useMemo } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { Case } from '../data/types'; 
import { useAuth } from '../context/AuthContext';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, Trash2, Briefcase, ChevronDown, LayoutTemplate,
  Lock, BrainCircuit, Archive, Scale } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- HIGH-FIDELITY LEGAL STYLES ---
const lawyerGradeStyles = `
  @media print {
    body * { visibility: hidden; }
    .legal-document, .legal-document * { visibility: visible; }
    .legal-document {
      position: absolute; left: 0; top: 0; width: 100%;
      margin: 0; padding: 2.5cm; box-shadow: none; border: none;
    }
    @page { size: A4; margin: 0; }
  }

  /* FORCED LEGAL CONTRAST */
  .legal-content, .legal-content * {
    color: #000000 !important;
    border-color: #000000 !important;
  }

  .legal-content {
    font-family: 'Times New Roman', Times, serif;
    line-height: 1.6;
    text-align: justify;
    text-justify: inter-word;
    hyphens: auto;
  }
  
  /* HIGH-GRADE HEADERS */
  .legal-content h1 { text-align: center; text-transform: uppercase; font-weight: bold; margin-bottom: 2rem; font-size: 14pt; letter-spacing: 0.05em; }
  .legal-content h2 { text-transform: uppercase; font-weight: bold; margin-top: 1.5rem; margin-bottom: 1rem; font-size: 12pt; border-bottom: 1.5px solid #000; padding-bottom: 4px; }
  .legal-content h3 { font-weight: bold; margin-top: 1.2rem; margin-bottom: 0.8rem; font-size: 12pt; text-decoration: underline; text-underline-offset: 3px; }
  .legal-content p { margin-bottom: 1rem; }
  .legal-content ul, .legal-content ol { margin-left: 2.5rem; margin-bottom: 1rem; }
  .legal-content blockquote { margin-left: 2.5rem; border-left: 3px solid #000; padding-left: 1rem; font-style: italic; margin-bottom: 1rem; }
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
}

const constructSmartPrompt = (userText: string, template: TemplateType): string => {
    let domainHint = "";
    const lowerText = userText.toLowerCase();
    if (lowerText.includes('alimentacion') || lowerText.includes('femij') || lowerText.includes('martes') || lowerText.includes('shkurorëzim')) {
        domainHint = "DOMAIN: FAMILY LAW. MANDATORY: Cite 'Ligji për Familjen'. BAN: Corporate, Criminal.";
    } else if (lowerText.includes('shpk') || lowerText.includes('aksion') || lowerText.includes('biznes')) {
        domainHint = "DOMAIN: CORPORATE LAW. MANDATORY: Cite 'Ligji për Shoqëritë Tregtare'.";
    }
    return `[INSTRUCTION: ${domainHint}] [TEMPLATE: ${template}] \n\n CONTENT: ${userText}`;
};

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-1">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
    </span>
);

const DraftResultRenderer: React.FC<{ text: string }> = ({ text }) => {
    return (
        <div className="legal-document bg-white w-full lg:max-w-[21cm] mx-auto px-6 py-8 sm:px-[2.5cm] sm:py-[2.5cm] shadow-[0_20px_50px_rgba(0,0,0,0.2)] my-4 sm:my-8 border border-gray-300 ring-1 ring-black/5">
             <div className="legal-content text-[11pt] sm:text-[12pt]">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    components={{
                        h1: ({node, ...props}) => <h1 {...props} />,
                        h2: ({node, ...props}) => <h2 {...props} />,
                        h3: ({node, ...props}) => <h3 {...props} />,
                        p: ({node, ...props}) => {
                            const content = String(props.children);
                            if (content.includes('gjeneruar nga AI')) return <p className="text-center italic mt-16 pt-4 border-t border-black text-[10pt] opacity-70" {...props} />;
                            return <p {...props} />;
                        },
                        strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                        hr: () => <hr className="my-8 border-black/30" />,
                        a: ({children}) => <span className="font-bold underline cursor-default">{children}</span>,
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
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const [currentJob, setCurrentJob] = useState<DraftingJobState>(() => {
    const saved = localStorage.getItem('drafting_job');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.status === 'PROCESSING') parsed.status = parsed.result ? 'COMPLETED' : 'FAILED';
        return parsed;
      } catch (e) { return { status: null, result: null, error: null }; }
    }
    return { status: null, result: null, error: null };
  });

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { localStorage.setItem('drafting_job', JSON.stringify(currentJob)); }, [currentJob]);
  useEffect(() => { apiService.getCases().then(res => setCases(res || [])).catch(console.error); }, []);

  const handleAutofillCase = (caseId: string) => {
    const c = cases.find(item => item.id === caseId);
    if (c) setContext(`RASTI: ${c.title || c.case_number}\nKLIENTI: ${c.client?.name || 'N/A'}\nFAKTET:\n${c.description || '-'}`);
  };

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setSaveSuccess(null);
    let acc = "";
    try {
      const stream = apiService.draftLegalDocumentStream({
          user_prompt: constructSmartPrompt(context.trim(), selectedTemplate),
          document_type: isPro ? selectedTemplate : 'generic',
          case_id: isPro ? selectedCaseId : undefined,
          use_library: isPro && !!selectedCaseId
      });
      for await (const chunk of stream) {
          acc += chunk;
          setCurrentJob(prev => ({ ...prev, result: acc }));
      }
      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));
    } catch (e: any) {
      setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: e.message || "Gabim!" }));
    } finally { setIsSubmitting(false); }
  };

  const handleSaveToArchive = async () => {
    if (!currentJob.result) return;
    setSaving(true);
    try {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const fileName = `draft-${selectedTemplate}-${Date.now()}.txt`;
      await apiService.uploadArchiveItem(new File([blob], fileName), fileName, 'DRAFT', selectedCaseId);
      setSaveSuccess("U arkivua me sukses!");
    } catch (err) { alert("Gabim gjatë arkivimit!"); } finally { setSaving(false); }
  };

  const statusDisplay = (() => {
    switch(currentJob.status) {
      case 'COMPLETED': return { text: "Përfunduar", color: 'text-green-400', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED': return { text: "Dështoi", color: 'text-red-400', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING': return { text: "Duke u hartuar", color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default: return { text: "Rezultati", color: 'text-white', icon: <Scale className="h-5 w-5 text-gray-500" /> };
    }
  })();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8 flex flex-col h-full lg:overflow-hidden overflow-y-auto">
      <style>{lawyerGradeStyles}</style>
      
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center justify-center gap-3">
            <PenTool className="text-primary-start" />Hartimi AI
        </h1>
      </div>

      <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 flex-1 lg:overflow-hidden">
        
        {/* CONFIG PANEL */}
        <div className="glass-panel flex flex-col p-4 sm:p-6 rounded-2xl border border-white/10 lg:overflow-y-auto shrink-0">
            <h3 className="text-white font-semibold mb-6 flex items-center gap-2">
                <FileText className="text-primary-start" size={20} />Konfigurimi
            </h3>
            <div className="flex flex-col gap-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <div className="flex justify-between mb-1">
                            <label className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">Rasti</label>
                            {!isPro && <span className="text-[9px] text-amber-500 font-bold bg-amber-500/10 px-1.5 rounded border border-amber-500/20 flex items-center gap-1"><Lock size={8}/> PRO</span>}
                        </div>
                        <div className="relative">
                            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                            <select value={selectedCaseId || ''} onChange={(e) => { setSelectedCaseId(e.target.value); handleAutofillCase(e.target.value); }} disabled={!isPro} className="glass-input w-full pl-10 pr-10 py-3.5 rounded-xl text-sm appearance-none outline-none">
                                <option value="">Pa Kontekst</option>
                                {isPro && cases.map(c => <option key={c.id} value={c.id} className="bg-gray-900">{c.title || c.case_name}</option>)}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                        </div>
                    </div>
                    <div>
                        <label className="block text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Modeli</label>
                        <div className="relative">
                            <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                            <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value as TemplateType)} disabled={!isPro} className="glass-input w-full pl-10 pr-10 py-3.5 rounded-xl text-sm appearance-none outline-none">
                                <option value="generic">Hartim i Lirë</option>
                                <optgroup label="LITIGIM" className="bg-gray-900 italic">
                                    <option value="padi">Padi</option>
                                    <option value="pergjigje">Përgjigje në Padi</option>
                                    <option value="kunderpadi">Kundërpadi</option>
                                    <option value="ankese">Ankesë</option>
                                    <option value="prapësim">Prapësim</option>
                                </optgroup>
                                <optgroup label="KORPORATIVE" className="bg-gray-900 italic">
                                    <option value="nda">NDA (Konfidencialitet)</option>
                                    <option value="mou">MoU (Memorandum)</option>
                                    <option value="shareholders">Marrëveshje Aksionarësh</option>
                                </optgroup>
                                <optgroup label="PUNËSIM" className="bg-gray-900 italic">
                                    <option value="employment_contract">Kontratë Pune</option>
                                    <option value="termination_notice">Njoftim Shkëputje</option>
                                </optgroup>
                                <optgroup label="PRONËSI" className="bg-gray-900 italic">
                                    <option value="lease_agreement">Kontratë Qiraje</option>
                                    <option value="sales_purchase">Kontratë Shitblerje</option>
                                </optgroup>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                        </div>
                    </div>
                </div>

                <div>
                    <label className="block text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Udhëzimet & Faktet</label>
                    <textarea 
                        value={context} 
                        onChange={(e) => setContext(e.target.value)} 
                        placeholder="Përshkruani faktet e rastit..." 
                        className="glass-input w-full p-4 rounded-xl text-sm min-h-[160px] lg:min-h-[200px] resize-none outline-none focus:ring-1 focus:ring-primary-start/40 transition-all"
                    />
                </div>

                <button onClick={runDraftingStream} disabled={isSubmitting || !context.trim()} className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end text-white font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-primary-start/20 hover:opacity-95 transition-all active:scale-[0.98]">
                  {isSubmitting ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
                  {isSubmitting ? "Duke u hartuar..." : "Gjenero Dokumentin (AI)"}
                </button>
            </div>
        </div>

        {/* RESULT PANEL */}
        <div className="flex flex-col min-h-[500px] lg:h-full rounded-2xl bg-[#0d0f14] border border-white/10 overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-4 bg-white/5 border-b border-white/5">
                <div className="flex items-center gap-3">
                   <div className={`${statusDisplay.color} p-2 bg-white/5 rounded-lg`}>{statusDisplay.icon}</div>
                   <h3 className="text-white text-xs sm:text-sm font-semibold uppercase tracking-widest leading-none">{statusDisplay.text}</h3>
                </div>
                <div className="flex gap-1 sm:gap-2">
                    <button onClick={handleSaveToArchive} title="Arkivo në rast" disabled={!currentJob.result || saving} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-primary-start transition-colors disabled:opacity-30">
                        {saving ? <RefreshCw className="animate-spin" size={18}/> : <Archive size={18}/>}
                    </button>
                    <button onClick={() => { if(currentJob.result) { navigator.clipboard.writeText(currentJob.result); alert("U kopjua!"); } }} title="Kopjo tekstin" className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-colors"><Copy size={18}/></button>
                    <button onClick={() => { if(currentJob.result) { const blob = new Blob([currentJob.result], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `draft-${Date.now()}.txt`; a.click(); } }} title="Shkarko si skedar" className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-colors"><Download size={18}/></button>
                    <button onClick={() => { if(window.confirm("A jeni të sigurt?")) setCurrentJob({ status: null, result: null, error: null }); }} title="Fshij rezultatin" className="p-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"><Trash2 size={18}/></button>
                </div>
            </div>

            <div className="flex-1 bg-gray-900/40 overflow-y-auto p-4 sm:p-10 relative custom-scrollbar">
                <AnimatePresence mode="wait">
                    {currentJob.result ? (
                        <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                            {saveSuccess && <div className="mb-4 p-3 bg-green-500/20 text-green-400 text-xs rounded-lg flex items-center gap-2 border border-green-500/20"><CheckCircle size={14}/> {saveSuccess}</div>}
                            <DraftResultRenderer text={currentJob.result} />
                        </motion.div>
                    ) : (
                        <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 flex flex-col items-center justify-center text-center px-6">
                            {isSubmitting ? (
                                <div className="flex flex-col items-center">
                                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg shadow-primary-start/20 mb-6 animate-pulse">
                                        <BrainCircuit className="w-8 h-8 text-white" />
                                    </div>
                                    <p className="text-white font-medium flex items-center">Duke u hartuar dokumenti<ThinkingDots /></p>
                                </div>
                            ) : (
                                <div className="opacity-20 flex flex-col items-center">
                                    <FileText size={56} className="text-gray-600 mb-4" />
                                    <p className="text-gray-400 text-sm">Zgjidhni konfigurimin për të filluar hartimin</p>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;