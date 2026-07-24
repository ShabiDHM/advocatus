// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - SPREADSHEET ANALYST V8.0 (STANDARDIZED TYPOGRAPHY & ZERO DOUBLE SCROLL)

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, CheckCircle, RefreshCw, Send, ShieldAlert, Bot, Save, FileText, AlertCircle, Info, Table
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

const CACHE_KEY = 'juristi_analyst_cache';
const getCache = () => { try { const raw = localStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : {}; } catch { return {}; } };

// --- DATA STRUCTURES ---
interface SmartFinancialReport { executive_summary: string; }
interface ChatMessage { id: string; role: 'user' | 'agent'; content: string; timestamp: Date; evidenceCount?: number; }
interface CachedState { report: SmartFinancialReport; chat: ChatMessage[]; fileName: string; }
interface SpreadsheetAnalystProps { caseId: string; }

// --- High-Fidelity Markdown Renderer (theme-aware) ---
const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
        const trimmed = line.trim();
        if (trimmed === '---') return <hr key={i} className="border-main my-6" />;
        if (!trimmed) return <div key={i} className="h-3" />;
        if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
            return <h3 key={i} className="text-xs font-black text-text-primary uppercase tracking-wider mt-6 mb-3 border-b border-main pb-2">{trimmed.slice(2, -2)}</h3>;
        }
        if (/^\d\.\d\.?/.test(trimmed) || /^\d\.\s/.test(trimmed)) {
             return <h4 key={i} className="text-primary-start font-black text-xs uppercase tracking-wider mt-4 mb-2">{trimmed}</h4>;
        }
        if (trimmed.includes(':')) {
            const parts = trimmed.split(/:(.*)/s);
            if (parts.length > 1 && parts[0].length < 35) { 
                return (
                    <p key={i} className="text-text-primary text-xs sm:text-sm leading-relaxed mb-2.5">
                        <strong className="font-black uppercase text-[10px] tracking-wider text-primary-start mr-2">{parts[0]}:</strong>
                        <span>{parts[1]}</span>
                    </p>
                );
            }
        }
        if (trimmed.startsWith('* ')) {
            return (
                <div key={i} className="flex gap-2.5 ml-1 mb-2.5 items-start">
                    <span className="text-primary-start mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-start shrink-0" />
                    <p className="text-text-primary text-xs sm:text-sm leading-relaxed">{trimmed.substring(2)}</p>
                </div>
            );
        }
        return <p key={i} className="text-text-primary text-xs sm:text-sm leading-relaxed mb-2.5">{trimmed}</p>;
    });
};

const useTypewriter = (text: string, speed: number = 10) => {
    const [displayText, setDisplayText] = useState('');
    useEffect(() => {
        setDisplayText('');
        if (text) {
            let i = 0;
            const intervalId = setInterval(() => {
                if (i < text.length) { setDisplayText(p => p + text.charAt(i)); i++; } 
                else clearInterval(intervalId);
            }, speed);
            return () => clearInterval(intervalId);
        }
    }, [text, speed]);
    return displayText;
};

const TypingChatMessage: React.FC<{ message: ChatMessage, onComplete: () => void }> = ({ message, onComplete }) => {
    const displayText = useTypewriter(message.content);
    const { t } = useTranslation();
    useEffect(() => { if (displayText.length === message.content.length) onComplete(); }, [displayText, message.content.length, onComplete]);
    return (
        <div className="flex justify-start">
            <div className="max-w-[88%] rounded-2xl rounded-tl-none p-4 text-xs sm:text-sm leading-relaxed bg-surface border border-main shadow-sm text-text-primary">
                <div>{renderMarkdown(displayText)}</div>
                {message.evidenceCount !== undefined && (
                    <div className="mt-2.5 pt-2.5 border-t border-main flex items-center gap-1.5 text-[10px] font-black text-text-muted uppercase tracking-wider">
                        <ShieldAlert className="w-3.5 h-3.5 text-status-success" />
                        {t('analyst.verifiedAgainst', 'Verifikuar kundrejt {{count}} dëshmive', { count: message.evidenceCount })}
                    </div>
                )}
            </div>
        </div>
    );
};

const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId }) => {
    const { t, i18n } = useTranslation();
    const [fileName, setFileName] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<SmartFinancialReport | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [question, setQuestion] = useState('');
    const [isInterrogating, setIsInterrogating] = useState(false);
    const [typingMessage, setTypingMessage] = useState<ChatMessage | null>(null);
    const [isArchiving, setIsArchiving] = useState(false);
    const [archiveSuccess, setArchiveSuccess] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const cache = getCache();
        const caseData = cache[caseId];
        if (caseData) {
            setResult(caseData.report);
            setChatHistory(caseData.chat.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })));
            setFileName(caseData.fileName);
        }
    }, [caseId]);

    useEffect(() => {
        if (result && !typingMessage) {
            const cache = getCache();
            const dataToCache: CachedState = { report: result, chat: chatHistory, fileName: fileName || 'File' };
            cache[caseId] = dataToCache;
            localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
        }
    }, [result, chatHistory, fileName, caseId, typingMessage]);

    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory, typingMessage]);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const newFile = e.target.files[0];
            setFileName(newFile.name); setError(null); setResult(null); setChatHistory([]); setIsAnalyzing(true);
            try {
                const data = await apiService.forensicAnalyzeSpreadsheet(caseId, newFile, i18n.language || 'sq') as unknown as SmartFinancialReport;
                setResult(data);
            } catch (err: any) { 
                const msg = err.response?.data?.detail || t('analyst.errorAnalysis', 'Analiza dështoi. Sigurohuni që skedari ka kolonën "Shuma" ose "Amount".');
                setError(msg); 
            } finally { setIsAnalyzing(false); }
        }
    };

    return (
        <div className="w-full flex flex-col gap-6 pb-6">
            {/* EXECUTIVE TOOLBAR – Command Center Header */}
            <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-main bg-surface shadow-sm transition-all">
                <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="flex flex-col gap-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                            <Activity className="text-primary-start shrink-0" size={18} />
                            <h2 className="text-xs font-black uppercase tracking-wider text-text-primary leading-none truncate">
                                {t('analyst.title', 'Analizë Financiare Forenzike')}
                            </h2>
                            {result && <CheckCircle className="w-4 h-4 text-status-success rounded-full shrink-0" />}
                        </div>
                        {fileName && <p className="text-[10px] font-mono text-text-muted truncate mt-1 ml-7">{fileName}</p>}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                        {result && (
                            <div className="flex gap-2">
                                <button onClick={async () => {
                                    setIsArchiving(true);
                                    try { 
                                        await apiService.archiveForensicReport(caseId, `${t('analyst.forensicMemo', 'Memorandum Forenzik')} - ${fileName}`, result.executive_summary); 
                                        setArchiveSuccess(true); setTimeout(() => setArchiveSuccess(false), 3000); 
                                    } 
                                    catch { setError(t('analyst.errorArchive', 'Arkivimi dështoi.')); } finally { setIsArchiving(false); }
                                }} disabled={isArchiving || archiveSuccess} className={`h-10 px-5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all border flex items-center gap-2 ${archiveSuccess ? 'bg-status-success text-white border-status-success' : 'bg-primary-start text-white border-primary-start shadow-sm'}`}>
                                    {isArchiving ? <RefreshCw className="animate-spin" size={14} /> : archiveSuccess ? <CheckCircle size={14} /> : <Save size={14} />}
                                    {archiveSuccess ? t('analyst.archived', 'Arkivuar!') : t('analyst.archiveMemo', 'Arkivo Memo')}
                                </button>
                                <button onClick={() => {setFileName(null); setResult(null); setChatHistory([]); const c = getCache(); delete c[caseId]; localStorage.setItem(CACHE_KEY, JSON.stringify(c));}} className="h-10 px-5 rounded-xl border border-main bg-canvas text-text-muted hover:text-text-primary text-xs font-bold uppercase tracking-wider hover-lift transition-all flex items-center gap-2">
                                    <RefreshCw size={14} /> {t('analyst.newAnalysis', 'Analizë e Re')}
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                <AnimatePresence>
                    {error && (
                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mt-4">
                            <div className="p-3.5 bg-danger-start/10 border border-danger-start/20 rounded-xl flex items-center gap-2.5 text-danger-start shadow-sm">
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                <span className="text-xs font-bold uppercase tracking-wide">{error}</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
            
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }} 
                        animate={{ opacity: 1, y: 0 }} 
                        exit={{ opacity: 0, y: -10 }} 
                        className="grid grid-cols-1 lg:grid-cols-2 gap-6"
                    >
                        {/* LEFT PANEL: Forensic Report */}
                        <div className="glass-panel p-0 rounded-2xl border border-main bg-surface flex flex-col h-[65vh] min-h-[450px] overflow-hidden shadow-sm">
                            <div className="px-6 py-4 border-b border-main bg-canvas/80 backdrop-blur-md flex items-center gap-2.5 shrink-0">
                                <FileText size={16} className="text-primary-start" />
                                <h3 className="text-xs font-black text-text-primary uppercase tracking-wider">Memorandumi i Gjetjeve</h3>
                            </div>
                            <div className="flex-1 overflow-y-auto p-6 custom-finance-scroll">
                                <div className="max-w-2xl mx-auto">
                                    {renderMarkdown(result.executive_summary)}
                                </div>
                            </div>
                        </div>

                        {/* RIGHT PANEL: Chat Interrogation */}
                        <div className="glass-panel p-0 rounded-2xl border border-main bg-surface flex flex-col h-[65vh] min-h-[450px] overflow-hidden shadow-sm">
                            <div className="px-6 py-4 border-b border-main bg-canvas/80 backdrop-blur-md flex items-center gap-2.5 shrink-0">
                                <Bot className="text-primary-start w-4 h-4 shrink-0" />
                                <div>
                                    <h3 className="text-xs font-black text-text-primary uppercase tracking-wider leading-none">{t('analyst.interrogationTitle', 'Interrogimi i Dëshmive')}</h3>
                                    <p className="text-[10px] font-medium text-text-muted mt-0.5">{t('analyst.interrogationSubtitle', 'Bëni pyetje rreth gjetjeve të memorandumit.')}</p>
                                </div>
                            </div>
                            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-finance-scroll">
                                {(chatHistory || []).map((msg) => (
                                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[85%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-sm border ${msg.role === 'user' ? 'bg-primary-start text-white border-primary-start rounded-tr-none' : 'bg-canvas text-text-primary border-main rounded-tl-none'}`}>
                                            {renderMarkdown(msg.content)}
                                        </div>
                                    </div>
                                ))}
                                {typingMessage && <TypingChatMessage message={typingMessage} onComplete={() => {setChatHistory(p => [...p, typingMessage]); setTypingMessage(null);}} />}
                                <div ref={chatEndRef} />
                            </div>
                            <div className="p-4 border-t border-main bg-canvas shrink-0">
                                <form onSubmit={async (e) => { 
                                    e.preventDefault(); 
                                    if (!question.trim() || isInterrogating || typingMessage) return; 
                                    const cur = question; setQuestion(''); 
                                    setChatHistory(p => [...p, { id: Date.now().toString(), role: 'user', content: cur, timestamp: new Date() }]); 
                                    setIsInterrogating(true); 
                                    try { 
                                        const r = await apiService.forensicInterrogateEvidence(caseId, cur); 
                                        setTypingMessage({ id: (Date.now()+1).toString(), role: 'agent', content: r.answer || t('analyst.noAnswer', 'Nuk u gjet përgjigje.'), timestamp: new Date(), evidenceCount: r.supporting_evidence_count }); 
                                    } catch { 
                                        setTypingMessage({ id: (Date.now()+1).toString(), role: 'agent', content: t('analyst.errorConnection', 'Lidhja dështoi.'), timestamp: new Date() }); 
                                    } finally { setIsInterrogating(false); } 
                                }} className="relative flex items-center gap-2 max-w-4xl mx-auto">
                                    <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t('analyst.placeholderQuestion', 'Bëni një pyetje rreth dosjes...')} className="w-full p-3 pr-12 bg-surface border border-main rounded-xl text-xs sm:text-sm leading-relaxed text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"/>
                                    <button type="submit" disabled={!question.trim() || isInterrogating || !!typingMessage} className="absolute right-2 h-8 w-8 flex items-center justify-center bg-primary-start text-white rounded-lg hover:bg-primary-start/90 transition-all disabled:opacity-30">
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
                    {/* STANDARDIZED EXECUTIVE HERO PANEL */}
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

                    {/* STANDARDIZED HELPER CARDS */}
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