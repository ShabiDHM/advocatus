// FILE: src/components/analysis/WarRoomTab.tsx
import React, { useState } from 'react';
import { Target, Skull, Clock, AlertOctagon, ShieldAlert, CheckCircle2, FileText, Scale } from 'lucide-react';
import { TFunction } from 'i18next';
import { DeepAnalysisResult, ChronologyEvent, Contradiction } from '../../data/types';
import { RenderCitationItem } from './CitationRenderer';
import { Spinner } from './AnalysisBadges';
import { safeString } from '../../utils/analysisHelpers';

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
    'px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all border border-main flex items-center justify-center gap-2 cursor-pointer focus:outline-none hover-lift shadow-sm w-full sm:w-auto h-11 sm:h-auto shrink-0';
  const activeSubTabClass = 'bg-primary-start border-primary-start text-white shadow-accent-glow';
  const inactiveSubTabClass = 'bg-surface text-text-secondary hover:text-text-primary hover:bg-hover';

  const renderSubTabLoader = () => (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-32 bg-canvas">
      <Spinner size="w-16 h-16" />
      <h3 className="text-lg font-black text-text-primary uppercase tracking-widest mb-3 mt-6">
        {t('analysis.loading_deep_title', 'Duke Simuluar...')}
      </h3>
      <p className="text-text-muted text-[12px] font-bold uppercase tracking-widest">
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
    const l = level?.toUpperCase();
    if (l === 'HIGH') return t('analysis.risk_high', 'I LARTË');
    if (l === 'MEDIUM') return t('analysis.risk_medium', 'I MESËM');
    if (l === 'LOW') return t('analysis.risk_low', 'I ULËT');
    return level;
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex flex-col sm:flex-row flex-wrap gap-2 mb-6 shrink-0 pb-1">
        <button
          type="button"
          onClick={() => setWarRoomSubTab('strategy')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'strategy' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <Target size={14} className="inline shrink-0" /> {t('analysis.subtab_strategy', 'Plani Strategjik')}
        </button>
        <button
          type="button"
          onClick={() => setWarRoomSubTab('adversarial')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'adversarial' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <Skull size={14} className="inline shrink-0" /> {t('analysis.subtab_adversarial', 'Simulimi i Palës')}
        </button>
        <button
          type="button"
          onClick={() => setWarRoomSubTab('timeline')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'timeline' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <Clock size={14} className="inline shrink-0" /> {t('analysis.subtab_timeline', 'Kronologjia')}
        </button>
        <button
          type="button"
          onClick={() => setWarRoomSubTab('contradictions')}
          className={`${subTabBaseClass} ${warRoomSubTab === 'contradictions' ? activeSubTabClass : inactiveSubTabClass}`}
        >
          <AlertOctagon size={14} className="inline shrink-0" /> {t('analysis.subtab_contradictions', 'Kontradiktat')}
        </button>
      </div>

      <div className="space-y-6 animate-in fade-in">
        {warRoomSubTab === 'strategy' ? (
          <div className="space-y-6">
            <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm">
              <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest mb-4 flex items-center gap-2">
                <Target size={15} className="text-primary-start" /> {t('analysis.section_analysis', 'Analiza Strategjike')}
              </h3>
              <div className="text-text-secondary leading-relaxed border-l-2 border-primary-start/30 pl-4 ml-1">
                <RenderCitationItem item={strategicAnalysis} />
              </div>
            </div>

            <div className="bg-danger-start/5 p-6 rounded-2xl border border-danger-start/20 shadow-sm">
              <h3 className="text-[11px] font-black text-danger-start uppercase tracking-widest mb-4 flex items-center gap-2">
                <ShieldAlert size={15} /> {t('analysis.section_weaknesses', 'Pikat e Dobëta (Risku)')}
              </h3>
              <ul className="space-y-3">
                {weaknesses.map((w: any, i: number) => (
                  <li key={i} className="flex items-center gap-3 text-text-secondary bg-surface p-3.5 rounded-xl border border-danger-start/10 shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-danger-start shrink-0 opacity-50" />
                    <RenderCitationItem item={w} />
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-status-success/5 p-6 rounded-2xl border border-status-success/20 shadow-sm">
              <h3 className="text-[11px] font-black text-status-success uppercase tracking-widest mb-4 flex items-center gap-2">
                <CheckCircle2 size={15} /> {t('analysis.section_conclusion', 'Plani i Veprimit (Hapat)')}
              </h3>
              <div className="space-y-3">
                {actionPlan.map((step: any, i: number) => (
                  <div key={i} className="flex items-start gap-4 text-text-secondary bg-surface p-4 rounded-xl border border-status-success/10 shadow-sm">
                    <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-status-success/20 text-status-success font-black text-xs shrink-0">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed font-medium mt-0.5">
                      <RenderCitationItem item={step} />
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : warRoomSubTab === 'adversarial' ? (
          isSimLoading ? (
            renderSubTabLoader()
          ) : deepResult?.adversarial_simulation ? (
            <div className="space-y-6">
              <div className="bg-surface p-6 rounded-2xl border border-danger-start/30 shadow-lg shadow-danger-start/5">
                <h3 className="text-[11px] font-black text-danger-start mb-4 uppercase tracking-widest flex items-center gap-2">
                  <Skull size={15} /> {t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}
                </h3>
                <div className="text-text-secondary leading-relaxed font-medium">
                  <RenderCitationItem item={opponentStrategy} />
                </div>
              </div>

              {weaknessAttacks.length > 0 && (
                <div className="grid gap-3">
                  {weaknessAttacks.map((attack: string, i: number) => (
                    <div key={i} className="flex gap-3 bg-surface p-4 rounded-xl border border-main shadow-sm">
                      <Target size={16} className="text-danger-start shrink-0 mt-0.5" />
                      <div className="text-text-secondary leading-relaxed">
                        <RenderCitationItem item={attack} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-20 text-text-secondary">
              <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit të simulimit.')}</p>
            </div>
          )
        ) : warRoomSubTab === 'timeline' ? (
          isChronLoading ? (
            renderSubTabLoader()
          ) : deepResult?.chronology ? (
            <div className="space-y-5 relative border-l-2 border-main ml-4 pl-6 py-2">
              {deepResult.chronology.map((event: ChronologyEvent, i: number) => (
                <div key={i} className="relative group bg-surface p-4 rounded-xl border border-main shadow-sm">
                  <div className="absolute -left-[33px] top-5 w-3.5 h-3.5 rounded-full bg-canvas border-4 border-indigo-500 shadow-sm" />
                  <div className="flex flex-col gap-1.5">
                    <span className="text-indigo-500 font-mono text-[10px] uppercase tracking-widest font-black">{event.date}</span>
                    <div className="text-text-secondary leading-relaxed">
                      <RenderCitationItem item={event.event} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-20 text-text-secondary">
              <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p>
            </div>
          )
        ) : warRoomSubTab === 'contradictions' ? (
          isContradictLoading ? (
            renderSubTabLoader()
          ) : deepResult?.contradictions ? (
            <div className="grid gap-5">
              {deepResult.contradictions.length === 0 ? (
                <div className="bg-surface p-10 rounded-2xl text-center border border-main shadow-sm">
                  <CheckCircle2 size={40} className="mx-auto mb-3 text-status-success/50 animate-bounce" />
                  <p className="text-text-primary font-bold text-base">{t('analysis.no_contradictions', 'Gjithçka e pastër.')}</p>
                  <p className="text-text-muted text-xs mt-1 font-medium">Nuk u gjetën kontradikta mes deklaratave dhe provave.</p>
                </div>
              ) : (
                deepResult.contradictions.map((c: Contradiction, i: number) => (
                  <div key={i} className="bg-surface border border-warning-start/30 p-5 rounded-2xl shadow-md shadow-warning-start/5">
                    <div className="flex justify-between items-start mb-4 pb-3 border-b border-main">
                      <div className="flex items-center gap-2 text-warning-start font-black text-xs uppercase tracking-widest">
                        <AlertOctagon size={15} /> {t('analysis.contradiction_label', 'Mospërputhje Factual')}
                      </div>
                      <span className="text-[10px] font-black bg-warning-start/10 text-warning-start px-2 py-0.5 rounded border border-warning-start/20 uppercase tracking-widest">
                        {getRiskLabel(c.severity)}
                      </span>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4 mb-3">
                      <div className="p-4 bg-canvas rounded-xl border border-main">
                        <span className="text-[10px] text-danger-start font-black uppercase tracking-widest mb-2 flex items-center gap-1.5">
                          <FileText size={13} /> {t('analysis.claim_label', 'Deklarata')}
                        </span>
                        <div className="text-text-secondary leading-relaxed italic text-xs">
                          &quot;<RenderCitationItem item={c.claim} />&quot;
                        </div>
                      </div>
                      <div className="p-4 bg-canvas rounded-xl border border-main">
                        <span className="text-[10px] text-status-success font-black uppercase tracking-widest mb-2 flex items-center gap-1.5">
                          <Scale size={13} /> {t('analysis.evidence_label', 'Prova Objektive')}
                        </span>
                        <div className="text-text-secondary font-medium leading-relaxed text-xs">
                          <RenderCitationItem item={c.evidence} />
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 p-3 bg-warning-start/5 rounded-xl border border-warning-start/10 text-xs">
                      <span className="text-[10px] text-warning-start font-black uppercase tracking-widest block mb-1">Impakti</span>
                      <div className="text-text-secondary leading-relaxed">
                        <RenderCitationItem item={c.impact} />
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="text-center py-20 text-text-secondary">
              <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p>
            </div>
          )
        ) : null}
      </div>
    </div>
  );
};