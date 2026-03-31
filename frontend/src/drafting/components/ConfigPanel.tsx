// FILE: src/drafting/components/ConfigPanel.tsx
// ARCHITECTURE: STRICT KOSOVO LEGAL TAXONOMY & PERSISTENT UI STATE (TS FIXED)

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { FileText, Lock, Send, RefreshCw, ChevronDown, Briefcase } from 'lucide-react';
import { ConfigPanelProps } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';
import { TemplateType } from '../types';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  t,
  isPro,
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
  
  // Refs for custom dropdown click-outside handling
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target as Node) && 
        buttonRef.current && 
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // LAYER 2: STRICT KOSOVO LEGAL TAXONOMY IN UI
  // These groups now map directly to specific Kosovo statutes in the prompting engine
  const templateGroups = [
    { 
      label: t('drafting.groupLitigation', 'Procedura Kontestimore'), 
      options: ['padi', 'pergjigje', 'kunderpadi', 'ankese', 'prapësim'] 
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
      generic: t('drafting.templateGeneric', 'Dokument i Përgjithshëm'),
      // Procedura Kontestimore (Ligji për Procedurën Kontestimore)
      padi: t('drafting.templatePadi', 'Padi (Lawsuit)'),
      pergjigje: t('drafting.templatePergjigje', 'Përgjigje në Padi'),
      kunderpadi: t('drafting.templateKunderpadi', 'Kundërpadi'),
      ankese: t('drafting.templateAnkese', 'Ankesë (Appeal)'),
      prapësim: t('drafting.templatePrapesim', 'Prapësim'),
      // E Drejta Komerciale (Ligji për Shoqëritë Tregtare)
      nda: t('drafting.templateNDA', 'Marrëveshje për Moszbulim (NDA)'),
      mou: t('drafting.templateMoU', 'Marrëveshje e Mirëkuptimit (MoU)'),
      shareholders: t('drafting.templateShareholders', 'Marrëveshje e Ortakërisë'),
      sla: t('drafting.templateSLA', 'Marrëveshje për Nivelin e Shërbimit (SLA)'),
      // E Drejta e Punës (Ligji i Punës)
      employment_contract: t('drafting.templateKontrate', 'Kontratë Pune'),
      termination_notice: t('drafting.templateTermination', 'Vendim për Ndërprerje'),
      warning_letter: t('drafting.templateWarning', 'Vërejtje me Shkrim'),
      // E Drejta Detyrimore (Ligji për Marrëdhëniet e Detyrimeve)
      lease_agreement: t('drafting.templateLease', 'Kontratë Qiraje'),
      sales_purchase: t('drafting.templateSales', 'Kontratë Shitblerje'),
      power_of_attorney: t('drafting.templatePoA', 'Autorizim (Power of Attorney)'),
      // Pajtueshmëria
      terms_conditions: t('drafting.templateTerms', 'Kushtet e Përdorimit'),
      privacy_policy: t('drafting.templatePrivacy', 'Politika e Privatësisë'),
    };
    return map[value] || value;
  };

  const handleSelect = (value: TemplateType) => {
    onSelectTemplate(value);
    setIsOpen(false);
  };

  const handleCaseChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (onSelectCase) {
      onSelectCase(e.target.value);
    }
  };

  return (
    <div className="glass-panel border border-border-main rounded-3xl p-6 sm:p-8 flex flex-col h-auto lg:h-[700px] shrink-0 shadow-sm transition-all duration-300 relative group pointer-events-auto z-10">
      <div className="absolute inset-0 rounded-3xl border border-transparent group-hover:border-primary-start transition-colors duration-300 pointer-events-none" />

      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border-main pb-5 mb-6 flex-shrink-0">
        <div className="p-2 bg-primary-start/10 rounded-xl border border-primary-start/20">
          <FileText className="text-primary-start" size={20} />
        </div>
        <h2 className="text-sm font-black text-text-primary uppercase tracking-widest leading-none">
          {t('drafting.configuration', 'Konfigurimi')}
        </h2>
      </div>

      <div className="flex flex-col gap-6 flex-1 min-h-0">
        
        {/* CASE CONTEXT DROPDOWN - STABILIZED */}
        <div className="flex-shrink-0 relative z-30">
          <label className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-2 block">
            {t('drafting.caseLabel', 'Rasti / Çështja Lidhur')}
          </label>
          <div className="relative">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-primary-start pointer-events-none z-10">
              <Briefcase size={16} />
            </div>
            <select
              className="w-full pl-11 pr-4 py-3.5 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start outline-none transition-all appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              value={selectedCaseId || ''}
              onChange={handleCaseChange}
              disabled={cases.length === 0}
            >
              <option value="">
                {cases.length === 0 
                  ? t('drafting.noCases', 'Nuk ka raste të hapura...') 
                  : t('drafting.selectCase', 'Zgjidh rastin (Opcionale)...')}
              </option>
              {cases.map((c: any) => (
                <option key={String(c.id)} value={String(c.id)}>
                  {c.title || `Rasti #${c.id}`}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* TEMPLATE SELECTOR - Z-INDEX FIXED */}
        <div className="flex-shrink-0 relative z-40">
          <div className="flex justify-between items-center mb-2">
            <label className="text-[10px] font-black text-text-muted uppercase tracking-widest">
              {t('drafting.templateLabel', 'Lloji i Dokumentit')}
            </label>
            {!isPro && (
              <span className="text-[9px] text-warning-start font-black bg-warning-start/10 px-2 py-0.5 rounded border border-warning-start/20 uppercase tracking-widest flex items-center gap-1">
                <Lock size={10} /> PRO
              </span>
            )}
          </div>
          
          <button 
            ref={buttonRef} 
            type="button" 
            onClick={() => isPro && setIsOpen(!isOpen)} 
            disabled={!isPro} 
            className="w-full pl-4 pr-10 py-3.5 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary flex items-center justify-between pointer-events-auto transition-colors hover:border-primary-start"
          >
            <span className="truncate">{getOptionLabel(selectedTemplate)}</span>
            <ChevronDown className={`h-4 w-4 text-text-muted transition-transform absolute right-4 ${isOpen ? 'rotate-180' : ''}`} />
          </button>

          {isOpen && isPro && (
            <div 
              ref={dropdownRef} 
              className="absolute left-0 right-0 top-full mt-2 bg-white dark:bg-gray-900 border border-border-main rounded-xl shadow-2xl max-h-64 overflow-y-auto custom-scrollbar z-[100]"
            >
              <div 
                onClick={() => handleSelect('generic' as TemplateType)} 
                className="px-4 py-3 hover:bg-hover cursor-pointer text-sm font-bold text-text-primary border-b border-border-main/50"
              >
                {t('drafting.templateGeneric', 'Dokument i Përgjithshëm')}
              </div>
              
              {templateGroups.map((group) => (
                <div key={group.label}>
                  <div className="px-4 py-2 text-[10px] font-black uppercase tracking-widest text-primary-start bg-primary-start/5 sticky top-0 z-10 border-b border-border-main/50 backdrop-blur-md">
                    {group.label}
                  </div>
                  {group.options.map((opt) => (
                    <div 
                      key={opt} 
                      onClick={() => handleSelect(opt as TemplateType)} 
                      className="px-4 py-2.5 hover:bg-hover cursor-pointer text-sm font-semibold text-text-primary pl-6 border-b border-border-main/10 last:border-none"
                    >
                      {getOptionLabel(opt)}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* CONTEXT TEXTAREA */}
        <div className="flex-1 flex flex-col min-h-0 relative z-10">
           <textarea 
             value={context} 
             onChange={(e) => onChangeContext(e.target.value)} 
             placeholder={placeholder || t('drafting.contextPlaceholder', 'Përshkruani detajet e rastit këtu... (psh. Palët, data e ngjarjes, shuma në kontest)')} 
             className="w-full p-5 bg-surface border border-border-main rounded-xl text-sm flex-1 resize-none font-medium text-text-primary focus:border-primary-start outline-none transition-all shadow-inner" 
           />
        </div>

        {/* SUBMIT BUTTON */}
        <button 
          onClick={() => onSubmit()} 
          disabled={isSubmitting || !context.trim()} 
          className="btn-primary w-full h-14 flex items-center justify-center gap-3 flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:shadow-lg hover:shadow-primary-start/20 z-10"
        >
          {isSubmitting ? (
            <RefreshCw className="animate-spin" size={18} />
          ) : (
            <Send size={18} />
          )}
          <span className="uppercase tracking-widest font-black text-xs">
            {isSubmitting ? t('drafting.statusWorking', 'Duke Gjeneruar...') : t('drafting.generateBtn', 'Gjenero Dokumentin')}
          </span>
        </button>
      </div>
    </div>
  );
};