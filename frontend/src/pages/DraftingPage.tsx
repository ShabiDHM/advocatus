// FILE: src/pages/DraftingPage.tsx
// ARCHITECTURE: ZERO-HALLUCINATION KOSOVO LEGAL ENGINE & PERSISTENT STATE

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

// ============================================================================
// CORE LEGAL ENGINE: ZERO-HALLUCINATION PROMPT MATRIX
// ============================================================================
const buildKosovoSystemPrompt = (template: string, basePrompt: string): string => {
  let statute = "";
  
  // Map Document Templates directly to strict Kosovo Statutes
  switch (true) {
    case ['padi', 'pergjigje', 'kunderpadi', 'ankese', 'prapësim'].includes(template):
      statute = "Ligjin për Procedurën Kontestimore (Nr. 03/L-006) të Republikës së Kosovës"; 
      break;
    case ['nda', 'mou', 'shareholders', 'sla'].includes(template):
      statute = "Ligjin për Shoqëritë Tregtare (Nr. 06/L-016) dhe Ligjin për Marrëdhëniet e Detyrimeve (Nr. 04/L-077) të Republikës së Kosovës"; 
      break;
    case ['employment_contract', 'termination_notice', 'warning_letter'].includes(template):
      statute = "Ligjin e Punës (Nr. 03/L-212) të Republikës së Kosovës"; 
      break;
    case ['lease_agreement', 'sales_purchase', 'power_of_attorney'].includes(template):
      statute = "Ligjin për Marrëdhëniet e Detyrimeve (Nr. 04/L-077) të Republikës së Kosovës"; 
      break;
    case ['terms_conditions', 'privacy_policy'].includes(template):
      statute = "Ligjin për Mbrojtjen e të Dhënave Personale (Nr. 06/L-082) dhe Ligjin për Mbrojtjen e Konsumatorit (Nr. 06/L-034) të Republikës së Kosovës"; 
      break;
    default:
      statute = "Kornizën e Përgjithshme Ligjore të Republikës së Kosovës";
  }

  return `[SYSTEM DIRECTIVE - STRICT KOSOVO LEGAL ENGINE]
ROLI YT: Ti je një Avokat dhe Ekspert Ligjor i licencuar në Republikën e Kosovës. Detyra jote është të hartosh një dokument ligjor profesional me standardet më të larta juridike.

RREGULLAT E RREPTA (ZERO HALLUCINATION PROTOCOL):
1. BAZA LIGJORE (KOSOVO ONLY): Ky dokument duhet të bazohet EKSKLUZIVISHT në ${statute}. Ndalohet rreptësisht përdorimi apo citimi i ligjeve të shteteve të tjera (p.sh. Shqipëria, SHBA, BE).
2. GJUHA: Përdor vetëm Gjuhën Zyrtare Shqipe (standarde, formale, terminologji juridike e saktë).
3. STRUKTURA PROFESIONALE: 
   - Fillo me një TITULL të qartë, të qendërzuar dhe me shkronja të mëdha.
   - Përfshi identifikimin e saktë të palëve.
   - Përfshi bazën ligjore dhe arsyetimin/dispozitat e qarta.
   - Përfundo dokumentin me hapësirat për nënshkrime (psh. "PËR PALËN A: _________________").
4. PLACEHOLDERS (TË DHËNAT QË MUNGOJNË): Mos shpik të dhëna fiktive ose emra të rremë! Për çdo të dhënë që mungon përdor formatin me kllapa katrore: [EMRI_MBIEMRI], [DATA], [ADRESA], [SHUMA], [NR_LETERNJOFTIMIT], etj.

KONTEKSTI DHE KËRKESA E KLIENTIT:
${basePrompt}`;
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

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await apiService.getCases();
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
      // 1. Generate base prompt
      const basePrompt = constructSmartPrompt(context.trim(), selectedTemplate);
      
      // 2. Wrap base prompt in our strict Kosovo Legal Engine matrix
      const securePrompt = buildKosovoSystemPrompt(selectedTemplate, basePrompt);

      const stream = await apiService.draftLegalDocumentStream({
        user_prompt: securePrompt, // Safely injected with strict parameters
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
            {t('drafting.title', 'Hartimi Ligjor')}
          </h1>
        </div>

        <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 flex-1 lg:h-[750px] min-h-0 pointer-events-auto">
          <div className="h-full overflow-y-auto custom-scrollbar">
            <ConfigPanel
              t={t}
              isPro={isPro}
              cases={cases}
              selectedCaseId={selectedCaseId || undefined}
              onSelectCase={(id: string | undefined) => setSelectedCaseId(id || '')}
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