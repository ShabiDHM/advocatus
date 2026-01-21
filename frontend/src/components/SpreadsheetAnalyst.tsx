// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - FRONTEND V3.8 (CLEAN CHAT UI)
// 1. UI CLEANUP: Removed the automatic welcome message from the chat after analysis completes.
// 2. LOGIC: `runAnalysis` now only sets the report result, leaving the chat empty.
// 3. UX: Retains all previous fixes, including persistence and typewriter effect for subsequent messages.

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, AlertTriangle, TrendingUp, 
    CheckCircle, RefreshCw, Lightbulb, ArrowRight, TrendingDown, 
    Send, ShieldAlert, Bot 
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

// --- CONSTANTS & HELPERS ---
const CACHE_KEY = 'juristi_analyst_cache';
const getCache = () => { try { const raw = localStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : {}; } catch { return {}; } };

// --- TYPES ---
interface SmartFinancialReport { executive_summary: string; anomalies: Array<{ date: string; amount: number; description: string; risk_level: 'HIGH' | 'MEDIUM' | 'LOW'; explanation: string; }>; trends: Array<{ category: string; trend: 'UP' | 'DOWN' | 'STABLE'; percentage: string; comment: string; }>; recommendations: string[]; }
interface ChatMessage { id: string; role: 'user' | 'agent'; content: string; timestamp: Date; evidenceCount?: number; }
interface CachedState { report: SmartFinancialReport; chat: ChatMessage[]; fileName: string; }
interface SpreadsheetAnalystProps { caseId: string; }

// --- TYPEWRITER HOOK ---
const useTypewriter = (text: string, speed: number = 30) => {
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

// --- TYPING CHAT MESSAGE COMPONENT ---
const TypingChatMessage: React.FC<{ message: ChatMessage, onComplete: () => void }> = ({ message, onComplete }) => {
    const displayText = useTypewriter(message.content);
    const { t } = useTranslation();

    useEffect(() => {
        if (displayText.length === message.content.length) {
            onComplete();
        }
    }, [displayText, message.content.length, onComplete]);

    return (
        <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed break-words bg-white/10 text-gray-200 border border-white/5 rounded-bl-none">
                <div>{displayText}</div>
                {message.evidenceCount !== undefined && (
                    <div className="mt-2 pt-2 border-t border-white/10 flex items-center gap-2 text-[10px] text-gray-400">
                        <ShieldAlert className="w-3 h-3" />
                        {t('analyst.verifiedAgainst', { count: message.evidenceCount })}
                    </div>
                )}
            </div>
        </div>
    );
};


const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId }) => {
    const { t } = useTranslation();
    
    // State
    const [file, setFile] = useState<File | null>(null);
    const [fileName, setFileName] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<SmartFinancialReport | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [question, setQuestion] = useState('');
    const [isInterrogating, setIsInterrogating] = useState(false);
    const [typingMessage, setTypingMessage] = useState<ChatMessage | null>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Effects
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
        if (result && !typingMessage) { // Also check chat history if you want to save only after interaction
            const cache = getCache();
            const stateToSave: CachedState = { 
                report: result, 
                chat: chatHistory, 
                fileName: file?.name || fileName || 'Unknown File' 
            };
            cache[caseId] = stateToSave;
            try { 
                localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); 
            } catch (e) { 
                console.error("Failed to save to localStorage", e); 
            }
        }
    }, [result, chatHistory, file, fileName, caseId, typingMessage]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory, typingMessage]);

    // Handlers
    const runAnalysis = async (fileToAnalyze: File) => {
        if (!fileToAnalyze) return;
        setIsAnalyzing(true);
        setError(null);
        try {
            const data = await apiService.analyzeSpreadsheet(caseId, fileToAnalyze) as unknown as SmartFinancialReport;
            setResult(data);
            // PHOENIX FIX: Welcome message logic removed to keep chat clean.
        } catch (err: any) {
            console.error(err);
            setError(t('analyst.error.analysisFailed'));
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const newFile = e.target.files[0];
            setFile(newFile);
            setFileName(newFile.name);
            setError(null);
            setResult(null);
            setChatHistory([]);
            handleReset(false);
            await runAnalysis(newFile);
        }
    };
    
    const handleReset = (fullReset = true) => {
        if(fullReset) { setFile(null); setFileName(null); }
        setResult(null);
        setChatHistory([]);
        setError(null);
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
            const response = await apiService.interrogateFinancialRecords(caseId, currentQ);
            const agentMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'agent', content: response.answer || t('analyst.noRelevantData'), timestamp: new Date(), evidenceCount: response.referenced_rows_count };
            setTypingMessage(agentMsg);
        } catch (err) {
            const errorMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'agent', content: t('analyst.connectionFailed'), timestamp: new Date() };
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

    // Renderers
    const renderMarkdown = (text: string) => {
        if (!text) return null;
        const cleanText = text.replace(/```markdown/g, '').replace(/```/g, '').replace(/^---$/gm, '').trim();
        return cleanText.split('\n').map((line, i) => {
            const trimmed = line.trim();
            if (!trimmed) return <div key={i} className="h-2" />;
            if (trimmed.startsWith('#')) {
                const level = trimmed.match(/^#+/)?.[0].length || 0;
                const content = trimmed.replace(/^#+\s*/, '');
                if (level <= 2) return <h3 key={i} className="text-white font-bold text-lg mt-4 mb-2 pb-2 border-b border-white/10 uppercase tracking-wide">{content}</h3>;
                return <h4 key={i} className="text-primary-200 font-bold text-sm mt-3 mb-1">{content}</h4>;
            }
            if (trimmed.startsWith('**') && trimmed.includes(':')) return <div key={i} className="mt-2 text-sm text-gray-200">{parseBold(trimmed)}</div>;
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                const content = trimmed.substring(2);
                return <div key={i} className="flex gap-2 ml-1 mb-1 items-start"><span className="text-primary-400 mt-1.5 w-1 h-1 rounded-full bg-primary-400 shrink-0"/><p className="text-gray-300 text-sm leading-relaxed">{parseBold(content)}</p></div>;
            }
            if (/^\d+\./.test(trimmed)) {
                const match = trimmed.match(/^(\d+\.)\s+(.*)/);
                if (match) return <div key={i} className="flex gap-2 ml-1 mb-1 text-sm text-gray-300 items-start"><span className="font-mono text-primary-300 shrink-0 font-bold">{match[1]}</span><span className="leading-relaxed">{parseBold(match[2])}</span></div>;
            }
            return <p key={i} className="text-gray-300 text-sm leading-relaxed mb-1 break-words">{parseBold(trimmed)}</p>;
        });
    };

    const parseBold = (line: string) => {
        const parts = line.split(/(\*\*.*?\*\*)/g);
        return parts.map((part, index) => part.startsWith('**') && part.endsWith('**') ? <strong key={index} className="text-white font-bold">{part.slice(2, -2)}</strong> : part);
    };
    
    const getRiskBadge = (level: string) => { switch (level) { case 'HIGH': return 'bg-red-500/20 text-red-300 border-red-500/30'; case 'MEDIUM': return 'bg-amber-500/20 text-amber-300 border-amber-500/30'; default: return 'bg-blue-500/20 text-blue-300 border-blue-500/30'; } };
    const getTrendIcon = (trend: string) => { if (trend === 'UP') return <TrendingUp className="w-4 h-4 text-emerald-400" />; if (trend === 'DOWN') return <TrendingDown className="w-4 h-4 text-red-400" />; return <Activity className="w-4 h-4 text-blue-400" />; };

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-2 sm:p-1">
            <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-white/10 bg-white/5 relative overflow-hidden flex-shrink-0">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -z-10 pointer-events-none" />
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div><h2 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2"><Activity className="text-primary-start" />{t('analyst.title')}{result && <CheckCircle className="w-5 h-5 text-emerald-500" />}</h2></div>
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto">
                        {!result && !isAnalyzing && (<div className="relative group w-full md:w-auto"><input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" /><div className="flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-dashed transition-all cursor-pointer bg-black/20 border-gray-600 hover:border-gray-400"><FileSpreadsheet className="w-5 h-5 text-gray-400" /><span className="text-sm text-gray-300 truncate max-w-[200px]">{t('analyst.selectFile')}</span></div></div>)}
                        {result && (<button onClick={() => handleReset(true)} className="px-4 py-2 border border-white/10 text-gray-300 hover:text-white rounded-xl text-sm transition-colors flex justify-center items-center gap-2 hover:bg-white/5"><RefreshCw className="w-4 h-4" />{t('analyst.newAnalysis')}</button>)}
                    </div>
                </div>
                {error && <div className="mt-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-200 animate-in fade-in slide-in-from-top-2"><AlertTriangle className="w-5 h-5" />{error}</div>}
            </div>
            
            <AnimatePresence mode="wait">
                {result && (<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[850px]">
                    <div className="flex flex-col gap-6 overflow-visible lg:overflow-y-auto custom-scrollbar h-auto lg:h-full lg:pr-2">
                        <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/5 flex flex-col shrink-0"><h3 className="text-md font-bold text-white mb-2 flex items-center gap-2 shrink-0"><ShieldAlert className="text-primary-start w-4 h-4" />{t('analyst.narrative')}</h3><div className="pl-1">{renderMarkdown(result.executive_summary)}</div></div>
                        {result.recommendations && result.recommendations.length > 0 && (<div className="glass-panel p-4 rounded-xl border border-emerald-500/20 bg-emerald-900/10 shrink-0"><h3 className="text-sm font-bold text-emerald-400 mb-2 flex items-center gap-2"><Lightbulb className="w-4 h-4" />{t('analyst.recommendations')}</h3><ul className="space-y-1">{result.recommendations.map((rec, i) => <li key={i} className="flex gap-2 items-start text-xs text-gray-300"><ArrowRight className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" /><span>{rec}</span></li>)}</ul></div>)}
                        <div className="grid grid-cols-2 gap-4 shrink-0">{result.trends.map((trend, idx) => <div key={idx} className="bg-white/5 p-4 rounded-xl border border-white/10"><div className="flex justify-between items-start mb-1"><span className="text-gray-400 text-xs font-bold uppercase truncate">{trend.category}</span>{getTrendIcon(trend.trend)}</div><div className="text-xl font-bold text-white">{trend.percentage}</div></div>)}</div>
                        <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/5 flex flex-col shrink-0 min-h-[500px]"><h3 className="text-md font-bold text-white mb-4 flex items-center gap-2 shrink-0"><AlertTriangle className="text-yellow-400 w-4 h-4" />{t('analyst.redFlags')}</h3><div className="space-y-3">{result.anomalies.map((anomaly, idx) => <div key={idx} className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors"><div className="flex justify-between items-center mb-1"><span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${getRiskBadge(anomaly.risk_level)}`}>{anomaly.risk_level}</span><span className="text-xs text-gray-500 font-mono">{anomaly.date}</span></div><div className="flex justify-between items-baseline"><p className="text-xs text-white font-bold truncate max-w-[200px]">{anomaly.description}</p><p className="text-xs font-mono text-red-300">€{(anomaly.amount || 0).toLocaleString()}</p></div><p className="text-[10px] text-gray-400 mt-1 break-words">{anomaly.explanation}</p></div>)}</div></div>
                    </div>
                    <div className="glass-panel rounded-2xl border border-primary-start/30 bg-black/40 flex flex-col h-[600px] lg:h-full overflow-hidden shadow-2xl relative sticky top-0">
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none"></div>
                        <div className="p-4 border-b border-white/10 bg-white/5 flex items-center gap-3 shrink-0"><Bot className="text-primary-start w-5 h-5" /><div><h3 className="text-sm font-bold text-white">{t('analyst.agentTitle')}</h3></div></div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                            {chatHistory.map((msg) => <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed break-words ${msg.role === 'user' ? 'bg-primary-start text-white rounded-br-none' : 'bg-white/10 text-gray-200 border border-white/5 rounded-bl-none'}`}><div>{renderMarkdown(msg.content)}</div>{msg.role === 'agent' && msg.evidenceCount !== undefined && <div className="mt-2 pt-2 border-t border-white/10 flex items-center gap-2 text-[10px] text-gray-400"><ShieldAlert className="w-3 h-3" />{t('analyst.verifiedAgainst', { count: msg.evidenceCount })}</div>}</div></div>)}
                            {typingMessage && <TypingChatMessage message={typingMessage} onComplete={onTypingComplete} />}
                            {isInterrogating && !typingMessage && <div className="flex justify-start"><div className="bg-white/5 rounded-2xl rounded-bl-none p-4 border border-white/5 flex gap-1"><div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} /><div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} /><div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} /></div></div>}
                            <div ref={chatEndRef} />
                        </div>
                        <form onSubmit={handleInterrogate} className="p-4 border-t border-white/10 bg-white/5 flex gap-2 shrink-0">
                            <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t('analyst.askPlaceholder')} className="flex-1 bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary-start/50 transition-colors" />
                            <button type="submit" disabled={!question.trim() || isInterrogating || !!typingMessage} className="p-3 bg-primary-start text-white rounded-xl hover:bg-primary-end disabled:opacity-50 disabled:cursor-not-allowed transition-colors"><Send className="w-5 h-5" /></button>
                        </form>
                    </div>
                </motion.div>)}
            </AnimatePresence>
            <AnimatePresence>
                {isAnalyzing && !result && (<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-32"><div className="relative"><div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-primary-start animate-spin"></div><div className="absolute inset-0 flex items-center justify-center"><Activity className="w-6 h-6 text-primary-start" /></div></div><p className="text-xl text-white font-medium mt-6">{t('analyst.processing')}</p></motion.div>)}
            </AnimatePresence>
            <AnimatePresence>
                {!result && !isAnalyzing && (<motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center justify-center text-center py-20 px-6 glass-panel rounded-2xl border border-white/5"><FileSpreadsheet className="w-12 h-12 text-gray-600 mb-6" /><h3 className="text-lg font-bold text-white mb-2">Gati për Hulumtim</h3><p className="text-sm text-gray-400 max-w-md">Zgjidhni një skedar Excel ose CSV duke përdorur butonin sipër për të filluar skanimin forenzik dhe për të zbuluar informacione të rëndësishme financiare.</p></motion.div>)}
            </AnimatePresence>
        </div>
    );
};

export default SpreadsheetAnalyst;