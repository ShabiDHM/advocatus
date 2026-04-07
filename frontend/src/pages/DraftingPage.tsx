// FILE: src/pages/ DraftingPage.tsx
// PHOENIX PROTOCOL – TYPESCRIPT COMPLIANCE & PERSISTENCE v12.5

import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
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

const buildKosovoSystemPrompt = (template: string, basePrompt: string): string => {
  let statute = "";
  let structuralBlueprint = "";
  
  switch (true) {
    case ['padi', 'pergjigje', 'kunderpadi', 'ankese', 'prapësim'].includes(template):
      statute = "Ligjin për Procedurën Kontestimore (Nr. 03/L-006) të Republikës së Kosovës"; 
      structuralBlueprint = `GJYKATËS THEMELORE NË [QYTETI]\nDepartamenti: [DEPARTAMENTI]\nPaditësi: [EMRI], E Paditura: [EMRI]...`;
      break;
    case ['employment_contract', 'termination_notice'].includes(template):
      statute = "Ligjin e Punës (Nr. 03/L-212) të Republikës së Kosovës"; 
      structuralBlueprint = `KONTRATË PUNE: Ndërmjet Punëdhënësit [EMRI] dhe Punëmarrësit [EMRI]...`;
      break;
    default:
      statute = "Kornizën Ligjore të Republikës së Kosovës";
      structuralBlueprint = "Përdor formatin standard ligjor të Kosovës.";
  }

  return `[SYSTEM DIRECTIVE] ROLI YT: Avokat në Kosovë. BAZA LIGJORE: ${statute}. GJUHA: Shqipe standarde. MOS SHPIK EMRA, përdor [PLACEHOLDERS].\n\nSTRUKTURA:\n${structuralBlueprint}\n\nKËRKESA:\n${basePrompt}`;
};

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  
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
        if (parsed.status === 'PROCESSING') return { ...parsed, status: 'FAILED' };
        return parsed;
      } catch { return { status: null, result: null, error: null }; }
    }
    return { status: null, result: null, error: null };
  });

  const isPro = useMemo(() => 
    (user as any)?.subscription_tier === 'PRO' || (user as any)?.plan_tier === 'GROWTH' || user?.role === 'ADMIN', 
    [user]
  );

  useEffect(() => {
    apiService.getCases().then(setCases).catch(console.error);
  }, []);

  useEffect(() => { localStorage.setItem('drafting_context', context); }, [context]);
  useEffect(() => { localStorage.setItem('drafting_job', JSON.stringify(currentJob)); }, [currentJob]);

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setNotification(null);
    let acc = '';
    
    try {
      const basePrompt = constructSmartPrompt(context.trim(), selectedTemplate);
      const securePrompt = buildKosovoSystemPrompt(selectedTemplate, basePrompt);
      const stream = await apiService.draftLegalDocumentStream({
        user_prompt: securePrompt,
        document_type: isPro ? selectedTemplate : 'generic',
        case_id: selectedCaseId || undefined
      });
      
      for await (const chunk of stream) {
        acc += chunk;
        setCurrentJob(prev => ({ ...prev, result: acc }));
      }
      setCurrentJob(prev => ({ ...prev, status: 'COMPLETED' }));
    } catch (e: any) {
      setCurrentJob(prev => ({ ...prev, status: 'FAILED', error: e.message }));
      setNotification({ msg: t('drafting.statusFailed'), type: 'error' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Generic Save to Archive (Required by ResultPanelProps)
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

  // Modal-driven Save with Custom Title
  const handleSaveWithTitle = async (title: string) => {
    if (!currentJob.result) return;
    setSaving(true);
    try {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const fileName = `${title.replace(/\s+/g, '_')}.txt`;
      const file = new File([blob], fileName, { type: 'text/plain' });
      await apiService.uploadArchiveItem(file, title, 'DRAFT', selectedCaseId || undefined);
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

  return (
    <motion.div className="w-full min-h-screen pb-12 bg-canvas" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-24 pb-8 flex flex-col h-full">
        <style>{lawyerGradeStyles}</style>

        <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 mt-4 flex-1 lg:h-[750px] min-h-0">
          <div className="h-full overflow-y-auto custom-scrollbar">
            <ConfigPanel
              t={t}
              isPro={isPro}
              cases={cases}
              selectedCaseId={selectedCaseId || undefined}
              onSelectCase={(id) => setSelectedCaseId(id || '')}
              selectedTemplate={selectedTemplate}
              context={context}
              isSubmitting={isSubmitting}
              onSelectTemplate={(val) => setSelectedTemplate(val as TemplateType)}
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
              onSaveToCase={handleSaveWithTitle}
              onRetry={runDraftingStream}
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