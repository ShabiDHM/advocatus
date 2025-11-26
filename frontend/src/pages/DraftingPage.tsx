// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE (CLEANED)
// 1. REMOVED: Unused import (CheckCircle).
// 2. FUNCTIONAL: Legal Drafting with AI.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { Case, CreateDraftingJobRequest, DraftingJobStatus } from '../data/types';
import { FileText, Loader2, Download, RefreshCw, AlertCircle } from 'lucide-react';

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>('');
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeJob, setActiveJob] = useState<DraftingJobStatus | null>(null);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      const data = await apiService.getCases();
      setCases(data);
    } catch (error) {
      console.error("Failed to load cases", error);
    }
  };

  const handleDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt) return;
    setIsSubmitting(true);
    setResult(null);
    
    try {
      const requestData: CreateDraftingJobRequest = {
        user_prompt: prompt,
        case_id: selectedCase || undefined,
        context: selectedCase ? `Case Context ID: ${selectedCase}` : ""
      };

      const jobStatus = await apiService.initiateDraftingJob(requestData);
      setActiveJob(jobStatus);
      pollJobStatus(jobStatus.job_id);
    } catch (error) {
      console.error("Drafting failed", error);
      alert(t('error.generic'));
      setIsSubmitting(false);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await apiService.getDraftingJobStatus(jobId);
        setActiveJob(status);

        if (status.status === 'COMPLETED') {
          clearInterval(interval);
          setIsSubmitting(false);
          const resultData = await apiService.getDraftingJobResult(jobId);
          setResult(resultData.document_text || resultData.result_text || "");
        } else if (status.status === 'FAILED') {
          clearInterval(interval);
          setIsSubmitting(false);
        }
      } catch (error) {
        console.error("Polling error", error);
        clearInterval(interval);
        setIsSubmitting(false);
      }
    }, 3000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">{t('drafting.title', 'Draftimi Inteligjent')}</h1>
        <p className="text-text-secondary">{t('drafting.subtitle', 'Krijoni dokumente ligjore automatikisht.')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Form */}
        <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge h-fit">
          <form onSubmit={handleDraft} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">{t('drafting.selectCase', 'Zgjidhni Rastin (Opsionale)')}</label>
              <select 
                value={selectedCase} 
                onChange={(e) => setSelectedCase(e.target.value)}
                className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-2.5 text-white focus:ring-1 focus:ring-primary-start outline-none"
              >
                <option value="">{t('drafting.noCase', 'Pa Rast (Draftim i Përgjithshëm)')}</option>
                {cases.map(c => (
                  <option key={c.id} value={c.id}>{c.case_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">{t('drafting.promptLabel', 'Udhëzimet për Draftin')}</label>
              <textarea 
                required
                rows={6}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={t('drafting.promptPlaceholder', 'Psh: Krijo një kontratë qiraje për një apartament në Prishtinë...')}
                className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-3 text-white focus:ring-1 focus:ring-primary-start outline-none custom-scrollbar"
              />
            </div>

            <button 
              type="submit" 
              disabled={isSubmitting}
              className="w-full flex justify-center items-center py-3 rounded-xl bg-gradient-to-r from-accent-start to-accent-end text-white font-bold shadow-lg glow-accent hover:scale-[1.02] transition-transform disabled:opacity-50 disabled:hover:scale-100"
            >
              {isSubmitting ? <Loader2 className="animate-spin mr-2" /> : <FileText className="mr-2" />}
              {isSubmitting ? t('drafting.generating', 'Duke Gjeneruar...') : t('drafting.generateButton', 'Gjenero Dokumentin')}
            </button>
          </form>
        </div>

        {/* Result Area */}
        <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge min-h-[500px] flex flex-col">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FileText className="text-primary-start" /> {t('drafting.resultTitle', 'Rezultati')}
          </h3>

          {activeJob && activeJob.status === 'PROCESSING' && (
            <div className="flex-1 flex flex-col items-center justify-center text-text-secondary space-y-4">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-primary-start/30 border-t-primary-start rounded-full animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 text-primary-start animate-pulse" />
                </div>
              </div>
              <p className="animate-pulse">{t('drafting.processingMessage', 'AI po shkruan dokumentin...')}</p>
            </div>
          )}

          {activeJob && activeJob.status === 'FAILED' && (
            <div className="flex-1 flex flex-col items-center justify-center text-red-400 space-y-4">
              <AlertCircle className="w-16 h-16" />
              <p>{t('drafting.failedMessage', 'Gjenerimi dështoi. Provoni përsëri.')}</p>
              <p className="text-sm text-red-400/60">{activeJob.error}</p>
            </div>
          )}

          {result && (
            <div className="flex-1 flex flex-col">
              <div className="flex-1 bg-white text-black p-8 rounded-lg shadow-inner overflow-y-auto custom-scrollbar mb-4 font-serif whitespace-pre-wrap leading-relaxed">
                {result}
              </div>
              <div className="flex justify-end">
                <button className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                  <Download size={18} /> {t('general.download', 'Shkarko PDF')}
                </button>
              </div>
            </div>
          )}

          {!activeJob && !result && (
            <div className="flex-1 flex flex-col items-center justify-center text-text-secondary opacity-50">
              <FileText className="w-16 h-16 mb-4" />
              <p>{t('drafting.emptyState', 'Rezultati do të shfaqet këtu.')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DraftingPage;