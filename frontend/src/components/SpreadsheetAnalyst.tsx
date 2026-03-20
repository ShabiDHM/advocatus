// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - SPREADSHEET ANALYST V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: glass-panel, border-main, text-text-primary, text-text-secondary, text-text-muted.
// 2. Preserved all analysis, chat, and archival functionality.
// 3. Uses semantic color variables consistently.

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, CheckCircle, RefreshCw, Send, ShieldAlert, Bot, Save
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

// --- Helper Functions ---
const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
        const trimmed = line.trim();

        if (trimmed === '---') {
            return <hr key={i} className="border-main my-6" />;
        }
        if (!trimmed) {
            return <div key={i} className="h-3" />;
        }
        if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
            const content = trimmed.slice(2, -2);
            return <h3 key={i} className="text-text-primary font-bold text-lg mt-6 mb-4 pb-2 border-b border-main">{content}</h3>;
        }
        if (/^\d\.\d\.?/.test(trimmed) || /^\d\.\s/.test(trimmed)) {
             return <h4 key={i} className="text-primary-start font-semibold text-md mt-5 mb-3">{trimmed}</h4>;
        }
        if (trimmed.includes(':')) {
            const parts = trimmed.split(/:(.*)/s);
            if (parts.length > 1 && parts[0].length < 30) { 
                return (
                    <p key={i} className="text-text-secondary text-sm leading-relaxed mb-2">
                        <strong className="text-text-primary font-semibold">{parts[0]}:</strong>
                        <span>{parts[1]}</span>
                    </p>
                );
            }
        }
        if (trimmed.startsWith('* ')) {
            return <div key={i} className="flex gap-2 ml-1 mb-2 items-start"><span className="text-primary-start mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-start shrink-0"/><p className="text-text-secondary text-sm leading-relaxed">{trimmed.substring(2)}</p></div>;
        }
        return <p key={i} className="text-text-secondary text-sm leading-relaxed mb-2">{trimmed}</p>;
    });
};

const useTypewriter = (text: string, speed: number = 15) => {
    const [displayText, setDisplayText] = useState('');
    useEffect(() => {
        setDisplayText('');
        if (text) {
            let i = 0;
            const intervalId = setInterval(() => {
                i < text.length ? setDisplayText(prev => prev + text.charAt(i++)) : clearInterval(intervalId);
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
            <div className="max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed break-words bg-surface/20 text-text-secondary border border-main rounded-bl-none">
                <div>{renderMarkdown(displayText)}</div>
                {message.evidenceCount !== undefined && (
                    <div className="mt-2 pt-2 border-t border-main flex items-center gap-2 text-[10px] text-text-muted">
                        <ShieldAlert className="w-3 h-3" />
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
            try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch (e) { console.error("Failed to save to localStorage", e); }
        }
    }, [result, chatHistory, fileName, caseId, typingMessage]);
    
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory, typingMessage]);

    const runAnalysis = async (fileToAnalyze: File) => {
        setIsAnalyzing(true);
        setError(null);
        try {
            const lang = i18n.language || 'sq'; 
            const data = await apiService.forensicAnalyzeSpreadsheet(caseId, fileToAnalyze, lang) as unknown as SmartFinancialReport;
            setResult(data);
        } catch (err) {
            setError(t('analyst.errorAnalysis', "Analiza dështoi. Ju lutemi kontrolloni formatin e skedarit."));
            console.error('Analysis error:', err);
        } finally {
            setIsAnalyzing(false);
        }
    };
    
    const handleArchiveReport = async () => {
        if (!result) return;
        setIsArchiving(true);
        try {
            const title = `${t('analyst.forensicMemo', 'Memorandum Forenzik')} - ${fileName || t('analyst.analysis', 'Analizë')}`;
            await apiService.archiveForensicReport(caseId, title, result.executive_summary);
            setArchiveSuccess(true);
            setTimeout(() => setArchiveSuccess(false), 3000);
        } catch (err) {
            console.error(err);
            setError(t('analyst.errorArchive', "Arkivimi dështoi."));
        } finally {
            setIsArchiving(false);
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const newFile = e.target.files[0];
            setFileName(newFile.name);
            setError(null);
            setResult(null);
            setChatHistory([]);
            await runAnalysis(newFile);
        }
    };
    
    const handleReset = () => {
        setFileName(null); setResult(null); setChatHistory([]); setError(null);
        const cache = getCache();
        delete cache[caseId];
        try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch (e) { console.error("Failed to clear from localStorage", e); }
    };

    const handleInterrogate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || isInterrogating || typingMessage) return;
        
        const currentQ = question;
        setQuestion('');
        const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: currentQ, timestamp: new Date() };
        setChatHistory(prev => [...prev, userMsg]);
        setIsInterrogating(true);
        
        try {
            const response = await apiService.forensicInterrogateEvidence(caseId, currentQ);
            const agentMsg: ChatMessage = {
                id: (Date.now() + 1).toString(), role: 'agent', content: response.answer || t('analyst.noAnswer', "Nuk u gjet përgjigje."),
                timestamp: new Date(), evidenceCount: response.supporting_evidence_count
            };
            setTypingMessage(agentMsg);
        } catch (err) {
            console.error('Interrogation error:', err);
            const errorMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'agent', content: t('analyst.errorConnection', "Lidhja dështoi."), timestamp: new Date() };
            setTypingMessage(errorMsg);
        } finally {
            setIsInterrogating(false);
        }
    };

    const onTypingComplete = () => {
        if (typingMessage) {
            setChatHistory(prev => [...prev, typingMessage]);
            setTypingMessage(null);
        }
    };

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-2 sm:p-1">
            <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-main bg-surface/10 flex-shrink-0">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-xl sm:text-2xl font-bold text-text-primary flex items-center gap-2">
                            <Activity className="text-primary-start" />
                            {t('analyst.title', 'Analizë Financiare Forenzike')}
                            {result && <CheckCircle className="w-5 h-5 text-success-start" />}
                        </h2>
                    </div>
                    <div className="flex items-center gap-3 w-full md:w-auto">
                        {!result && !isAnalyzing && (
                            <div className="relative group flex-1">
                                <input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"/>
                                <div className="flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-dashed transition-all cursor-pointer bg-surface/20 border-main hover:border-primary-start/50">
                                    <FileSpreadsheet className="w-5 h-5 text-text-muted" />
                                    <span className="text-sm text-text-secondary">{t('analyst.selectFile', 'Zgjidh Excel/CSV...')}</span>
                                </div>
                            </div>
                        )}
                        {result && (
                            <div className="flex gap-2">
                                <button 
                                    onClick={handleArchiveReport} 
                                    disabled={isArchiving || archiveSuccess} 
                                    className={`px-4 py-2 border rounded-xl text-sm transition-all flex justify-center items-center gap-2 ${
                                        archiveSuccess 
                                            ? 'bg-success-start/20 border-success-start/50 text-success-start' 
                                            : 'bg-primary-start/10 border-primary-start/30 text-primary-start hover:bg-primary-start/20'
                                    }`}
                                >
                                    {isArchiving ? <RefreshCw className="w-4 h-4 animate-spin" /> : archiveSuccess ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                                    {archiveSuccess ? t('analyst.archived', 'Arkivuar!') : t('analyst.archiveMemo', 'Arkivo Memo')}
                                </button>
                                <button 
                                    onClick={handleReset} 
                                    className="px-4 py-2 border border-main text-text-secondary hover:text-text-primary rounded-xl text-sm transition-colors flex justify-center items-center gap-2 hover:bg-surface/20"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                    {t('analyst.newAnalysis', 'Analizë e Re')}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
                {error && (
                    <div className="mt-4 p-3 bg-danger-start/30 border border-danger-start/50 rounded-lg flex items-center gap-2 text-danger-start">
                        <ShieldAlert className="w-5 h-5" />{error}
                    </div>
                )}
            </div>
            
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[850px]">
                        <div className="flex flex-col gap-6 overflow-y-auto custom-scrollbar h-full lg:pr-2">
                            <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-main bg-surface/10">
                                {renderMarkdown(result.executive_summary)}
                            </div>
                        </div>
                        
                        <div className="glass-panel rounded-2xl border border-primary-start/30 bg-canvas/40 flex flex-col h-[600px] lg:h-full overflow-hidden shadow-2xl">
                            <div className="p-4 border-b border-main bg-surface/20 flex items-center gap-3 shrink-0">
                                <Bot className="text-primary-start w-5 h-5" />
                                <div>
                                    <h3 className="text-sm font-bold text-text-primary">{t('analyst.interrogationTitle', 'Interrogimi i Dëshmive')}</h3>
                                    <p className="text-[10px] text-text-muted">{t('analyst.interrogationSubtitle', 'Bëni pyetje rreth gjetjeve të memorandumit.')}</p>
                                </div>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                                {(chatHistory || []).map((msg) => (
                                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed break-words ${
                                            msg.role === 'user' 
                                                ? 'btn-primary text-text-primary rounded-br-none' 
                                                : 'bg-surface/20 text-text-secondary border border-main rounded-bl-none'
                                        }`}>
                                            {renderMarkdown(msg.content)}
                                        </div>
                                    </div>
                                ))}
                                {typingMessage && <TypingChatMessage message={typingMessage} onComplete={onTypingComplete} />}
                                {isInterrogating && !typingMessage && (
                                    <div className="flex justify-start">
                                        <div className="bg-surface/20 rounded-2xl p-4 flex gap-1">
                                            <div className="w-2 h-2 bg-text-muted rounded-full animate-bounce" />
                                            <div className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                            <div className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                                        </div>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>
                            <form onSubmit={handleInterrogate} className="p-4 border-t border-main bg-surface/20 flex gap-2 shrink-0">
                                <input 
                                    type="text" 
                                    value={question} 
                                    onChange={(e) => setQuestion(e.target.value)} 
                                    placeholder={t('analyst.placeholderQuestion', 'Bëni një pyetje rreth dosjes...')} 
                                    className="flex-1 glass-input rounded-xl px-4 py-3 text-text-primary focus:outline-none focus:border-primary-start/50"
                                />
                                <button 
                                    type="submit" 
                                    disabled={!question.trim() || isInterrogating || !!typingMessage} 
                                    className="p-3 btn-primary rounded-xl disabled:opacity-50 transition-colors"
                                >
                                    <Send className="w-5 h-5" />
                                </button>
                            </form>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            
            <AnimatePresence>
                {isAnalyzing && !result && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-32">
                        <div className="relative">
                            <div className="w-16 h-16 rounded-full border-4 border-main border-t-primary-start animate-spin"></div>
                            <Activity className="absolute inset-0 m-auto w-6 h-6 text-primary-start" />
                        </div>
                        <p className="text-xl text-text-primary font-medium mt-6">{t('analyst.analyzing', 'Duke kryer Analizën Forenzike...')}</p>
                    </motion.div>
                )}
            </AnimatePresence>
            
            <AnimatePresence>
                {!result && !isAnalyzing && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="flex flex-col items-center justify-center text-center py-20 px-6 glass-panel rounded-2xl border border-main">
                        <FileSpreadsheet className="w-12 h-12 text-text-muted mb-6" />
                        <h3 className="text-lg font-bold text-text-primary mb-2">{t('analyst.readyTitle', 'Gati për Hulumtim Forenzik')}</h3>
                        <p className="text-sm text-text-secondary max-w-md mb-4">{t('analyst.readySubtitle', 'Zgjidhni një skedar Excel ose CSV për të filluar analizën dhe për të gjeneruar një memorandum strategjik.')}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default SpreadsheetAnalyst;