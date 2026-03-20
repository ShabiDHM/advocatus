// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V6.0 (LOGIC PRESERVED + WORLD CLASS UI)
// 1. FIXED: Title visibility across all themes using 'text-text-primary'.
// 2. FIXED: Page layout spacing and alignment matches Case View perfectly.
// 3. RETAINED: 100% of the original drafting logic, HTTP streaming, and CSS strings.

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Case } from '../data/types';
import { PenTool } from 'lucide-react';
import { motion } from 'framer-motion';

// Import drafting modules
import { TemplateType, DraftingJobState, NotificationState } from '../drafting/types';
import { ConfigPanel } from '../drafting/components/ConfigPanel';
import { ResultPanel } from '../drafting/components/ResultPanel';
import { constructSmartPrompt } from '../drafting/utils/promptConstructor';

const lawyerGradeStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Tinos:ital,wght@0,400;0,700;1,400;1,700&display=swap');

  .legal-document {
    font-family: 'Tinos', 'Times New Roman', serif;
    background: white;
    color: black;
    padding: 2.5cm 2cm;
    line-height: 1.5;
    font-size: 12pt;
    text-align: justify;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    margin: 0 auto;
    width: 21cm;
    max-width: 100%;
    box-sizing: border-box;
    min-height: 29.7cm;
    position: relative;
  }

  @media print {
    @page { margin: 2cm; size: A4; }
    body * { visibility: hidden; }
    .legal-document, .legal-document * { visibility: visible; }
    .legal-document {
      position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0;
      box-shadow: none; border: none;
    }
  }

  .legal-content h1 { text-align: center; text-transform: uppercase; font-weight: 700; font-size: 14pt; margin-bottom: 24pt; border-bottom: 2px solid #000; padding-bottom: 4pt; }
  .legal-content h2 { text-transform: uppercase; font-weight: 700; font-size: 12pt; margin-top: 18pt; margin-bottom: 12pt; text-align: center; }
  .legal-content h3 { font-weight: 700; font-size: 12pt; margin-top: 12pt; margin-bottom: 6pt; text-transform: uppercase; text-align: left; }
  .legal-content p { margin-bottom: 12pt; }
  .legal-content strong, .legal-content b { font-weight: 700 !important; }
  .legal-content blockquote { border: none; margin: 3cm 0 0 50%; padding: 0; text-align: center; font-style: normal; font-weight: 700; }
`;

const DraftingPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [context, setContext] = useState(() => localStorage.getItem('drafting_context') || '');
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('generic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<NotificationState | null>(null);
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

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);

  useEffect(() => {
    localStorage.setItem('drafting_context', context);
  }, [context]);

  useEffect(() => {
    localStorage.setItem('drafting_job', JSON.stringify(currentJob));
  }, [currentJob]);

  useEffect(() => {
    if (isPro) apiService.getCases().then(res => setCases(res || [])).catch(console.error);
  }, [isPro]);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const handleAutofillCase = useCallback(
    (caseId: string) => {
      const c = cases.find(item => item.id === caseId);
      if (c) {
        setContext(prev => {
          const caseBlock = `[[TË_DHËNAT_E_RASTIT]]\n${t('drafting.caseRef', 'REFERENCA E RASTIT')}: ${
            c.title || c.case_number
          }\n${t('drafting.clientLabel', 'KLIENTI')}: ${c.client?.name || 'N/A'}\n${t('drafting.factsLabel', 'FAKTET')}: ${
            c.description || '-'
          }\n[[FUND_TËDHËNAVE]]\n\n`;
          if (prev.includes('[[TË_DHËNAT_E_RASTIT]]'))
            return prev.replace(/\[\[TË_DHËNAT_E_RASTIT\]\][\s\S]*?\[\[FUND_TËDHËNAVE\]\]\s*/, caseBlock);
          return caseBlock + prev;
        });
      }
    },
    [cases, t]
  );

  const runDraftingStream = async () => {
    if (!context.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCurrentJob({ status: 'PROCESSING', result: '', error: null });
    setNotification(null);
    let acc = '';
    try {
      let finalPromptText = context.trim();
      if (isPro && selectedCaseId) {
        const selectedCase = cases.find(c => c.id === selectedCaseId);
        if (selectedCase && !finalPromptText.includes('[[TË_DHËNAT_E_RASTIT]]')) {
          const hiddenContext = `\n\n[DATABASE DATA]\n${t('drafting.caseRef')}: ${
            selectedCase.title || selectedCase.case_number
          }\n${t('drafting.clientLabel')}: ${selectedCase.client?.name || 'N/A'}\n${t('drafting.factsLabel')}: ${
            selectedCase.description || 'N/A'
          }\n[END DATABASE DATA]\n`;
          finalPromptText = hiddenContext + finalPromptText;
        }
      }
      const stream = apiService.draftLegalDocumentStream({
        user_prompt: constructSmartPrompt(finalPromptText, selectedTemplate, t),
        document_type: isPro ? selectedTemplate : 'generic',
        case_id: isPro && selectedCaseId ? selectedCaseId : undefined,
        use_library: isPro && !!selectedCaseId,
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

  const handleSaveToCase = async (title: string) => {
    if (!currentJob.result || !selectedCaseId) return;
    setSaving(true);
    try {
      const blob = new Blob([currentJob.result], { type: 'text/plain;charset=utf-8' });
      const fileName = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${Date.now()}.txt`;
      await apiService.uploadArchiveItem(new File([blob], fileName), fileName, 'DRAFT', selectedCaseId);
      setNotification({ msg: 'Drafti u ruajt me sukses në lëndë', type: 'success' });
      setSaveModalOpen(false);
    } catch (err) {
      setNotification({ msg: 'Ruajtja dështoi', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const clearJob = () => {
    if (currentJob.result && !window.confirm(t('drafting.confirmClear'))) return;
    setCurrentJob({ status: null, result: null, error: null });
    setContext('');
  };

  const retry = () => {
    runDraftingStream();
  };

  return (
    <motion.div className="w-full min-h-screen pb-12" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-6 sm:px-8 pt-24 pb-8 flex flex-col h-full">
        <style>{lawyerGradeStyles}</style>

        {/* Page Header: Executive Alignment (Matches Case View) */}
        <div className="flex items-center gap-4 mb-8 ml-2 flex-shrink-0">
            <div className="w-12 h-12 rounded-2xl bg-primary-start/10 flex items-center justify-center text-primary-start shadow-lawyer-light">
                <PenTool size={24} />
            </div>
            <h1 className="text-4xl font-black text-text-primary tracking-tighter leading-none">
              {t('drafting.title')}
            </h1>
        </div>

        {/* Main Grid: Symmetrical with Case View */}
        <div className="flex flex-col lg:grid lg:grid-cols-2 gap-8 flex-1 lg:h-[750px] min-h-0">
          <ConfigPanel
            t={t}
            isPro={isPro}
            cases={cases}
            selectedCaseId={selectedCaseId}
            selectedTemplate={selectedTemplate}
            context={context}
            isSubmitting={isSubmitting}
            onSelectCase={(id: string) => {
              setSelectedCaseId(id);
              handleAutofillCase(id);
            }}
            onSelectTemplate={(val: string) => setSelectedTemplate(val as TemplateType)}
            onChangeContext={setContext}
            onSubmit={runDraftingStream}
          />
          <ResultPanel
            t={t}
            currentJob={currentJob}
            saving={saving}
            notification={notification}
            onSave={handleSaveToArchive}
            onSaveToCase={handleSaveToCase}
            onRetry={retry}
            onClear={clearJob}
            selectedCaseId={selectedCaseId}
            saveModalOpen={saveModalOpen}
            setSaveModalOpen={setSaveModalOpen}
          />
        </div>
      </div>
    </motion.div>
  );
};

export default DraftingPage;