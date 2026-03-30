// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V8.5 (FIXED CONTEXT ERRORS)

import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { PenTool } from 'lucide-react';
import { motion } from 'framer-motion';

import { TemplateType, DraftingJobState, NotificationState } from '../drafting/types';
import { ConfigPanel } from '../drafting/components/ConfigPanel';
import { ResultPanel } from '../drafting/components/ResultPanel';
import { constructSmartPrompt } from '../drafting/utils/promptConstructor';

const lawyerGradeStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--border-main); border-radius: 10px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--primary-start); }
`;

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth(); // workspace removed
  
  const [context, setContext] = useState(() => localStorage.getItem('drafting_context') || '');
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<NotificationState | null>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  
  const [currentJob, setCurrentJob] = useState<DraftingJobState>(() => {
    const saved = localStorage.getItem('drafting_job');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.status === 'PROCESSING')
          return parsed.result ? { ...parsed, status: 'COMPLETED' } : { ...parsed, status: 'FAILED', error: 'Interrupted' };
        return parsed;
      } catch {
        return { status: null, result: null, error: null };
      }
    }
    return { status: null, result: null, error: null };
  });

  const isPro = useMemo(() => 
    (user as any)?.subscription_tier === 'PRO' || (user as any)?.plan_tier === 'GROWTH' || (user as any)?.plan_tier === 'ENTERPRISE' || user?.role === 'ADMIN', 
    [user]
  );

  // Fetch Cases - removed workspace argument
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await apiService.getCases(); // Expected 0 arguments
        setCases(data);
      } catch (err) {
        console.error("Failed to fetch cases", err);
      }
    };
    fetchCases();
  }, []);

  useEffect(() => {
    localStorage.setItem('drafting_context', context);
  }, [context]);

  useEffect(() => {
    localStorage.setItem('drafting_job', JSON.stringify(currentJob));
  }, [currentJob]);

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setNotification(null);
    let acc = '';
    try {
      const stream = await apiService.draftLegalDocumentStream({
        user_prompt: constructSmartPrompt(context.trim(), selectedTemplate, t),
        document_type: isPro ? selectedTemplate : 'generic',
        case_id: selectedCaseId || undefined
      });
      
      for await (const chunk of stream) {
        acc += chunk;
        setCurrentJob(prev => ({ ...prev, result: acc }));
      }
      
      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));
    } catch (e: any) {
      setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: e.message || t('common.error') }));
      setNotification({ msg: t('drafting.statusFailed'), type: 'error' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveToArchive = async () => {
    if (!currentJob.result) return;
    setSaving(true);
    try {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const fileName = `draft-${selectedTemplate}-${Date.now()}.txt`;
      await apiService.uploadArchiveItem(new File([blob], fileName), fileName, 'DRAFT', selectedCaseId || undefined);
      setNotification({ msg: t('drafting.savedToArchive'), type: 'success' });
    } catch (err) {
      setNotification({ msg: t('drafting.saveFailed'), type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const clearJob = () => {
    if (currentJob.result && !window.confirm(t('drafting.confirmClear'))) return;
    setCurrentJob({ status: null, result: null, error: null });
    setContext('');
  };

  const retry = () => runDraftingStream();

  return (
    <motion.div className="w-full min-h-screen pb-12 bg-canvas" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-8 flex flex-col h-full">
        <style>{lawyerGradeStyles}</style>

        <div className="flex items-center gap-4 mb-8 flex-shrink-0">
          <div className="w-12 h-12 rounded-2xl bg-primary-start/10 flex items-center justify-center text-primary-start shadow-sm">
            <PenTool size={24} />
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-text-primary tracking-tighter leading-none">
            {t('drafting.title')}
          </h1>
        </div>

        <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 flex-1 lg:h-[750px] min-h-0 pointer-events-auto">
          <div className="h-full overflow-y-auto custom-scrollbar">
            <ConfigPanel
              t={t}
              isPro={isPro}
              cases={cases}
              selectedCaseId={selectedCaseId}
              onSelectCase={setSelectedCaseId}
              selectedTemplate={selectedTemplate}
              context={context}
              isSubmitting={isSubmitting}
              onSelectTemplate={(val: string) => setSelectedTemplate(val as TemplateType)}
              onChangeContext={setContext}
              onSubmit={runDraftingStream}
            />
          </div>

          <div className="h-full overflow-y-auto custom-scrollbar">
            <ResultPanel
              t={t}
              currentJob={currentJob}
              saving={saving}
              notification={notification}
              onSave={handleSaveToArchive}
              onSaveToCase={async () => {}}
              onRetry={retry}
              onClear={clearJob}
              selectedCaseId={selectedCaseId}
              saveModalOpen={saveModalOpen}
              setSaveModalOpen={setSaveModalOpen}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default DraftingPage;