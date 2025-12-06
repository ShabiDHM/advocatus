// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING RENDERER UPGRADE
// 1. FEATURE: Integrated 'react-markdown' for structured legal document rendering.
// 2. STYLE: Applied typography styles (Gold/Bold, Spacing) for readability.
// 3. UI: Preserved exact layout structure while removing the raw <pre> tag.

import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  PenTool, Send, Copy, Download, RefreshCw, AlertCircle, CheckCircle, Clock, FileText, Sparkles, RotateCcw
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'SUCCESS' | 'FAILED' | 'FAILURE';

interface DraftingJobState {
  jobId: string | null;
  status: JobStatus | null;
  result: string | null;
  error: string | null;
}

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  
  const [context, setContext] = useState('');
  
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

  const runDraftingJob = async () => {
    if (!context.trim()) return;

    setIsSubmitting(true);
    setCurrentJob({ jobId: null, status: 'PENDING', result: null, error: null });

    try {
      const jobResponse = await apiService.initiateDraftingJob({
        user_prompt: context.trim(),
        context: context.trim(),
        case_id: undefined, 
        use_library: false 
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runDraftingJob();
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
                    <button 
                        onClick={runDraftingJob} 
                        disabled={!currentJob.result || isSubmitting} 
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" 
                        title={t('drafting.regenerate', 'Rigjenero')}
                    >
                        <RotateCcw size={18}/>
                    </button>
                    <button onClick={handleCopyResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.copyTitle')}><Copy size={18}/></button>
                    <button onClick={handleDownloadResult} disabled={!currentJob.result} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 disabled:opacity-30 transition-colors" title={t('drafting.downloadTitle')}><Download size={18}/></button>
                </div>
            </div>
            {currentJob.error && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4 text-sm text-red-300 flex items-center gap-2 flex-shrink-0"><AlertCircle size={16} />{currentJob.error}</div>
            )}
            <div className="flex-1 bg-black/50 rounded-xl border border-white/5 p-4 overflow-auto custom-scrollbar relative">
                {currentJob.result ? (
                    // --- PHOENIX: Replaced <pre> with ReactMarkdown ---
                    <div className="markdown-content text-gray-300 text-sm leading-relaxed">
                        <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                                p: ({node, ...props}) => <p className="mb-4 last:mb-0 text-justify" {...props} />,
                                strong: ({node, ...props}) => <span className="font-bold text-amber-100" {...props} />,
                                em: ({node, ...props}) => <span className="italic text-gray-400" {...props} />,
                                ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-2 my-3 marker:text-primary-500" {...props} />,
                                ol: ({node, ...props}) => <ol className="list-decimal pl-5 space-y-2 my-3 marker:text-primary-500" {...props} />,
                                li: ({node, ...props}) => <li className="pl-1" {...props} />,
                                h1: ({node, ...props}) => <h1 className="text-xl font-bold text-white mt-6 mb-4 border-b border-white/10 pb-2 uppercase tracking-wide text-center" {...props} />,
                                h2: ({node, ...props}) => <h2 className="text-lg font-bold text-white mt-5 mb-3" {...props} />,
                                h3: ({node, ...props}) => <h3 className="text-base font-bold text-gray-200 mt-4 mb-2" {...props} />,
                                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary-500 pl-4 py-2 my-4 bg-white/5 italic text-gray-400" {...props} />,
                                code: ({node, ...props}) => <code className="bg-black/40 px-1.5 py-0.5 rounded text-xs font-mono text-pink-300" {...props} />,
                                table: ({node, ...props}) => <div className="overflow-x-auto my-4"><table className="min-w-full border-collapse border border-white/10 text-xs" {...props} /></div>,
                                th: ({node, ...props}) => <th className="border border-white/10 px-3 py-2 bg-white/5 font-bold text-left" {...props} />,
                                td: ({node, ...props}) => <td className="border border-white/10 px-3 py-2" {...props} />,
                            }}
                        >
                            {currentJob.result}
                        </ReactMarkdown>
                    </div>
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