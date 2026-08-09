// FILE: src/components/analysis/WarRoomTab.tsx
// PHOENIX PROTOCOL - WAR ROOM TAB V33.0 (ALBANIAN SEVERITY BADGES & NDIKIMI FORMATTING)

import React, { useState } from 'react';
import { Target, Skull, Clock, AlertOctagon, ShieldAlert, CheckCircle2, FileText, Scale } from 'lucide-react';
import { TFunction } from 'i18next';
import { DeepAnalysisResult, ChronologyEvent, Contradiction } from '../../data/types';
import { RenderCitationItem } from './CitationRenderer';
import { Spinner } from './AnalysisBadges';
import { safeString, cleanActionStepText } from '../../utils/analysisHelpers';

interface WarRoomTabProps {
  deepResult: DeepAnalysisResult | null;
  strategicAnalysis: string;
  weaknesses: any[];
  actionPlan: any[];
  isSimLoading: boolean;
  isChronLoading: boolean;
  isContradictLoading: boolean;
  t: TFunction;
}

export const WarRoomTab: React.FC<WarRoomTabProps> = ({
  deepResult,
  strategicAnalysis,
  weaknesses,
  actionPlan,
  isSimLoading,
  isChronLoading,
  isContradictLoading,
  t,
}) => {
  const [warRoomSubTab, setWarRoomSubTab] = useState<'strategy' | 'adversarial' | 'timeline' | 'contradictions'>('strategy');

  const subTabBaseClass =
    'px-3 py-2 sm:px-4 sm:py-2.5 rounded-xl text-[10px] sm:text-[11px] font-black uppercase tracking-widest transition-all border flex items-center justify-center gap-1.5 sm:gap-2 cursor-pointer focus:outline-none shadow-sm whitespace-nowrap shrink-0';
  const activeSubTabClass = 'bg-primary-start border-primary-start text-white shadow-md shadow-primary-start/20';
  const inactiveSubTabClass = 'bg-surface border-main text-text-secondary hover:text-text-primary hover:border-primary-start/40 hover:bg-hover';

  const renderSubTabLoader = () => (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-16 sm:py-24 bg-canvas/50 rounded-2xl border border-main">
      <Spinner size="w-12 h-12 sm:w-14 sm:h-14" />
      <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-widest mb-1.5 mt-4 sm:mt-5">
        {t('analysis.loading_deep_title', 'Duke Simuluar...')}
      </h3>
      <p className="text-text-muted text-[10px] sm:text-[11px] font-bold uppercase tracking-widest">
        {t('analysis.rag_processing', 'Analiza e thellë statutore...')}
      </p>
    </div>
  );

  const simObj = ((deepResult as any)?.adversarial_simulation?.adversarial_simulation ||
    (deepResult as any)?.adversarial_simulation ||
    {}) as any;
  const opponentStrategy = safeString(
    simObj.opponent_strategy || simObj.strategy || simObj.description || (typeof simObj === 'string' ? simObj : 'Strategjia e kundërshtarit është përpunuar.')
  );
  const weaknessAttacks = Array.isArray(simObj.weakness_attacks) ? simObj.weakness_attacks : [];

  const getRiskLabel = (level: string) => {
    const l = (level || '').toUpperCase();
    if (l.includes('CRIT') || l === 'CRITICAL') return { label: 'KRITIKE', style: 'bg-rose-500/20 text-rose-400 border-rose-500/40 font-black' };
    if (l.includes('HIGH') || l === 'LARTË') return { label: 'E LARTË', style: 'bg-rose-500/20 text-rose-400 border-rose-500/40 font-black' };
    if (l.includes('MED') || l === 'MESËM') return { label: 'E MESME', style: 'bg-amber-500/20 text-amber-400 border-amber-500/40 font-black' };
    if (l.includes('LOW') || l === 'ULËT') return { label: 'E ULËT', style: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 font-black' };
    return { label: 'KRITIKE', style: 'bg-rose-500/20 text-rose-400 border-rose-500/40 font-black' };
  };

  return (
    <div className="h-full flex flex-col">
      {/* Horizontally scrollable Subtabs Bar for Mobile */}
      <div className="flex gap-1.5 sm:gap-2 mb-4 sm:mb-6 shrink-0 p-1 sm:p-1.5 bg-canvas rounded-xl sm:rounded-2xl border border-main overflow-x-auto no-scrollbar scroll-smooth w-full sm:w-fit">
        <button
          type="button"
          onClick={() => setWarRoomSubTab('strategy')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'strategy' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <Target size={13} className="shrink-0" /> {t('analysis.subtab_strategy', 'Plani Strategjik')}
        </button>
        <button
          type="button"
          onClick={() => setWarRoomSubTab('adversarial')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'adversarial' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <Skull size={13} className="shrink-0" /> {t('analysis.subtab_adversarial', 'Simulimi i Palës')}
        </button>
        <button
          type="button"
          onClick={() => setWarRoomSubTab('timeline')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'timeline' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <Clock size={13} className="shrink-0" /> {t('analysis.subtab_timeline', 'Kronologjia')}
        </button>
        <button
          type="button"
          onClick={() => setWarRoomSubTab('contradictions')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'contradictions' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <AlertOctagon size={13} className="shrink-0 text-amber-400" /> {t('analysis.subtab_contradictions', 'Kontradiktat')}
        </button>
      </div>

      <div className="space-y-4 sm:space-y-6 animate-in fade-in">
        {warRoomSubTab === 'strategy' ? (
          <div className="space-y-4 sm:space-y-6">
            <div className="bg-surface p-4 sm:p-6 rounded-2xl border border-main shadow-sm">
              <h3 className="text-[10px] sm:text-[11px] font-black text-text-secondary uppercase tracking-widest mb-3 sm:mb-4 flex items-center gap-2">
                <Target size={14} className="text-primary-start shrink-0" /> {t('analysis.section_analysis', 'Analiza Strategjike')}
              </h3>
              <div className="text-text-secondary text-xs sm:text-sm leading-relaxed border-l-2 border-primary-start/40 pl-3 sm:pl-4 ml-0.5">
                <RenderCitationItem item={strategicAnalysis} />
              </div>
            </div>

            {/* Weaknesses Highlighted in Vivid Danger Red Colors */}
            <div className="bg-rose-500/10 p-4 sm:p-6 rounded-2xl border border-rose-500/30 shadow-md shadow-rose-500/5">
              <h3 className="text-[10px] sm:text-[11px] font-black text-rose-400 uppercase tracking-widest mb-3 sm:mb-4 flex items-center gap-2">
                <ShieldAlert size={15} className="text-rose-400 shrink-0" /> {t('analysis.section_weaknesses', 'Dobësitë e Kundërshtarit / Rreziku')}
              </h3>
              <ul className="space-y-2.5 sm:space-y-3">
                {weaknesses.map((w: any, i: number) => (
                  <li key={i} className="flex items-center gap-2.5 sm:gap-3 text-text-primary bg-surface/90 p-3 sm:p-3.5 rounded-xl border border-rose-500/20 shadow-sm text-xs sm:text-sm">
                    <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0 shadow-sm shadow-rose-500/50" />
                    <div className="font-medium">
                      <RenderCitationItem item={w} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Action Plan - Unified without HAPAT PËR QYTETARIN / HAPAT PËR AVOKATIN */}
            <div className="bg-emerald-500/10 p-4 sm:p-6 rounded-2xl border border-emerald-500/30 shadow-sm">
              <h3 className="text-[10px] sm:text-[11px] font-black text-emerald-400 uppercase tracking-widest mb-3 sm:mb-4 flex items-center gap-2">
                <CheckCircle2 size={15} className="text-emerald-400 shrink-0" /> {t('analysis.section_conclusion', 'Plani i Veprimit')}
              </h3>
              <div className="space-y-2.5 sm:space-y-3">
                {actionPlan.map((step: any, i: number) => {
                  const cleanedStep = cleanActionStepText(step);
                  return (
                    <div key={i} className="flex items-start gap-3 sm:gap-4 text-text-primary bg-surface/90 p-3.5 sm:p-4 rounded-xl border border-emerald-500/20 shadow-sm text-xs sm:text-sm">
                      <span className="flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-emerald-500/20 text-emerald-400 font-black text-[11px] sm:text-xs shrink-0">
                        {i + 1}
                      </span>
                      <span className="leading-relaxed font-medium mt-0.5">
                        <RenderCitationItem item={cleanedStep} />
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : warRoomSubTab === 'adversarial' ? (
          isSimLoading ? (
            renderSubTabLoader()
          ) : deepResult?.adversarial_simulation ? (
            <div className="space-y-4 sm:space-y-6">
              <div className="bg-rose-500/10 p-4 sm:p-6 rounded-2xl border border-rose-500/30 shadow-lg shadow-rose-500/5">
                <h3 className="text-[10px] sm:text-[11px] font-black text-rose-400 mb-3 sm:mb-4 uppercase tracking-widest flex items-center gap-2">
                  <Skull size={15} className="text-rose-400 shrink-0" /> {t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}
                </h3>
                <div className="text-text-primary text-xs sm:text-sm leading-relaxed font-medium">
                  <RenderCitationItem item={opponentStrategy} />
                </div>
              </div>

              {weaknessAttacks.length > 0 && (
                <div className="grid gap-2.5 sm:gap-3">
                  {weaknessAttacks.map((attack: string, i: number) => (
                    <div key={i} className="flex gap-2.5 sm:gap-3 bg-surface p-3.5 sm:p-4 rounded-xl border border-rose-500/20 shadow-sm text-xs sm:text-sm">
                      <Target size={15} className="text-rose-400 shrink-0 mt-0.5" />
                      <div className="text-text-secondary leading-relaxed font-medium">
                        <RenderCitationItem item={attack} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-16 text-text-secondary text-xs sm:text-sm">
              <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit të simulimit.')}</p>
            </div>
          )
        ) : warRoomSubTab === 'timeline' ? (
          isChronLoading ? (
            renderSubTabLoader()
          ) : deepResult?.chronology ? (
            <div className="space-y-4 sm:space-y-5 relative border-l-2 border-primary-start/40 ml-3 sm:ml-4 pl-4 sm:pl-6 py-1 sm:py-2">
              {deepResult.chronology.map((event: ChronologyEvent, i: number) => (
                <div key={i} className="relative group bg-surface p-3.5 sm:p-4 rounded-xl border border-main shadow-sm">
                  <div className="absolute -left-[23px] sm:-left-[33px] top-4 sm:top-5 w-3 h-3 sm:w-3.5 sm:h-3.5 rounded-full bg-canvas border-2 sm:border-4 border-primary-start shadow-sm" />
                  <div className="flex flex-col gap-1">
                    <span className="text-primary-start font-mono text-[9px] sm:text-[10px] uppercase tracking-widest font-black">{event.date}</span>
                    <div className="text-text-secondary text-xs sm:text-sm leading-relaxed font-medium">
                      <RenderCitationItem item={event.event} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 text-text-secondary text-xs sm:text-sm">
              <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p>
            </div>
          )
        ) : warRoomSubTab === 'contradictions' ? (
          isContradictLoading ? (
            renderSubTabLoader()
          ) : deepResult?.contradictions ? (
            <div className="grid gap-4 sm:gap-5">
              {deepResult.contradictions.length === 0 ? (
                <div className="bg-surface p-8 sm:p-10 rounded-2xl text-center border border-main shadow-sm">
                  <CheckCircle2 size={36} className="mx-auto mb-2.5 text-emerald-400" />
                  <p className="text-text-primary font-bold text-sm sm:text-base">{t('analysis.no_contradictions', 'Gjithçka e pastër.')}</p>
                  <p className="text-text-muted text-[11px] sm:text-xs mt-1 font-medium">Nuk u gjetën kontradikta mes deklaratave dhe provave.</p>
                </div>
              ) : (
                deepResult.contradictions.map((c: Contradiction, i: number) => {
                  const riskInfo = getRiskLabel(c.severity);
                  return (
                    <div key={i} className="bg-amber-500/10 border border-amber-500/30 p-4 sm:p-5 rounded-2xl shadow-md shadow-amber-500/5">
                      <div className="flex justify-between items-center mb-3 sm:mb-4 pb-2.5 sm:pb-3 border-b border-amber-500/20 gap-2">
                        <div className="flex items-center gap-1.5 sm:gap-2 text-amber-400 font-black text-[10px] sm:text-xs uppercase tracking-widest truncate">
                          <AlertOctagon size={15} className="text-amber-400 shrink-0" />
                          <span className="truncate">{t('analysis.contradiction_label', 'Mospërputhje Faktike / Kontradiktë')}</span>
                        </div>
                        <span className={`text-[9px] sm:text-[10px] font-black px-2.5 py-0.5 rounded border uppercase tracking-widest shrink-0 ${riskInfo.style}`}>
                          {riskInfo.label}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 mb-3">
                        <div className="p-3.5 sm:p-4 bg-surface rounded-xl border border-rose-500/30 shadow-sm">
                          <span className="text-[9px] sm:text-[10px] text-rose-400 font-black uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                            <FileText size={12} className="text-rose-400 shrink-0" /> {t('analysis.claim_label', 'Deklarata')}
                          </span>
                          <div className="text-text-primary leading-relaxed italic text-xs font-medium">
                            &quot;<RenderCitationItem item={c.claim} />&quot;
                          </div>
                        </div>

                        <div className="p-3.5 sm:p-4 bg-surface rounded-xl border border-emerald-500/30 shadow-sm">
                          <span className="text-[9px] sm:text-[10px] text-emerald-400 font-black uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                            <Scale size={12} className="text-emerald-400 shrink-0" /> {t('analysis.evidence_label', 'Prova Objektive')}
                          </span>
                          <div className="text-text-primary font-medium leading-relaxed text-xs">
                            <RenderCitationItem item={c.evidence} />
                          </div>
                        </div>
                      </div>

                      <div className="mt-2.5 sm:mt-3 p-3 sm:p-3.5 bg-surface/80 rounded-xl border border-amber-500/20 text-xs">
                        <span className="text-[9px] sm:text-[10px] text-amber-400 font-black uppercase tracking-widest block mb-1">
                          Ndikimi
                        </span>
                        <div className="text-text-secondary leading-relaxed font-medium text-xs">
                          <RenderCitationItem item={c.impact} />
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          ) : (
            <div className="text-center py-16 text-text-secondary text-xs sm:text-sm">
              <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p>
            </div>
          )
        ) : null}
      </div>
    </div>
  );
};