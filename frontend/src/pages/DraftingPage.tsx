// FILE: src/pages/DraftingPage.tsx
// PHOENIX PROTOCOL - DRAFTING PAGE V7.2 (100% TEMPLATE-SPECIFIC CUSTOM PROMPT MATRIX)

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

import { TemplateType, DraftingJobState, NotificationState } from '../drafting/types';
import { ConfigPanel } from '../drafting/components/ConfigPanel';
import { ResultPanel } from '../drafting/components/ResultPanel';
import { constructSmartPrompt } from '../drafting/utils/promptConstructor';

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
  useAuth();
  
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

  const isPro = true;

  useEffect(() => {
    apiService.getCases().then(setCases).catch(console.error);
  }, []);

  // TEMPLATE & ROLE MATRIX AUTO-PROMPT GENERATOR
  useEffect(() => {
    if (!selectedCaseId || cases.length === 0) return;
    const activeCase = cases.find((c: any) => String(c.id) === String(selectedCaseId));
    if (!activeCase) return;

    const pos = (activeCase.client_position || 'DEFENDANT').toUpperCase();
    const caseTitle = activeCase.title || activeCase.case_name || 'Lënda';
    const caseNum = activeCase.case_number ? `(Nr. ${activeCase.case_number})` : '';
    const clientName = activeCase.client?.name || 'Klienti ynë';
    const opposingParty = activeCase.opposing_party?.name || 'Pala Kundërshtare';

    let generatedPrompt = '';

    switch (selectedTemplate) {
      case 'prapësim':
        generatedPrompt = `Në emër të të paditurit (${clientName}) në lëndën "${caseTitle}" ${caseNum} kundër paditësit (${opposingParty}):\n\n1. Paraqes këtë PRAPËSIM me të cilin kundërshtoj në tërësi kërkesëpadinë e paditësit si të pabazuar në ligj dhe në prova.\n2. Shfrytëzoj lëshimet procedurale, mungesën e autorizimit dhe parashkrimin e afateve.\n3. Kërkoj nga Gjykata hedhjen poshtë ose refuzimin e padisë.`;
        break;
      case 'padi':
        generatedPrompt = `Në emër të paditësit (${clientName}) në lëndën "${caseTitle}" ${caseNum} kundër të paditurit (${opposingParty}):\n\n1. Paraqes këtë KËRKESËPADI për vërtetimin e detyrimit dhe kompensimin e dëmit të shkaktuar.\n2. Kërkoj detyrimin e të paditurit për përmbushjen e të gjitha detyrimeve së bashku me kamatën vonesore.\n3. Kërkoj caktimin e masës së sigurisë për mbrojtjen e kërkesës sonë.`;
        break;
      case 'kunderpadi':
        generatedPrompt = `Në emër të të paditurit/kundërpaditësit (${clientName}) kundër paditësit/të kundërpaditurit (${opposingParty}) në lëndën "${caseTitle}":\n\n1. Paraqes KUNDËRPADI për shkak të shkeljes së detyrimeve reciproke.\n2. Kërkoj kompensimin e dëmit të shkaktuar dhe përmbushjen e detyrimeve ligjore nga pala tjetër.`;
        break;
      case 'ankese':
        generatedPrompt = `Në emër të palës (${clientName}) në lëndën "${caseTitle}" ${caseNum}:\n\n1. Paraqes ANKESË kundër vendimit të Gjykatës për shkak të shkeljeve esenciale të dispozitave të procedurës dhe vërtetimit të gabuar të gjendjes faktike.\n2. Kërkoj nga Gjykata e Shkallës së Dytë ndryshimin apo prishjen e vendimit të ankimuar.`;
        break;
      case 'employment_contract':
        generatedPrompt = `Hartoj KONTRATË PUNE sipas Ligjit të Punës Nr. 03/L-212 ndërmjet Punëdhënësit (${clientName}) dhe Punëmarrësit (${opposingParty}) me kohë të caktuar/pacaktuar, orar të plotë dhe të drejta të garantuara.`;
        break;
      case 'lease_agreement':
        generatedPrompt = `Hartoj KONTRATË QIRAJE sipas LMD-së ndërmjet Qiradhënësit (${clientName}) dhe Qiramarrësit (${opposingParty}) për shfrytëzimin e paluajtshmërisë me afat të përcaktuar dhe depozitë garancie.`;
        break;
      case 'nda':
        generatedPrompt = `Hartoj MARRËVESHJE PËR MOSZBULIM TË INFORMACIONIT CONFIDENTIAL (NDA) midis palëve ${clientName} dhe ${opposingParty} për mbrojtjen e sekretit afarist dhe të dhënave komerciale.`;
        break;
      case 'power_of_attorney':
        generatedPrompt = `Hartoj AUTORIZIM ZYRTAR (Prokurë) me të cilin ${clientName} autorizon avokatin për përfaqësim të plotë para të gjitha gjykatave, zyrave përmbarimore dhe organeve shtetërore në Kosovë.`;
        break;
      default:
        if (pos === 'DEFENDANT') {
          generatedPrompt = `Në emër të të paditurit (${clientName}) në lëndën "${caseTitle}" ${caseNum} kundër paditësit (${opposingParty}):\n\n1. Kundërshtoj në tërësi pretendimet si të pabazuara.\n2. Kërkoj mbrojtje ligjore dhe hedhjen poshtë të kërkesës.`;
        } else if (pos === 'PLAINTIFF') {
          generatedPrompt = `Në emër të paditësit (${clientName}) në lëndën "${caseTitle}" ${caseNum} kundër të paditurit (${opposingParty}):\n\n1. Paraqes këtë shkresë për vërtetimin e detyrimit dhe mbrojtjen e të drejtave tona.`;
        } else {
          generatedPrompt = `Hartoj një shkresë dhe analizë të paanshme ligjore për lëndën "${caseTitle}" ${caseNum} që përfshin palët ${clientName} dhe ${opposingParty}.`;
        }
        break;
    }

    setContext(generatedPrompt);
  }, [selectedCaseId, selectedTemplate, cases]);

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
        document_type: selectedTemplate,
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
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-24 pb-8 flex flex-col h-full bg-canvas">
        <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 sm:gap-8 mt-4 flex-1 lg:h-[730px] min-h-0">
          
          <div className="h-full overflow-y-auto custom-finance-scroll border border-main rounded-2xl bg-surface/30 p-4">
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

          <div className="h-full overflow-y-auto custom-finance-scroll border border-main rounded-2xl bg-surface/30 p-4">
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