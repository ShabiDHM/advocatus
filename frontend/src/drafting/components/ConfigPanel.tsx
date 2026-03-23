// FILE: src/drafting/components/ConfigPanel.tsx
// PHOENIX PROTOCOL - CONFIG PANEL V6.0 (FULL LOGIC + EXECUTIVE DESIGN)

import React, { useMemo } from 'react';
import { FileText, Briefcase, ChevronDown, LayoutTemplate, Lock, Send, RefreshCw } from 'lucide-react';
import { ConfigPanelProps } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  t, isPro, cases, selectedCaseId, selectedTemplate, context, isSubmitting,
  onSelectCase, onSelectTemplate, onChangeContext, onSubmit,
}) => {
  const placeholder = useMemo(() => getTemplatePlaceholder(selectedTemplate), [selectedTemplate]);

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
            <div className="relative group">
              <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-primary-start opacity-70" />
              <select
                value={selectedCaseId}
                onChange={(e) => onSelectCase(e.target.value)}
                disabled={!isPro}
                className="w-full pl-11 pr-10 py-3.5 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start outline-none transition-all appearance-none cursor-pointer disabled:opacity-50"
              >
                <option value="" className="bg-surface">{t('drafting.noCaseSelected')}</option>
                {cases.map((c: any) => (
                  <option key={c.id} value={c.id} className="bg-surface">
                    {c.title || c.case_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
            </div>
          </div>

          {/* Template Selector */}
          <div>
            <label className="block text-[10px] font-black text-text-muted uppercase tracking-widest mb-2">
              {t('drafting.templateLabel')}
            </label>
            <div className="relative group">
              <LayoutTemplate className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-primary-start opacity-70" />
              <select
                value={selectedTemplate}
                onChange={(e) => onSelectTemplate(e.target.value)}
                disabled={!isPro}
                className="w-full pl-11 pr-10 py-3.5 bg-surface border border-border-main rounded-xl text-sm font-bold appearance-none cursor-pointer disabled:opacity-50 focus:border-primary-start outline-none transition-all"
              >
                <option value="generic" className="bg-surface">{t('drafting.templateGeneric')}</option>
                <optgroup label={t('drafting.groupLitigation')} className="bg-surface text-text-primary italic">
                  <option value="padi" className="bg-surface not-italic">{t('drafting.templatePadi')}</option>
                  <option value="pergjigje" className="bg-surface not-italic">{t('drafting.templatePergjigje')}</option>
                  <option value="kunderpadi" className="bg-surface not-italic">{t('drafting.templateKunderpadi')}</option>
                  <option value="ankese" className="bg-surface not-italic">{t('drafting.templateAnkese')}</option>
                  <option value="prapësim" className="bg-surface not-italic">{t('drafting.templatePrapesim')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupCorporate')} className="bg-surface text-text-primary italic">
                  <option value="nda" className="bg-surface not-italic">{t('drafting.templateNDA')}</option>
                  <option value="mou" className="bg-surface not-italic">{t('drafting.templateMoU')}</option>
                  <option value="shareholders" className="bg-surface not-italic">{t('drafting.templateShareholders')}</option>
                  <option value="sla" className="bg-surface not-italic">{t('drafting.templateSLA')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupEmployment')} className="bg-surface text-text-primary italic">
                  <option value="employment_contract" className="bg-surface not-italic">{t('drafting.templateKontrate')}</option>
                  <option value="termination_notice" className="bg-surface not-italic">{t('drafting.templateTermination')}</option>
                  <option value="warning_letter" className="bg-surface not-italic">{t('drafting.templateWarning')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupRealEstate')} className="bg-surface text-text-primary italic">
                  <option value="lease_agreement" className="bg-surface not-italic">{t('drafting.templateLease')}</option>
                  <option value="sales_purchase" className="bg-surface not-italic">{t('drafting.templateSales')}</option>
                  <option value="power_of_attorney" className="bg-surface not-italic">{t('drafting.templatePoA')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupCompliance')} className="bg-surface text-text-primary italic">
                  <option value="terms_conditions" className="bg-surface not-italic">{t('drafting.templateTerms')}</option>
                  <option value="privacy_policy" className="bg-surface not-italic">{t('drafting.templatePrivacy')}</option>
                </optgroup>
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
            </div>
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
          className="btn-primary w-full h-14 flex items-center justify-center gap-3 mt-2 flex-shrink-0 disabled:opacity-40 shadow-lg shadow-primary-start/20"
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