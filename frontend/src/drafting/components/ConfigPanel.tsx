// FILE: src/drafting/components/ConfigPanel.tsx
// PHOENIX PROTOCOL - CONFIG PANEL V7.0 (IMPROVED CONTRAST & HOVER FIX)

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { FileText, LayoutTemplate, Lock, Send, RefreshCw, ChevronDown } from 'lucide-react';
import { ConfigPanelProps } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  t,
  isPro,
  selectedTemplate,
  context,
  isSubmitting,
  onSelectTemplate,
  onChangeContext,
  onSubmit,
}) => {
  const placeholder = useMemo(() => getTemplatePlaceholder(selectedTemplate), [selectedTemplate]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close dropdown when clicking outside
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

  const templateGroups = [
    { label: t('drafting.groupLitigation'), options: ['padi', 'pergjigje', 'kunderpadi', 'ankese', 'prapësim'] },
    { label: t('drafting.groupCorporate'), options: ['nda', 'mou', 'shareholders', 'sla'] },
    { label: t('drafting.groupEmployment'), options: ['employment_contract', 'termination_notice', 'warning_letter'] },
    { label: t('drafting.groupRealEstate'), options: ['lease_agreement', 'sales_purchase', 'power_of_attorney'] },
    { label: t('drafting.groupCompliance'), options: ['terms_conditions', 'privacy_policy'] },
  ];

  const getOptionLabel = (value: string) => {
    const map: Record<string, string> = {
      generic: t('drafting.templateGeneric'),
      padi: t('drafting.templatePadi'),
      pergjigje: t('drafting.templatePergjigje'),
      kunderpadi: t('drafting.templateKunderpadi'),
      ankese: t('drafting.templateAnkese'),
      prapësim: t('drafting.templatePrapesim'),
      nda: t('drafting.templateNDA'),
      mou: t('drafting.templateMoU'),
      shareholders: t('drafting.templateShareholders'),
      sla: t('drafting.templateSLA'),
      employment_contract: t('drafting.templateKontrate'),
      termination_notice: t('drafting.templateTermination'),
      warning_letter: t('drafting.templateWarning'),
      lease_agreement: t('drafting.templateLease'),
      sales_purchase: t('drafting.templateSales'),
      power_of_attorney: t('drafting.templatePoA'),
      terms_conditions: t('drafting.templateTerms'),
      privacy_policy: t('drafting.templatePrivacy'),
    };
    return map[value] || value;
  };

  const handleSelect = (value: string) => {
    onSelectTemplate(value);
    setIsOpen(false);
  };

  const handleGenerateClick = () => {
    if (typeof onSubmit === 'function') {
      onSubmit();
    }
  };

  const isButtonDisabled = isSubmitting || !context.trim();

  return (
    <div className="glass-panel border border-border-main rounded-3xl p-6 sm:p-8 flex flex-col h-auto lg:h-[700px] shrink-0 shadow-sm hover:border-primary-start/50 transition-all duration-300">
      
      {/* Executive Header */}
      <div className="flex items-center gap-3 border-b border-border-main pb-5 mb-6 flex-shrink-0">
        <FileText className="text-accent-primary" size={20} />
        <h2 className="text-sm font-black text-text-primary uppercase tracking-widest leading-none">
          {t('drafting.configuration', 'Konfigurimi')}
        </h2>
      </div>

      <div className="flex flex-col gap-6 flex-1 min-h-0 overflow-hidden">
        {/* Template Selector Only */}
        <div className="flex-shrink-0 relative z-20">
          <div className="flex justify-between items-center mb-2">
            <label className="text-[10px] font-black text-text-muted uppercase tracking-widest">
              {t('drafting.templateLabel')}
            </label>
            {!isPro && (
              <span className="text-[9px] text-warning-start font-black bg-warning-start/10 px-2 py-0.5 rounded border border-warning-start/20 flex items-center gap-1 uppercase tracking-widest">
                <Lock size={10} /> PRO
              </span>
            )}
          </div>
          
          {/* Custom Dropdown */}
          <div className="relative">
            <LayoutTemplate className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-accent-primary pointer-events-none z-10" />
            <button
              ref={buttonRef}
              type="button"
              onClick={() => isPro && setIsOpen(!isOpen)}
              disabled={!isPro}
              className="w-full pl-11 pr-10 py-3.5 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start outline-none transition-all appearance-none cursor-pointer disabled:opacity-50 flex items-center justify-between"
            >
              <span>{getOptionLabel(selectedTemplate)}</span>
              <ChevronDown className={`h-4 w-4 text-text-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {isOpen && isPro && (
              <div
                ref={dropdownRef}
                className="absolute z-[9999] mt-1 w-full bg-card border border-border-main rounded-xl shadow-xl max-h-60 overflow-y-auto custom-scrollbar"
                style={{ backgroundColor: 'var(--bg-card)' }}
              >
                <div
                  onClick={() => handleSelect('generic')}
                  className="px-4 py-2 hover:bg-hover cursor-pointer text-sm font-bold text-text-primary"
                >
                  {t('drafting.templateGeneric')}
                </div>
                {templateGroups.map((group) => (
                  <div key={group.label}>
                    <div className="px-4 py-1 text-xs font-black uppercase tracking-widest text-text-muted bg-surface/50 sticky top-0">
                      {group.label}
                    </div>
                    {group.options.map((opt) => (
                      <div
                        key={opt}
                        onClick={() => handleSelect(opt)}
                        className="px-4 py-2 hover:bg-hover cursor-pointer text-sm font-bold text-text-primary pl-6"
                      >
                        {getOptionLabel(opt)}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Dynamic Context Textarea */}
        <div className="flex-1 flex flex-col min-h-0">
          <label className="block text-[10px] font-black text-text-muted uppercase tracking-widest mb-2">
            {t('drafting.instructionsLabel')}
          </label>
          <textarea
            value={context}
            onChange={(e) => onChangeContext(e.target.value)}
            placeholder={placeholder}
            className="w-full p-5 bg-surface border border-border-main rounded-xl text-sm flex-1 resize-none font-medium text-text-primary focus:border-primary-start outline-none transition-all placeholder:text-text-muted"
          />
        </div>

        {/* Primary Action Button */}
        <button
          onClick={handleGenerateClick}
          disabled={isButtonDisabled}
          className="btn-primary w-full h-14 flex items-center justify-center gap-3 mt-2 flex-shrink-0 disabled:opacity-40 shadow-lg shadow-primary-start/20 hover-lift"
        >
          {isSubmitting ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
          <span className="uppercase tracking-widest font-black text-xs">
            {isSubmitting ? t('drafting.statusWorking') : t('drafting.generateBtn')}
          </span>
        </button>
      </div>
    </div>
  );
};