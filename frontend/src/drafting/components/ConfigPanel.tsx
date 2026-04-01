// FILE: src/drafting /components/ConfigPanel.tsx
// PHOENIX PROTOCOL - CONFIG PANEL V8.3 (PREMIUM OPAQUE DROPDOWN FIX)

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { FileText, Send, RefreshCw, ChevronDown, Briefcase, Lock } from 'lucide-react';
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
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click ensuring state stability
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
    { label: t('drafting.groupLitigation', 'Procedura Kontestimore'), options: ['padi', 'pergjigje', 'kunderpadi', 'ankese', 'prapësim'] },
    { label: t('drafting.groupCorporate', 'E Drejta Komerciale'), options: ['nda', 'mou', 'shareholders', 'sla'] },
    { label: t('drafting.groupEmployment', 'E Drejta e Punës'), options: ['employment_contract', 'termination_notice', 'warning_letter'] },
    { label: t('drafting.groupObligational', 'E Drejta Detyrimore'), options: ['lease_agreement', 'sales_purchase', 'power_of_attorney'] },
    { label: t('drafting.groupCompliance', 'Politikat & Pajtueshmëria'), options: ['terms_conditions', 'privacy_policy'] },
  ];

  const getOptionLabel = (value: string) => {
    const map: Record<string, string> = {
      generic: t('drafting.templateGeneric', 'Dokument i Përgjithshëm (I lirë)'),
      padi: t('drafting.templatePadi', 'Padi (Lawsuit)'),
      pergjigje: t('drafting.templatePergjigje', 'Përgjigje në Padi'),
      kunderpadi: t('drafting.templateKunderpadi', 'Kundërpadi'),
      ankese: t('drafting.templateAnkese', 'Ankesë'),
      prapësim: t('drafting.templatePrapesim', 'Prapësim'),
      nda: t('drafting.templateNDA', 'Marrëveshje për Moszbulim'),
      mou: t('drafting.templateMoU', 'Marrëveshje e Mirëkuptimit'),
      shareholders: t('drafting.templateShareholders', 'Marrëveshje e Ortakërisë'),
      sla: t('drafting.templateSLA', 'SLA'),
      employment_contract: t('drafting.templateKontrate', 'Kontratë Pune'),
      termination_notice: t('drafting.templateTermination', 'Vendim për Ndërprerje'),
      warning_letter: t('drafting.templateWarning', 'Vërejtje me Shkrim'),
      lease_agreement: t('drafting.templateLease', 'Kontratë Qiraje'),
      sales_purchase: t('drafting.templateSales', 'Kontratë Shitblerje'),
      power_of_attorney: t('drafting.templatePoA', 'Autorizim'),
      terms_conditions: t('drafting.templateTerms', 'Kushtet e Përdorimit'),
      privacy_policy: t('drafting.templatePrivacy', 'Politika e Privatësisë'),
    };
    return map[value] || value;
  };

  return (
    <div className="glass-panel border border-border-main rounded-3xl p-6 flex flex-col h-full shrink-0 shadow-sm relative pointer-events-auto">
      
      {/* SECTION HEADER */}
      <div className="flex items-center gap-3 border-b border-border-main pb-5 mb-6">
        <div className="p-2 bg-primary-start/10 rounded-xl border border-primary-start/20">
          <FileText className="text-primary-start" size={18} />
        </div>
        <h2 className="text-[11px] font-black text-text-primary uppercase tracking-widest leading-none">
          {t('drafting.configuration', 'Konfigurimi')}
        </h2>
      </div>

      <div className="flex flex-col gap-6 flex-1 min-h-0">
        
        {/* CASE SELECTION */}
        <div className="relative">
          <label className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-2 block">
            {t('drafting.caseLabel', 'Zgjidh rastin')}
          </label>
          <div className="relative flex items-center">
            <Briefcase size={16} className="absolute left-4 text-primary-start" />
            <select
              className="w-full pl-11 pr-4 py-3 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start outline-none appearance-none cursor-pointer transition-all"
              value={selectedCaseId || ''}
              onChange={(e) => onSelectCase?.(e.target.value)}
            >
              <option value="">{t('drafting.selectCase', 'Zgjidh rastin...')}</option>
              {cases.map((c: any) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-4 text-text-muted pointer-events-none" />
          </div>
        </div>

        {/* TEMPLATE SELECTION (Fixed Opaque Dropdown) */}
        <div className="relative" ref={dropdownRef}>
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
            type="button" 
            onClick={() => isPro && setIsOpen(!isOpen)} 
            disabled={!isPro} 
            className="w-full px-4 py-3 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary flex items-center justify-between transition-all hover:border-primary-start focus:border-primary-start focus:ring-1 focus:ring-primary-start"
          >
            <span className="truncate">{getOptionLabel(selectedTemplate)}</span>
            <ChevronDown size={16} className={`text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* BULLETPROOF OPAQUE MENU */}
          {isOpen && isPro && (
            <div className="absolute left-0 right-0 top-[calc(100%+8px)] bg-[#0B1221] border border-[#1E293B] rounded-xl shadow-[0_25px_50px_-12px_rgba(0,0,0,1)] max-h-[300px] overflow-y-auto z-[9999] ring-1 ring-white/5 flex flex-col custom-scrollbar">
              {templateGroups.map((group) => (
                <div key={group.label} className="flex flex-col">
                  {/* Sticky Opaque Header */}
                  <div className="sticky top-0 px-4 py-2.5 text-[9px] font-black uppercase text-slate-400 bg-[#0B1221] border-b border-[#1E293B] z-10 tracking-wider">
                    {group.label}
                  </div>
                  {/* Options */}
                  {group.options.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => { onSelectTemplate(opt as TemplateType); setIsOpen(false); }}
                      className="w-full text-left px-4 py-3 hover:bg-[#161F33] cursor-pointer text-sm font-medium text-slate-200 border-b border-[#1E293B]/50 last:border-none transition-colors"
                    >
                      {getOptionLabel(opt)}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* INSTRUCTIONS */}
        <div className="flex-1 flex flex-col min-h-0 relative z-0">
          <label className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-2 block">
            {t('drafting.instructionsLabel', 'Udhëzimet')}
          </label>
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
          className="btn-primary w-full h-12 flex items-center justify-center gap-2 flex-shrink-0 uppercase tracking-widest font-black text-xs disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isSubmitting ? <RefreshCw className="animate-spin" size={16} /> : <Send size={16} />}
          {isSubmitting ? t('drafting.statusWorking', 'Duke Gjeneruar...') : t('drafting.generateBtn', 'Gjenero Dokumentin')}
        </button>
      </div>
    </div>
  );
};