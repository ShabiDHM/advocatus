// FILE: src/components/SpreadsheetAnalyst.tsx
// PHOENIX PROTOCOL - CLEANUP V1.1
// 1. FIX: Removed unused imports (Upload, ChevronRight).
// 2. STATUS: Linter clean.

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileSpreadsheet, Activity, AlertTriangle, TrendingUp, BarChart2, Loader2, CheckCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { SpreadsheetAnalysisResult, AnalysisChartConfig } from '../data/types';

interface SpreadsheetAnalystProps {
    caseId: string;
}

const SimpleBarChart: React.FC<{ chart: AnalysisChartConfig }> = ({ chart }) => {
    // Find max value for scaling
    const maxVal = Math.max(...chart.data.map(d => d.value));

    return (
        <div className="bg-white/5 p-4 rounded-xl border border-white/10 mt-4">
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
                                className="h-full bg-gradient-to-r from-primary-start to-primary-end rounded-full"
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
            setError(t('error.analysisFailed', 'Analysis failed. Please check the file format.'));
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-1">
            
            {/* 1. Header & Upload Section */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <Activity className="text-primary-start" />
                            {t('analyst.title', 'Smart Financial Analyst')}
                        </h2>
                        <p className="text-gray-400 mt-1">
                            {t('analyst.subtitle', 'Upload Excel/CSV records for automated forensic analysis.')}
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
                                    flex items-center gap-3 px-4 py-2 rounded-xl border border-dashed transition-all
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
                                className="px-6 py-2 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg hover:shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-50"
                            >
                                {isAnalyzing ? <Loader2 className="animate-spin w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                                {isAnalyzing ? t('analyst.analyzing', 'Analyzing...') : t('analyst.run', 'Run Analysis')}
                            </button>
                        )}
                        
                        {result && (
                             <button
                                onClick={() => { setResult(null); setFile(null); }}
                                className="px-4 py-2 border border-white/10 text-gray-300 hover:text-white rounded-xl text-sm transition-colors"
                             >
                                {t('analyst.newAnalysis', 'New Analysis')}
                             </button>
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
                            {/* Narrative Card */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <CheckCircle className="text-green-400 w-5 h-5" />
                                    {t('analyst.reportTitle', 'Forensic Narrative')}
                                </h3>
                                <div className="prose prose-invert max-w-none text-gray-300 leading-relaxed">
                                    {result.narrative_report.split('\n').map((para, i) => (
                                        <p key={i} className="mb-2">{para}</p>
                                    ))}
                                </div>
                            </div>

                            {/* Key Stats Grid */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {Object.entries(result.key_statistics).map(([key, value]) => (
                                    <div key={key} className="bg-white/5 p-4 rounded-xl border border-white/10 text-center">
                                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">{key.replace(/_/g, ' ')}</p>
                                        <p className="text-xl font-bold text-white">{value}</p>
                                    </div>
                                ))}
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
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 h-full">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <AlertTriangle className="text-yellow-400 w-5 h-5" />
                                    {t('analyst.anomaliesTitle', 'Detected Anomalies')}
                                </h3>
                                
                                <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
                                    {result.anomalies.length === 0 ? (
                                        <p className="text-gray-500 italic text-center py-4">{t('analyst.noAnomalies', 'No significant anomalies detected.')}</p>
                                    ) : (
                                        result.anomalies.map((anomaly, idx) => (
                                            <div key={idx} className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                                                <div className="flex justify-between items-start mb-1">
                                                    <span className="text-xs font-bold text-red-300 uppercase">{anomaly.severity} SEVERITY</span>
                                                    <span className="text-xs text-gray-400">Row {anomaly.row_index}</span>
                                                </div>
                                                <p className="text-sm text-white font-medium mb-1">Col: {anomaly.column} = {anomaly.value}</p>
                                                <p className="text-xs text-gray-400">{anomaly.reason}</p>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Loading Skeleton if analyzing */}
             <AnimatePresence>
                {isAnalyzing && !result && (
                    <motion.div 
                        initial={{ opacity: 0 }} 
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex flex-col items-center justify-center py-20"
                    >
                        <Loader2 className="w-12 h-12 text-primary-start animate-spin mb-4" />
                        <p className="text-lg text-white font-medium">{t('analyst.processing', 'AI is analyzing data structure...')}</p>
                        <p className="text-sm text-gray-400">{t('analyst.wait', 'This may take a few seconds depending on file size.')}</p>
                    </motion.div>
                )}
            </AnimatePresence>

        </div>
    );
};

export default SpreadsheetAnalyst;