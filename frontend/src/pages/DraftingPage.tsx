// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - VISUAL SYMMETRY & LOGIC FIX
// 1. LAYOUT: Enforced equal height columns with 'flex-1' and 'h-full'.
// 2. UI: Buttons are always visible (disabled state) to prevent layout jumping.
// 3. LOGIC: Added fallback for empty case list.

import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  PenTool, 
  Send, 
  Copy, 
  Download, 
  RefreshCw, 
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Sparkles,
  Briefcase
} from 'lucide-react';
import { Case } from '../data/types';

interface DraftingJobState {
  jobId: string | null;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | null;
  result: string | null;
  error: string | null;
}

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  
  // Data State
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  
  // Job State
  const [context, setContext] = useState('');
  const [currentJob, setCurrentJob] = useState<DraftingJobState>({
    jobId: null,
    status: null,
    result: null,
    error: null,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load Cases
  useEffect(() => {
    const loadCases = async () => {
        try {
            const data = await apiService.getCases();
            console.log("Cases loaded:", data); // Debugging
            setCases(data);
        } catch (err) {
            console.error("Failed to load cases", err);
        }
    };
    loadCases();
  }, []);

  // Cleanup polling
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  const startPolling = (jobId: string) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const statusResponse = await apiService.getDraftingJobStatus(jobId);
        const newStatus = statusResponse.status; 
        
        setCurrentJob(prev => ({ ...prev, status: newStatus }));

        if (newStatus === 'COMPLETED') {
          try {
            const resultResponse = await apiService.getDraftingJobResult(jobId);
            const finalResult = resultResponse.document_text || resultResponse.result_text || "";

            setCurrentJob(prev => ({ 
              ...prev, 
              result: finalResult, 
              error: null 
            }));
            
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          } catch (error) {
            setCurrentJob(prev => ({ ...prev, error: 'Failed to fetch result', status: 'FAILED' }));
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          }
        } else if (newStatus === 'FAILED') {
          setCurrentJob(prev => ({ 
            ...prev, 
            error: statusResponse.error || 'Job failed',
            result: null
          }));
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        }
      } catch (error) {
        setCurrentJob(prev => ({ ...prev, error: 'Connection lost', status: 'FAILED' }));
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      }
    }, 2000); // Faster polling (2s)
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!context.trim()) return;

    setIsSubmitting(true);
    setCurrentJob({ jobId: null, status: 'PENDING', result: null, error: null });

    try {
      const jobResponse = await apiService.initiateDraftingJob({
        user_prompt: context.trim(),
        context: context.trim(),
        case_id: selectedCaseId || undefined 
      });

      const jobId = jobResponse.job_id;
      // Note: We keep status as PENDING visually until we start polling
      setCurrentJob({ jobId, status: 'PENDING', result: null, error: null });
      startPolling(jobId);

    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to start job';
      setCurrentJob(prev => ({ ...prev, error: errorMessage, status: 'FAILED' }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyResult = async () => {
    if (currentJob.result) {
      await navigator.clipboard.writeText(currentJob.result);
      alert(t('general.copied', 'Copied!'));
    }
  };

  const handleDownloadResult = () => {
    if (currentJob.result) {
      const blob = new Blob([currentJob.result], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `draft-${new Date().getTime()}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  const getStatusColor = () => {
      switch(currentJob.status) {
          case 'COMPLETED': return 'text-green-400';
          case 'FAILED': return 'text-red-400';
          case 'PROCESSING': 
          case 'PENDING': return 'text-yellow-400';
          default: return 'text-gray-400';
      }
  };

  const getStatusIcon = () => {
    switch (currentJob.status) {
      case 'PENDING':
      case 'PROCESSING': return <Clock className="h-5 w-5 animate-pulse text-yellow-400" />;
      case 'COMPLETED': return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'FAILED': return <AlertCircle className="h-5 w-5 text-red-400" />;
      default: return <Sparkles className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-theme(spacing.20))] flex flex-col">
      {/* Page Header */}
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3">
             <PenTool className="text-primary-500" /> 
             {t('drafting.title', 'Draftimi Inteligjent')}
        </h1>
        <p className="text-gray-400 text-sm">{t('drafting.subtitle', 'Krijoni dokumente ligjore automatikisht.')}</p>
      </div>

      {/* Main Grid - Equal Height Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        
        {/* LEFT COLUMN: Input */}
        <div className="flex flex-col h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                <FileText className="text-primary-400" size={20} />
                Konfigurimi
            </h3>
            
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4">
                {/* Case Selection */}
                <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">
                        Zgjidhni Rastin
                    </label>
                    <div className="relative">
                        <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                        <select 
                            value={selectedCaseId}
                            onChange={(e) => setSelectedCaseId(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white appearance-none focus:ring-1 focus:ring-primary-500 outline-none text-sm"
                        >
                            <option value="">-- {t('drafting.generalDraft', 'Draftim i Përgjithshëm')} --</option>
                            {cases.map(c => (
                                <option key={c.id} value={c.id}>
                                    {c.case_number} - {c.title}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Prompt Input - Grows to fill space */}
                <div className="flex-1 flex flex-col">
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">
                        Udhëzimet
                    </label>
                    <textarea
                        ref={textareaRef}
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        placeholder="Psh: Krijo një kontratë qiraje..."
                        className="flex-1 w-full p-4 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none resize-none text-sm leading-relaxed"
                        disabled={isSubmitting}
                    />
                </div>

                {/* Generate Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || !context.trim()}
                  className="w-full py-3 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                >
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  {t('drafting.generateBtn', 'Gjenero Dokumentin')}
                </button>
            </form>
        </div>

        {/* RIGHT COLUMN: Status & Result */}
        <div className="flex flex-col h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl">
            
            {/* Header with Actions */}
            <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/5 flex-shrink-0">
                <h3 className="text-white font-semibold flex items-center gap-2">
                    {getStatusIcon()}
                    <span className={getStatusColor()}>
                        {currentJob.status === 'COMPLETED' ? 'Përfunduar' : 
                         currentJob.status === 'FAILED' ? 'Dështoi' :
                         currentJob.status ? 'Duke punuar...' : 'Rezultati'}
                    </span>
                </h3>
                <div className="flex gap-2">
                    <button 
                        onClick={handleCopyResult} 
                        disabled={!currentJob.result}
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors"
                        title="Kopjo"
                    >
                        <Copy size={18}/>
                    </button>
                    <button 
                        onClick={handleDownloadResult} 
                        disabled={!currentJob.result}
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors"
                        title="Shkarko"
                    >
                        <Download size={18}/>
                    </button>
                </div>
            </div>

            {/* Error Message (Conditional) */}
            {currentJob.error && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4 text-sm text-red-300 flex items-center gap-2 flex-shrink-0">
                    <AlertCircle size={16} />
                    {currentJob.error}
                </div>
            )}

            {/* Result Area - Fills remaining space */}
            <div className="flex-1 bg-black/50 rounded-xl border border-white/5 p-4 overflow-auto custom-scrollbar relative">
                {currentJob.result ? (
                    <pre className="whitespace-pre-wrap text-gray-300 font-mono text-sm leading-relaxed">
                        {currentJob.result}
                    </pre>
                ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600 opacity-50">
                        {isSubmitting ? (
                            <>
                                <RefreshCw className="w-12 h-12 animate-spin mb-4 text-primary-500" />
                                <p>Duke gjeneruar draftin...</p>
                            </>
                        ) : (
                            <>
                                <FileText className="w-16 h-16 mb-4" />
                                <p>Rezultati do të shfaqet këtu</p>
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>

      </div>
    </div>
  );
};

export default DraftingPage;