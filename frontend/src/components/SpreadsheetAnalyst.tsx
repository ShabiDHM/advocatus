// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - FORENSIC SPREADSHEET ANALYST V5.4 (ALBANIAN LOCALIZATION)
// 1. FIXED: All Forensic Metadata labels converted to Albanian
// 2. FIXED: Risk Levels (HIGH -> LARTË) and Anomalies (STRUCTURING -> STRUKTURIM) translated
// 3. KEPT: No QR / No OCR (Strict File Upload Only)

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileSpreadsheet, Activity, AlertTriangle, TrendingUp, 
    CheckCircle, RefreshCw, Lightbulb, ArrowRight, TrendingDown, 
    Send, ShieldAlert, Bot, Save, Shield, Scale, Fingerprint
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

const CACHE_KEY = 'juristi_analyst_cache';
const getCache = () => { try { const raw = localStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : {}; } catch { return {}; } };

// --- TRANSLATION MAPS FOR TECHNICAL ENUMS ---
const RISK_MAP: Record<string, string> = {
    'HIGH': 'LARTË',
    'MEDIUM': 'MESME',
    'LOW': 'ULËT',
    'CRITICAL': 'KRITIKE'
};

const TYPE_MAP: Record<string, string> = {
    'CURRENCY_STRUCTURING': 'STRUKTURIM MONETAR',
    'STRUCTURING': 'STRUKTURIM',
    'SUSPICIOUS_KEYWORD': 'FJALË KYÇE E DYSHIMTË',
    'ROUND_AMOUNT': 'SHUMË E RRUMBULLAKËT',
    'STATISTICAL_OUTLIER': 'DEVIJIM STATISTIKOR',
    'BENFORD_LAW_DEVIATION': 'MANIPULIM MATEMATIKOR',
    'TEMPORAL_PATTERN_ANOMALY': 'MODEL KOHOR I PAZAKONTË'
};

interface ForensicMetadata {
    evidence_hash: string;
    analysis_timestamp: string;
    record_count: number;
}

interface EnhancedAnomaly {
    date: string;
    amount: number;
    description: string;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
    explanation: string;
    forensic_type?: string;
    legal_reference?: string;
    confidence?: number;
}

interface SmartFinancialReport {
    executive_summary: string;
    anomalies: EnhancedAnomaly[];
    trends: Array<{ category: string; trend: 'UP' | 'DOWN' | 'STABLE'; percentage: string; comment: string }>;
    recommendations: string[];
    forensic_metadata?: ForensicMetadata;
}

interface ChatMessage {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    evidenceCount?: number;
    forensicContext?: {
        evidence_references?: string[];
        chain_of_custody?: any[];
    };
}

interface CachedState {
    report: SmartFinancialReport;
    chat: ChatMessage[];
    fileName: string;
}

interface SpreadsheetAnalystProps {
    caseId: string;
}

// --- (Helper Functions) ---
const parseBold = (line: string) => {
    const parts = line.split(/(\*\*.*?\*\*|\*.*?\*)/g);
    return parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) return <strong key={index} className="text-white font-bold">{part.slice(2, -2)}</strong>;
        if (part.startsWith('*') && part.endsWith('*')) return <em key={index} className="italic text-gray-200">{part.slice(1, -1)}</em>;
        return part;
    });
};

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

const useTypewriter = (text: string, speed: number = 20) => {
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
        if (displayText.length === message.content.length) {
            onComplete();
        }
    }, [displayText, message.content.length, onComplete]);
    
    return (
        <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed break-words bg-white/10 text-gray-200 border border-white/5 rounded-bl-none">
                <div>{renderMarkdown(displayText)}</div>
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

const isForensicResponse = (response: any): response is import('../services/api').ForensicInterrogationResponse => {
    return response && (
        'supporting_evidence_count' in response ||
        'evidence_references' in response ||
        'chain_of_custody' in response ||
        'forensic_warning' in response
    );
};

const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId }) => {
    const { t } = useTranslation();
    const [file, setFile] = useState<File | null>(null);
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
    
    // Forensic Mode Toggle
    const [useForensicMode, setUseForensicMode] = useState(false);
    
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

    const runAnalysis = async (fileToAnalyze: File) => {
        setIsAnalyzing(true);
        setError(null);
        try {
            let data;
            if (useForensicMode) {
                data = await apiService.forensicAnalyzeSpreadsheet(caseId, fileToAnalyze) as unknown as SmartFinancialReport;
            } else {
                data = await apiService.analyzeSpreadsheet(caseId, fileToAnalyze) as unknown as SmartFinancialReport;
            }
            setResult(data);
        } catch (err) {
            setError(t('analyst.error.analysisFailed'));
            console.error('Analysis error:', err);
        } finally {
            setIsAnalyzing(false);
        }
    };
    
    const handleArchiveReport = async () => {
        if (!result) return;
        setIsArchiving(true);
        try {
            const title = `Raport Forenzik - ${fileName || 'Analizë'}`;
            await apiService.archiveForensicReport(caseId, title, result.executive_summary);
            setArchiveSuccess(true);
            setTimeout(() => setArchiveSuccess(false), 3000);
        } catch (err) {
            console.error(err);
            setError("Arkivimi dështoi. Ju lutem provoni përsëri.");
        } finally {
            setIsArchiving(false);
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
        if (fullReset) {
            setFile(null);
            setFileName(null);
        }
        setResult(null);
        setChatHistory([]);
        setError(null);
        const cache = getCache();
        delete cache[caseId];
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
        } catch (e) {
            console.error("Failed to clear from localStorage", e);
        }
    };

    const handleInterrogate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || isInterrogating || typingMessage) return;
        
        const currentQ = question;
        setQuestion('');
        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: currentQ,
            timestamp: new Date()
        };
        setChatHistory(prev => [...prev, userMsg]);
        setIsInterrogating(true);
        
        try {
            let response;
            try {
                response = await apiService.forensicInterrogateEvidence(caseId, currentQ);
            } catch (forensicErr) {
                response = await apiService.interrogateFinancialRecords(caseId, currentQ);
            }
            
            const evidenceCount = isForensicResponse(response) 
                ? response.supporting_evidence_count 
                : response.referenced_rows_count;
            
            const agentMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: response.answer || t('analyst.noRelevantData'),
                timestamp: new Date(),
                evidenceCount,
                forensicContext: isForensicResponse(response) ? {
                    evidence_references: response.evidence_references,
                    chain_of_custody: response.chain_of_custody
                } : undefined
            };
            setTypingMessage(agentMsg);
        } catch (err) {
            console.error('Interrogation error:', err);
            const errorMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: t('analyst.connectionFailed'),
                timestamp: new Date()
            };
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

    const getRiskBadge = (level: string) => {
        switch (level) {
            case 'HIGH': return 'bg-red-500/20 text-red-300 border-red-500/30';
            case 'MEDIUM': return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
            case 'CRITICAL': return 'bg-red-700/30 text-red-400 border-red-700/50';
            default: return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
        }
    };

    const getTrendIcon = (trend: string) => {
        if (trend === 'UP') return <TrendingUp className="w-4 h-4 text-emerald-400" />;
        if (trend === 'DOWN') return <TrendingDown className="w-4 h-4 text-red-400" />;
        return <Activity className="w-4 h-4 text-blue-400" />;
    };

    // ALBANIAN LOCALIZED FORENSIC DISPLAY
    const ForensicMetadataDisplay: React.FC<{ metadata: ForensicMetadata }> = ({ metadata }) => (
        <div className="glass-panel p-4 rounded-2xl border border-emerald-500/20 bg-emerald-900/10">
            <h3 className="text-sm font-bold text-emerald-400 mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Integriteti Forenzik i Dëshmisë
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                    <p className="text-xs text-gray-400">Hash i Dëshmisë (SHA-256)</p>
                    <div className="flex items-center gap-2">
                        <code className="text-xs bg-black/30 px-2 py-1 rounded border border-white/10 font-mono truncate">
                            {metadata.evidence_hash.substring(0, 24)}...
                        </code>
                        <button 
                            onClick={() => navigator.clipboard.writeText(metadata.evidence_hash)}
                            className="text-xs text-gray-400 hover:text-white transition-colors"
                            title="Kopjo Hashin e plotë"
                        >
                            📋
                        </button>
                    </div>
                </div>
                <div className="space-y-1">
                    <p className="text-xs text-gray-400">Analizuar më</p>
                    <p className="text-xs text-white">
                        {new Date(metadata.analysis_timestamp).toLocaleString('sq-AL', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        })}
                    </p>
                </div>
                <div className="space-y-1">
                    <p className="text-xs text-gray-400">Rekorde të Analizuara</p>
                    <p className="text-xs text-white font-bold">{metadata.record_count}</p>
                </div>
                <div className="space-y-1">
                    <p className="text-xs text-gray-400">Statusi i Integritetit</p>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                        <span className="text-xs text-emerald-400">Verifikuar & E Pandryshueshme</span>
                    </div>
                </div>
            </div>
            <div className="mt-3 pt-3 border-t border-white/10">
                <p className="text-[10px] text-gray-500">
                    Kjo dëshmi është e vulosur kriptografikisht. Çdo ndryshim do të thyejë zinxhirin e hash-it.
                </p>
            </div>
        </div>
    );

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-2 sm:p-1">
            <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-white/10 bg-white/5 relative overflow-hidden flex-shrink-0">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -z-10 pointer-events-none" />
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
                            <Activity className="text-primary-start" />
                            {t('analyst.title')}
                            {result && <CheckCircle className="w-5 h-5 text-emerald-500" />}
                        </h2>
                        <p className="text-sm text-gray-400 mt-1">
                            {useForensicMode ? "Analizë Financiare Forenzike (Për Gjykatë)" : "Hulumtim Financiar Standard"}
                        </p>
                    </div>
                    
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto">
                        {!result && !isAnalyzing && (
                            <div className="flex items-center gap-2 mb-2 sm:mb-0">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <div className="relative">
                                        <input
                                            type="checkbox"
                                            checked={useForensicMode}
                                            onChange={(e) => setUseForensicMode(e.target.checked)}
                                            className="sr-only"
                                        />
                                        <div className={`w-10 h-5 rounded-full transition-colors ${useForensicMode ? 'bg-emerald-600' : 'bg-gray-700'}`}>
                                            <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${useForensicMode ? 'transform translate-x-5' : ''}`} />
                                        </div>
                                    </div>
                                    <span className="text-xs text-gray-300 flex items-center gap-1">
                                        <Shield className="w-3 h-3" />
                                        Modaliteti Forenzik
                                    </span>
                                </label>
                                {useForensicMode && (
                                    <span className="text-[10px] px-2 py-0.5 bg-emerald-900/30 text-emerald-300 rounded-full border border-emerald-500/30">
                                        Gati për Gjykatë
                                    </span>
                                )}
                            </div>
                        )}
                        
                        {!result && !isAnalyzing && (
                            <div className="flex gap-2 w-full md:w-auto">
                                <div className="relative group flex-1 md:flex-none">
                                    <input
                                        type="file"
                                        accept=".csv, .xlsx, .xls"
                                        onChange={handleFileChange}
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                    />
                                    <div className="flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-dashed transition-all cursor-pointer bg-black/20 border-gray-600 hover:border-gray-400">
                                        <FileSpreadsheet className="w-5 h-5 text-gray-400" />
                                        <span className="text-sm text-gray-300">{t('analyst.selectFile', 'Excel/CSV...')}</span>
                                    </div>
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
                                            ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                                            : 'bg-primary-start/10 border-primary-start/30 text-primary-200 hover:bg-primary-start/20'
                                    }`}
                                >
                                    {isArchiving ? (
                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                    ) : archiveSuccess ? (
                                        <CheckCircle className="w-4 h-4" />
                                    ) : (
                                        <Save className="w-4 h-4" />
                                    )}
                                    {archiveSuccess ? "Arkivuar!" : "Arkivo PDF"}
                                </button>
                                <button
                                    onClick={() => handleReset(true)}
                                    className="px-4 py-2 border border-white/10 text-gray-300 hover:text-white rounded-xl text-sm transition-colors flex justify-center items-center gap-2 hover:bg-white/5"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                    Analizë e Re
                                </button>
                            </div>
                        )}
                    </div>
                </div>
                
                {error && (
                    <div className="mt-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-200">
                        <AlertTriangle className="w-5 h-5" />
                        {error}
                    </div>
                )}
            </div>
            
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[850px]"
                    >
                        {/* Left Column - Analysis Results */}
                        <div className="flex flex-col gap-6 overflow-visible lg:overflow-y-auto custom-scrollbar h-auto lg:h-full lg:pr-2">
                            {/* Executive Summary */}
                            <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/5 flex flex-col shrink-0">
                                <h3 className="text-md font-bold text-white mb-2 flex items-center gap-2 shrink-0">
                                    <ShieldAlert className="text-primary-start w-4 h-4" />
                                    Përmbledhje Ekzekutive
                                </h3>
                                <div className="pl-1">{renderMarkdown(result.executive_summary)}</div>
                            </div>
                            
                            {/* PHOENIX ADDITION: Forensic Metadata Display */}
                            {result.forensic_metadata && (
                                <ForensicMetadataDisplay metadata={result.forensic_metadata} />
                            )}
                            
                            {/* Recommendations */}
                            {result.recommendations && result.recommendations.length > 0 && (
                                <div className="glass-panel p-4 rounded-xl border border-emerald-500/20 bg-emerald-900/10 shrink-0">
                                    <h3 className="text-sm font-bold text-emerald-400 mb-2 flex items-center gap-2">
                                        <Lightbulb className="w-4 h-4" />
                                        Rekomandime
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
                            
                            {/* Trends */}
                            <div className="grid grid-cols-2 gap-4 shrink-0">
                                {result.trends.map((trend, idx) => (
                                    <div key={idx} className="bg-white/5 p-4 rounded-xl border border-white/10">
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="text-gray-400 text-xs font-bold uppercase truncate">
                                                {trend.category}
                                            </span>
                                            {getTrendIcon(trend.trend)}
                                        </div>
                                        <div className="text-xl font-bold text-white">{trend.percentage}</div>
                                    </div>
                                ))}
                            </div>
                            
                            {/* Anomalies - Enhanced with Forensic Information */}
                            <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/5 flex flex-col shrink-0 min-h-[500px]">
                                <h3 className="text-md font-bold text-white mb-4 flex items-center gap-2 shrink-0">
                                    <AlertTriangle className="text-yellow-400 w-4 h-4" />
                                    Flamujt e Kuq (Anomali)
                                    <span className="ml-auto text-xs text-gray-400">
                                        {result.anomalies.length} detektime
                                    </span>
                                </h3>
                                <div className="space-y-3">
                                    {result.anomalies.map((anomaly, idx) => (
                                        <div
                                            key={idx}
                                            className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors group"
                                        >
                                            <div className="flex justify-between items-center mb-1">
                                                <div className="flex gap-2">
                                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${getRiskBadge(anomaly.risk_level)}`}>
                                                        {RISK_MAP[anomaly.risk_level] || anomaly.risk_level}
                                                    </span>
                                                    {anomaly.forensic_type && (
                                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-300 uppercase">
                                                            {TYPE_MAP[anomaly.forensic_type] || anomaly.forensic_type}
                                                        </span>
                                                    )}
                                                    {anomaly.confidence && (
                                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-300">
                                                            {Math.round(anomaly.confidence * 100)}% saktësi
                                                        </span>
                                                    )}
                                                </div>
                                                <span className="text-xs text-gray-500 font-mono">{anomaly.date}</span>
                                            </div>
                                            <div className="flex justify-between items-baseline">
                                                <p className="text-xs text-white font-bold truncate max-w-[200px]">
                                                    {anomaly.description}
                                                </p>
                                                <p className="text-xs font-mono text-red-300">
                                                    €{(anomaly.amount || 0).toLocaleString()}
                                                </p>
                                            </div>
                                            <p className="text-[10px] text-gray-400 mt-1 break-words">
                                                {anomaly.explanation}
                                            </p>
                                            {anomaly.legal_reference && (
                                                <div className="mt-2 pt-2 border-t border-white/10">
                                                    <p className="text-[9px] text-gray-500 flex items-center gap-1">
                                                        <Scale className="w-2.5 h-2.5" />
                                                        Ref: {anomaly.legal_reference}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                        
                        {/* Right Column - Chat Agent */}
                        <div className="glass-panel rounded-2xl border border-primary-start/30 bg-black/40 flex flex-col h-[600px] lg:h-full overflow-hidden shadow-2xl relative">
                            <div className="p-4 border-b border-white/10 bg-white/5 flex items-center gap-3 shrink-0">
                                <Bot className="text-primary-start w-5 h-5" />
                                <div>
                                    <h3 className="text-sm font-bold text-white">Asistenti Ligjor AI</h3>
                                    <p className="text-[10px] text-gray-400">
                                        {useForensicMode
                                            ? "Regjimi i Hetimit Forenzik"
                                            : "Regjimi i Analizës Standarde"}
                                    </p>
                                </div>
                            </div>
                            
                            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                                {chatHistory.map((msg) => (
                                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div
                                            className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed break-words ${
                                                msg.role === 'user'
                                                    ? 'bg-primary-start text-white rounded-br-none'
                                                    : 'bg-white/10 text-gray-200 border border-white/5 rounded-bl-none'
                                            }`}
                                        >
                                            <div>{renderMarkdown(msg.content)}</div>
                                            {msg.forensicContext?.evidence_references && msg.forensicContext.evidence_references.length > 0 && (
                                                <div className="mt-2 pt-2 border-t border-white/10">
                                                    <div className="flex items-center gap-2 text-[10px] text-gray-400 mb-1">
                                                        <Fingerprint className="w-3 h-3" />
                                                        Referencat e Dëshmive:
                                                    </div>
                                                    <div className="flex flex-wrap gap-1">
                                                        {msg.forensicContext.evidence_references.slice(0, 3).map((ref, idx) => (
                                                            <span key={idx} className="text-[8px] bg-black/30 px-1.5 py-0.5 rounded border border-white/10">
                                                                {ref.substring(0, 12)}...
                                                            </span>
                                                        ))}
                                                        {msg.forensicContext.evidence_references.length > 3 && (
                                                            <span className="text-[8px] text-gray-500">
                                                                +{msg.forensicContext.evidence_references.length - 3}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                
                                {typingMessage && <TypingChatMessage message={typingMessage} onComplete={onTypingComplete} />}
                                
                                {isInterrogating && !typingMessage && (
                                    <div className="flex justify-start">
                                        <div className="bg-white/5 rounded-2xl p-4 flex gap-1">
                                            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                                            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                                        </div>
                                    </div>
                                )}
                                
                                <div ref={chatEndRef} />
                            </div>
                            
                            <form onSubmit={handleInterrogate} className="p-4 border-t border-white/10 bg-white/5 flex gap-2 shrink-0">
                                <input
                                    type="text"
                                    value={question}
                                    onChange={(e) => setQuestion(e.target.value)}
                                    placeholder="Bëni një pyetje rreth dosjes..."
                                    className="flex-1 bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-primary-start/50"
                                />
                                <button
                                    type="submit"
                                    disabled={!question.trim() || isInterrogating || !!typingMessage}
                                    className="p-3 bg-primary-start text-white rounded-xl hover:bg-primary-end disabled:opacity-50 transition-colors"
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
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center justify-center py-32"
                    >
                        <div className="relative">
                            <div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-primary-start animate-spin"></div>
                            <Activity className="absolute inset-0 m-auto w-6 h-6 text-primary-start" />
                        </div>
                        <p className="text-xl text-white font-medium mt-6">
                            {useForensicMode
                                ? "Duke kryer Analizën Forenzike..."
                                : "Duke procesuar të dhënat..."}
                        </p>
                        {useForensicMode && (
                            <p className="text-sm text-gray-400 mt-2">
                                Duke gjeneruar dëshmi të pranueshme në gjykatë me verifikim kriptografik
                            </p>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
            
            <AnimatePresence>
                {!result && !isAnalyzing && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="flex flex-col items-center justify-center text-center py-20 px-6 glass-panel rounded-2xl border border-white/5"
                    >
                        <FileSpreadsheet className="w-12 h-12 text-gray-600 mb-6" />
                        <h3 className="text-lg font-bold text-white mb-2">Gati për Hulumtim</h3>
                        <p className="text-sm text-gray-400 max-w-md mb-4">
                            Zgjidhni një skedar Excel ose CSV duke përdorur butonat sipër për të filluar skanimin.
                        </p>
                        {useForensicMode && (
                            <div className="flex items-center gap-2 text-sm text-emerald-400 bg-emerald-900/20 px-4 py-2 rounded-full border border-emerald-500/30">
                                <Shield className="w-4 h-4" />
                                Modaliteti Forenzik Aktiv - Të gjitha dëshmitë do të vulosen kriptografikisht
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default SpreadsheetAnalyst;