// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - REFACTOR V1.2 (I18N & UI POLISH)
// 1. I18N: All hardcoded strings replaced with t() functions.
// 2. UI: Improved spacing and card layouts for better readability.

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileSpreadsheet, Activity, AlertTriangle, TrendingUp, BarChart2, Loader2, CheckCircle, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { SpreadsheetAnalysisResult, AnalysisChartConfig } from '../data/types';

interface SpreadsheetAnalystProps {
    caseId: string;
}

const SimpleBarChart: React.FC<{ chart: AnalysisChartConfig }> = ({ chart }) => {
    const maxVal = Math.max(...chart.data.map(d => d.value));

    return (
        <div className="bg-white/5 p-4 rounded-xl border border-white/10 mt-4 hover:bg-white/10 transition-colors">
            <h4 className="text-white font-semibold mb-2 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-primary-start" />
                {chart.title}
            </h4>
            <p className="text-xs text-gray-400 mb-4">{chart.description}</p>
            <div className="space-y-3">
                {chart.data.map((item, idx) => (
                    <div key={idx} className="flex flex-col gap-1">
                        <div className="flex justify-between text-xs text-gray-300">
                            <span>{item.name}</span>
                            <span className="font-mono">{item.value.toLocaleString()}</span>
                        </div>
                        <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${(item.value / maxVal) * 100}%` }}
                                transition={{ duration: 1, delay: idx * 0.1 }}
                                className="h-full bg-gradient-to-r from-primary-start to-primary-end rounded-full shadow-[0_0_10px_rgba(59,130,246,0.5)]"
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const SpreadsheetAnalyst: React.FC<SpreadsheetAnalystProps> = ({ caseId }) => {
    const { t } = useTranslation();
    const [file, setFile] = useState<File | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<SpreadsheetAnalysisResult | null>(null);
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
            const data = await apiService.analyzeSpreadsheet(caseId, file);
            setResult(data);
        } catch (err: any) {
            console.error(err);
            setError(t('analyst.error.analysisFailed', 'Analysis failed. Please check the file format.'));
        } finally {
            setIsAnalyzing(false);
        }
    };

    // Helper to format keys like "Avg Shuma" -> "Avg Amount" depending on context, or just clean up
    const formatStatKey = (key: string) => {
        if (key.includes('Avg')) return `${t('analyst.stats.avg', 'Avg')} ${key.replace('Avg ', '')}`;
        if (key === 'Total Records') return t('analyst.stats.totalRecords', 'Total Records');
        if (key === 'Total Columns') return t('analyst.stats.totalColumns', 'Total Columns');
        if (key === 'Empty Cells') return t('analyst.stats.emptyCells', 'Empty Cells');
        return key;
    };

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-1">
            
            {/* 1. Header & Upload Section */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 relative overflow-hidden">
                {/* Background Decor */}
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

            {/* 2. Results Section */}
            <AnimatePresence mode="wait">
                {result && (
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="grid grid-cols-1 lg:grid-cols-3 gap-6"
                    >
                        {/* Column 1: Narrative & Summary */}
                        <div className="lg:col-span-2 space-y-6">
                            
                            {/* Key Stats Grid */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {Object.entries(result.key_statistics).map(([key, value]) => (
                                    <div key={key} className="bg-white/5 p-4 rounded-xl border border-white/10 text-center hover:border-primary-start/30 transition-colors">
                                        <p className="text-[10px] md:text-xs text-gray-400 uppercase tracking-wider mb-1 font-bold">{formatStatKey(key)}</p>
                                        <p className="text-lg md:text-2xl font-bold text-white">{value}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Narrative Card */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 shadow-xl">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2 border-b border-white/5 pb-2">
                                    <CheckCircle className="text-green-400 w-5 h-5" />
                                    {t('analyst.reportTitle', 'Forensic Narrative')}
                                </h3>
                                <div className="prose prose-invert max-w-none text-gray-300 leading-relaxed text-sm md:text-base">
                                    {result.narrative_report.split('\n').map((para, i) => (
                                        <p key={i} className="mb-3 last:mb-0">{para}</p>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Charts Area */}
                             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {result.charts.map(chart => (
                                    <SimpleBarChart key={chart.id} chart={chart} />
                                ))}
                             </div>
                        </div>

                        {/* Column 2: Anomalies & Data */}
                        <div className="lg:col-span-1 space-y-6">
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 h-full flex flex-col">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <AlertTriangle className="text-yellow-400 w-5 h-5" />
                                    {t('analyst.anomaliesTitle', 'Detected Anomalies')}
                                </h3>
                                
                                <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar max-h-[600px]">
                                    {result.anomalies.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center h-full text-center py-10 opacity-60">
                                            <CheckCircle className="w-12 h-12 text-green-500 mb-2" />
                                            <p className="text-gray-400">{t('analyst.noAnomalies', 'No significant anomalies detected.')}</p>
                                        </div>
                                    ) : (
                                        result.anomalies.map((anomaly, idx) => (
                                            <div key={idx} className="p-4 bg-red-500/5 border border-red-500/20 rounded-xl hover:bg-red-500/10 transition-colors group">
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                                        anomaly.severity === 'HIGH' ? 'bg-red-500/20 text-red-300' : 'bg-yellow-500/20 text-yellow-300'
                                                    }`}>
                                                        {t(`analyst.severity.${anomaly.severity.toLowerCase()}`, anomaly.severity)}
                                                    </span>
                                                    <span className="text-xs text-gray-500 font-mono">
                                                        {t('analyst.row', 'Row')} {anomaly.row_index}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-white font-medium mb-1">
                                                    <span className="text-gray-400">{t('analyst.col', 'Col')}:</span> {anomaly.column} 
                                                    <span className="mx-1 text-gray-600">→</span> 
                                                    <span className="text-red-200">{anomaly.value}</span>
                                                </p>
                                                <p className="text-xs text-gray-400 leading-snug group-hover:text-gray-300 transition-colors">{anomaly.reason}</p>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Loading Skeleton */}
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
                        <p className="text-xl text-white font-medium mt-6">{t('analyst.processing', 'AI is analyzing data structure...')}</p>
                        <p className="text-sm text-gray-400 mt-2">{t('analyst.wait', 'This may take a few seconds depending on file size.')}</p>
                    </motion.div>
                )}
            </AnimatePresence>

        </div>
    );
};

export default SpreadsheetAnalyst;