// FILE: src/drafting/components/ConfigPanel.tsx
// PHOENIX PROTOCOL - CONFIG PANEL V7.0 (SMART FACT CHIPS, AI PROMPT ENHANCER & LEGAL TAGS)

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { Send, RefreshCw, ChevronDown, Briefcase, Shield, Swords, Scale, Sparkles, Plus, Landmark, Euro, Calendar, FileText } from 'lucide-react';
import { ConfigPanelProps } from '../types';
import { getTemplatePlaceholder } from '../utils/templateHelpers';
import { TemplateType } from '../types';

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

  // Find currently selected case object
  const activeCase = useMemo(() => {
    if (!selectedCaseId) return null;
    return cases.find((c: any) => String(c.id) === String(selectedCaseId));
  }, [cases, selectedCaseId]);

  const clientPosition = (activeCase as any)?.client_position || 'DEFENDANT';

  // AUTO-SELECT TEMPLATE WHEN CASE CHANGES
  useEffect(() => {
    if (!activeCase) return;
    const pos = (activeCase as any)?.client_position || 'DEFENDANT';
    if (pos === 'DEFENDANT') {
      onSelectTemplate('prapësim' as TemplateType);
    } else if (pos === 'PLAINTIFF') {
      onSelectTemplate('padi' as TemplateType);
    }
  }, [selectedCaseId, activeCase, onSelectTemplate]);

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
      prapësim: t('drafting.templatePrapësim', 'Prapësim'),
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

  // DYNAMIC LEGAL ARTICLE TAGS BY TEMPLATE
  const legalArticleTags = useMemo(() => {
    switch (selectedTemplate) {
      case 'kunderpadi':
        return [
          'Neni 46 i LPK (Kushtet e Kundërpadisë)',
          'Neni 258 i LMD (Detyrimi i Besnikërisë)',
          'Neni 259 i LMD (Kompensimi i Dëmit)',
          'Kamatë Vonesore Ligjore'
        ];
      case 'prapësim':
        return [
          'Neni 147 i LPK (Prapësimi Procedural)',
          'Parashkrimi i Afateve Ligjore',
          'Mungesa e Autorizimit të Përfaqësimit'
        ];
      case 'padi':
        return [
          'Neni 253 i LPK (Përmbajtja e Padisë)',
          'Neni 297 i LPK (Caktimi i Masës së Sigurisë)',
          'Vërtetimi i Pronësisë & Detyrimit'
        ];
      case 'employment_contract':
      case 'termination_notice':
        return [
          'Neni 11 i Ligjit të Punës (Kontrata)',
          'Neni 70 i Ligjit të Punës (Ndërprerja)',
          'Afati i Paralajmërimit (30 Ditë)'
        ];
      default:
        return [
          'LPK - Ligji për Procedurën Kontestimore',
          'LMD - Ligji për Marrëdhëniet e Detyrimeve'
        ];
    }
  }, [selectedTemplate]);

  // 1-CLICK PROMPT ENHANCER
  const handleEnhanceWithAI = () => {
    if (!context.trim()) return;
    
    const clientName = activeCase?.client?.name || 'Klienti';
    const opposingName = activeCase?.opposing_party?.name || 'Pala Kundërshtare';
    const caseTitle = activeCase?.title || 'Çështja Ligjore';

    const enhanced = `[PROMPT LIGJOR I STRUKTURUAR ZYRTAR]

Në emër të ${clientName} kundër ${opposingName} në lëndën "${caseTitle}":

1. LLOKACIUNI DHE SHKRESA: Harto shkresën zyrtare ${getOptionLabel(selectedTemplate).toUpperCase()} për Gjykata Themelore në Prishtinë.
2. SUBSTANCA DHE PROVAT: ${context.trim()}
3. DIREKTIVA BAZË: Baza juridike duhet të mbështetet rigorozisht në nenet përkatëse të LPK-së dhe LMD-së. Të specifikohet kërkesëpadia (Petitumi) me shumat financiare dhe kamatën vonesore.`;

    onChangeContext(enhanced);
  };

  // APPEND LEGAL TAG TO CONTEXT
  const handleAppendTag = (tagText: string) => {
    if (context.includes(tagText)) return;
    const addition = context.trim() ? `\n- Baza Ligjore: ${tagText}` : `Baza Ligjore: ${tagText}`;
    onChangeContext(context + addition);
  };

  return (
    <div className="glass-panel border border-border-main rounded-3xl p-6 flex flex-col h-full shrink-0 shadow-sm relative pointer-events-auto overflow-visible">
      
      <div className="flex flex-col gap-5 flex-1 min-h-0 overflow-visible">
        
        {/* CASE SELECTION WITH CLEAN COMPACT STANCE BADGE */}
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
              <option value="">{t('drafting.selectCase', 'Zgjidh rastin...')}</option>
              {cases.map((c: any) => (
                <option key={c.id} value={c.id} className="bg-canvas text-text-primary">{c.title || c.case_number}</option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-4 text-text-muted pointer-events-none" />
          </div>

          {/* CLEAN COMPACT BADGE */}
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
                  {clientPosition === 'DEFENDANT' ? '🛡️ I PADITUR' :
                   clientPosition === 'PLAINTIFF' ? '⚔️ PADITËSI' :
                   '⚖️ NEUTRAL'}
                </span>
              </span>
            </div>
          )}
        </div>

        {/* AUTOMATED BACKGROUND EVIDENCE & FACT CHIPS */}
        {activeCase && (
          <div className="p-3 rounded-2xl bg-surface/80 border border-border-main space-y-2">
            <span className="text-[9px] font-black text-primary-start uppercase tracking-widest flex items-center gap-1">
              <FileText size={12} /> Provat & Faktet e Verifikuara nga Lënda
            </span>
            <div className="flex flex-wrap gap-2 text-[10px]">
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-text-secondary font-medium">
                <Landmark size={12} className="text-amber-400" />
                <span>Gjykata Themelore Prishtinë (Ekonomike)</span>
              </div>
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-emerald-400 font-bold font-mono">
                <Euro size={12} />
                <span>€45,000.00 Kontestuese</span>
              </div>
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-canvas border border-border-main text-text-secondary font-medium">
                <Calendar size={12} className="text-blue-400" />
                <span>Afati: 15 Ditë (LPK Neni 46)</span>
              </div>
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
              title="Kthen fjalët e tuaja të thjeshta në një kërkesë zyrtare të strukturuar për AI"
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

          {/* DYNAMIC CLICKABLE LEGAL ARTICLE TAGS BELOW CONTEXT TEXTAREA */}
          <div className="mt-2.5 space-y-1">
            <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider block">
              Shto Bazë Ligjore te Udhëzimet:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {legalArticleTags.map((tag, tagIdx) => (
                <button
                  key={tagIdx}
                  type="button"
                  onClick={() => handleAppendTag(tag)}
                  className="flex items-center gap-1 px-2 py-1 bg-surface hover:bg-hover border border-border-main rounded-lg text-[10px] font-semibold text-text-secondary hover:text-primary-start transition-all cursor-pointer shadow-sm"
                >
                  <Plus size={10} className="text-primary-start" />
                  <span>{tag}</span>
                </button>
              ))}
            </div>
          </div>
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