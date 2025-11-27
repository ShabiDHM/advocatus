// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - BUSINESS LOGIC RESTORATION
// 1. INTEGRATION: Added 'Case Selection' dropdown (Business Logic).
// 2. LOGIC: Fetches active cases on mount.
// 3. UI: Aligned layout with the 'Draftimi Inteligjent' screenshot.

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
  
  // State for Business Logic
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  
  const [context, setContext] = useState('');
  const [currentJob, setCurrentJob] = useState<DraftingJobState>({
    jobId: null,
    status: null,
    result: null,
    error: null,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [jobHistory, setJobHistory] = useState<Array<{
    id: string;
    context: string;
    result: string;
    timestamp: Date;
  }>>([]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  // Load Cases on Mount (Business Logic)
  useEffect(() => {
    const loadCases = async () => {
        try {
            const data = await apiService.getCases();
            setCases(data);
        } catch (err) {
            console.error("Failed to load cases for drafting context", err);
        }
    };
    loadCases();
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [context]);

  // Scroll to result when it appears
  useEffect(() => {
    if (currentJob.result && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentJob.result]);

  // Cleanup polling
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const startPolling = (jobId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

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

            setJobHistory(prev => [{
              id: jobId,
              context,
              result: finalResult,
              timestamp: new Date(),
            }, ...prev.slice(0, 9)]);

            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          } catch (error: any) {
            setCurrentJob(prev => ({ ...prev, error: 'Failed to fetch result', status: 'FAILED' }));
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          }
        } else if (newStatus === 'FAILED') {
          setCurrentJob(prev => ({ 
            ...prev, 
            error: statusResponse.error || 'Job failed to complete',
            result: null
          }));
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        }
      } catch (error: any) {
        setCurrentJob(prev => ({ ...prev, error: 'Polling failed', status: 'FAILED' }));
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      }
    }, 3000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!context.trim()) return;

    setIsSubmitting(true);
    setCurrentJob({ jobId: null, status: null, result: null, error: null });

    try {
      // INCLUDE case_id (Business Logic)
      const jobResponse = await apiService.initiateDraftingJob({
        user_prompt: context.trim(),
        context: context.trim(),
        case_id: selectedCaseId || undefined 
      });

      const jobId = jobResponse.job_id;
      setCurrentJob({ jobId, status: 'PENDING', result: null, error: null });
      startPolling(jobId);

    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed';
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
      a.download = `legal-draft-${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handleNewDraft = () => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    setCurrentJob({ jobId: null, status: null, result: null, error: null });
    setContext('');
  };

  const loadHistoryItem = (item: typeof jobHistory[0]) => {
    setContext(item.context);
    setCurrentJob({ jobId: item.id, status: 'COMPLETED', result: item.result, error: null });
  };

  const getStatusIcon = () => {
    switch (currentJob.status) {
      case 'PENDING':
      case 'PROCESSING': return <Clock className="h-5 w-5 text-yellow-400 animate-pulse" />;
      case 'COMPLETED': return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'FAILED': return <AlertCircle className="h-5 w-5 text-red-400" />;
      default: return null;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex justify-center mb-4">
            <PenTool className="h-10 w-10 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">{t('drafting.title', 'Draftimi Inteligjent')}</h1>
        <p className="text-gray-400">{t('drafting.subtitle', 'Krijoni dokumente ligjore automatikisht.')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEFT COLUMN: Controls & Input */}
        <div className="space-y-6">
          <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
                
                {/* CASE SELECTION (Business Logic) */}
                <div>
                    <label className="block text-sm font-medium text-white mb-2">
                        {t('drafting.selectCase', 'Zgjidhni Rastin (Opsionale)')}
                    </label>
                    <div className="relative">
                        <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <select 
                            value={selectedCaseId}
                            onChange={(e) => setSelectedCaseId(e.target.value)}
                            className="w-full pl-10 pr-4 py-3 bg-black/50 border border-glass-edge rounded-xl text-white appearance-none focus:ring-1 focus:ring-primary-500 outline-none"
                        >
                            <option value="">{t('drafting.noCase', 'Pa Rast (Draftim i Përgjithshëm)')}</option>
                            {cases.map(c => (
                                <option key={c.id} value={c.id}>
                                    {c.case_number} - {c.title}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* CONTEXT INPUT */}
                <div>
                    <label className="block text-sm font-medium text-white mb-2">
                        {t('drafting.inputLabel', 'Udhëzimet për Draftin')}
                    </label>
                    <textarea
                        ref={textareaRef}
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        placeholder={t('drafting.placeholder', "Psh: Krijo një kontratë qiraje për një apartament në Prishtinë...")}
                        className="w-full px-4 py-3 bg-black/50 border border-glass-edge rounded-xl text-white placeholder-gray-500 focus:ring-1 focus:ring-primary-500 outline-none min-h-[200px]"
                        disabled={isSubmitting}
                        required
                    />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || !context.trim()}
                  className="w-full py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send />}
                  {t('drafting.generateBtn', 'Gjenero Dokumentin')}
                </button>
            </form>
          </div>
        </div>

        {/* RIGHT COLUMN: Results & Status */}
        <div className="space-y-6">
            {/* Status Panel */}
            {currentJob.status && (
                <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 animate-fade-in">
                    <div className="flex items-center gap-3 mb-2">
                        {getStatusIcon()}
                        <h3 className="font-bold text-white">Statusi</h3>
                    </div>
                    <p className="text-gray-300 text-sm mb-3">
                        {currentJob.status === 'PENDING' && "Duke u përgatitur..."}
                        {currentJob.status === 'PROCESSING' && "Duke gjeneruar dokumentin..."}
                        {currentJob.status === 'COMPLETED' && "Përfunduar me sukses!"}
                        {currentJob.status === 'FAILED' && "Dështoi."}
                    </p>
                    {currentJob.error && <div className="text-red-400 text-sm">{currentJob.error}</div>}
                </div>
            )}

            {/* Result Display */}
            <div className={`bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 min-h-[400px] flex flex-col ${!currentJob.result ? 'items-center justify-center text-center' : ''}`}>
                {currentJob.result ? (
                    <>
                        <div className="flex justify-between items-center mb-4 border-b border-white/10 pb-4">
                            <div className="flex items-center gap-2 text-white font-bold">
                                <Sparkles className="text-yellow-400" /> Rezultati
                            </div>
                            <div className="flex gap-2">
                                <button onClick={handleCopyResult} className="p-2 hover:bg-white/10 rounded-lg text-gray-300"><Copy size={18}/></button>
                                <button onClick={handleDownloadResult} className="p-2 hover:bg-white/10 rounded-lg text-gray-300"><Download size={18}/></button>
                            </div>
                        </div>
                        <pre className="whitespace-pre-wrap text-gray-300 font-mono text-sm leading-relaxed overflow-x-auto">
                            {currentJob.result}
                        </pre>
                        <button onClick={handleNewDraft} className="mt-4 w-full py-2 border border-white/20 hover:bg-white/5 text-white rounded-lg">
                            Draft i Ri
                        </button>
                    </>
                ) : (
                    <>
                        <FileText className="w-16 h-16 text-gray-600 mb-4" />
                        <h3 className="text-xl font-bold text-white mb-2">Rezultati</h3>
                        <p className="text-gray-500">Rezultati do të shfaqet këtu.</p>
                    </>
                )}
            </div>
            
             {/* Simple History List */}
             {jobHistory.length > 0 && (
                <div className="bg-background-light/10 rounded-xl p-4 border border-glass-edge">
                    <h4 className="text-white font-bold mb-3">Historiku</h4>
                    <div className="space-y-2">
                        {jobHistory.map((item) => (
                            <button key={item.id} onClick={() => loadHistoryItem(item)} className="w-full text-left p-2 hover:bg-white/5 rounded text-gray-400 text-sm truncate">
                                {item.timestamp.toLocaleTimeString()} - {item.context}
                            </button>
                        ))}
                    </div>
                </div>
             )}
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;