// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V10.16 (CLEANUP)
// 1. FIXED: Removed unused 'Sparkles' import to resolve TypeScript warning.
// 2. RETAINED: All Smart Prompt logic and Legal Styling.

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { Case } from '../data/types'; 
import { useAuth } from '../context/AuthContext';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, RotateCcw, Trash2, Briefcase, ChevronDown, LayoutTemplate,
  Lock, BrainCircuit, Archive, Scale } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- LEGAL DOCUMENT STYLING (THE "PROFESSIONAL LOOK") ---
const legalStyles = `
  /* FORCE PRINT STYLES */
  @media print {
    body * { visibility: hidden; }
    .legal-document, .legal-document * { visibility: visible; }
    .legal-document {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      margin: 0;
      padding: 2.5cm; /* Standard Legal Margin */
      box-shadow: none;
      border: none;
    }
    @page { size: A4; margin: 0; }
  }

  /* DOCUMENT TYPOGRAPHY */
  .legal-content {
    font-family: 'Times New Roman', Times, serif;
    font-size: 12pt;
    line-height: 1.5;
    color: #000000;
    text-align: justify;
    text-justify: inter-word;
  }
  
  .legal-content h1 { text-align: center; text-transform: uppercase; font-weight: bold; margin-bottom: 24px; font-size: 14pt; letter-spacing: 1px; }
  .legal-content h2 { text-transform: uppercase; font-weight: bold; margin-top: 24px; margin-bottom: 12px; font-size: 12pt; border-bottom: 1px solid #000; padding-bottom: 4px; }
  .legal-content h3 { font-weight: bold; margin-top: 18px; margin-bottom: 8px; font-size: 12pt; text-decoration: underline; }
  .legal-content p { margin-bottom: 12px; }
  .legal-content ul, .legal-content ol { margin-left: 36px; margin-bottom: 12px; }
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

// --- SMART PROMPT ENGINEER (THE "DOCTOR") ---
const constructSmartPrompt = (userText: string, template: TemplateType): string => {
    let domainInstruction = "";
    const lowerText = userText.toLowerCase();

    // 1. DETECT FAMILY LAW (The "Alimony" Case)
    if (lowerText.includes('alimentacion') || lowerText.includes('femij') || lowerText.includes('martes') || lowerText.includes('shkurorëzim')) {
        domainInstruction = `
        CRITICAL INSTRUCTION: This is a FAMILY LAW case (Ligji për Familjen). 
        - YOU MUST CITE: Ligji Nr. 2004/32 për Familjen e Kosovës.
        - YOU MUST CITE: Ligji për Procedurën Kontestimore (if procedural).
        - FORBIDDEN: Do NOT cite 'Ligji për Shoqëritë Tregtare' (Corporate Law).
        - FORBIDDEN: Do NOT cite 'Kodi i Procedurës Penale' (Criminal Law).
        - TONE: Protective of the child's best interest.
        `;
    } 
    // 2. DETECT CORPORATE LAW
    else if (lowerText.includes('shpk') || lowerText.includes('aksion') || lowerText.includes('bord') || lowerText.includes('biznes')) {
        domainInstruction = `
        CRITICAL INSTRUCTION: This is a CORPORATE LAW case.
        - YOU MUST CITE: Ligji Nr. 06/L-016 për Shoqëritë Tregtare.
        `;
    }
    // 3. DETECT CRIMINAL LAW
    else if (lowerText.includes('burg') || lowerText.includes('veper penale') || lowerText.includes('polici') || lowerText.includes('prokuror')) {
        domainInstruction = `
        CRITICAL INSTRUCTION: This is a CRIMINAL LAW case.
        - YOU MUST CITE: Kodi Penal dhe Kodi i Procedurës Penale.
        `;
    }

    // 4. TEMPLATE SPECIFIC STRUCTURES
    let structureInstruction = "";
    switch(template) {
        case 'padi':
            structureInstruction = "STRUCTURE: Header (Court, Parties), Baza Ligjore, Facts (Arsyetimi), Petitumi (Kërkesëpadia).";
            break;
        case 'pergjigje':
            structureInstruction = "STRUCTURE: Response to Allegations, Counter-Arguments, Legal Basis for Rejection.";
            break;
        case 'ankese':
            structureInstruction = "STRUCTURE: Attack the previous judgment. Cite violations of substantive or procedural law.";
            break;
        default:
            structureInstruction = "STRUCTURE: Standard formal legal document.";
    }

    // COMBINE THE CURE
    return `
    ${domainInstruction}
    ${structureInstruction}
    
    USER CONTEXT:
    ${userText}
    `;
};

// --- AUTO-RESIZE TEXTAREA ---
const AutoResizeTextarea: React.FC<{ 
    value: string; onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void; 
    placeholder?: string; disabled?: boolean; className?: string; minHeight?: number; maxHeight?: number;
}> = ({ value, onChange, placeholder, disabled, className, minHeight = 150, maxHeight = 400 }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; 
            textareaRef.current.style.height = `${Math.min(Math.max(textareaRef.current.scrollHeight, minHeight), maxHeight)}px`;
        }
    }, [value, minHeight, maxHeight]);
    return <textarea ref={textareaRef} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled} className={className} />;
};

// --- LAWYER GRADE RENDERER ---
const DraftResultRenderer: React.FC<{ text: string }> = ({ text }) => {
    return (
        <div className="legal-document bg-white w-full lg:max-w-[21cm] mx-auto px-8 py-10 sm:px-[2.5cm] sm:py-[2.5cm] shadow-xl my-4 sm:my-8 border border-gray-200">
             <div className="legal-content">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    components={{
                        // FORCE BLACK TEXT AND LEGAL STYLING
                        p: ({node, ...props}) => {
                            const content = String(props.children);
                            if (content.includes('gjeneruar nga AI')) return <p style={{textAlign: 'center', fontSize: '10pt', fontStyle: 'italic', marginTop: '40px', borderTop: '1px solid #000', paddingTop: '10px'}} {...props} />;
                            return <p {...props} />;
                        },
                        strong: ({node, ...props}) => <strong style={{fontWeight: 'bold', color: '#000'}} {...props} />,
                        h1: ({node, ...props}) => <h1 {...props} />,
                        h2: ({node, ...props}) => <h2 {...props} />,
                        h3: ({node, ...props}) => <h3 {...props} />,
                        ul: ({node, ...props}) => <ul {...props} />,
                        ol: ({node, ...props}) => <ol {...props} />,
                        blockquote: ({node, ...props}) => <blockquote style={{marginLeft: '40px', fontStyle: 'italic', borderLeft: '3px solid #000', paddingLeft: '10px'}} {...props} />,
                        hr: () => <hr style={{margin: '20px 0', borderTop: '1px solid #000'}} />,
                        a: ({href, children}) => {
                            if (href?.startsWith('doc://')) return (<span style={{fontWeight: 'bold', textDecoration: 'none', color: '#000'}}>{children}</span>);
                            return <span style={{textDecoration: 'underline', color: '#000'}}>{children}</span>;
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
  
  const [currentJob, setCurrentJob] = useState<DraftingJobState>(() => {
    const saved = localStorage.getItem('drafting_job');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.status === 'PROCESSING') {
           if (parsed.result && parsed.result.length > 0) {
             parsed.status = 'COMPLETED';
           } else {
             parsed.status = 'FAILED';
             parsed.error = 'Procesi u ndërpre nga rifreskimi i faqes.';
           }
        }
        return parsed;
      } catch (e) {
        return { status: null, result: null, error: null };
      }
    }
    return { status: null, result: null, error: null };
  });

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  useEffect(() => { if (!isPro) { setSelectedCaseId(undefined); setSelectedTemplate('generic'); } }, [isPro]);
  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { localStorage.setItem('drafting_job', JSON.stringify(currentJob)); }, [currentJob]);

  useEffect(() => { const fetchCases = async () => { try { const res = await apiService.getCases(); setCases(res || []); } catch (e) { console.error(e); } }; fetchCases(); }, []);

  const getCaseDisplayName = (c: Case) => c.title || c.case_name || `Rasti #${c.id.substring(0, 8)}`;

  // FIXED: STRICT REPLACEMENT OF CONTEXT
  const handleAutofillCase = async (caseId: string) => {
    const caseData = cases.find(c => c.id === caseId);
    if (!caseData) return;
    const autofillText = `RASTI: ${caseData.title || caseData.case_number}\nKLIENTI: ${caseData.client?.name || 'N/A'}\nPALËT KUNDËRSHTARE: ${caseData.opposing_party || 'N/A'}\nFAKTET KRYESORE:\n${caseData.description || '-'}`;
    
    // Always replace context to avoid "Context Pollution"
    setContext(autofillText);
  };

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setSaveSuccess(null);
    let accumulatedText = "";

    // APPLY THE CURE: Inject Smart Prompt Logic
    const finalSmartPrompt = constructSmartPrompt(context.trim(), selectedTemplate);

    try {
      const stream = apiService.draftLegalDocumentStream({
          user_prompt: finalSmartPrompt, // SENDING TREATED PROMPT
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
  
  const handleClearResult = () => { 
      if (window.confirm("A jeni të sigurt?")) { 
          setCurrentJob({ status: null, result: null, error: null }); 
          setSaveSuccess(null); 
      } 
  };

  const getStatusDisplay = () => {
    switch(currentJob.status) {
      case 'COMPLETED': return { text: "Përfunduar", color: 'text-green-400', icon: <CheckCircle className="h-5 w-5" /> };
      case 'FAILED': return { text: "Dështoi", color: 'text-red-400', icon: <AlertCircle className="h-5 w-5" /> };
      case 'PROCESSING': return { text: "Duke u hartuar...", color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse" /> };
      default: return { text: "Rezultati", color: 'text-white', icon: <Scale className="h-5 w-5 text-gray-500" /> };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8 flex flex-col h-full lg:overflow-hidden overflow-y-auto">
      <style>{legalStyles}</style>
      
      {/* HEADER */}
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3">
            <PenTool className="text-primary-start" />Hartimi AI
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 lg:overflow-hidden">
        
        {/* INPUT PANEL */}
        <div className="glass-panel flex flex-col h-auto lg:h-full p-4 sm:p-6 rounded-2xl shadow-2xl border border-white/10 shrink-0 lg:overflow-y-auto custom-scrollbar">
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
                                    <option value="padi">Padi (Lawsuit)</option>
                                    <option value="pergjigje">Përgjigje (Response)</option>
                                    <option value="kunderpadi">Kundërpadi (Counter-claim)</option>
                                    <option value="ankese">Ankesë (Appeal)</option>
                                </optgroup>
                                <optgroup label="Korporative" className="bg-gray-900 italic text-gray-400">
                                    <option value="nda">NDA</option>
                                    <option value="mou">MoU</option>
                                    <option value="employment_contract">Kontratë Pune</option>
                                </optgroup>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                </div>

                <div className="flex-1 flex flex-col min-h-0">
                    <label className="block text-[10px] font-medium text-gray-400 mb-1 uppercase tracking-wider">Faktet & Udhëzimet</label>
                    <div className="flex-1 lg:overflow-y-auto pr-1 custom-scrollbar">
                        <AutoResizeTextarea 
                            value={context} 
                            onChange={(e) => setContext(e.target.value)} 
                            placeholder="Përshkruani faktet e rastit, kërkesën kryesore dhe palët..." 
                            className="glass-input w-full p-4 rounded-xl resize-none text-sm leading-relaxed border border-white/5 bg-transparent focus:ring-1 focus:ring-primary-start/50 outline-none" 
                            disabled={isSubmitting} 
                        />
                    </div>
                </div>

                <button type="submit" disabled={isSubmitting || !context.trim()} className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white font-bold rounded-xl shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 active:scale-95 shrink-0 transition-all">
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  Gjenero Dokumentin (AI)
                </button>
            </form>
        </div>

        {/* RESULT PANEL */}
        <div className="flex flex-col h-auto min-h-[500px] lg:h-full rounded-2xl overflow-hidden shadow-2xl bg-[#12141c] border border-white/10 shrink-0">
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
                                            Duke u hartuar...
                                        </div>
                                    </div>
                                ) : (
                                    <div className="opacity-20 flex flex-col items-center">
                                        <FileText className="w-12 h-12 text-gray-600 mb-4" />
                                        <p className="text-gray-400 text-sm font-medium">Zgjidhni rastin ose shkruani të dhënat</p>
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