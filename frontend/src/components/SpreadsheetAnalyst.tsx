// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - SPREADSHEET ANALYST V24.0 (CLEAN NEUTRAL CHAT BUBBLES WITHOUT SOLID BLUE BACKGROUNDS)

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, Send, Bot, FileText, AlertCircle, Info, Table, AlertTriangle, User, CheckCircle2, Gavel, BrainCircuit, Sparkles
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { LawCitationText } from './LawCitationText';
import { ThinkingDots } from './chat/ThinkingDots';
import { extractFollowUpQuestions } from '../utils/chatHelpers';

const CACHE_KEY = 'juristi_analyst_cache';
const getCache = () => { try { const raw = localStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : {}; } catch { return {}; } };

// --- DATA STRUCTURES ---
interface SmartFinancialReport { executive_summary: string; }
interface ChatMessage { id: string; role: 'user' | 'agent'; content: string; timestamp: Date; evidenceCount?: number; }
interface CachedState { report: SmartFinancialReport; chat: ChatMessage[]; fileName: string; }
interface SpreadsheetAnalystProps { 
  caseId: string; 
  onReportAvailable?: (summaryText: string, fileNameText: string) => void;
}

// --- High-Fidelity Executive Memorandum Renderer with Dual-Theme Contrast ---
const renderMarkdown = (text: string) => {
    if (!text) return null;

    const lines = text.split('\n');
    let currentSection = 1; // 1: BLUF/Citizen, 2: Anomalies (RED/ROSE), 3: Legal (INDIGO), 4: Action Plan (EMERALD)

    return lines.map((line, i) => {
        let trimmed = line.trim();
        if (trimmed === '---') return <hr key={i} className="border-main my-4" />;
        if (!trimmed) return <div key={i} className="h-2" />;

        // Update currentSection based on text keywords
        if (trimmed.includes('2.') || trimmed.includes('Parregullsive') || trimmed.includes('Anomalitë') || trimmed.includes('Anomali')) {
            currentSection = 2;
        } else if (trimmed.includes('3.') || trimmed.includes('Implikimet Ligjore') || trimmed.includes('Tatimore')) {
            currentSection = 3;
        } else if (trimmed.includes('4.') || trimmed.includes('Plani i Veprimit') || trimmed.includes('Hartimi')) {
            currentSection = 4;
        } else if (trimmed.includes('1.') || trimmed.includes('Përmbledhja')) {
            currentSection = 1;
        }

        // Citizen Guide Sub-Card (Blue)
        if (trimmed.includes('UDHËZUESI PËR QYTETARIN') || trimmed.includes('👨‍💼')) {
            const cleanTitle = trimmed.replace(/^[#\*\s]+|[#\*\s]+$/g, '');
            return (
                <div key={i} className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/30 mb-3 shadow-sm">
                    <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-black text-xs uppercase tracking-wider">
                        <User size={15} />
                        <span>{cleanTitle}</span>
                    </div>
                </div>
            );
        }

        // Technical Forensic Sub-Card (Teal)
        if (trimmed.includes('ANALIZA TEKNIKE FORENZIKE') || trimmed.includes('📊')) {
            const cleanTitle = trimmed.replace(/^[#\*\s]+|[#\*\s]+$/g, '');
            return (
                <div key={i} className="p-4 rounded-2xl bg-teal-500/10 border border-teal-500/30 mb-3 shadow-sm mt-4">
                    <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400 font-black text-xs uppercase tracking-wider">
                        <Activity size={15} />
                        <span>{cleanTitle}</span>
                    </div>
                </div>
            );
        }

        // Section Headers
        if (trimmed.startsWith('#') || (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length < 70)) {
            const titleClean = trimmed.replace(/^[#\*\s]+|[#\*\s]+$/g, '');
            
            let headingBadge = 'bg-primary-start/10 border-primary-start/30 text-primary-start';
            let HeadingIcon = Activity;

            if (currentSection === 2) {
                headingBadge = 'bg-rose-500/15 border-rose-500/40 text-rose-600 dark:text-rose-400';
                HeadingIcon = AlertTriangle;
            } else if (currentSection === 3) {
                headingBadge = 'bg-indigo-500/15 border-indigo-500/40 text-indigo-600 dark:text-indigo-400';
                HeadingIcon = Gavel;
            } else if (currentSection === 4) {
                headingBadge = 'bg-emerald-500/15 border-emerald-500/40 text-emerald-600 dark:text-emerald-400';
                HeadingIcon = CheckCircle2;
            }

            return (
                <div key={i} className={`p-3.5 rounded-2xl border mb-3.5 mt-5 shadow-sm flex items-center gap-2.5 ${headingBadge}`}>
                    <HeadingIcon size={16} className="shrink-0" />
                    <h3 className="text-xs sm:text-sm font-black uppercase tracking-wider">
                        {titleClean}
                    </h3>
                </div>
            );
        }

        // Detect Numbered Items (1., 2., 3., 4., 5.)
        const findingMatch = trimmed.match(/^(\d+)\.\s*\*\*(.*?)\*\*\s*:\s*(.*)/i) || trimmed.match(/^(\d+)\.\s*(.*)/i);
        if (findingMatch) {
            const num = findingMatch[1];
            let title = findingMatch[2] ? findingMatch[2].replace(/\*\*/g, '').trim() : '';
            let body = findingMatch[3] ? findingMatch[3].trim() : findingMatch[2] ? findingMatch[2].trim() : '';

            if (!title && body.includes(':')) {
                const parts = body.split(/:(.*)/s);
                title = parts[0].replace(/\*\*/g, '').trim();
                body = parts[1].replace(/\*\*/g, '').trim();
            }

            const isAnomaly = currentSection === 2 || /anomali|benford|deficit|mashtrim|dyshimt|rrezik|fiktiv|gabim|shkelje|mungesë/i.test(`${title} ${body}`);
            const isAction = currentSection === 4 || /auditimi|intervistimi|hartimi|kontrolli|bisedoni|përdorni/i.test(`${title} ${body}`);

            let cardStyle = 'bg-canvas border-main text-text-primary';
            let badgeStyle = 'bg-primary-start/20 text-primary-start border border-primary-start/30';
            let titleStyle = 'text-primary-start';
            let ItemIcon = Activity;

            if (isAnomaly) {
                cardStyle = 'bg-rose-500/10 border-rose-500/30 text-text-primary shadow-md shadow-rose-500/5';
                badgeStyle = 'bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/40';
                titleStyle = 'text-rose-600 dark:text-rose-400';
                ItemIcon = AlertTriangle;
            } else if (isAction) {
                cardStyle = 'bg-emerald-500/10 border-emerald-500/30 text-text-primary shadow-sm';
                badgeStyle = 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40';
                titleStyle = 'text-emerald-600 dark:text-emerald-400';
                ItemIcon = CheckCircle2;
            } else if (currentSection === 3) {
                cardStyle = 'bg-indigo-500/10 border-indigo-500/30 text-text-primary shadow-sm';
                badgeStyle = 'bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-500/40';
                titleStyle = 'text-indigo-600 dark:text-indigo-400';
                ItemIcon = Gavel;
            }

            return (
                <div key={i} className={`p-4 rounded-2xl border shadow-sm mb-3.5 transition-all ${cardStyle}`}>
                    <div className="flex items-center gap-2 mb-2">
                        <span className={`w-6 h-6 rounded-lg font-black text-xs flex items-center justify-center shrink-0 ${badgeStyle}`}>
                            {num}
                        </span>
                        {title && (
                            <h4 className={`text-xs font-black uppercase tracking-wide flex items-center gap-1.5 ${titleStyle}`}>
                                <ItemIcon size={14} className="shrink-0" />
                                {title}
                            </h4>
                        )}
                    </div>
                    <div className="text-xs sm:text-sm leading-relaxed font-medium pl-8 text-text-primary">
                        <LawCitationText text={(body || trimmed).replace(/\*\*/g, '')} />
                    </div>
                </div>
            );
        }

        // Regular Paragraph
        return (
            <p key={i} className="text-text-primary text-xs sm:text-sm leading-relaxed mb-3 font-medium">
                <LawCitationText text={trimmed.replace(/\*\*/g, '')} />
            </p>
        );
    });
};

const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId, onReportAvailable }) => {
    const { t, i18n } = useTranslation();
    const [fileName, setFileName] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<SmartFinancialReport | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [question, setQuestion] = useState('');
    const [isInterrogating, setIsInterrogating] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const notifyParent = useCallback((summary: string, file: string) => {
        (window as any).__LATEST_FORENSIC_SUMMARY__ = summary;
        (window as any).__LATEST_FORENSIC_FILENAME__ = file;
        if (onReportAvailable && summary) {
            onReportAvailable(summary, file);
        }
    }, [onReportAvailable]);

    useEffect(() => {
        const cache = getCache();
        const caseData = cache[caseId];
        if (caseData && caseData.report) {
            setResult(caseData.report);
            setChatHistory((caseData.chat || []).map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })));
            setFileName(caseData.fileName || 'File');
            notifyParent(caseData.report.executive_summary, caseData.fileName || 'File');
        }
    }, [caseId, notifyParent]);

    useEffect(() => {
        if (result) {
            const cache = getCache();
            const dataToCache: CachedState = { report: result, chat: chatHistory, fileName: fileName || 'File' };
            cache[caseId] = dataToCache;
            localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
            notifyParent(result.executive_summary, fileName || 'File');
        }
    }, [result, chatHistory, fileName, caseId, notifyParent]);

    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory, isInterrogating]);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const newFile = e.target.files[0];
            setFileName(newFile.name); setError(null); setResult(null); setChatHistory([]); setIsAnalyzing(true);
            try {
                const data = await apiService.forensicAnalyzeSpreadsheet(caseId, newFile, i18n.language || 'sq') as unknown as SmartFinancialReport;
                setResult(data);
                if (data && data.executive_summary) {
                    notifyParent(data.executive_summary, newFile.name);
                }
            } catch (err: any) { 
                const msg = err.response?.data?.detail || t('analyst.errorAnalysis', 'Analiza dështoi. Sigurohuni që skedari ka kolonën "Shuma" ose "Amount".');
                setError(msg); 
            } finally { setIsAnalyzing(false); }
        }
    };

    const handleSendQuestion = async (customPrompt?: string) => {
        const queryText = customPrompt || question.trim();
        if (!queryText || isInterrogating) return;

        if (!customPrompt) setQuestion('');
        const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: queryText, timestamp: new Date() };
        setChatHistory((prev) => [...prev, userMsg]);
        setIsInterrogating(true);

        try {
            const res = await apiService.forensicInterrogateEvidence(caseId, queryText);
            const aiContent = res.answer || t('analyst.noAnswer', 'Nuk u gjet përgjigje në pasqyrën financiare.');
            const aiMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: aiContent,
                timestamp: new Date(),
                evidenceCount: res.supporting_evidence_count,
            };
            setChatHistory((prev) => [...prev, aiMsg]);
        } catch {
            const errMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: t('analyst.errorConnection', 'Gabim gjatë lidhjes me shërbimin e analizës financiare.'),
                timestamp: new Date(),
            };
            setChatHistory((prev) => [...prev, errMsg]);
        } finally {
            setIsInterrogating(false);
        }
    };

    return (
        <div className="w-full flex flex-col gap-4 pb-4">
            <AnimatePresence>
                {error && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                        <div className="p-3.5 bg-danger-start/10 border border-danger-start/20 rounded-xl flex items-center gap-2.5 text-danger-start shadow-sm">
                            <AlertCircle className="w-4 h-4 shrink-0" />
                            <span className="text-xs font-bold uppercase tracking-wide">{error}</span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }} 
                        animate={{ opacity: 1, y: 0 }} 
                        exit={{ opacity: 0, y: -10 }} 
                        className="grid grid-cols-1 lg:grid-cols-2 gap-6"
                    >
                        {/* LEFT PANEL: Forensic Memorandum of Findings */}
                        <div className="glass-panel p-0 rounded-2xl border border-main bg-surface flex flex-col h-[72vh] min-h-[520px] overflow-hidden shadow-sm">
                            <div className="px-6 py-4 border-b border-main bg-canvas/80 backdrop-blur-md flex items-center justify-between gap-2.5 shrink-0">
                                <div className="flex items-center gap-2.5">
                                    <FileText size={16} className="text-primary-start shrink-0" />
                                    <h3 className="text-xs font-black text-text-primary uppercase tracking-wider">Memorandumi i Gjetjeve</h3>
                                </div>
                                {fileName && <span className="text-[10px] font-mono text-text-muted bg-canvas px-2.5 py-1 rounded-md border border-main">{fileName}</span>}
                            </div>
                            <div className="flex-1 overflow-y-auto p-6 custom-finance-scroll">
                                <div className="max-w-2xl mx-auto space-y-2">
                                    {renderMarkdown(result.executive_summary)}
                                </div>
                            </div>
                        </div>

                        {/* RIGHT PANEL: Socratic Interrogation Chat - CLEAN NEUTRAL BUBBLES */}
                        <div className="glass-panel p-0 rounded-2xl border border-main bg-surface flex flex-col h-[72vh] min-h-[520px] overflow-hidden shadow-sm">
                            <div className="px-6 py-4 border-b border-main bg-canvas/80 backdrop-blur-md flex items-center gap-2.5 shrink-0">
                                <Bot className="text-primary-start w-4 h-4 shrink-0" />
                                <div>
                                    <h3 className="text-xs font-black text-text-primary uppercase tracking-wider leading-none">{t('analyst.interrogationTitle', 'Interrogimi i Dëshmive')}</h3>
                                    <p className="text-[10px] font-medium text-text-muted mt-0.5">{t('analyst.interrogationSubtitle', 'Bëni pyetje rreth gjetjeve të memorandumit.')}</p>
                                </div>
                            </div>

                            {/* Chat Messages */}
                            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 custom-finance-scroll">
                                {(chatHistory || []).map((msg) => {
                                    const isAi = msg.role === 'agent' || (msg.role as string) === 'ai';
                                    const { cleanText, questions: suggestedQuestions } = extractFollowUpQuestions(msg.content);

                                    return (
                                        <div key={msg.id} className={`flex gap-3 ${!isAi ? 'flex-row-reverse' : 'flex-row'}`}>
                                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border shadow-sm ${
                                                isAi ? 'bg-primary-start text-white border-primary-start' : 'bg-surface border-main text-text-secondary'
                                            }`}>
                                                {isAi ? <BrainCircuit size={16} /> : <User size={16} />}
                                            </div>

                                            <div className={`relative max-w-[85%] rounded-2xl p-3.5 sm:p-4 text-xs sm:text-sm leading-relaxed shadow-sm border ${
                                                !isAi ? 'bg-surface text-text-primary border-main rounded-tr-none' : 'bg-canvas text-text-primary border-main rounded-tl-none'
                                            }`}>
                                                {renderMarkdown(cleanText || msg.content)}

                                                {/* Follow-up question pills */}
                                                {isAi && suggestedQuestions.length > 0 && (
                                                    <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-main">
                                                        <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                                                            <Sparkles size={11} className="text-primary-start animate-pulse" />
                                                            Pyetje Sugjeruese
                                                        </span>
                                                        <div className="flex flex-col gap-1.5">
                                                            {suggestedQuestions.map((q, qIdx) => (
                                                                <button
                                                                    key={qIdx}
                                                                    type="button"
                                                                    onClick={() => handleSendQuestion(q)}
                                                                    className="px-3 py-1.5 bg-surface border border-main hover:border-primary-start/50 text-text-secondary hover:text-text-primary rounded-xl text-xs font-medium text-left transition-all hover-lift focus:outline-none flex items-center gap-1.5"
                                                                >
                                                                    <span className="w-1.5 h-1.5 bg-primary-start/40 rounded-full shrink-0" />
                                                                    {q}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}

                                {/* SOKRATI DUKE MENDUAR THINKING BUBBLE */}
                                {isInterrogating && (
                                    <div className="flex items-start gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-primary-start text-white flex items-center justify-center shadow-sm shrink-0 border border-primary-start">
                                            <BrainCircuit size={16} className="animate-pulse" />
                                        </div>
                                        <div className="bg-surface border border-main rounded-2xl rounded-tl-none px-4 py-2.5 shadow-sm flex items-center gap-2">
                                            <span className="text-xs font-bold text-primary-start tracking-wide">
                                                Sokrati duke menduar
                                            </span>
                                            <ThinkingDots />
                                        </div>
                                    </div>
                                )}

                                <div ref={chatEndRef} />
                            </div>

                            {/* Chat Input Form */}
                            <div className="p-4 border-t border-main bg-canvas shrink-0">
                                <form 
                                    onSubmit={(e) => { 
                                        e.preventDefault(); 
                                        handleSendQuestion();
                                    }} 
                                    className="relative flex items-center gap-2 max-w-4xl mx-auto"
                                >
                                    <input 
                                        type="text" 
                                        value={question} 
                                        onChange={(e) => setQuestion(e.target.value)} 
                                        placeholder={t('analyst.placeholderQuestion', 'Bëni një pyetje rreth dosjes...')} 
                                        className="w-full p-3 pr-12 bg-surface border border-main rounded-xl text-xs sm:text-sm leading-relaxed text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
                                    />
                                    <button 
                                        type="submit" 
                                        disabled={!question.trim() || isInterrogating} 
                                        className="absolute right-2 h-8 w-8 flex items-center justify-center bg-primary-start text-white rounded-lg hover:bg-primary-start/90 transition-all disabled:opacity-30"
                                    >
                                        <Send size={15} />
                                    </button>
                                </form>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            
            {isAnalyzing && !result && (
                <div className="flex flex-col items-center justify-center py-24">
                    <div className="relative mb-6">
                        <div className="w-16 h-16 rounded-full border-4 border-primary-start/20 border-t-primary-start animate-spin"></div>
                        <Activity className="absolute inset-0 m-auto w-6 h-6 text-primary-start animate-pulse" />
                    </div>
                    <h3 className="text-base font-black text-text-primary uppercase tracking-wider">
                        {t('analysis.analyzing', 'Sokrati duke analizuar të dhënat...')}
                    </h3>
                    <p className="text-text-muted text-[10px] font-black uppercase tracking-widest mt-2">Algoritmi Forenzik i Juristi AI</p>
                </div>
            )}

            {!result && !isAnalyzing && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6 max-w-4xl mx-auto w-full">
                    <div className="flex flex-col items-center justify-center text-center py-12 sm:py-16 px-6 glass-panel rounded-3xl border border-main bg-surface shadow-sm w-full">
                        <div className="w-16 h-16 bg-primary-start/10 rounded-2xl border border-primary-start/20 flex items-center justify-center mb-6 shadow-sm">
                            <FileSpreadsheet className="w-8 h-8 text-primary-start" />
                        </div>
                        <h3 className="text-lg sm:text-xl font-black text-text-primary mb-2 uppercase tracking-tight">
                            {t('analyst.readyTitle', 'Gati për Hulumtim Forenzik')}
                        </h3>
                        <p className="text-xs sm:text-sm text-text-secondary max-w-md mb-8 leading-relaxed font-medium">
                            {t('analyst.readySubtitle', 'Zgjidhni një skedar Excel ose CSV për të filluar analizën automatike të pasqyrave financiare.')}
                        </p>
                        
                        <div className="relative group">
                            <input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"/>
                            <div className="h-11 px-8 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-md transition-all cursor-pointer">
                                <FileSpreadsheet className="w-4 h-4" />
                                <span>{t('analyst.selectFile', 'Zgjidh Skedarin')}</span>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="glass-panel p-6 rounded-2xl border border-main bg-surface shadow-sm">
                            <div className="flex items-center gap-2.5 mb-4">
                                <Table size={16} className="text-primary-start" />
                                <h4 className="text-xs font-black text-text-primary uppercase tracking-wider">Struktura e Kërkuar</h4>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-3 bg-canvas rounded-xl border border-main">
                                    <span className="text-xs font-bold text-text-secondary">Shuma / Amount</span>
                                    <span className="text-[10px] font-black text-danger-start uppercase tracking-wider bg-danger-start/10 px-2 py-0.5 rounded border border-danger-start/20">E Domosdoshme</span>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-canvas rounded-xl border border-main opacity-70">
                                    <span className="text-xs font-bold text-text-secondary">Data / Date</span>
                                    <span className="text-[10px] font-black text-text-muted uppercase tracking-wider px-2 py-0.5 rounded border border-main">Opsionale</span>
                                </div>
                            </div>
                        </div>

                        <div className="glass-panel p-6 rounded-2xl border border-main bg-surface shadow-sm">
                            <div className="flex items-center gap-2.5 mb-4">
                                <Info size={16} className="text-primary-start" />
                                <h4 className="text-xs font-black text-text-primary uppercase tracking-wider">Këshillë Strategjike</h4>
                            </div>
                            <p className="text-xs text-text-secondary leading-relaxed font-medium">
                                Algoritmi ynë zbulon anomali, mungesa dhe transaksione të dyshimta automatikisht. Sigurohuni që kolonat të jenë të lexueshme për saktësi maksimale.
                            </p>
                        </div>
                    </div>
                </motion.div>
            )}
        </div>
    );
};

export default SpreadsheetAnalyst;