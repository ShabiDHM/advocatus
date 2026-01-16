// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - REFACTOR V1.4 (FIXED TYPES)
// 1. FIX: Added forced type casting 'as unknown as SmartFinancialReport' to solve conversion error.
// 2. FIX: Removed unused 'BarChart2' import.

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileSpreadsheet, Activity, AlertTriangle, TrendingUp, Loader2, CheckCircle, RefreshCw, Lightbulb, ArrowRight, TrendingDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

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

interface SpreadsheetAnalystProps {
    caseId: string;
}

const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId }) => {
    const { t } = useTranslation();
    const [file, setFile] = useState<File | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<SmartFinancialReport | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const runAnalysis = async () => {
        if (!file) return;
        setIsAnalyzing(true);
        setError(null);
        try {
            // FIX: Double cast to bypass strict legacy type checking
            const data = await apiService.analyzeSpreadsheet(caseId, file) as unknown as SmartFinancialReport;
            setResult(data);
        } catch (err: any) {
            console.error(err);
            setError(t('analyst.error.analysisFailed', 'Analysis failed. Please check the file format.'));
        } finally {
            setIsAnalyzing(false);
        }
    };

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
            
            {/* Header */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -z-10 pointer-events-none" />

                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <Activity className="text-primary-start" />
                            {t('analyst.title', 'Smart Financial Analyst')}
                        </h2>
                        <p className="text-gray-400 mt-1 max-w-xl">
                            {t('analyst.subtitle', 'Upload Excel/CSV records for automated forensic analysis and anomaly detection.')}
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
                                        {file ? file.name : t('analyst.selectFile', 'Select Spreadsheet...')}
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
                                {isAnalyzing ? t('analyst.analyzing', 'Analyzing...') : t('analyst.run', 'Run Analysis')}
                            </button>
                        )}
                        
                        {result && (
                             <button
                                onClick={() => { setResult(null); setFile(null); }}
                                className="px-4 py-2 border border-white/10 text-gray-300 hover:text-white rounded-xl text-sm transition-colors flex items-center gap-2 hover:bg-white/5"
                             >
                                <RefreshCw className="w-4 h-4" />
                                {t('analyst.newAnalysis', 'New Analysis')}
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

            {/* Results */}
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="grid grid-cols-1 lg:grid-cols-3 gap-6"
                    >
                        {/* Narrative & Summary */}
                        <div className="lg:col-span-2 space-y-6">
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 shadow-xl">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2 border-b border-white/5 pb-2">
                                    <CheckCircle className="text-green-400 w-5 h-5" />
                                    {t('analyst.reportTitle', 'Forensic Narrative')}
                                </h3>
                                <p className="text-gray-300 leading-relaxed text-sm md:text-base whitespace-pre-line">
                                    {result.executive_summary}
                                </p>
                            </div>

                            {/* Trends */}
                            {result.trends && result.trends.length > 0 && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {result.trends.map((trend, idx) => (
                                        <div key={idx} className="bg-white/5 p-4 rounded-xl border border-white/10 hover:bg-white/10 transition-colors">
                                            <div className="flex justify-between items-start mb-2">
                                                <h4 className="text-white font-bold text-sm">{trend.category}</h4>
                                                {getTrendIcon(trend.trend)}
                                            </div>
                                            <div className="flex items-baseline gap-2 mb-2">
                                                <span className="text-2xl font-bold text-primary-200">{trend.percentage}</span>
                                                <span className="text-xs text-gray-500 uppercase tracking-wider">{trend.trend}</span>
                                            </div>
                                            <p className="text-xs text-gray-400">{trend.comment}</p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Recommendations */}
                            {result.recommendations && result.recommendations.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border border-emerald-500/20 bg-emerald-900/10">
                                    <h3 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
                                        <Lightbulb className="w-5 h-5" />
                                        {t('analyst.recommendations', 'Strategic Recommendations')}
                                    </h3>
                                    <ul className="space-y-3">
                                        {result.recommendations.map((rec, i) => (
                                            <li key={i} className="flex gap-3 items-start text-sm text-gray-300">
                                                <ArrowRight className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                                                <span>{rec}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>

                        {/* Anomalies Panel */}
                        <div className="lg:col-span-1 space-y-6">
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 h-full flex flex-col">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <AlertTriangle className="text-yellow-400 w-5 h-5" />
                                    {t('analyst.anomaliesTitle', 'Detected Anomalies')}
                                </h3>
                                
                                <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar max-h-[800px]">
                                    {(!result.anomalies || result.anomalies.length === 0) ? (
                                        <div className="flex flex-col items-center justify-center h-full text-center py-10 opacity-60">
                                            <CheckCircle className="w-12 h-12 text-green-500 mb-2" />
                                            <p className="text-gray-400">{t('analyst.noAnomalies', 'No significant anomalies detected.')}</p>
                                        </div>
                                    ) : (
                                        result.anomalies.map((anomaly, idx) => (
                                            <div key={idx} className="p-4 bg-red-500/5 border border-red-500/20 rounded-xl hover:bg-red-500/10 transition-colors group">
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getRiskBadge(anomaly.risk_level)}`}>
                                                        {anomaly.risk_level} RISK
                                                    </span>
                                                    <span className="text-xs text-gray-500 font-mono">
                                                        {anomaly.date}
                                                    </span>
                                                </div>
                                                <div className="flex justify-between items-baseline mb-1">
                                                     <p className="text-sm text-white font-bold truncate max-w-[150px]">{anomaly.description}</p>
                                                     <p className="text-sm font-mono text-red-300">€{anomaly.amount.toLocaleString()}</p>
                                                </div>
                                                <p className="text-xs text-gray-400 leading-snug mt-2 pt-2 border-t border-white/5">{anomaly.explanation}</p>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Loading */}
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
                        <p className="text-xl text-white font-medium mt-6">{t('analyst.processing', 'AI is auditing financial records...')}</p>
                        <p className="text-sm text-gray-400 mt-2">{t('analyst.wait', 'DeepSeek is identifying fiscal risks.')}</p>
                    </motion.div>
                )}
            </AnimatePresence>

        </div>
    );
};

export default SpreadsheetAnalyst;