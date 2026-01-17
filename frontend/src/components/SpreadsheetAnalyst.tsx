// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - FRONTEND V2.3 (MARKDOWN VISUALIZER)
// 1. UI: Added 'renderMarkdown()' to visualize the Forensic Report (Bold, Headers, Lists).
// 2. I18N: Full Albanian support maintained.
// 3. STATUS: Production Ready.

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, AlertTriangle, TrendingUp, Loader2, 
    CheckCircle, RefreshCw, Lightbulb, ArrowRight, TrendingDown, 
    MessageSquare, Send, ShieldAlert, Bot 
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

// --- TYPES ---
interface SmartFinancialReport {
    executive_summary: string;
    anomalies: Array<{
        date: string;
        amount: number;
        description: string;
        risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
        explanation: string;
    }>;
    trends: Array<{
        category: string;
        trend: 'UP' | 'DOWN' | 'STABLE';
        percentage: string;
        comment: string;
    }>;
    recommendations: string[];
}

interface ChatMessage {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    evidenceCount?: number;
}

interface SpreadsheetAnalystProps {
    caseId: string;
}

const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId }) => {
    const { t } = useTranslation();
    
    // State: File & Report
    const [file, setFile] = useState<File | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<SmartFinancialReport | null>(null);
    const [error, setError] = useState<string | null>(null);

    // State: Interrogation Room
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [question, setQuestion] = useState('');
    const [isInterrogating, setIsInterrogating] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll chat
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory]);

    // --- HANDLERS ---

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
            setResult(null);
            setChatHistory([]);
        }
    };

    const runAnalysis = async () => {
        if (!file) return;
        setIsAnalyzing(true);
        setError(null);
        try {
            const data = await apiService.analyzeSpreadsheet(caseId, file) as unknown as SmartFinancialReport;
            setResult(data);
            setChatHistory([{
                id: 'init',
                role: 'agent',
                content: t('analyst.systemWelcome', "Data vectorized. I have scanned the ledger. The Evidence Board is above. You may now interrogate the specific transaction rows."),
                timestamp: new Date()
            }]);
        } catch (err: any) {
            console.error(err);
            setError(t('analyst.error.analysisFailed', 'Analysis failed. Please check the file format.'));
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleInterrogate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || isInterrogating) return;

        const currentQ = question;
        setQuestion('');
        
        // Add User Message
        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: currentQ,
            timestamp: new Date()
        };
        setChatHistory(prev => [...prev, userMsg]);
        setIsInterrogating(true);

        try {
            const response = await apiService.interrogateFinancialRecords(caseId, currentQ);
            
            const agentMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: response.answer || t('analyst.noRelevantData', "No relevant data found."),
                timestamp: new Date(),
                evidenceCount: response.referenced_rows_count
            };
            setChatHistory(prev => [...prev, agentMsg]);
        } catch (err) {
            const errorMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: t('analyst.connectionFailed', "Connection to Forensic Core failed."),
                timestamp: new Date()
            };
            setChatHistory(prev => [...prev, errorMsg]);
        } finally {
            setIsInterrogating(false);
        }
    };

    // --- UTILS: NATIVE MARKDOWN RENDERER (No external deps) ---
    // Parses: **Bold**, #### Header, - List
    const renderMarkdown = (text: string) => {
        if (!text) return null;
        
        return text.split('\n').map((line, i) => {
            // 1. Headers (####)
            if (line.startsWith('####')) {
                return <h4 key={i} className="text-white font-bold text-sm mt-4 mb-2 border-b border-white/10 pb-1">{line.replace(/#/g, '')}</h4>;
            }
            if (line.startsWith('###')) {
                return <h3 key={i} className="text-primary-start font-bold text-base mt-4 mb-2">{line.replace(/#/g, '')}</h3>;
            }

            // 2. List Items (-)
            if (line.trim().startsWith('- ')) {
                const content = line.trim().substring(2);
                return (
                    <li key={i} className="ml-4 list-disc text-gray-300 text-sm mb-1">
                        {parseBold(content)}
                    </li>
                );
            }

            // 3. Regular Paragraphs (with Bold support)
            if (line.trim() === '') return <br key={i} />;
            
            return (
                <p key={i} className="text-gray-300 text-sm leading-relaxed mb-1">
                    {parseBold(line)}
                </p>
            );
        });
    };

    // Helper to parse **Bold** inside a line
    const parseBold = (line: string) => {
        const parts = line.split(/(\*\*.*?\*\*)/g);
        return parts.map((part, index) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={index} className="text-white font-bold">{part.slice(2, -2)}</strong>;
            }
            return part;
        });
    };

    // --- UI HELPERS ---

    const getRiskBadge = (level: string) => {
        switch (level) {
            case 'HIGH': return 'bg-red-500/20 text-red-300 border-red-500/30';
            case 'MEDIUM': return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
            default: return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
        }
    };

    const getTrendIcon = (trend: string) => {
        if (trend === 'UP') return <TrendingUp className="w-4 h-4 text-emerald-400" />;
        if (trend === 'DOWN') return <TrendingDown className="w-4 h-4 text-red-400" />;
        return <Activity className="w-4 h-4 text-blue-400" />;
    };

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-1">
            
            {/* Header Area */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -z-10 pointer-events-none" />
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <Activity className="text-primary-start" />
                            {t('analyst.title', 'Financial Interrogation Room')}
                            {result && <CheckCircle className="w-5 h-5 text-emerald-500" />} 
                        </h2>
                        <p className="text-gray-400 mt-1 max-w-xl">
                            {t('analyst.subtitle', 'Upload ledger. Vectors are generated automatically. Interrogate data below.')}
                        </p>
                    </div>

                    <div className="flex items-center gap-3 w-full md:w-auto">
                        {!result && (
                            <div className="relative group w-full md:w-auto">
                                <input 
                                    type="file" 
                                    accept=".csv, .xlsx, .xls"
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                />
                                <div className={`
                                    flex items-center gap-3 px-4 py-2.5 rounded-xl border border-dashed transition-all cursor-pointer
                                    ${file ? 'border-primary-start bg-primary-start/10' : 'border-gray-600 hover:border-gray-400 bg-black/20'}
                                `}>
                                    <FileSpreadsheet className={`w-5 h-5 ${file ? 'text-primary-start' : 'text-gray-400'}`} />
                                    <span className="text-sm text-gray-300 truncate max-w-[200px]">
                                        {file ? file.name : t('analyst.selectFile', 'Select Ledger...')}
                                    </span>
                                </div>
                            </div>
                        )}

                        {file && !result && (
                            <button
                                onClick={runAnalysis}
                                disabled={isAnalyzing}
                                className="px-6 py-2.5 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg hover:shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-50 disabled:active:scale-100"
                            >
                                {isAnalyzing ? <Loader2 className="animate-spin w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                                {isAnalyzing ? t('analyst.analyzing', 'Scanning...') : t('analyst.runAnalysis', 'Vectorize & Analyze')}
                            </button>
                        )}
                        
                        {result && (
                             <button
                                onClick={() => { setResult(null); setFile(null); setChatHistory([]); }}
                                className="px-4 py-2 border border-white/10 text-gray-300 hover:text-white rounded-xl text-sm transition-colors flex items-center gap-2 hover:bg-white/5"
                             >
                                <RefreshCw className="w-4 h-4" />
                                {t('analyst.newAnalysis', 'Reset Room')}
                             </button>
                        )}
                    </div>
                </div>
                {error && (
                    <div className="mt-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-200 animate-in fade-in slide-in-from-top-2">
                        <AlertTriangle className="w-5 h-5" />
                        {error}
                    </div>
                )}
            </div>

            {/* MAIN CONTENT GRID */}
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[800px]"
                    >
                        {/* LEFT COLUMN: EVIDENCE BOARD (Static) */}
                        <div className="flex flex-col gap-6 overflow-hidden h-full">
                            
                            {/* Summary Card (With Markdown Rendering) */}
                            <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/5 flex-shrink-0">
                                <h3 className="text-md font-bold text-white mb-2 flex items-center gap-2">
                                    <ShieldAlert className="text-primary-start w-4 h-4" />
                                    {t('analyst.narrative', 'Forensic Narrative')}
                                </h3>
                                <div className="max-h-64 overflow-y-auto custom-scrollbar pr-2">
                                    {renderMarkdown(result.executive_summary)}
                                </div>
                            </div>

                             {/* Recommendations */}
                             {result.recommendations && result.recommendations.length > 0 && (
                                <div className="glass-panel p-4 rounded-xl border border-emerald-500/20 bg-emerald-900/10 flex-shrink-0">
                                    <h3 className="text-sm font-bold text-emerald-400 mb-2 flex items-center gap-2">
                                        <Lightbulb className="w-4 h-4" />
                                        {t('analyst.recommendations', 'Strategic Recommendations')}
                                    </h3>
                                    <ul className="space-y-1">
                                        {result.recommendations.map((rec, i) => (
                                            <li key={i} className="flex gap-2 items-start text-xs text-gray-300">
                                                <ArrowRight className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
                                                <span>{rec}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Trends & Metrics */}
                            <div className="grid grid-cols-2 gap-4 flex-shrink-0">
                                {result.trends.map((trend, idx) => (
                                    <div key={idx} className="bg-white/5 p-4 rounded-xl border border-white/10">
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="text-gray-400 text-xs font-bold uppercase">{trend.category}</span>
                                            {getTrendIcon(trend.trend)}
                                        </div>
                                        <div className="text-xl font-bold text-white">{trend.percentage}</div>
                                    </div>
                                ))}
                            </div>

                            {/* Anomalies List (Scrollable) */}
                            <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/5 flex-1 overflow-hidden flex flex-col min-h-0">
                                <h3 className="text-md font-bold text-white mb-4 flex items-center gap-2">
                                    <AlertTriangle className="text-yellow-400 w-4 h-4" />
                                    {t('analyst.redFlags', 'Red Flags (Evidence)')}
                                </h3>
                                <div className="overflow-y-auto pr-2 custom-scrollbar flex-1 space-y-3">
                                    {result.anomalies.map((anomaly, idx) => (
                                        <div key={idx} className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${getRiskBadge(anomaly.risk_level)}`}>
                                                    {anomaly.risk_level}
                                                </span>
                                                <span className="text-xs text-gray-500 font-mono">{anomaly.date}</span>
                                            </div>
                                            <div className="flex justify-between items-baseline">
                                                 <p className="text-xs text-white font-bold truncate max-w-[200px]">{anomaly.description}</p>
                                                 <p className="text-xs font-mono text-red-300">€{(anomaly.amount || 0).toLocaleString()}</p>
                                            </div>
                                            <p className="text-[10px] text-gray-400 mt-1">{anomaly.explanation}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* RIGHT COLUMN: INTERROGATION CONSOLE (Dynamic) */}
                        <div className="glass-panel rounded-2xl border border-primary-start/30 bg-black/40 flex flex-col h-full overflow-hidden shadow-2xl relative">
                            {/* Decorative Grid Background */}
                            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none"></div>
                            
                            {/* Header */}
                            <div className="p-4 border-b border-white/10 bg-white/5 flex items-center gap-3">
                                <Bot className="text-primary-start w-5 h-5" />
                                <div>
                                    <h3 className="text-sm font-bold text-white">{t('analyst.agentTitle', 'Forensic Agent')}</h3>
                                    <p className="text-[10px] text-gray-400">
                                        {t('analyst.context', 'Context')}: {file?.name} ({result.anomalies.length} {t('analyst.flags', 'Flags')})
                                    </p>
                                </div>
                            </div>

                            {/* Chat History */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                                {chatHistory.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-2">
                                        <MessageSquare className="w-8 h-8 opacity-50" />
                                        <p className="text-xs">{t('analyst.consoleReady', 'Console Ready. Awaiting Questions.')}</p>
                                    </div>
                                ) : (
                                    chatHistory.map((msg) => (
                                        <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                            <div className={`
                                                max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed
                                                ${msg.role === 'user' 
                                                    ? 'bg-primary-start text-white rounded-br-none' 
                                                    : 'bg-white/10 text-gray-200 border border-white/5 rounded-bl-none'}
                                            `}>
                                                {/* Use renderMarkdown for chat messages too */}
                                                <div>{renderMarkdown(msg.content)}</div>
                                                
                                                {msg.role === 'agent' && msg.evidenceCount !== undefined && (
                                                    <div className="mt-2 pt-2 border-t border-white/10 flex items-center gap-2 text-[10px] text-gray-400">
                                                        <ShieldAlert className="w-3 h-3" />
                                                        {t('analyst.verifiedAgainst', { count: msg.evidenceCount })}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                                {isInterrogating && (
                                    <div className="flex justify-start">
                                        <div className="bg-white/5 rounded-2xl rounded-bl-none p-4 border border-white/5 flex gap-1">
                                            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>

                            {/* Input Area */}
                            <form onSubmit={handleInterrogate} className="p-4 border-t border-white/10 bg-white/5 flex gap-2">
                                <input
                                    type="text"
                                    value={question}
                                    onChange={(e) => setQuestion(e.target.value)}
                                    placeholder={t('analyst.askPlaceholder', "Ask about specific transactions...")}
                                    className="flex-1 bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary-start/50 transition-colors"
                                />
                                <button 
                                    type="submit" 
                                    disabled={!question.trim() || isInterrogating}
                                    className="p-3 bg-primary-start text-white rounded-xl hover:bg-primary-end disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <Send className="w-5 h-5" />
                                </button>
                            </form>
                        </div>

                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Loading State */}
             <AnimatePresence>
                {isAnalyzing && !result && (
                    <motion.div 
                        initial={{ opacity: 0 }} 
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center justify-center py-32"
                    >
                        <div className="relative">
                            <div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-primary-start animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Activity className="w-6 h-6 text-primary-start" />
                            </div>
                        </div>
                        <p className="text-xl text-white font-medium mt-6">{t('analyst.processing', 'Deep Forensic Scan in Progress...')}</p>
                        <p className="text-sm text-gray-400 mt-2">{t('analyst.wait', 'Generating vector embeddings for every transaction.')}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default SpreadsheetAnalyst;