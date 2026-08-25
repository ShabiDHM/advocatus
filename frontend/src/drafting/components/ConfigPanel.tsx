// FILE: src/drafting/components/ConfigPanel.tsx
// PHOENIX PROTOCOL - CONFIG PANEL V14.1 (SAFE TYPE-CAST DYNAMIC PROPS & ZERO WARNINGS)

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { 
  Send, RefreshCw, ChevronDown, Briefcase, Shield, Swords, 
  Scale, Sparkles, Landmark, Euro, Calendar, FileText, AlertOctagon 
} from 'lucide-react';
import { ConfigPanelProps, TemplateType } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  t,
  selectedTemplate,
  context,
  isSubmitting,
  onSelectTemplate,
  onChangeContext,
  onSubmit,
  cases = [], 
  selectedCaseId, 
  onSelectCase
}) => {
  const placeholder = useMemo(() => getTemplatePlaceholder(selectedTemplate), [selectedTemplate]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Support both MongoDB `_id` and `id`
  const activeCase = useMemo(() => {
    if (!selectedCaseId) return null;
    return cases.find((c: any) => String(c.id || c._id) === String(selectedCaseId));
  }, [cases, selectedCaseId]);

  const clientPosition = (activeCase as any)?.client_position || 'DEFENDANT';

  // Safe dynamic extraction from case payload
  const dynamicCourt = (activeCase as any)?.court || (activeCase as any)?.court_name || (activeCase as any)?.jurisdiction;
  const dynamicValue = (activeCase as any)?.claim_value || (activeCase as any)?.value || (activeCase as any)?.dispute_value;
  const dynamicDeadline = (activeCase as any)?.deadline || (activeCase as any)?.statute_limit;
  const dynamicCaseNum = (activeCase as any)?.case_number || (activeCase as any)?.reference_number;

  // AUTO-SELECT TEMPLATE ONLY WHEN UNINITIALIZED
  useEffect(() => {
    if (!activeCase) return;
    if (selectedTemplate && selectedTemplate !== 'generic') return;

    const pos = (activeCase as any)?.client_position || 'DEFENDANT';
    if (pos === 'DEFENDANT') {
      onSelectTemplate('prapësim' as TemplateType);
    } else if (pos === 'PLAINTIFF') {
      onSelectTemplate('padi' as TemplateType);
    }
  }, [selectedCaseId, activeCase, selectedTemplate, onSelectTemplate]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const templateGroups = [
    { 
      label: t('drafting.groupLitigation', 'Procedura Kontestimore'), 
      options: ['padi', 'pergjigje', 'kunderpadi', 'ankese', 'prapësim'] 
    },
    { 
      label: t('drafting.groupCriminal', 'E Drejta Penale'), 
      options: ['kallezim_penal'] 
    },
    { 
      label: t('drafting.groupCorporate', 'E Drejta Komerciale'), 
      options: ['nda', 'mou', 'shareholders', 'sla'] 
    },
    { 
      label: t('drafting.groupEmployment', 'E Drejta e Punës'), 
      options: ['employment_contract', 'termination_notice', 'warning_letter'] 
    },
    { 
      label: t('drafting.groupObligational', 'E Drejta Detyrimore'), 
      options: ['lease_agreement', 'sales_purchase', 'power_of_attorney'] 
    },
    { 
      label: t('drafting.groupCompliance', 'Politikat & Pajtueshmëria'), 
      options: ['terms_conditions', 'privacy_policy'] 
    },
  ];

  const getOptionLabel = (value: string) => {
    const map: Record<string, string> = {
      generic: t('drafting.templateGeneric', 'Dokument i Përgjithshëm (I lirë)'),
      padi: t('drafting.templatePadi', 'Padi (Kërkesëpadi)'),
      pergjigje: t('drafting.templatePergjigje', 'Përgjigje në Padi'),
      kunderpadi: t('drafting.templateKunderpadi', 'Kundërpadi'),
      ankese: t('drafting.templateAnkese', 'Ankesë'),
      prapësim: t('drafting.templatePrapësim', 'Prapësim'),
      kallezim_penal: t('drafting.templateKallezimPenal', 'Kallëzim Penal'),
      nda: t('drafting.templateNDA', 'Marrëveshje për Moszbulim (NDA)'),
      mou: t('drafting.templateMoU', 'Marrëveshje e Mirëkuptimit (MoU)'),
      shareholders: t('drafting.templateShareholders', 'Marrëveshje e Ortakërisë'),
      sla: t('drafting.templateSLA', 'SLA (Marrëveshje e Nivelit të Shërbimit)'),
      employment_contract: t('drafting.templateKontrate', 'Kontratë Pune'),
      termination_notice: t('drafting.templateTermination', 'Vendim për Ndërprerje të Marrëdhënies'),
      warning_letter: t('drafting.templateWarning', 'Vërejtje me Shkrim'),
      lease_agreement: t('drafting.templateLease', 'Kontratë Qiraje'),
      sales_purchase: t('drafting.templateSales', 'Kontratë Shitblerje'),
      power_of_attorney: t('drafting.templatePoA', 'Autorizim Avokatie'),
      terms_conditions: t('drafting.templateTerms', 'Kushtet e Përdorimit'),
      privacy_policy: t('drafting.templatePrivacy', 'Politika e Privatësisë'),
    };
    return map[value] || value;
  };

  // DYNAMIC & INTELLIGENT AI PROMPT ENHANCER (NO FICTITIOUS DATA)
  const handleEnhanceWithAI = () => {
    if (!context.trim()) return;
    
    const clientName = (activeCase as any)?.client?.name || (activeCase as any)?.client_name;
    const opposingName = (activeCase as any)?.opposing_party?.name || (activeCase as any)?.opposing_party;
    const caseTitle = (activeCase as any)?.title || (activeCase as any)?.case_name;
    const caseNum = dynamicCaseNum ? `(Nr. ${dynamicCaseNum})` : '';

    let legalBasisDirective = '';
    if (selectedTemplate === 'kallezim_penal') {
      legalBasisDirective = `BAZA LIGJORE E APLIKUESHME:
   - Kodi i Procedurës Penale të Republikës së Kosovës (KPPRK Nr. 08/L-032).
   - Kodi Penal i Republikës së Kosovës (KPRK Nr. 06/L-074).
   - Të identifikohet me saktësi neni i veprës penale dhe elementet e qarta të figurës së veprës penale.`;
    } else if (['padi', 'kunderpadi', 'pergjigje', 'ankese', 'prapësim'].includes(selectedTemplate)) {
      legalBasisDirective = `BAZA LIGJORE E APLIKUESHME:
   - Ligji Nr. 03/L-006 për Procedurën Kontestimore të Kosovës (LPK).
   - Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve (LMD) ose ligji përkatës material sipas natyrës së kontestit.`;
    } else if (['employment_contract', 'termination_notice', 'warning_letter'].includes(selectedTemplate)) {
      legalBasisDirective = `BAZA LIGJORE E APLIKUESHME:
   - Ligji i Punës i Republikës së Kosovës (Ligji Nr. 03/L-212).`;
    } else {
      legalBasisDirective = `BAZA LIGJORE: Legjislacioni përkatës pozitiv në fuqi në Republikën e Kosovës.`;
    }

    const partyIntro = (clientName && opposingName)
      ? `Në emër të [${clientName}] në raport me [${opposingName}] ${caseTitle ? `në lidhje me "${caseTitle}" ${caseNum}` : ''}:`
      : (caseTitle ? `Lidhur me çështjen "${caseTitle}" ${caseNum}:` : `Kërkesë për hartim profesional ligjor:`);

    const enhanced = `[PROMPT LIGJOR I STRUKTURUAR ZYRTAR]

${partyIntro}

1. LLOJI I DOKUMENTIT: ${getOptionLabel(selectedTemplate).toUpperCase()}
2. SUBSTANCA DHE PROVAT E OFRUARA NGA KLIENTI:
${context.trim()}

3. ${legalBasisDirective}

4. DIREKTIVA PROFESIONALE:
   - Të hartohet në gjuhë standarde juridike pa asnjë gabim procedural.
   - Për çdo element faktik të paspecifikuar përdor kllapa katrore të qarta (p.sh. [EMRI_I_PLOTË], [DATA], [NUMRI_I_XHIROLLOGARISË]).
   - MOS përdor vija bosh si "____" dhe MOS shpik fakte jashtë udhëzimeve.`;

    onChangeContext(enhanced);
  };

  return (
    <div className="glass-panel border border-border-main rounded-3xl p-6 flex flex-col h-full shrink-0 shadow-sm relative pointer-events-auto overflow-visible">
      
      <div className="flex flex-col gap-5 flex-1 min-h-0 overflow-visible">
        
        {/* CASE SELECTION */}
        <div className="relative flex-shrink-0 space-y-2">
          <label className="text-[10px] font-black text-text-muted uppercase tracking-widest block">
            {t('drafting.caseLabel', 'Zgjidh rastin')}
          </label>
          <div className="relative flex items-center">
            <Briefcase size={16} className="absolute left-4 text-primary-start" />
            <select
              className="w-full pl-11 pr-4 py-3 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start outline-none appearance-none cursor-pointer transition-all"
              value={selectedCaseId || ''}
              onChange={(e) => onSelectCase?.(e.target.value)}
            >
              <option value="">{t('drafting.selectCase', 'Zgjidh rastin (Opsionale - Hartim i Lirë)...')}</option>
              {cases.map((c: any) => (
                <option key={c.id || c._id} value={c.id || c._id} className="bg-canvas text-text-primary">
                  {c.title || c.case_number || c.case_name}
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-4 text-text-muted pointer-events-none" />
          </div>

          {/* COMPACT ROLE STANCE BADGE */}
          {activeCase && (
            <div className="pt-0.5 flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-[10px] font-black uppercase tracking-wider border shadow-sm ${
                clientPosition === 'DEFENDANT'
                  ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30'
                  : clientPosition === 'PLAINTIFF'
                  ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30'
                  : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
              }`}>
                {clientPosition === 'DEFENDANT' ? <Shield size={12} /> : clientPosition === 'PLAINTIFF' ? <Swords size={12} /> : <Scale size={12} />}
                <span>
                  {clientPosition === 'DEFENDANT' ? '🛡️ I PADITUR / I DENONCUAR' :
                   clientPosition === 'PLAINTIFF' ? '⚔️ PADITËS / KALLËZUES' :
                   '⚖️ NEUTRAL'}
                </span>
              </span>
            </div>
          )}
        </div>

        {/* DYNAMIC BACKGROUND EVIDENCE & FACT CHIPS */}
        {activeCase && (dynamicCourt || dynamicValue || dynamicDeadline || dynamicCaseNum) && (
          <div className="p-3.5 rounded-2xl bg-surface/90 border border-border-main space-y-2 shadow-sm animate-in fade-in duration-200">
            <span className="text-[9px] font-black text-primary-start uppercase tracking-widest flex items-center gap-1">
              <FileText size={12} /> Provat & Faktet e Verifikuara nga Lënda
            </span>
            <div className="flex flex-wrap gap-2 text-[10px]">
              {dynamicCourt && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-text-secondary font-medium">
                  <Landmark size={12} className="text-amber-400 shrink-0" />
                  <span>{dynamicCourt}</span>
                </div>
              )}
              {dynamicValue && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-emerald-400 font-bold font-mono">
                  <Euro size={12} className="shrink-0" />
                  <span>{typeof dynamicValue === 'number' ? `€${dynamicValue.toLocaleString()}` : dynamicValue}</span>
                </div>
              )}
              {dynamicDeadline && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-text-secondary font-medium">
                  <Calendar size={12} className="text-blue-400 shrink-0" />
                  <span>{dynamicDeadline}</span>
                </div>
              )}
              {dynamicCaseNum && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-text-muted font-mono">
                  <AlertOctagon size={12} className="text-primary-start shrink-0" />
                  <span>{dynamicCaseNum}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TEMPLATE SELECTION */}
        <div className="relative flex-shrink-0 overflow-visible" ref={dropdownRef}>
          <div className="flex justify-between items-center mb-2">
            <label className="text-[10px] font-black text-text-muted uppercase tracking-widest">
              {t('drafting.templateLabel', 'Lloji i Dokumentit')}
            </label>
          </div>
          
          <button 
            type="button" 
            onClick={() => setIsOpen(!isOpen)} 
            className="w-full px-4 py-3 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary flex items-center justify-between transition-all hover:border-primary-start focus:border-primary-start focus:ring-1 focus:ring-primary-start"
          >
            <span className="truncate">{getOptionLabel(selectedTemplate)}</span>
            <ChevronDown size={16} className={`text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
          </button>

          {isOpen && (
            <div className="absolute left-0 right-0 top-full mt-2 z-[999] bg-canvas border border-border-main rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.15)] dark:shadow-[0_20px_50px_rgba(0,0,0,0.6)] max-h-[350px] overflow-y-auto custom-scrollbar">
              {templateGroups.map((group, groupIdx) => (
                <div key={group.label} className="flex flex-col">
                  <div className={`
                    px-4 py-2 
                    text-[10px] font-black uppercase tracking-widest text-text-muted
                    bg-surface/50
                    border-y border-border-main
                    ${groupIdx === 0 ? 'border-t-0' : ''}
                  `}>
                    {group.label}
                  </div>
                  <div className="flex flex-col py-1">
                    {group.options.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => { onSelectTemplate(opt as TemplateType); setIsOpen(false); }}
                        className="w-full text-left px-5 py-2.5 hover:bg-hover hover:text-primary-start transition-all text-sm font-bold text-text-primary focus:outline-none"
                      >
                        {getOptionLabel(opt)}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* INSTRUCTIONS & PROMPT ENHANCER */}
        <div className="flex-1 flex flex-col min-h-0 relative z-0">
          <div className="flex items-center justify-between mb-2">
            <label className="text-[10px] font-black text-text-muted uppercase tracking-widest block">
              {t('drafting.instructionsLabel', 'Udhëzimet')}
            </label>

            {/* 1-CLICK AI PROMPT ENHANCER BUTTON */}
            <button
              type="button"
              onClick={handleEnhanceWithAI}
              disabled={!context.trim()}
              className="flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 text-[10px] font-black uppercase transition-all disabled:opacity-30 cursor-pointer"
              title="Kthen fjalët e thjeshta në një kërkesë zyrtare të strukturuar për AI"
            >
              <Sparkles size={11} className="animate-pulse" />
              <span>Përmirëso me AI</span>
            </button>
          </div>

          <textarea 
            value={context} 
            onChange={(e) => onChangeContext(e.target.value)} 
            placeholder={placeholder} 
            className="w-full p-4 bg-surface border border-border-main rounded-xl text-sm flex-1 resize-none font-medium text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start outline-none shadow-inner transition-all custom-scrollbar" 
          />
        </div>

        {/* ACTION BUTTON */}
        <button 
          onClick={() => onSubmit()} 
          disabled={isSubmitting || !context.trim()} 
          className="btn-primary w-full h-12 flex items-center justify-center gap-2 flex-shrink-0 uppercase tracking-widest font-black text-xs disabled:opacity-50 disabled:cursor-not-allowed transition-all relative z-0 mt-2"
        >
          {isSubmitting ? <RefreshCw className="animate-spin" size={16} /> : <Send size={16} />}
          {isSubmitting ? t('drafting.statusWorking', 'Duke Gjeneruar...') : t('drafting.generateBtn', 'Gjenero Dokumentin')}
        </button>
      </div>
    </div>
  );
};

export default ConfigPanel;