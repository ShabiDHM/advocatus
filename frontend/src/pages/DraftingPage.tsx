import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { TFunction } from 'i18next';
import { Case } from '../data/types'; 
import { useAuth } from '../context/AuthContext';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, 
  FileText, Trash2, Briefcase, ChevronDown, LayoutTemplate,
  Lock, BrainCircuit, Archive, Scale 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- TYPE DEFINITIONS ---
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

interface NotificationState {
    msg: string;
    type: 'success' | 'error';
}

// --- PROPS INTERFACES ---
interface ConfigPanelProps {
    t: TFunction;
    isPro: boolean;
    cases: Case[];
    selectedCaseId: string;
    selectedTemplate: TemplateType;
    context: string;
    isSubmitting: boolean;
    onSelectCase: (id: string) => void;
    onSelectTemplate: (val: string) => void;
    onChangeContext: (val: string) => void;
    onSubmit: () => void;
}

interface ResultPanelProps {
    t: TFunction;
    currentJob: DraftingJobState;
    saving: boolean;
    notification: NotificationState | null;
    onSave: () => void;
    onClear: () => void;
}

// --- KOSOVO COURT STYLING ENGINE (A4 FORMAT, CENTERED, JUSTIFIED) ---
const lawyerGradeStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Tinos:ital,wght@0,400;0,700;1,400&display=swap');

  .legal-document {
    font-family: 'Tinos', 'Times New Roman', serif;
    background: white;
    color: black;
    padding: 2.5cm 2cm;
    line-height: 1.5;
    font-size: 12pt;
    text-align: justify;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    margin: 0 auto;
    width: 21cm;
    max-width: 100%;
    box-sizing: border-box;
    min-height: 29.7cm; /* A4 Height */
  }

  /* Print Optimization */
  @media print {
    @page { margin: 2cm; size: A4; }
    body * { visibility: hidden; }
    .legal-document, .legal-document * { visibility: visible; }
    .legal-document {
      position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0;
      box-shadow: none; border: none;
    }
  }

  /* Typographic Hierarchy for Kosovo Courts */
  .legal-content h1 { 
    text-align: center; 
    text-transform: uppercase; 
    font-weight: 700; 
    font-size: 14pt; 
    margin-bottom: 24pt;
    letter-spacing: 1px;
    border-bottom: 2px solid #000;
    padding-bottom: 4pt;
  }
  
  .legal-content h2 { 
    text-transform: uppercase; 
    font-weight: 700; 
    font-size: 12pt; 
    margin-top: 18pt; 
    margin-bottom: 12pt; 
    text-align: center;
  }

  .legal-content h3 { 
    font-weight: 700; 
    font-size: 12pt; 
    margin-top: 12pt; 
    margin-bottom: 6pt; 
    text-transform: uppercase;
    text-decoration: none;
    text-align: left;
  }

  .legal-content p { 
    margin-bottom: 12pt; 
  }

  .legal-content ul, .legal-content ol { 
    margin-left: 1.5cm; 
    margin-bottom: 12pt; 
  }
  
  .legal-content li {
    padding-left: 0.5cm;
  }

  .legal-content strong {
    font-weight: 700;
  }

  /* Signature Block Simulation */
  .legal-content blockquote {
    border: none;
    margin: 3cm 0 0 50%;
    padding: 0;
    text-align: center;
    font-style: normal;
  }
  
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.3); border-radius: 10px; }
`;

// --- AI PROMPT ENGINEERING ---
const constructSmartPrompt = (userText: string, template: TemplateType): string => {
    // Determine Domain & Restrictions
    let domainInstruction = "";
    const lowerText = userText.toLowerCase();
    
    if (['alimentacion', 'femij', 'martes', 'shkurorëzim'].some(k => lowerText.includes(k))) {
        domainInstruction = "DOMAIN: FAMILY LAW (Kosovo). CITE: 'Ligji për Familjen'.";
    } else if (['shpk', 'aksion', 'biznes'].some(k => lowerText.includes(k))) {
        domainInstruction = "DOMAIN: CORPORATE LAW (Kosovo). CITE: 'Ligji për Shoqëritë Tregtare'.";
    }

    // Strict Formatting Instructions for Kosovo Courts
    const formatInstruction = `
    FORMAT REQUIREMENT: KOSOVO COURT STYLE (Gjykata Themelore Standard).
    STRUCTURE:
    1. Header: COURT NAME (Centered, Uppercase).
    2. Parties: Paditës vs I Paditur (Left aligned).
    3. Subject (Lënda): Short summary (Left aligned).
    4. TITLE: (e.g. PADIT, KUNDËRPADI) - Centered, Bold, Uppercase.
    5. SECTIONS: BAZA LIGJORE (Legal Basis), ARSYETIMI (Reasoning), PETITUMI/KONKLUZIONI (Petition). Write these headings in uppercase followed by a colon, left‑aligned.
    6. SIGNATURE BLOCK: Place at bottom right.
    
    TONE: Formal, Direct, Legal Albanian.
    `;

    return `[INSTRUCTION: ${domainInstruction}] [TEMPLATE: ${template}] \n${formatInstruction}\n\n CONTENT INPUT:\n${userText}`;
};

// --- SUB-COMPONENTS ---

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-1 text-primary-start">
        {[0, 0.2, 0.4].map((delay, i) => (
            <motion.span 
                key={i}
                animate={{ opacity: [0.3, 1, 0.3] }} 
                transition={{ duration: 1.2, repeat: Infinity, delay }} 
                className="w-1 h-1 bg-current rounded-full mx-0.5" 
            />
        ))}
    </span>
);

// Preprocess text: convert uppercase lines to markdown headings.
// - If a line matches a known section heading (with or without colon), ensure it ends with a colon and becomes H3.
// - Other uppercase lines become H2 (centered titles).
const preprocessHeadings = (text: string): string => {
    const lines = text.split('\n');
    const knownSections = ['BAZA LIGJORE', 'ARSYETIMI', 'PETITUMI', 'KONKLUZIONI'];
    
    return lines.map(line => {
        const trimmed = line.trim();
        // Skip empty lines
        if (trimmed.length === 0) return line;
        
        // Check if line is uppercase (allowing punctuation)
        const isUppercase = /^[A-ZËÇÜÖÄ\s\d\.,\-–—:]+$/.test(trimmed);
        if (!isUppercase) return line;
        
        // Check if it's a known section heading (with or without colon)
        const withoutColon = trimmed.replace(/:$/, '');
        if (knownSections.includes(withoutColon)) {
            // Ensure it ends with a colon
            const fixed = trimmed.endsWith(':') ? trimmed : `${trimmed}:`;
            return `### ${fixed}`;
        }
        
        // Other uppercase lines become H2 (centered titles)
        return `## ${line}`;
    }).join('\n');
};

const DraftResultRenderer: React.FC<{ text: string }> = React.memo(({ text }) => {
    const processedText = preprocessHeadings(text);
    return (
        <div className="legal-document">
             <div className="legal-content">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    components={{
                        h1: ({node, ...props}) => <h1 {...props} />,
                        h2: ({node, ...props}) => <h2 {...props} />,
                        h3: ({node, ...props}) => <h3 {...props} />,
                        blockquote: ({node, ...props}) => <blockquote {...props} />, // Used for signature block
                        p: ({node, ...props}) => {
                            const content = String(props.children);
                            // Special handling for AI-generated disclaimer
                            if (content.includes('gjeneruar nga AI')) {
                                return <p className="text-center italic mt-12 pt-4 border-t border-black text-[9pt] opacity-60" {...props} />;
                            }
                            return <p {...props} />;
                        }
                    }} 
                >
                    {processedText}
                </ReactMarkdown>
             </div>
        </div>
    );
});

// --- SUB COMPONENTS (Internal for Single-File Requirement) ---

const ConfigPanel: React.FC<ConfigPanelProps> = ({ 
    t, isPro, cases, selectedCaseId, selectedTemplate, context, isSubmitting, 
    onSelectCase, onSelectTemplate, onChangeContext, onSubmit 
}) => (
    <div className="glass-panel flex flex-col h-auto lg:h-[700px] p-4 sm:p-6 rounded-2xl border border-white/10 shrink-0">
        <h3 className="text-white font-semibold mb-6 flex items-center gap-2">
            <FileText className="text-primary-start" size={20} />{t('drafting.configuration')}
        </h3>
        <div className="flex flex-col gap-5 flex-1 min-h-0 overflow-hidden">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 flex-shrink-0">
                {/* Case Selector */}
                <div>
                    <div className="flex justify-between mb-1">
                        <label className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">{t('drafting.caseLabel')}</label>
                        {!isPro && <span className="text-[9px] text-amber-500 font-bold bg-amber-500/10 px-1.5 rounded border border-amber-500/20 flex items-center gap-1"><Lock size={8}/> PRO</span>}
                    </div>
                    <div className="relative">
                        <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <select 
                            value={selectedCaseId} 
                            onChange={(e) => onSelectCase(e.target.value)} 
                            disabled={!isPro} 
                            className="glass-input w-full pl-10 pr-10 py-3.5 rounded-xl text-sm appearance-none outline-none"
                        >
                            <option value="">{t('drafting.noCaseSelected')}</option>
                            {cases.map((c: any) => <option key={c.id} value={c.id} className="bg-gray-900">{c.title || c.case_name}</option>)}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                    </div>
                </div>
                
                {/* Template Selector */}
                <div>
                    <label className="block text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">{t('drafting.templateLabel')}</label>
                    <div className="relative">
                        <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <select 
                            value={selectedTemplate} 
                            onChange={(e) => onSelectTemplate(e.target.value)} 
                            disabled={!isPro} 
                            className="glass-input w-full pl-10 pr-10 py-3.5 rounded-xl text-sm appearance-none outline-none"
                        >
                            <option value="generic">{t('drafting.templateGeneric')}</option>
                            
                            <optgroup label={t('drafting.groupLitigation')} className="bg-gray-900 italic">
                                <option value="padi">{t('drafting.templatePadi')}</option>
                                <option value="pergjigje">{t('drafting.templatePergjigje')}</option>
                                <option value="kunderpadi">{t('drafting.templateKunderpadi')}</option>
                                <option value="ankese">{t('drafting.templateAnkese')}</option>
                                <option value="prapësim">{t('drafting.templatePrapesim')}</option>
                            </optgroup>
                            
                            <optgroup label={t('drafting.groupCorporate')} className="bg-gray-900 italic">
                                <option value="nda">{t('drafting.templateNDA')}</option>
                                <option value="mou">{t('drafting.templateMoU')}</option>
                                <option value="shareholders">{t('drafting.templateShareholders')}</option>
                                <option value="sla">{t('drafting.templateSLA')}</option>
                            </optgroup>
                            
                             <optgroup label={t('drafting.groupEmployment')} className="bg-gray-900 italic">
                                <option value="employment_contract">{t('drafting.templateKontrate')}</option>
                                <option value="termination_notice">{t('drafting.templateTermination')}</option>
                                <option value="warning_letter">{t('drafting.templateWarning')}</option>
                            </optgroup>

                            <optgroup label={t('drafting.groupRealEstate')} className="bg-gray-900 italic">
                                <option value="lease_agreement">{t('drafting.templateLease')}</option>
                                <option value="sales_purchase">{t('drafting.templateSales')}</option>
                                <option value="power_of_attorney">{t('drafting.templatePoA')}</option>
                            </optgroup>

                            <optgroup label={t('drafting.groupCompliance')} className="bg-gray-900 italic">
                                <option value="terms_conditions">{t('drafting.templateTerms')}</option>
                                <option value="privacy_policy">{t('drafting.templatePrivacy')}</option>
                            </optgroup>
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                    </div>
                </div>
            </div>

            {/* Context Input */}
            <div className="flex-1 flex flex-col min-h-0">
                <label className="block text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">{t('drafting.instructionsLabel')}</label>
                <textarea 
                    value={context} 
                    onChange={(e) => onChangeContext(e.target.value)} 
                    placeholder={t('drafting.promptPlaceholder')} 
                    className="glass-input w-full p-4 rounded-xl text-sm flex-1 resize-none outline-none focus:ring-1 focus:ring-primary-start/40 transition-all overflow-y-auto custom-scrollbar"
                />
            </div>

            <button 
                onClick={onSubmit} 
                disabled={isSubmitting || !context.trim()} 
                className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end text-white font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-primary-start/20 hover:opacity-95 transition-all active:scale-[0.98] mt-4 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
              {isSubmitting ? t('drafting.statusWorking') : t('drafting.generateBtn')}
            </button>
        </div>
    </div>
);

const ResultPanel: React.FC<ResultPanelProps> = ({ t, currentJob, saving, notification, onSave, onClear }) => {
    
    // Derived Status UI
    const statusUI = useMemo(() => {
        switch(currentJob.status) {
            case 'COMPLETED': return { text: t('drafting.statusCompleted'), color: 'text-green-400', icon: <CheckCircle className="h-5 w-5" /> };
            case 'FAILED': return { text: t('drafting.statusFailed'), color: 'text-red-400', icon: <AlertCircle className="h-5 w-5" /> };
            case 'PROCESSING': return { text: t('drafting.statusWorking'), color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse" /> };
            default: return { text: t('drafting.statusResult'), color: 'text-white', icon: <Scale className="h-5 w-5 text-gray-500" /> };
        }
    }, [currentJob.status, t]);

    return (
        <div className="flex flex-col h-auto lg:h-[700px] rounded-2xl bg-[#0d0f14] border border-white/10 overflow-hidden shadow-2xl shrink-0">
            {/* Header */}
            <div className="flex justify-between items-center p-4 bg-white/5 border-b border-white/5 flex-shrink-0">
                <div className="flex items-center gap-3">
                   <div className={`${statusUI.color} p-2 bg-white/5 rounded-lg`}>{statusUI.icon}</div>
                   <h3 className="text-white text-xs sm:text-sm font-semibold uppercase tracking-widest leading-none">{statusUI.text}</h3>
                </div>
                <div className="flex gap-1 sm:gap-2">
                    <button onClick={onSave} title={t('drafting.saveToArchive')} disabled={!currentJob.result || saving} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-primary-start transition-colors disabled:opacity-30">
                        {saving ? <RefreshCw className="animate-spin" size={18}/> : <Archive size={18}/>}
                    </button>
                    <button 
                        onClick={() => { if(currentJob.result) { navigator.clipboard.writeText(currentJob.result); } }} 
                        title={t('drafting.copy')} 
                        className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-colors"
                    >
                        <Copy size={18}/>
                    </button>
                    <button 
                        onClick={() => { 
                            if(currentJob.result) { 
                                const blob = new Blob([currentJob.result], { type: 'text/plain' }); 
                                const url = URL.createObjectURL(blob); 
                                const a = document.createElement('a'); 
                                a.href = url; 
                                a.download = `draft-${Date.now()}.txt`; 
                                a.click(); 
                            } 
                        }} 
                        title={t('drafting.download')} 
                        className="p-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-colors"
                    >
                        <Download size={18}/>
                    </button>
                    <button onClick={onClear} title={t('drafting.clear')} className="p-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"><Trash2 size={18}/></button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 bg-gray-900/40 overflow-y-auto p-4 sm:p-8 relative custom-scrollbar flex justify-center">
                <AnimatePresence mode="wait">
                    {currentJob.result ? (
                        <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="w-full flex justify-center">
                            {notification && (
                                <div className={`mb-4 p-3 text-xs rounded-lg flex items-center gap-2 border w-full max-w-[21cm] mx-auto ${notification.type === 'success' ? 'bg-green-500/20 text-green-400 border-green-500/20' : 'bg-red-500/20 text-red-400 border-red-500/20'}`}>
                                    {notification.type === 'success' ? <CheckCircle size={14}/> : <AlertCircle size={14}/>} 
                                    {notification.msg}
                                </div>
                            )}
                            <DraftResultRenderer text={currentJob.result} />
                        </motion.div>
                    ) : (
                        <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 flex flex-col items-center justify-center text-center px-6 pointer-events-none">
                            {currentJob.status === 'PROCESSING' ? (
                                <div className="flex flex-col items-center">
                                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg shadow-primary-start/20 mb-6 animate-pulse">
                                        <BrainCircuit className="w-8 h-8 text-white" />
                                    </div>
                                    <p className="text-white font-medium flex items-center">{t('drafting.statusWorking')}<ThinkingDots /></p>
                                </div>
                            ) : (
                                <div className="opacity-20 flex flex-col items-center">
                                    <FileText size={56} className="text-gray-600 mb-4" />
                                    <p className="text-gray-400 text-sm">{t('drafting.emptyState')}</p>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

// --- MAIN COMPONENT ---

const DraftingPage: React.FC = () => {
  const { t } = useTranslation(); 
  const { user } = useAuth();
  
  // State
  const [context, setContext] = useState(() => localStorage.getItem('drafting_context') || '');
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<NotificationState | null>(null);

  const [currentJob, setCurrentJob] = useState<DraftingJobState>(() => {
    const saved = localStorage.getItem('drafting_job');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.status === 'PROCESSING') {
            return parsed.result ? { ...parsed, status: 'COMPLETED' } : { ...parsed, status: 'FAILED', error: 'Interrupted' };
        }
        return parsed;
      } catch { return { status: null, result: null, error: null }; }
    }
    return { status: null, result: null, error: null };
  });

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  // Effects
  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { localStorage.setItem('drafting_job', JSON.stringify(currentJob)); }, [currentJob]);
  useEffect(() => { 
      if(isPro) apiService.getCases().then(res => setCases(res || [])).catch(console.error); 
  }, [isPro]);
  
  // Notification Timer
  useEffect(() => {
      if (notification) {
          const timer = setTimeout(() => setNotification(null), 3000);
          return () => clearTimeout(timer);
      }
  }, [notification]);

  // Handlers
  const handleAutofillCase = useCallback((caseId: string) => {
    const c = cases.find(item => item.id === caseId);
    if (c) {
        setContext(prev => {
            const newContext = `RASTI: ${c.title || c.case_number}\nKLIENTI: ${c.client?.name || 'N/A'}\nFAKTET:\n${c.description || '-'}`;
            return prev ? `${prev}\n\n${newContext}` : newContext;
        });
    }
  }, [cases]);

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setNotification(null);
    
    let acc = "";
    try {
      const stream = apiService.draftLegalDocumentStream({
          user_prompt: constructSmartPrompt(context.trim(), selectedTemplate),
          document_type: isPro ? selectedTemplate : 'generic',
          case_id: isPro && selectedCaseId ? selectedCaseId : undefined,
          use_library: isPro && !!selectedCaseId
      });
      
      for await (const chunk of stream) {
          acc += chunk;
          setCurrentJob(prev => ({ ...prev, result: acc }));
      }
      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));
    } catch (e: any) {
      setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: e.message || t('common.error') }));
      setNotification({ msg: t('drafting.statusFailed'), type: 'error' });
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
      await apiService.uploadArchiveItem(new File([blob], fileName), fileName, 'DRAFT', selectedCaseId || undefined);
      setNotification({ msg: t('drafting.savedToArchive'), type: 'success' });
    } catch (err) { 
        setNotification({ msg: t('drafting.saveFailed'), type: 'error' });
    } finally { setSaving(false); }
  };

  const clearJob = () => {
      if (currentJob.result && !window.confirm(t('drafting.confirmClear'))) return;
      setCurrentJob({ status: null, result: null, error: null });
      setContext('');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8 flex flex-col h-full lg:overflow-hidden overflow-y-auto">
      <style>{lawyerGradeStyles}</style>
      
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center justify-center gap-3">
            <PenTool className="text-primary-start" />{t('drafting.title')}
        </h1>
      </div>

      <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 flex-1 lg:overflow-hidden min-h-0">
        
        {/* === CONFIGURATION PANEL === */}
        <ConfigPanel 
            t={t}
            isPro={isPro}
            cases={cases}
            selectedCaseId={selectedCaseId}
            selectedTemplate={selectedTemplate}
            context={context}
            isSubmitting={isSubmitting}
            onSelectCase={(id: string) => { setSelectedCaseId(id); handleAutofillCase(id); }}
            onSelectTemplate={(val: string) => setSelectedTemplate(val as TemplateType)}
            onChangeContext={setContext}
            onSubmit={runDraftingStream}
        />

        {/* === RESULT PANEL === */}
        <ResultPanel 
            t={t}
            currentJob={currentJob}
            saving={saving}
            notification={notification}
            onSave={handleSaveToArchive}
            onClear={clearJob}
        />
      </div>
    </div>
  );
};

export default DraftingPage;