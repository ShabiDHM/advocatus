// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE
// 1. FIX: Removed unused '@headlessui/react' import.
// 2. STATUS: Clean, Custom Toggle UI.

import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, FileText, Sparkles, Briefcase, BookOpen
} from 'lucide-react';
import { Case } from '../data/types';
// PHOENIX FIX: Removed Switch import as we use a custom button below

type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'SUCCESS' | 'FAILED' | 'FAILURE';

interface DraftingJobState {
  jobId: string | null;
  status: JobStatus | null;
  result: string | null;
  error: string | null;
}

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [context, setContext] = useState('');
  const [useLibrary, setUseLibrary] = useState(false);
  
  const [currentJob, setCurrentJob] = useState<DraftingJobState>({
    jobId: null, 
    status: null, 
    result: null, 
    error: null,
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollingIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    const loadCases = async () => {
        try {
            const data = await apiService.getCases();
            setCases(data);
        } catch (err) {
            console.error("Failed to load cases", err);
        }
    };
    loadCases();
  }, []);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  const startPolling = (jobId: string) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = window.setInterval(async () => {
      try {
        const statusResponse = await apiService.getDraftingJobStatus(jobId);
        const newStatus = statusResponse.status as JobStatus; 
        
        setCurrentJob(prev => ({ ...prev, status: newStatus }));

        if (newStatus === 'COMPLETED' || newStatus === 'SUCCESS') {
          try {
            const resultResponse = await apiService.getDraftingJobResult(jobId);
            const finalResult = resultResponse.document_text || resultResponse.result_text || "";

            setCurrentJob(prev => ({ 
              ...prev, 
              status: 'COMPLETED',
              result: finalResult, 
              error: null 
            }));
            
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
            setIsSubmitting(false);

          } catch (error) {
            setCurrentJob(prev => ({ ...prev, error: t('drafting.errorFetchResult'), status: 'FAILED' }));
            if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
            setIsSubmitting(false);
          }
        } else if (newStatus === 'FAILED' || newStatus === 'FAILURE') {
          setCurrentJob(prev => ({ 
            ...prev, 
            status: 'FAILED',
            error: statusResponse.error || t('drafting.errorJobFailed'),
            result: null
          }));
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsSubmitting(false);
        }
      } catch (error) {
        console.warn("Polling error:", error);
      }
    }, 2000);
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
        case_id: selectedCaseId || undefined,
        use_library: useLibrary 
      });

      const jobId = jobResponse.job_id;
      setCurrentJob({ jobId, status: 'PENDING', result: null, error: null });
      startPolling(jobId);

    } catch (error: any) {
      console.error("Submit Error:", error);
      const errorMessage = error.response?.data?.detail || error.message || t('drafting.errorStartJob');
      setCurrentJob(prev => ({ ...prev, error: errorMessage, status: 'FAILED' }));
      setIsSubmitting(false);
    }
  };

  const handleCopyResult = async () => {
    if (currentJob.result) {
      await navigator.clipboard.writeText(currentJob.result);
      alert(t('general.copied'));
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

  const getStatusDisplay = () => {
    switch(currentJob.status) {
      case 'COMPLETED': 
      case 'SUCCESS': return { text: t('drafting.statusCompleted'), color: 'text-green-400', icon: <CheckCircle className="h-5 w-5 text-green-400" /> };
      case 'FAILED': 
      case 'FAILURE': return { text: t('drafting.statusFailed'), color: 'text-red-400', icon: <AlertCircle className="h-5 w-5 text-red-400" /> };
      case 'PROCESSING':
      case 'PENDING': return { text: t('drafting.statusWorking'), color: 'text-yellow-400', icon: <Clock className="h-5 w-5 animate-pulse text-yellow-400" /> };
      default: return { text: t('drafting.statusResult'), color: 'text-white', icon: <Sparkles className="h-5 w-5 text-gray-500" /> };
    }
  };
  
  const statusDisplay = getStatusDisplay();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-theme(spacing.20))] flex flex-col">
      <div className="text-center mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white mb-1 flex items-center justify-center gap-3">
             <PenTool className="text-primary-500" /> 
             {t('drafting.title')}
        </h1>
        <p className="text-gray-400 text-sm">{t('drafting.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        {/* Input Column */}
        <div className="flex flex-col h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                <FileText className="text-primary-400" size={20} />
                {t('drafting.configuration')}
            </h3>
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4">
                
                <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.selectCaseLabel')}</label>
                    <div className="relative">
                        <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                        <select 
                            value={selectedCaseId}
                            onChange={(e) => setSelectedCaseId(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-white appearance-none focus:ring-1 focus:ring-primary-500 outline-none text-sm"
                        >
                            <option value="">-- {t('drafting.generalDraft')} --</option>
                            {cases.map(c => <option key={c.id} value={c.id}>{c.case_number} - {c.title}</option>)}
                        </select>
                    </div>
                </div>

                {/* Library Toggle */}
                <div className="flex items-center justify-between bg-black/30 p-3 rounded-xl border border-white/5">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${useLibrary ? 'bg-primary-500/20 text-primary-400' : 'bg-gray-800 text-gray-500'}`}>
                            <BookOpen size={18} />
                        </div>
                        <div>
                            <span className="text-sm font-medium text-white block">Përdor Arkivën (Beta)</span>
                            <span className="text-xs text-gray-500">Kërko në modelet e ruajtura</span>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => setUseLibrary(!useLibrary)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
                            useLibrary ? 'bg-primary-600' : 'bg-gray-700'
                        }`}
                    >
                        <span className={`${useLibrary ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition`}/>
                    </button>
                </div>

                <div className="flex-1 flex flex-col">
                    <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{t('drafting.instructionsLabel')}</label>
                    <textarea
                        ref={textareaRef}
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        placeholder={t('drafting.promptPlaceholder')}
                        className="flex-1 w-full p-4 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:ring-1 focus:ring-primary-500 outline-none resize-none text-sm leading-relaxed"
                        disabled={isSubmitting}
                    />
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting || !context.trim()}
                  className="w-full py-3 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                >
                  {isSubmitting ? <RefreshCw className="animate-spin" /> : <Send size={18} />}
                  {t('drafting.generateBtn')}
                </button>
            </form>
        </div>

        {/* Result Column */}
        <div className="flex flex-col h-full bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl">
            <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/5 flex-shrink-0">
                <h3 className="text-white font-semibold flex items-center gap-2">
                    {statusDisplay.icon}
                    <span className={statusDisplay.color}>{statusDisplay.text}</span>
                </h3>
                <div className="flex gap-2">
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.copyTitle')}><Copy size={18}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.downloadTitle')}><Download size={18}/></button>
                </div>
            </div>
            {currentJob.error && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4 text-sm text-red-300 flex items-center gap-2 flex-shrink-0"><AlertCircle size={16} />{currentJob.error}</div>
            )}
            <div className="flex-1 bg-black/50 rounded-xl border border-white/5 p-4 overflow-auto custom-scrollbar relative">
                {currentJob.result ? (
                    <pre className="whitespace-pre-wrap text-gray-300 font-mono text-sm leading-relaxed">{currentJob.result}</pre>
                ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600 opacity-50">
                        {isSubmitting || (currentJob.status === 'PENDING' || currentJob.status === 'PROCESSING') ? (
                            <><RefreshCw className="w-12 h-12 animate-spin mb-4 text-primary-500" /><p>{t('drafting.generatingMessage')}</p></>
                        ) : (
                            <><FileText className="w-16 h-16 mb-4" /><p>{t('drafting.emptyState')}</p></>
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