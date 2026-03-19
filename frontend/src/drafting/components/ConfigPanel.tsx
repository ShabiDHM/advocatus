// src/drafting/components/ConfigPanel.tsx
import React, { useMemo } from 'react';
import { FileText, Briefcase, ChevronDown, LayoutTemplate, Lock, Send, RefreshCw } from 'lucide-react';
import { ConfigPanelProps } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  t,
  isPro,
  cases,
  selectedCaseId,
  selectedTemplate,
  context,
  isSubmitting,
  onSelectCase,
  onSelectTemplate,
  onChangeContext,
  onSubmit,
}) => {
  const placeholder = useMemo(() => getTemplatePlaceholder(selectedTemplate), [selectedTemplate]);

  return (
    <div className="glass-panel flex flex-col h-auto lg:h-[700px] p-4 sm:p-6 rounded-2xl border border-white/10 shrink-0">
      <h3 className="text-white font-semibold mb-6 flex items-center gap-2">
        <FileText className="text-primary-start" size={20} />
        {t('drafting.configuration')}
      </h3>
      <div className="flex flex-col gap-5 flex-1 min-h-0 overflow-hidden">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 flex-shrink-0">
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">
                {t('drafting.caseLabel')}
              </label>
              {!isPro && (
                <span className="text-[9px] text-amber-500 font-bold bg-amber-500/10 px-1.5 rounded border border-amber-500/20 flex items-center gap-1">
                  <Lock size={8} /> PRO
                </span>
              )}
            </div>
            <div className="relative">
              <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <select
                value={selectedCaseId}
                onChange={(e) => onSelectCase(e.target.value)}
                disabled={!isPro}
                className="glass-input w-full pl-10 pr-10 py-3.5 rounded-xl text-sm appearance-none outline-none"
              >
                <option value="">{t('drafting.noCaseSelected')}</option>
                {cases.map((c: any) => (
                  <option key={c.id} value={c.id} className="bg-gray-900">
                    {c.title || c.case_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
          <div>
            <label className="block text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">
              {t('drafting.templateLabel')}
            </label>
            <div className="relative">
              <LayoutTemplate className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <select
                value={selectedTemplate}
                onChange={(e) => onSelectTemplate(e.target.value)}
                disabled={!isPro}
                className="glass-input w-full pl-10 pr-10 py-3.5 rounded-xl text-sm appearance-none outline-none"
              >
                <option value="generic">{t('drafting.templateGeneric')}</option>
                <optgroup label={t('drafting.groupLitigation')} className="bg-gray-900 italic">
                  <option value="padi">{t('drafting.templatePadi')}</option>
                  <option value="pergjigje">{t('drafting.templatePergjigje')}</option>
                  <option value="kunderpadi">{t('drafting.templateKunderpadi')}</option>
                  <option value="ankese">{t('drafting.templateAnkese')}</option>
                  <option value="prapësim">{t('drafting.templatePrapesim')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupCorporate')} className="bg-gray-900 italic">
                  <option value="nda">{t('drafting.templateNDA')}</option>
                  <option value="mou">{t('drafting.templateMoU')}</option>
                  <option value="shareholders">{t('drafting.templateShareholders')}</option>
                  <option value="sla">{t('drafting.templateSLA')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupEmployment')} className="bg-gray-900 italic">
                  <option value="employment_contract">{t('drafting.templateKontrate')}</option>
                  <option value="termination_notice">{t('drafting.templateTermination')}</option>
                  <option value="warning_letter">{t('drafting.templateWarning')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupRealEstate')} className="bg-gray-900 italic">
                  <option value="lease_agreement">{t('drafting.templateLease')}</option>
                  <option value="sales_purchase">{t('drafting.templateSales')}</option>
                  <option value="power_of_attorney">{t('drafting.templatePoA')}</option>
                </optgroup>
                <optgroup label={t('drafting.groupCompliance')} className="bg-gray-900 italic">
                  <option value="terms_conditions">{t('drafting.templateTerms')}</option>
                  <option value="privacy_policy">{t('drafting.templatePrivacy')}</option>
                </optgroup>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>
        <div className="flex-1 flex flex-col min-h-0">
          <label className="block text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">
            {t('drafting.instructionsLabel')}
          </label>
          <textarea
            value={context}
            onChange={(e) => onChangeContext(e.target.value)}
            placeholder={placeholder}
            className="glass-input w-full p-4 rounded-xl text-sm flex-1 resize-none outline-none focus:ring-1 focus:ring-primary-start/40 transition-all overflow-y-auto custom-scrollbar font-mono placeholder:text-gray-600"
          />
        </div>
        <button
          onClick={onSubmit}
          disabled={isSubmitting || !context.trim()}
          className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end text-white font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-primary-start/20 hover:opacity-95 transition-all active:scale-[0.98] mt-4 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? <RefreshCw className="animate-spin" size={18} /> : <Send size={18} />}
          {isSubmitting ? t('drafting.statusWorking') : t('drafting.generateBtn')}
        </button>
      </div>
    </div>
  );
};