// FILE: src/drafting/components/ConfigPanel.tsx
import React, { useMemo } from 'react';
import { FileText, Briefcase, LayoutTemplate, Lock, Send, RefreshCw } from 'lucide-react';
import { ConfigPanelProps } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';
import { CustomSelect } from '../../components/ui/CustomSelect';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  t, isPro, cases, selectedCaseId, selectedTemplate, context, isSubmitting,
  onSelectCase, onSelectTemplate, onChangeContext, onSubmit,
}) => {
  const placeholder = useMemo(() => getTemplatePlaceholder(selectedTemplate), [selectedTemplate]);

  // Prepare case options for the custom select
  const caseOptions = [
    { value: '', label: t('drafting.noCaseSelected') },
    ...cases.map((c: any) => ({
      value: c.id,
      label: c.title || c.case_name,
    })),
  ];

  // Prepare template options with groups
  const templateOptions = [
    { value: 'generic', label: t('drafting.templateGeneric'), group: '' },
    // Litigation group
    { value: 'padi', label: t('drafting.templatePadi'), group: t('drafting.groupLitigation') },
    { value: 'pergjigje', label: t('drafting.templatePergjigje'), group: t('drafting.groupLitigation') },
    { value: 'kunderpadi', label: t('drafting.templateKunderpadi'), group: t('drafting.groupLitigation') },
    { value: 'ankese', label: t('drafting.templateAnkese'), group: t('drafting.groupLitigation') },
    { value: 'prapësim', label: t('drafting.templatePrapesim'), group: t('drafting.groupLitigation') },
    // Corporate group
    { value: 'nda', label: t('drafting.templateNDA'), group: t('drafting.groupCorporate') },
    { value: 'mou', label: t('drafting.templateMoU'), group: t('drafting.groupCorporate') },
    { value: 'shareholders', label: t('drafting.templateShareholders'), group: t('drafting.groupCorporate') },
    { value: 'sla', label: t('drafting.templateSLA'), group: t('drafting.groupCorporate') },
    // Employment group
    { value: 'employment_contract', label: t('drafting.templateKontrate'), group: t('drafting.groupEmployment') },
    { value: 'termination_notice', label: t('drafting.templateTermination'), group: t('drafting.groupEmployment') },
    { value: 'warning_letter', label: t('drafting.templateWarning'), group: t('drafting.groupEmployment') },
    // Real Estate group
    { value: 'lease_agreement', label: t('drafting.templateLease'), group: t('drafting.groupRealEstate') },
    { value: 'sales_purchase', label: t('drafting.templateSales'), group: t('drafting.groupRealEstate') },
    { value: 'power_of_attorney', label: t('drafting.templatePoA'), group: t('drafting.groupRealEstate') },
    // Compliance group
    { value: 'terms_conditions', label: t('drafting.templateTerms'), group: t('drafting.groupCompliance') },
    { value: 'privacy_policy', label: t('drafting.templatePrivacy'), group: t('drafting.groupCompliance') },
  ];

  return (
    <div className="glass-panel border border-border-main rounded-3xl p-6 sm:p-8 flex flex-col h-auto lg:h-[700px] shrink-0 shadow-sm hover:lift transition-all">
      
      {/* Executive Header */}
      <div className="flex items-center gap-3 border-b border-border-main pb-5 mb-6 flex-shrink-0">
        <FileText className="text-primary-start" size={20} />
        <h2 className="text-sm font-black text-text-primary uppercase tracking-widest leading-none">
          {t('drafting.configuration', 'Konfigurimi')}
        </h2>
      </div>

      <div className="flex flex-col gap-6 flex-1 min-h-0 overflow-hidden">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 flex-shrink-0">
          
          {/* Case Selector */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-[10px] font-black text-text-muted uppercase tracking-widest">
                {t('drafting.caseLabel')}
              </label>
              {!isPro && (
                <span className="text-[9px] text-warning-start font-black bg-warning-start/10 px-2 py-0.5 rounded border border-warning-start/20 flex items-center gap-1 uppercase tracking-widest">
                  <Lock size={10} /> PRO
                </span>
              )}
            </div>
            <CustomSelect
              value={selectedCaseId}
              onChange={onSelectCase}
              options={caseOptions}
              disabled={!isPro}
              icon={<Briefcase className="h-4 w-4" />}
            />
          </div>

          {/* Template Selector */}
          <div>
            <label className="block text-[10px] font-black text-text-muted uppercase tracking-widest mb-2">
              {t('drafting.templateLabel')}
            </label>
            <CustomSelect
              value={selectedTemplate}
              onChange={onSelectTemplate}
              options={templateOptions}
              disabled={!isPro}
              icon={<LayoutTemplate className="h-4 w-4" />}
            />
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
          onClick={onSubmit}
          disabled={isSubmitting || !context.trim()}
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