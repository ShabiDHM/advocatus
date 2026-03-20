// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - SPREADSHEET ANALYST V7.1 (TS ERROR FIXED & ERROR UI RESTORED)
// 1. FIXED: Restored the Error Alert display to resolve TS6133.
// 2. RETAINED: Unified Action Bar Symmetry (h-12 Executive Cards).
// 3. RETAINED: 'bg-paper' Reading Surface with Serif Typography for Memorandums.
// 4. RETAINED: 100% Logic parity (Caching, Interrogation, Typewriter effect).

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, CheckCircle, RefreshCw, Send, ShieldAlert, Bot, Save, ChevronDown, FileText, AlertCircle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

const CACHE_KEY = 'juristi_analyst_cache';
const getCache = () => { try { const raw = localStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : {}; } catch { return {}; } };

// --- DATA STRUCTURES ---
interface SmartFinancialReport {
    executive_summary: string;
}
interface ChatMessage {
    id: string; role: 'user' | 'agent'; content: string; timestamp: Date; evidenceCount?: number;
}
interface CachedState {
    report: SmartFinancialReport; chat: ChatMessage[]; fileName: string;
}
interface SpreadsheetAnalystProps {
    caseId: string;
}

// --- High-Fidelity Markdown Renderer ---
const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
        const trimmed = line.trim();

        if (trimmed === '---') return <hr key={i} className="border-border-main my-8" />;
        if (!trimmed) return <div key={i} className="h-4" />;
        
        if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
            const content = trimmed.slice(2, -2);
            return <h3 key={i} className="text-sm font-black text-text-primary uppercase tracking-widest mt-8 mb-4 border-b border-border-main/50 pb-2">{content}</h3>;
        }
        
        if (/^\d\.\d\.?/.test(trimmed) || /^\d\.\s/.test(trimmed)) {
             return <h4 key={i} className="text-primary-start font-black text-xs uppercase tracking-tight mt-6 mb-3">{trimmed}</h4>;
        }
        
        if (trimmed.includes(':')) {
            const parts = trimmed.split(/:(.*)/s);
            if (parts.length > 1 && parts[0].length < 35) { 
                return (
                    <p key={i} className="text-text-primary text-[15px] leading-relaxed mb-3">
                        <strong className="font-black uppercase text-[10px] tracking-widest text-primary-start mr-2">{parts[0]}:</strong>
                        <span>{parts[1]}</span>
                    </p>
                );
            }
        }
        
        if (trimmed.startsWith('* ')) {
            return (
                <div key={i} className="flex gap-3 ml-2 mb-3 items-start">
                    <span className="text-primary-start mt-2 w-1.5 h-1.5 rounded-full bg-primary-start shrink-0 shadow-accent-glow"/>
                    <p className="text-text-primary text-[15px] leading-relaxed">{trimmed.substring(2)}</p>
                </div>
            );
        }
        
        return <p key={i} className="text-text-primary text-[15px] leading-relaxed mb-3">{trimmed}</p>;
    });
};

const useTypewriter = (text: string, speed: number = 10) => {
    const [displayText, setDisplayText] = useState('');
    useEffect(() => {
        setDisplayText('');
        if (text) {
            let i = 0;
            const intervalId = setInterval(() => {
                if (i < text.length) {
                    setDisplayText(prev => prev + text.charAt(i));
                    i++;
                } else {
                    clearInterval(intervalId);
                }
            }, speed);
            return () => clearInterval(intervalId);
        }
    }, [text, speed]);
    return displayText;
};

const TypingChatMessage: React.FC<{ message: ChatMessage, onComplete: () => void }> = ({ message, onComplete }) => {
    const displayText = useTypewriter(message.content);
    const { t } = useTranslation();
    useEffect(() => {
        if (displayText.length === message.content.length) onComplete();
    }, [displayText, message.content.length, onComplete]);
    
    return (
        <div className="flex justify-start">
            <div className="max-w-[85%] rounded-[1.5rem] rounded-tl-none p-5 text-sm leading-relaxed bg-surface border border-border-main shadow-lawyer-light text-text-primary">
                <div>{renderMarkdown(displayText)}</div>
                {message.evidenceCount !== undefined && (
                    <div className="mt-3 pt-3 border-t border-border-main/50 flex items-center gap-2 text-[10px] font-black text-text-muted uppercase tracking-widest">
                        <ShieldAlert className="w-3.5 h-3.5 text-success-start" />
                        {t('analyst.verifiedAgainst', { count: message.evidenceCount })}
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
            const stateToSave: CachedState = { report: result, chat: chatHistory, fileName: fileName || 'Unknown File' };
            const cache = getCache();
            cache[caseId] = stateToSave;
            try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch (e) { console.error("Cache save fail", e); }
        }
    }, [result, chatHistory, fileName, caseId, typingMessage]);
    
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory, typingMessage]);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const newFile = e.target.files[0];
            setFileName(newFile.name); setError(null); setResult(null); setChatHistory([]);
            setIsAnalyzing(true);
            try {
                const data = await apiService.forensicAnalyzeSpreadsheet(caseId, newFile, i18n.language || 'sq') as unknown as SmartFinancialReport;
                setResult(data);
            } catch (err) { setError(t('analyst.errorAnalysis')); } finally { setIsAnalyzing(false); }
        }
    };
    
    const handleArchiveReport = async () => {
        if (!result) return;
        setIsArchiving(true);
        try {
            const title = `${t('analyst.forensicMemo')} - ${fileName}`;
            await apiService.archiveForensicReport(caseId, title, result.executive_summary);
            setArchiveSuccess(true); setTimeout(() => setArchiveSuccess(false), 3000);
        } catch { setError(t('analyst.errorArchive')); } finally { setIsArchiving(false); }
    };

    const handleInterrogate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || isInterrogating || typingMessage) return;
        const currentQ = question; setQuestion('');
        setChatHistory(prev => [...prev, { id: Date.now().toString(), role: 'user', content: currentQ, timestamp: new Date() }]);
        setIsInterrogating(true);
        try {
            const response = await apiService.forensicInterrogateEvidence(caseId, currentQ);
            setTypingMessage({ id: (Date.now()+1).toString(), role: 'agent', content: response.answer || t('analyst.noAnswer'), timestamp: new Date(), evidenceCount: response.supporting_evidence_count });
        } catch {
            setTypingMessage({ id: (Date.now()+1).toString(), role: 'agent', content: t('analyst.errorConnection'), timestamp: new Date() });
        } finally { setIsInterrogating(false); }
    };

    return (
        <div className="w-full flex flex-col gap-8 pb-10">
            {/* EXECUTIVE TOOLBAR */}
            <div className="glass-panel p-6 sm:p-8 rounded-[1.5rem] border border-border-main bg-surface shadow-lawyer-light">
                <div className="flex flex-col md:flex-row justify-between items-center gap-8">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-2xl font-black text-text-primary tracking-tighter uppercase leading-none flex items-center gap-3">
                            <Activity className="text-primary-start" size={24} />
                            {t('analyst.title', 'Analizë Financiare Forenzike')}
                            {result && <CheckCircle className="w-6 h-6 text-success-start shadow-accent-glow rounded-full" />}
                        </h2>
                        {fileName && <p className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mt-1 ml-9">{fileName}</p>}
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                        {!result && !isAnalyzing && (
                            <div className="relative group h-12 min-w-[240px]">
                                <input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"/>
                                <div className="h-full flex items-center justify-center gap-3 px-6 rounded-xl bg-surface border border-border-main shadow-lawyer-light transition-all duration-300 hover-lift">
                                    <FileSpreadsheet className="w-4 h-4 text-primary-start opacity-70" />
                                    <span className="text-[11px] font-black uppercase tracking-widest text-text-secondary">{t('analyst.selectFile', 'Zgjidh Excel/CSV...')}</span>
                                    <ChevronDown size={14} className="text-text-muted ml-2" />
                                </div>
                            </div>
                        )}
                        {result && (
                            <div className="flex gap-3">
                                <button 
                                    onClick={handleArchiveReport} 
                                    disabled={isArchiving || archiveSuccess} 
                                    className={`h-12 px-6 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-sm transition-all border flex items-center gap-2 ${
                                        archiveSuccess 
                                            ? 'bg-success-start text-white border-success-start' 
                                            : 'bg-primary-start text-white border-primary-start hover:brightness-110 shadow-accent-glow'
                                    }`}
                                >
                                    {isArchiving ? <RefreshCw className="animate-spin" size={16} /> : archiveSuccess ? <CheckCircle size={16} /> : <Save size={16} />}
                                    {archiveSuccess ? t('analyst.archived') : t('analyst.archiveMemo')}
                                </button>
                                <button 
                                    onClick={() => {setFileName(null); setResult(null); setChatHistory([]); const c = getCache(); delete c[caseId]; localStorage.setItem(CACHE_KEY, JSON.stringify(c));}} 
                                    className="h-12 px-6 rounded-xl border border-border-main bg-surface text-text-muted hover:text-text-primary text-[10px] font-black uppercase tracking-widest hover-lift transition-all flex items-center gap-2"
                                >
                                    <RefreshCw size={16} /> {t('analyst.newAnalysis')}
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* RESTORED: EXECUTIVE ERROR DISPLAY (Resolves TS6133) */}
                <AnimatePresence>
                    {error && (
                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mt-6">
                            <div className="p-4 bg-danger-start/10 border border-danger-start/20 rounded-xl flex items-center gap-3 text-danger-start shadow-sm">
                                <AlertCircle className="w-5 h-5 shrink-0" />
                                <span className="text-xs font-bold uppercase tracking-wide">{error}</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
            
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-auto lg:h-[800px]">
                        
                        {/* Executive Summary Surface */}
                        <div className="glass-panel p-0 rounded-[2rem] border border-border-main bg-surface overflow-hidden shadow-lawyer-dark flex flex-col">
                            <div className="px-8 py-5 border-b border-border-main bg-canvas/30 flex items-center gap-3">
                                <FileText size={18} className="text-primary-start" />
                                <h3 className="text-xs font-black text-text-primary uppercase tracking-widest">Memorandumi i Gjetjeve</h3>
                            </div>
                            <div className="flex-1 bg-paper p-10 overflow-y-auto custom-scrollbar shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
                                <div className="max-w-2xl mx-auto font-serif">
                                    {renderMarkdown(result.executive_summary)}
                                </div>
                            </div>
                        </div>
                        
                        {/* Evidence Interrogation Surface */}
                        <div className="glass-panel p-0 rounded-[2rem] border border-border-main bg-canvas/40 flex flex-col h-[600px] lg:h-full overflow-hidden shadow-lawyer-dark">
                            <div className="px-8 py-5 border-b border-border-main bg-surface/80 backdrop-blur-md flex items-center gap-3 shrink-0">
                                <Bot className="text-primary-start w-5 h-5 shadow-accent-glow rounded-full" />
                                <div className="flex flex-col">
                                    <h3 className="text-xs font-black text-text-primary uppercase tracking-widest leading-none">{t('analyst.interrogationTitle', 'Interrogimi i Dëshmive')}</h3>
                                    <p className="text-[9px] font-bold text-text-muted uppercase tracking-tighter mt-1">{t('analyst.interrogationSubtitle')}</p>
                                </div>
                            </div>
                            
                            <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar no-scrollbar">
                                {(chatHistory || []).map((msg) => (
                                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[85%] rounded-[1.5rem] p-5 text-sm leading-relaxed shadow-sm border ${
                                            msg.role === 'user' 
                                                ? 'bg-primary-start text-white border-primary-start rounded-tr-none' 
                                                : 'bg-surface text-text-primary border-border-main rounded-tl-none'
                                        }`}>
                                            {renderMarkdown(msg.content)}
                                        </div>
                                    </div>
                                ))}
                                {typingMessage && <TypingChatMessage message={typingMessage} onComplete={() => {setChatHistory(p => [...p, typingMessage]); setTypingMessage(null);}} />}
                                {isInterrogating && !typingMessage && (
                                    <div className="flex justify-start">
                                        <div className="bg-surface border border-border-main rounded-2xl px-6 py-4 flex gap-1 shadow-lawyer-light">
                                            <div className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" />
                                            <div className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                            <div className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                                        </div>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>

                            <div className="p-6 border-t border-border-main bg-surface shrink-0">
                                <form onSubmit={handleInterrogate} className="relative flex items-end gap-3 max-w-5xl mx-auto">
                                    <input 
                                        type="text" value={question} onChange={(e) => setQuestion(e.target.value)} 
                                        placeholder={t('analyst.placeholderQuestion')} 
                                        className="glass-input w-full p-4 pr-16 rounded-2xl text-sm leading-relaxed shadow-inner-trough"
                                    />
                                    <button 
                                        type="submit" disabled={!question.trim() || isInterrogating || !!typingMessage} 
                                        className="absolute right-2.5 bottom-2.5 h-10 w-10 flex items-center justify-center bg-primary-start text-white rounded-xl shadow-accent-glow hover:brightness-110 active:scale-95 transition-all disabled:opacity-30"
                                    >
                                        <Send size={18} />
                                    </button>
                                </form>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Full Screen Loading State */}
            <AnimatePresence>
                {isAnalyzing && !result && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-40">
                        <div className="relative mb-8">
                            <div className="w-20 h-20 rounded-full border-4 border-primary-start/10 border-t-primary-start animate-spin shadow-accent-glow"></div>
                            <Activity className="absolute inset-0 m-auto w-8 h-8 text-primary-start animate-pulse" />
                        </div>
                        <h3 className="text-xl font-black text-text-primary uppercase tracking-widest">{t('analyst.analyzing', 'Sokrati duke analizuar dhënat...')}</h3>
                        <p className="text-text-muted text-[10px] font-black uppercase tracking-[0.3em] mt-3">Algoritmi Forenzik i Juristi AI</p>
                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Pristine Empty State */}
            {!result && !isAnalyzing && (
                <AnimatePresence>
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center justify-center text-center py-32 px-6 glass-panel rounded-[2rem] border border-border-main bg-surface shadow-lawyer-dark max-w-4xl mx-auto">
                        <div className="w-24 h-24 bg-canvas rounded-[2rem] border border-border-main flex items-center justify-center mb-8 shadow-inner">
                            <FileSpreadsheet className="w-12 h-12 text-primary-start opacity-40" strokeWidth={1} />
                        </div>
                        <h3 className="text-2xl font-black text-text-primary mb-3 uppercase tracking-tighter">{t('analyst.readyTitle', 'Gati për Hulumtim Forenzik')}</h3>
                        <p className="text-base text-text-secondary max-w-lg mb-10 leading-relaxed font-medium">
                            {t('analyst.readySubtitle', 'Zgjidhni një skedar Excel ose CSV për të filluar analizën automatike të pasqyrave financiare dhe për të gjeneruar memorandumin strategjik.')}
                        </p>
                        <div className="relative group h-14 min-w-[280px]">
                            <input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"/>
                            <div className="h-full flex items-center justify-center gap-4 px-10 rounded-[1.2rem] bg-primary-start text-white shadow-accent-glow transition-all duration-300 hover:brightness-110 active:scale-95">
                                <FileSpreadsheet className="w-5 h-5" />
                                <span className="text-xs font-black uppercase tracking-[0.2em]">{t('analyst.selectFile', 'Zgjidh Skedarin')}</span>
                            </div>
                        </div>
                    </motion.div>
                </AnimatePresence>
            )}
        </div>
    );
};

export default SpreadsheetAnalyst;