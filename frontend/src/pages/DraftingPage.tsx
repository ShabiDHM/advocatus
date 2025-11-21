// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - MOBILE OPTIMIZATION & LOCALIZATION
// 1. LAYOUT: Responsive grid (col-1 mobile, col-2 desktop).
// 2. HEIGHTS: Enforced min-heights for input/output areas on mobile.
// 3. TYPOGRAPHY: Scaled titles for better fit.
// 4. LOCALIZATION: Now using 't(drafting.status...)' instead of raw uppercase strings.

import React, { useState, useEffect, useCallback, useRef } from 'react'; 
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { CreateDraftingJobRequest } from '../data/types'; 
import moment from 'moment';
import { motion } from 'framer-motion';

const DownloadIcon = (props: React.SVGProps<SVGSVGElement>) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
);

type JobStatus = 'IDLE' | 'INITIATED' | 'POLLING' | 'SUCCESS' | 'FAILURE';

interface JobState { 
  id: string | null; 
  status: JobStatus | string;
  resultText: string; 
  error: string | null; 
  startTime: number | null;
}

const POLL_INTERVAL_MS = 3000;

export const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const [context, setContext] = useState<string>('');
  const [job, setJob] = useState<JobState>({ 
    id: null, 
    status: 'IDLE', 
    resultText: '', 
    error: null, 
    startTime: null,
  });

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);


  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);


  const startPolling = useCallback((jobId: string) => {
    stopPolling();

    const interval = setInterval(async () => {
      try {
        const statusResponse = await apiService.getDraftingJobStatus(jobId);
        const backendStatus = statusResponse.status;

        if (backendStatus === 'SUCCESS') {
          stopPolling();
          const resultResponse = await apiService.getDraftingJobResult(jobId);
          setJob(prev => ({
            ...prev,
            status: 'SUCCESS',
            resultText: resultResponse.result_text || t('drafting.noResult'),
            error: null,
          }));
        } else if (backendStatus === 'FAILURE') {
          stopPolling();
          setJob(prev => ({
            ...prev,
            status: 'FAILURE',
            resultText: '',
            error: statusResponse.result_summary || t('drafting.unknownError'), 
          }));
        } else {
          setJob(prev => ({ ...prev, status: 'POLLING' }));
        }
        
      } catch (error) {
        stopPolling();
        console.error("Polling or result fetch failed:", error);
        setJob(prev => ({
          ...prev,
          status: 'FAILURE',
          resultText: '',
          error: t('drafting.apiPollingFailure'), 
        }));
      }
    }, POLL_INTERVAL_MS);

    pollingIntervalRef.current = interval;
    setJob(prev => ({ ...prev, status: 'POLLING' }));
  }, [stopPolling, t]);


  const handleGenerateDocument = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    stopPolling(); 

    if (!context.trim()) {
      alert(t('drafting.alertNoContext'));
      return;
    }

    setJob({ id: null, status: 'INITIATED', resultText: '', error: null, startTime: Date.now() });

    try {
      const request: CreateDraftingJobRequest = { context };
      const jobResponse = await apiService.initiateDraftingJob(request);
      
      if (!jobResponse.job_id) {
          throw new Error("API response missing 'job_id' field.");
      }
      
      setJob(prev => ({ ...prev, id: jobResponse.job_id, status: 'POLLING' }));
      startPolling(jobResponse.job_id);

    } catch (error) {
      console.error("Initiate Drafting Job Failed:", error);
      setJob({ 
        id: null, 
        status: 'FAILURE', 
        resultText: '', 
        error: t('drafting.jobInitiateFailure'), 
        startTime: null,
      });
    }
  }, [context, startPolling, stopPolling, t]);


  const timeElapsed = job.startTime ? moment.duration(Date.now() - job.startTime).asSeconds().toFixed(0) : 0;
  const isDocumentReady = job.status === 'SUCCESS' && !!job.resultText;
  
  const handleExportDocx = () => {
    if (!job.resultText) {
        alert(t('drafting.alertNoTextToExport'));
        return;
    }
    const file = new Blob([job.resultText], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    const fileURL = URL.createObjectURL(file);
    const fileName = `Drafted_Document_${moment().format('YYYYMMDD_HHmmss')}.docx`;
    const link = document.createElement('a');
    link.href = fileURL;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(fileURL);
  };
  
  const statusColorClasses = (status: JobStatus | string) => {
    switch (status) {
      case 'SUCCESS': return 'bg-success-start/20 text-success-start';
      case 'POLLING':
      case 'INITIATED':
      case 'PENDING':
      case 'STARTED':
      case 'PROGRESS':
        return 'bg-accent-start/20 text-accent-start animate-pulse-slow';
      case 'FAILURE': return 'bg-red-500/20 text-red-500';
      default: return 'bg-background-light/20 text-text-secondary';
    }
  };


  return (
    <motion.div 
        className="drafting-container flex flex-col min-h-[calc(100vh-100px)]"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
    >
      <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary mb-4 sm:mb-6">{t('drafting.pageTitle')}</h1>

      <div className="compact-workspace flex-grow grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* INPUT SECTION */}
        <div className="compact-input-section flex flex-col min-h-[50vh] lg:min-h-0">
          <motion.form 
            onSubmit={handleGenerateDocument} 
            className="compact-input-panel flex flex-col flex-1 bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl shadow-xl min-h-0"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div className="compact-panel-header p-4 border-b border-glass-edge/50">
              <h2 className="text-lg sm:text-xl font-bold text-text-primary">{t('drafting.inputPanelTitle')}</h2>
              <p className="text-xs sm:text-sm text-text-secondary/70">{t('drafting.inputPanelSubtitle')}</p>
            </div>
            <div className="compact-panel-body flex-1 min-h-0 p-3 sm:p-4">
              <textarea 
                className="compact-drafting-textarea w-full h-full bg-background-dark/80 text-text-primary p-3 sm:p-4 rounded-xl resize-none focus:ring-primary-start focus:border-primary-start border border-glass-edge text-sm sm:text-base"
                placeholder={t('drafting.inputPlaceholder')}
                value={context}
                onChange={(e) => setContext(e.target.value)}
                style={{ minHeight: '200px' }}
              />
            </div>
            <div className="compact-action-bar p-3 sm:p-4 border-t border-glass-edge/50">
              <motion.button 
                type="submit"
                className="w-full flex justify-center py-3 px-4 rounded-xl shadow-lg glow-primary text-white font-medium 
                           bg-gradient-to-r from-primary-start to-primary-end disabled:opacity-50 transition-opacity"
                disabled={job.status === 'POLLING' || !context.trim()}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
              >
                {job.status === 'POLLING' ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {t('drafting.generatingStatus')} ({timeElapsed}s)
                  </span>
                ) : t('drafting.generateButton')}
              </motion.button>
            </div>
          </motion.form>
        </div>

        {/* OUTPUT SECTION */}
        <div className="compact-output-section flex flex-col min-h-[50vh] lg:min-h-0">
          <div className="panel compact-output-panel flex flex-col flex-1 bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl shadow-xl min-h-0">
            <div className="panel-header flex-none p-4 border-b border-glass-edge/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-0">
              <h2 className="text-lg sm:text-xl font-bold text-text-primary">{t('drafting.outputPanelTitle')}</h2>
              <div className="flex items-center self-end sm:self-auto">
                  {isDocumentReady && (
                    <motion.button onClick={handleExportDocx} 
                        className="w-8 h-8 flex items-center justify-center rounded-xl transition-all duration-300 shadow-lg glow-primary
                                     bg-gradient-to-r from-primary-start to-primary-end mr-2" 
                        whileHover={{ scale: 1.05 }}
                        title={t('drafting.exportButton')}
                    >
                        <DownloadIcon className="w-4 h-4 text-white" />
                    </motion.button>
                  )}
                  <div className={`text-xs sm:text-sm font-semibold px-3 py-1 rounded-full ${statusColorClasses(job.status)}`}>
                      {/* PHOENIX FIX: Translating Job Status */}
                      {t(`drafting.status.${job.status}`, { defaultValue: job.status.toUpperCase() })}
                  </div>
              </div>
            </div>
            
            <div className="panel-body compact-document-container flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 custom-scrollbar">
              {job.status === 'POLLING' && (
                <div className="h-full flex flex-col items-center justify-center text-center">
                  <svg className="animate-spin h-10 w-10 text-primary-start glow-primary mb-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <h4 className="text-lg font-semibold text-text-primary">{t('drafting.loadingTitle')}</h4>
                  <p className="text-sm text-text-secondary/70">{t('drafting.loadingSubtitle')}</p>
                </div>
              )}
              
              {job.status === 'FAILURE' && (
                <div className="h-full flex flex-col items-center justify-center text-center text-red-500">
                  <div className="text-4xl mb-4">❌</div>
                  <h4 className="text-lg font-semibold">{t('drafting.jobFailedTitle')}</h4> 
                  <p className="text-sm">{job.error}</p>
                </div>
              )}

              {isDocumentReady && (
                <div className="document-view space-y-4 h-full flex flex-col">
                  <div className="text-center p-3 border border-accent-start/30 bg-accent-start/10 rounded-xl flex-shrink-0">
                    <h3 className="text-lg font-bold text-accent-start">{t('drafting.readyTitle')}</h3>
                    <p className="text-xs text-text-secondary/70">{t('drafting.readySubtitle')}</p>
                  </div>
                  <div className="bg-background-dark/80 text-text-primary p-4 sm:p-6 rounded-xl shadow-inner border border-glass-edge overflow-y-auto flex-grow">
                    <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm">
                      {job.resultText}
                    </pre>
                  </div>
                </div>
              )}
              
              {job.status === 'IDLE' && (
                <div className="h-full flex items-center justify-center text-center">
                  <div className="text-text-secondary">
                    <div className="text-5xl sm:text-6xl mb-4 opacity-50">📝</div>
                    <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2">{t('drafting.emptyTitle')}</h3>
                    <p className="text-sm text-text-secondary/70">{t('drafting.emptySubtitle')}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default DraftingPage;