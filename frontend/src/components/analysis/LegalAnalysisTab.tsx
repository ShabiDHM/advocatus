// FILE: src/components/analysis/LegalAnalysisTab.tsx
import React from 'react';
import { Info, Gavel, AlertTriangle, FileText, BookOpen, Globe, Scale } from 'lucide-react';
import { TFunction } from 'i18next';
import { RenderCitationItem } from './CitationRenderer';
import { splitExecutiveSummary } from '../../utils/analysisHelpers';

interface LegalAnalysisTabProps {
  summary: any;
  burden_of_proof: string;
  missing_evidence: any[];
  key_issues: any[];
  legal_basis: any[];
  t: TFunction;
}

export const LegalAnalysisTab: React.FC<LegalAnalysisTabProps> = ({
  summary,
  burden_of_proof,
  missing_evidence,
  key_issues,
  legal_basis,
  t,
}) => {
  const { unifiedText } = splitExecutiveSummary(summary);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Executive Summary Section - Unified without Qytetari/Avokati tabs */}
        <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm flex flex-col h-auto">
          <div className="flex items-center justify-between mb-4 border-b border-main pb-3">
            <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest flex items-center gap-2">
              <Info size={15} className="text-primary-start" /> {t('analysis.section_summary', 'Përmbledhje Ekzekutive')}
            </h3>
          </div>
          <div className="text-text-secondary leading-relaxed border-l-2 border-primary-start/40 pl-4 ml-1 animate-in fade-in duration-300">
            <RenderCitationItem item={unifiedText} />
          </div>
        </div>

        {/* Burden of Proof */}
        {burden_of_proof && (
          <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm flex flex-col justify-between">
            <div>
              <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest mb-4 flex items-center gap-2">
                <Gavel size={15} className="text-primary-start" /> {t('analysis.section_burden', 'Barra e Provës')}
              </h3>
              <div className="text-text-secondary leading-relaxed italic border-l-2 border-primary-start/30 pl-4 ml-1">
                <RenderCitationItem item={burden_of_proof} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Missing Evidence - Highlighted in Amber Warning Colors */}
      {missing_evidence && missing_evidence.length > 0 && (
        <div className="bg-amber-500/10 p-6 rounded-2xl border border-amber-500/30 shadow-md shadow-amber-500/5">
          <h3 className="text-[11px] font-black text-amber-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-400 shrink-0 animate-pulse" />
            {t('analysis.section_missing', 'Mungesa e Provave')}
          </h3>
          <div className="grid gap-3">
            {missing_evidence.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 text-text-primary bg-surface/90 p-4 rounded-xl border border-amber-500/20 shadow-sm"
              >
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shrink-0 animate-ping" />
                <div className="font-medium">
                  <RenderCitationItem item={item} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Issues */}
      {key_issues && key_issues.length > 0 && (
        <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm">
          <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest mb-4 flex items-center gap-2">
            <FileText size={15} className="text-primary-start" /> {t('analysis.section_issues', 'Çështjet Kryesore')}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {key_issues.map((issue: any, idx: number) => (
              <div key={idx} className="flex items-start gap-3 bg-canvas/40 p-4 rounded-xl border border-main">
                <span className="text-primary-start font-black text-sm leading-none opacity-60 mt-0.5">#{idx + 1}</span>
                <div className="text-text-secondary font-medium leading-relaxed">
                  <RenderCitationItem item={issue} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Statutory Legal Basis */}
      {legal_basis && legal_basis.length > 0 && (
        <div className="bg-primary-start/5 p-6 rounded-2xl border border-primary-start/20 shadow-sm">
          <h3 className="text-[11px] font-black text-primary-start uppercase tracking-widest mb-4 flex items-center gap-2">
            <BookOpen size={15} /> {t('analysis.section_rules', 'Baza Ligjore (Statutore)')}
          </h3>
          <ul className="space-y-3">
            {legal_basis.map((lawItem: any, i: number) => {
              const lawStr = typeof lawItem === 'string' ? lawItem : lawItem.law || '';
              const isGlobal = lawStr.includes('UNCRC') || lawStr.includes('Konventa') || lawStr.includes('KEDNJ');
              return (
                <li
                  key={i}
                  className={`flex gap-3 text-xs items-start p-4 rounded-xl transition-colors shadow-sm bg-surface border ${
                    isGlobal ? 'border-indigo-500/30' : 'border-main'
                  }`}
                >
                  {isGlobal ? (
                    <Globe size={18} className="text-indigo-400 shrink-0 mt-0.5" />
                  ) : (
                    <Scale size={18} className="text-primary-start shrink-0 mt-0.5" />
                  )}
                  <RenderCitationItem item={lawItem} />
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};