// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - FINAL POLISH
// 1. CLEANUP: Removed unused 'DraftingJobStatus' import.
// 2. STATUS: Zero warnings, full UI/Logic restoration.

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
  Sparkles
} from 'lucide-react';

interface DraftingJobState {
  jobId: string | null;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | null;
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
  
  // History state
  const [jobHistory, setJobHistory] = useState<Array<{
    id: string;
    context: string;
    result: string;
    timestamp: Date;
  }>>([]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

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

  // Cleanup polling on unmount
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
        // Map backend status to frontend state
        const newStatus = statusResponse.status; 
        
        setCurrentJob(prev => ({ ...prev, status: newStatus }));

        if (newStatus === 'COMPLETED') {
          // Fetch the result
          try {
            const resultResponse = await apiService.getDraftingJobResult(jobId);
            
            // Prefer HTML, fallback to text
            const finalResult = resultResponse.document_text || resultResponse.result_text || "";

            setCurrentJob(prev => ({ 
              ...prev, 
              result: finalResult,
              error: null 
            }));

            // Add to history
            setJobHistory(prev => [{
              id: jobId,
              context,
              result: finalResult,
              timestamp: new Date(),
            }, ...prev.slice(0, 9)]); // Keep last 10 jobs

            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
            }
          } catch (error: any) {
            setCurrentJob(prev => ({ 
              ...prev, 
              error: 'Failed to fetch result',
              status: 'FAILED'
            }));
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
            }
          }
        } else if (newStatus === 'FAILED') {
          setCurrentJob(prev => ({ 
            ...prev, 
            error: statusResponse.error || 'Job failed to complete',
            result: null
          }));
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
        }
      } catch (error: any) {
        console.error('Polling error:', error);
        setCurrentJob(prev => ({ 
          ...prev, 
          error: 'Failed to check job status',
          status: 'FAILED'
        }));
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
      }
    }, 3000); // Poll every 3 seconds
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!context.trim()) return;

    setIsSubmitting(true);
    
    // Reset current job state
    setCurrentJob({
      jobId: null,
      status: null,
      result: null,
      error: null,
    });

    try {
      // Step 1: Initiate the drafting job using the verified apiService method
      const jobResponse = await apiService.initiateDraftingJob({
        user_prompt: context.trim(), // API expects 'user_prompt'
        context: context.trim()      // Legacy support just in case
      });

      const jobId = jobResponse.job_id;
      
      setCurrentJob({
        jobId,
        status: 'PENDING',
        result: null,
        error: null,
      });

      // Step 2: Start polling for status
      startPolling(jobId);

    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 
                          error.message || 
                          'Failed to create drafting job';
      setCurrentJob(prev => ({ 
        ...prev, 
        error: errorMessage,
        status: 'FAILED'
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyResult = async () => {
    if (currentJob.result) {
      try {
        await navigator.clipboard.writeText(currentJob.result);
        alert(t('general.copied', 'Copied to clipboard!'));
      } catch (error) {
        console.error('Failed to copy to clipboard:', error);
      }
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
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    setCurrentJob({
      jobId: null,
      status: null,
      result: null,
      error: null,
    });
    setContext('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const loadHistoryItem = (item: typeof jobHistory[0]) => {
    setContext(item.context);
    setCurrentJob({
      jobId: item.id,
      status: 'COMPLETED',
      result: item.result,
      error: null,
    });
  };

  const getStatusIcon = () => {
    switch (currentJob.status) {
      case 'PENDING':
      case 'PROCESSING':
        return <Clock className="h-5 w-5 text-yellow-400 animate-pulse" />;
      case 'COMPLETED':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'FAILED':
        return <AlertCircle className="h-5 w-5 text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (currentJob.status) {
      case 'PENDING':
        return t('drafting.statusQueued', 'Job queued for processing...');
      case 'PROCESSING':
        return t('drafting.statusProcessing', 'AI is drafting your document...');
      case 'COMPLETED':
        return t('drafting.statusSuccess', 'Draft completed successfully!');
      case 'FAILED':
        return t('drafting.statusFailed', 'Draft generation failed');
      default:
        return '';
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex justify-center mb-4">
          <div className="bg-primary-600 p-3 rounded-full shadow-lg shadow-primary-600/20">
            <PenTool className="h-8 w-8 text-white" />
          </div>
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">{t('drafting.title', 'AI Legal Drafting')}</h1>
        <p className="text-gray-400 max-w-2xl mx-auto">
          {t('drafting.subtitle', 'Provide context and instructions to generate professional legal documents.')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Input Form */}
          <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-xl">
            <form onSubmit={handleSubmit}>
              <label htmlFor="context" className="block text-lg font-medium text-white mb-4">
                {t('drafting.inputLabel', 'Document Context & Instructions')}
              </label>
              <textarea
                ref={textareaRef}
                id="context"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder={t('drafting.placeholder', "Describe the legal document you need drafted...")}
                className="block w-full px-4 py-3 border border-glass-edge rounded-xl bg-black/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none min-h-[200px] transition-all"
                disabled={isSubmitting || (currentJob.status !== null && currentJob.status !== 'FAILED')}
                required
              />
              <div className="flex justify-between items-center mt-4">
                <span className="text-sm text-gray-500">
                  {context.length} characters
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || !context.trim() || (currentJob.status !== null && currentJob.status !== 'FAILED')}
                  className="inline-flex items-center px-6 py-2.5 rounded-xl shadow-lg text-sm font-bold text-white bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      {t('general.processing', 'Submitting...')}
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      {t('drafting.generateBtn', 'Generate Draft')}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Status Display */}
          {currentJob.status && (
            <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 animate-in fade-in slide-in-from-top-4">
              <div className="flex items-center space-x-3 mb-4">
                {getStatusIcon()}
                <h2 className="text-xl font-semibold text-white">
                  {t('drafting.statusTitle', 'Generation Status')}
                </h2>
              </div>
              <p className="text-gray-300 mb-4">{getStatusText()}</p>
              
              {currentJob.error && (
                <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-4 mb-4">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                    <span className="text-red-300">{currentJob.error}</span>
                  </div>
                </div>
              )}
              
              {(currentJob.status === 'PENDING' || currentJob.status === 'PROCESSING') && (
                <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden">
                  <div className="bg-primary-500 h-2 rounded-full animate-progress" style={{ width: '100%' }}></div>
                </div>
              )}
            </div>
          )}

          {/* Result Display */}
          {currentJob.result && (
            <div ref={resultRef} className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 shadow-2xl animate-in fade-in slide-in-from-bottom-4">
              <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
                <div className="flex items-center space-x-3">
                  <Sparkles className="h-6 w-6 text-secondary-400" />
                  <h2 className="text-xl font-semibold text-white">{t('drafting.resultTitle', 'Generated Draft')}</h2>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={handleCopyResult}
                    className="inline-flex items-center px-3 py-2 border border-glass-edge rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/5 transition duration-200"
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    {t('general.copy', 'Copy')}
                  </button>
                  <button
                    onClick={handleDownloadResult}
                    className="inline-flex items-center px-3 py-2 border border-glass-edge rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/5 transition duration-200"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    {t('general.download', 'Download')}
                  </button>
                  <button
                    onClick={handleNewDraft}
                    className="inline-flex items-center px-3 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm transition duration-200 shadow-lg"
                  >
                    <PenTool className="h-4 w-4 mr-2" />
                    {t('drafting.newDraft', 'New Draft')}
                  </button>
                </div>
              </div>
              
              <div className="bg-black/80 rounded-xl p-6 border border-white/10 overflow-x-auto">
                <pre className="whitespace-pre-wrap text-gray-300 font-mono text-sm leading-relaxed">
                  {currentJob.result}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar - History */}
        <div className="lg:col-span-1">
          <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge p-6 sticky top-8">
            <h3 className="text-lg font-semibold text-white mb-4">{t('drafting.historyTitle', 'Recent Drafts')}</h3>
            
            {jobHistory.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="mx-auto h-12 w-12 text-gray-600 mb-4 opacity-50" />
                <p className="text-gray-500 text-sm">{t('drafting.noHistory', 'No drafts generated yet')}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {jobHistory.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => loadHistoryItem(item)}
                    className="w-full text-left p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 transition duration-200 group"
                  >
                    <p className="text-gray-300 text-sm font-medium mb-1 line-clamp-2 group-hover:text-white">
                      {item.context.substring(0, 100)}...
                    </p>
                    <p className="text-gray-500 text-xs">
                      {item.timestamp.toLocaleDateString()} {item.timestamp.toLocaleTimeString()}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;