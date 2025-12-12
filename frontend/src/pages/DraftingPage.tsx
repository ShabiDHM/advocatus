// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V6.0 (UX ENHANCED)
// 1. UX: Replaced static textarea with 'AutoResizeTextarea' for better editing.
// 2. LOGIC: Textarea expands with content and shrinks on generation.
// 3. LAYOUT: Maintained responsive grid while allowing input flexibility.

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

// --- KOSOVO STRICT CONSTRAINTS ---
const LEGAL_CONSTRAINTS = `
*** UDHËZIME STRIKTE (SISTEMI I KOSOVËS): ***
1. JURISDIKSIONI: VETËM REPUBLIKA E KOSOVËS. 
2. NDALIM: MOS përdor kurrë ligje, gjykata apo referenca nga Republika e Shqipërisë (psh. Tiranë, Kodi Civil i Shqipërisë).
3. LIGJI: Referoju vetëm legjislacionit të Kosovës (psh. Ligji për Familjen i Kosovës, Ligji për Procedurën Kontestimore i Kosovës).
4. Nëse nuk e di nenin specifik të Kosovës, shkruaj: "Sipas dispozitave ligjore në fuqi në Kosovë".
**********************************************************************
`;

const TEMPLATE_PROMPTS: Record<TemplateType, string> = {
    generic: "",
    padi: `${LEGAL_CONSTRAINTS}
**Lloji:** Padi (Lawsuit)
**Gjykata:** {{COURT_NAME}}

**Palët:**
- Paditësi: {{CLIENT_NAME}}
- I Padituri: {{OPPOSING_PARTY}}

**Objekti i Mosmarrëveshjes:**
{{CASE_CONTEXT}}

**Baza Ligjore:**
[Cito saktë ligjin përkatës të Kosovës]

**Kërkesëpadia (Petitiumi):**
Kërkoj nga gjykata që të aprovojë kërkesën dhe të detyrojë të paditurin të...

{{CITY}}, [Data]`,
    
    pergjigje: `${LEGAL_CONSTRAINTS}
**Lloji:** Përgjigje në Padi
**Gjykata:** {{COURT_NAME}}
**Numri i Lëndës:** {{CASE_NUMBER}}

**Deklarim:**
I padituri {{CLIENT_NAME}} kundërshton në tërësi pretendimet e palës tjetër...

**Arsyetimi Ligjor:**
Padia nuk ka bazë ligjore sipas ligjeve të Republikës së Kosovës.

**Kërkesa:**
Kërkojmë nga gjykata që të refuzojë padinë si të pabazuar.

{{CITY}}, [Data]`,
    
    kunderpadi: `${LEGAL_CONSTRAINTS}
**Lloji:** Kundërpadi
**Gjykata:** {{COURT_NAME}}
**Në lidhje me rastin:** {{CASE_NUMBER}}

**Palët:**
- Kundërpaditësi: {{CLIENT_NAME}}
- I Kundërpadituri: {{OPPOSING_PARTY}}

**Baza e Kundërpadisë:**
Përveç që kundërshtojmë padinë, ne kërkojmë...

**Faktet Kryesore:**
[Shpjego faktet]

{{CITY}}, [Data]`,
    
    kontrate: `${LEGAL_CONSTRAINTS}
**Lloji:** Kontratë
**Jurisdiksioni:** Republika e Kosovës

**Palët:**
1. {{CLIENT_NAME}} (Palë A)
2. {{OPPOSING_PARTY}} (Palë B)

**Nenet Kryesore:**
- Objekti: ...
- Çmimi: ...
- Kohëzgjatja: ...

**Zgjidhja e Mosmarrëveshjeve:**
[Gjykata Themelore në {{CITY}}]`
};

// --- AUTO RESIZE TEXTAREA COMPONENT ---
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

    // Auto-resize logic
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; // Reset to calculate true scrollHeight
            const scrollHeight = textareaRef.current.scrollHeight;
            
            // Clamp height between min and max
            const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
            textareaRef.current.style.height = `${newHeight}px`;
            
            // If content exceeds maxHeight, show scrollbar
            textareaRef.current.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
        }
    }, [value, minHeight, maxHeight]);

    // Reset logic: If disabled (submitting), shrink to minHeight
    useEffect(() => {
        if (disabled && textareaRef.current) {
             textareaRef.current.style.height = `${minHeight}px`;
             textareaRef.current.scrollTop = 0;
        }
    }, [disabled, minHeight]);

    return (
        <textarea
            ref={textareaRef}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            disabled={disabled}
            className={`${className} transition-all duration-200 ease-in-out`}
            style={{ minHeight: `${minHeight}px` }}
        />
    );
};

// --- STREAMING COMPONENT ---
const StreamedMarkdown: React.FC<{ text: string, isNew: boolean, onComplete: () => void }> = ({ text, isNew, onComplete }) => {
    const [displayedText, setDisplayedText] = useState(isNew ? "" : text);
    
    useEffect(() => {
        if (!isNew) {
            setDisplayedText(text);
            return;
        }

        setDisplayedText(""); 
        let index = 0;
        const speed = 5; 

        const intervalId = setInterval(() => {
            setDisplayedText((prev) => {
                if (index >= text.length) {
                    clearInterval(intervalId);
                    onComplete(); 
                    return text;
                }
                const nextChar = text.charAt(index);
                index++;
                return prev + nextChar;
            });
        }, speed);

        return () => clearInterval(intervalId);
    }, [text, isNew, onComplete]);

    return (
        <div className="markdown-content text-gray-300 text-sm leading-relaxed">
             <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
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
                }}
            >
                {displayedText}
            </ReactMarkdown>
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

  // SAVE TO LOCAL STORAGE
  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { localStorage.setItem('drafting_job', JSON.stringify(currentJob)); }, [currentJob]);

  // FETCH CASES ON MOUNT
  useEffect(() => {
    const fetchCases = async () => {
        try {
            const userCases = await apiService.getCases();
            if (Array.isArray(userCases)) {
                setCases(userCases);
            } else {
                setCases([]);
            }
        } catch (error) {
            console.error("DraftingPage: Failed to fetch cases:", error);
        }
    };
    fetchCases();
  }, []);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  // --- KOSOVO CITY DETECTOR ---
  const detectKosovoContext = (c: Case) => {
    const kosovoKeywords = ['prizren', 'pej', 'gjakov', 'gjilan', 'ferizaj', 'mitrovic', 'podujev', 'vushtrri', 'suharek', 'rahovec', 'drenas', 'lipjan', 'malishev', 'kamenic', 'viti', 'decan', 'istog', 'kline', 'skenderaj', 'dragash', 'fushe kosov', 'kacanik', 'shtime'];
    
    const searchString = `${c.court_info?.name || ''} ${c.client?.name || ''} ${c.description || ''} ${c.title || ''}`.toLowerCase();

    let city = 'Prishtinë'; // Default capital

    // Extract specific city if found
    for (const kw of kosovoKeywords) {
        if (searchString.includes(kw)) {
            city = kw.charAt(0).toUpperCase() + kw.slice(1);
            if (city === 'Pej') city = 'Pejë';
            if (city === 'Gjakov') city = 'Gjakovë';
            break;
        }
    }

    return { city };
  };

  // --- INTELLIGENT TEMPLATE ENGINE ---
  const applyTemplate = (templateKey: TemplateType, caseId?: string) => {
      if (templateKey === 'generic') return;

      let templateText = TEMPLATE_PROMPTS[templateKey];
      
      // HYDRATE WITH CASE DATA
      if (caseId) {
          const activeCase = cases.find(c => String(c.id) === caseId);
          if (activeCase) {
              const { city } = detectKosovoContext(activeCase);
              
              const clientName = activeCase.client?.name || '[Emri i Klientit]';
              const opposingName = activeCase.opposing_party?.name || '[Emri i Kundërshtarit]';
              const caseNum = activeCase.case_number || '[Numri i Lëndës]';
              const courtName = activeCase.court_info?.name || `Gjykata Themelore në ${city}`;
              const caseCtx = activeCase.title || activeCase.case_name || activeCase.description || '[Përshkruaj natyrën e çështjes]';

              templateText = templateText
                  .replace(/{{CITY}}/g, city)
                  .replace(/{{COURT_NAME}}/g, courtName)
                  .replace(/{{CLIENT_NAME}}/g, clientName)
                  .replace(/{{OPPOSING_PARTY}}/g, opposingName)
                  .replace(/{{CASE_NUMBER}}/g, caseNum)
                  .replace(/{{CASE_CONTEXT}}/g, caseCtx);
          }
      } else {
          // Fallbacks
          templateText = templateText
              .replace(/{{CITY}}/g, 'Prishtinë')
              .replace(/{{COURT_NAME}}/g, '[Emri i Gjykatës]')
              .replace(/{{CLIENT_NAME}}/g, '[Emri dhe Mbiemri / Kompania]')
              .replace(/{{OPPOSING_PARTY}}/g, '[Emri i Kundërshtarit]')
              .replace(/{{CASE_NUMBER}}/g, '[Numri i Lëndës]')
              .replace(/{{CASE_CONTEXT}}/g, '[Përshkruaj shkurtimisht natyrën e çështjes]');
      }

      setContext(templateText);
  };

  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      const newTemplate = e.target.value as TemplateType;
      
      const isDirty = context.trim().length > 0;
      const isCleanSwitch = !isDirty || Object.values(TEMPLATE_PROMPTS).some(t => context.includes(t.substring(0, 20))); 

      if (isDirty && !isCleanSwitch) {
          if (!window.confirm(t('drafting.confirmTemplateSwitch', 'Ndryshimi i shabllonit do të zëvendësojë tekstin aktual. Vazhdo?'))) {
              return; 
          }
      }

      setSelectedTemplate(newTemplate);
      if (newTemplate === 'generic') setContext('');
      else applyTemplate(newTemplate, selectedCaseId);
  };

  const handleCaseChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      const newCaseId = e.target.value || undefined;
      setSelectedCaseId(newCaseId);
      
      if (selectedTemplate !== 'generic') {
          applyTemplate(selectedTemplate, newCaseId);
      }
  };

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
      const jobResponse = await apiService.initiateDraftingJob({
        user_prompt: context.trim(),
        context: context.trim(),
        case_id: selectedCaseId, 
        use_library: !!selectedCaseId
      });

      const jobId = jobResponse.job_id;
      setCurrentJob({ jobId, status: 'PENDING', result: null, error: null });
      startPolling(jobId);

    } catch (error: any) {
      console.error("Submit Error:", error);
      const errorMessage = error.response?.data?.detail || error.message || t('drafting.errorStartJob');
      setCurrentJob(prev => ({ ...prev, error: errorMessage, status: 'FAILED' }));
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); runDraftingJob(); };
  const handleCopyResult = async () => { if (currentJob.result) { await navigator.clipboard.writeText(currentJob.result); alert(t('general.copied')); } };
  const handleDownloadResult = () => { if (currentJob.result) { const blob = new Blob([currentJob.result], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `draft-${new Date().getTime()}.txt`; document.body.appendChild(a); a.click(); document.body.removeChild(a); } };
  const handleClearResult = () => { if (window.confirm(t('drafting.confirmClear', 'A jeni i sigurt?'))) { if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current); setCurrentJob({ jobId: null, status: null, result: null, error: null }); setIsResultNew(false); } };

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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-theme(spacing.20))] flex flex-col">
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3"><PenTool className="text-primary-500" />{t('drafting.title')}</h1>
        <p className="text-gray-400 text-sm">{t('drafting.subtitle')}</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[600px]">
        <div className="flex flex-col h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl overflow-hidden">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2 flex-shrink-0"><FileText className="text-primary-400" size={20} />{t('drafting.configuration')}</h3>
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4 min-h-0">
                
                {/* SELECTORS ROW */}
                <div className="flex flex-col sm:flex-row gap-4 flex-shrink-0">
                    <div className='flex-1 min-w-0'>
                        <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.caseLabel', 'Rasti')}</label>
                        <div className="relative">
                            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select
                                value={selectedCaseId || ''}
                                onChange={handleCaseChange}
                                className="w-full bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none text-sm pl-10 pr-10 py-3 appearance-none transition-colors cursor-pointer truncate"
                                disabled={isSubmitting}
                            >
                                <option value="" className="bg-gray-900 text-gray-400">{t('drafting.noCaseSelected', 'Pa Kontekst (Gjenerik)')}</option>
                                {cases.length > 0 ? (
                                    cases.map(c => (
                                        <option key={c.id} value={String(c.id)} className="bg-gray-900 text-white">
                                            {getCaseDisplayName(c)}
                                        </option>
                                    ))
                                ) : (
                                    <option value="" disabled className="bg-gray-900 text-gray-500 italic">
                                        {t('drafting.noCasesFound', 'Asnjë rast i gjetur')}
                                    </option>
                                )}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                    <div className='flex-1 min-w-0'>
                        <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.templateLabel', 'Lloji i Dokumentit')}</label>
                        <div className="relative">
                            <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                            <select
                                value={selectedTemplate}
                                onChange={handleTemplateChange}
                                className="w-full bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none text-sm pl-10 pr-10 py-3 appearance-none transition-colors cursor-pointer"
                                disabled={isSubmitting}
                            >
                                <option value="generic" className="bg-gray-900 text-gray-400">{t('drafting.templateGeneric', 'I lirë (Pa shabllon)')}</option>
                                <option value="padi" className="bg-gray-900 text-white">{t('drafting.templatePadi', 'Padi')}</option>
                                <option value="pergjigje" className="bg-gray-900 text-white">{t('drafting.templatePergjigje', 'Përgjigje në Padi')}</option>
                                <option value="kunderpadi" className="bg-gray-900 text-white">{t('drafting.templateKunderpadi', 'Kundërpadi')}</option>
                                <option value="kontrate" className="bg-gray-900 text-white">{t('drafting.templateKontrate', 'Kontratë')}</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"/>
                        </div>
                    </div>
                </div>

                {/* SMART EXPANDING TEXTAREA */}
                <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider flex-shrink-0">{t('drafting.instructionsLabel')}</label>
                    <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                        <AutoResizeTextarea
                            value={context}
                            onChange={(e) => setContext(e.target.value)}
                            placeholder={t('drafting.promptPlaceholder')}
                            className="w-full p-4 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none resize-none text-sm leading-relaxed"
                            disabled={isSubmitting}
                            minHeight={150}
                            maxHeight={500}
                        />
                    </div>
                </div>

                <button type="submit" disabled={isSubmitting || !context.trim()} className="w-full py-3 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-2 flex-shrink-0">
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  {t('drafting.generateBtn')}
                </button>
            </form>
        </div>
        <div className="flex flex-col h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl overflow-hidden">
            <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/5 flex-shrink-0">
                <h3 className="text-white font-semibold flex items-center gap-2">{statusDisplay.icon}<span className={statusDisplay.color}>{statusDisplay.text}</span></h3>
                <div className="flex gap-2">
                    <button onClick={runDraftingJob} disabled={!currentJob.result || isSubmitting} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.regenerate', 'Rigjenero')}><RotateCcw size={18}/></button>
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.copyTitle')}><Copy size={18}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.downloadTitle')}><Download size={18}/></button>
                    <button onClick={handleClearResult} disabled={!currentJob.result && !currentJob.error} className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg disabled:opacity-30 transition-colors border border-red-500/20" title={t('drafting.clearTitle', 'Pastro')}><Trash2 size={18}/></button>
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