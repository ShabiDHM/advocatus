// FILE: src/components/DepositionAnalyst.tsx
// PHOENIX PROTOCOL - FIX V1.1 (MISSING IMPORT)
// 1. FIX: Added 'Activity' to lucide-react imports.
// 2. STATUS: Linter clean.

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileText, UserCheck, AlertTriangle, MessageSquare, 
    BrainCircuit, Loader2, CheckCircle, RefreshCw, Zap,
    Activity // <--- ADDED THIS
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { DepositionAnalysisResult } from '../data/types';

interface DepositionAnalystProps {
    caseId: string;
}

const DepositionAnalyst: React.FC<DepositionAnalystProps> = ({ caseId }) => {
    const { t } = useTranslation();
    const [file, setFile] = useState<File | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<DepositionAnalysisResult | null>(null);
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
            const data = await apiService.analyzeDeposition(caseId, file);
            setResult(data);
        } catch (err: any) {
            console.error(err);
            setError(t('deposition.error.failed', 'Analysis failed. Ensure the file is a readable PDF/Docx transcript.'));
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="w-full h-full min-h-[500px] flex flex-col gap-6 p-1">
            
            {/* 1. Header & Upload Section */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl -z-10 pointer-events-none" />

                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <BrainCircuit className="text-purple-400" />
                            {t('deposition.title', 'Deposition & Testimony Analyst')}
                        </h2>
                        <p className="text-gray-400 mt-1 max-w-xl">
                            {t('deposition.subtitle', 'Upload transcripts to detect inconsistencies, emotional markers, and generate cross-examination strategies.')}
                        </p>
                    </div>

                    <div className="flex items-center gap-3 w-full md:w-auto">
                        {!result && (
                            <div className="relative group w-full md:w-auto">
                                <input 
                                    type="file" 
                                    accept=".pdf, .docx, .txt"
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                />
                                <div className={`
                                    flex items-center gap-3 px-4 py-2.5 rounded-xl border border-dashed transition-all cursor-pointer
                                    ${file ? 'border-purple-500 bg-purple-500/10' : 'border-gray-600 hover:border-gray-400 bg-black/20'}
                                `}>
                                    <FileText className={`w-5 h-5 ${file ? 'text-purple-400' : 'text-gray-400'}`} />
                                    <span className="text-sm text-gray-300 truncate max-w-[200px]">
                                        {file ? file.name : t('deposition.selectFile', 'Select Transcript...')}
                                    </span>
                                </div>
                            </div>
                        )}

                        {file && !result && (
                            <button
                                onClick={runAnalysis}
                                disabled={isAnalyzing}
                                className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-purple-800 text-white rounded-xl font-bold flex items-center gap-2 shadow-lg hover:shadow-purple-500/20 transition-all active:scale-95 disabled:opacity-50"
                            >
                                {isAnalyzing ? <Loader2 className="animate-spin w-4 h-4" /> : <Zap className="w-4 h-4" />}
                                {isAnalyzing ? t('deposition.analyzing', 'Analyzing...') : t('deposition.run', 'Run Forensics')}
                            </button>
                        )}
                        
                        {result && (
                             <button
                                onClick={() => { setResult(null); setFile(null); }}
                                className="px-4 py-2 border border-white/10 text-gray-300 hover:text-white rounded-xl text-sm transition-colors flex items-center gap-2 hover:bg-white/5"
                             >
                                <RefreshCw className="w-4 h-4" />
                                {t('deposition.newAnalysis', 'New Analysis')}
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
                        {/* Column 1: Core Analysis & Questions */}
                        <div className="lg:col-span-2 space-y-6">
                            
                            {/* Witness Profile Card */}
                            <div className="flex gap-4">
                                <div className="flex-1 bg-white/5 p-4 rounded-xl border border-white/10 flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-gray-400 uppercase font-bold">{t('deposition.witness', 'Witness')}</p>
                                        <p className="text-xl font-bold text-white">{result.witness_name || 'Unknown'}</p>
                                    </div>
                                    <UserCheck className="w-8 h-8 text-purple-400 opacity-50" />
                                </div>
                                <div className="flex-1 bg-white/5 p-4 rounded-xl border border-white/10 flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-gray-400 uppercase font-bold">{t('deposition.credibility', 'Credibility Score')}</p>
                                        <p className={`text-xl font-bold ${result.credibility_score > 70 ? 'text-green-400' : result.credibility_score > 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                                            {result.credibility_score}/100
                                        </p>
                                    </div>
                                    <Activity className="w-8 h-8 text-purple-400 opacity-50" />
                                </div>
                            </div>

                            {/* Summary */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <CheckCircle className="text-green-400 w-5 h-5" />
                                    {t('deposition.summary', 'Executive Summary')}
                                </h3>
                                <p className="text-gray-300 leading-relaxed text-sm">{result.summary}</p>
                            </div>

                            {/* Strategic Questions */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <MessageSquare className="text-blue-400 w-5 h-5" />
                                    {t('deposition.strategy', 'Cross-Examination Strategy')}
                                </h3>
                                <div className="space-y-4">
                                    {result.suggested_questions.map((q, idx) => (
                                        <div key={idx} className="bg-black/20 p-4 rounded-xl border border-white/5 hover:border-purple-500/30 transition-colors">
                                            <div className="flex justify-between mb-2">
                                                <span className="text-xs font-bold text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded uppercase">{q.strategy}</span>
                                            </div>
                                            <p className="text-white font-medium mb-1">"{q.question}"</p>
                                            <p className="text-xs text-gray-400 italic">{q.rationale}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Column 2: Inconsistencies & Emotions */}
                        <div className="lg:col-span-1 space-y-6">
                            
                            {/* Inconsistencies */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <AlertTriangle className="text-red-400 w-5 h-5" />
                                    {t('deposition.contradictions', 'Contradictions')}
                                </h3>
                                <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
                                    {result.inconsistencies.map((inc, idx) => (
                                        <div key={idx} className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                                            <div className="flex justify-between mb-1">
                                                <span className="text-[10px] text-red-300 font-bold">{inc.severity}</span>
                                                <span className="text-[10px] text-gray-500">{inc.source_ref}</span>
                                            </div>
                                            <p className="text-xs text-gray-300 mb-1">"{inc.statement}"</p>
                                            <p className="text-xs text-red-200 font-medium">VS: {inc.contradiction}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Emotional Markers */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-white/5">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <BrainCircuit className="text-pink-400 w-5 h-5" />
                                    {t('deposition.emotions', 'Psycholinguistic Markers')}
                                </h3>
                                <div className="space-y-3">
                                    {result.emotional_segments.map((em, idx) => (
                                        <div key={idx} className="p-3 bg-pink-500/5 border border-pink-500/20 rounded-lg">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-[10px] font-bold bg-pink-500/20 text-pink-300 px-2 rounded">{em.emotion}</span>
                                            </div>
                                            <p className="text-xs text-white mb-1">"{em.segment}"</p>
                                            <p className="text-[10px] text-gray-400">{em.analysis}</p>
                                        </div>
                                    ))}
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
                            <div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-purple-500 animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <BrainCircuit className="w-6 h-6 text-purple-500" />
                            </div>
                        </div>
                        <p className="text-xl text-white font-medium mt-6">{t('deposition.processing', 'AI is analyzing testimony patterns...')}</p>
                        <p className="text-sm text-gray-400 mt-2">{t('deposition.wait', 'Cross-referencing timeline and psychological markers.')}</p>
                    </motion.div>
                )}
            </AnimatePresence>

        </div>
    );
};

export default DepositionAnalyst;