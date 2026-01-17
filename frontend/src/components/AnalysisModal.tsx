// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V8.6 (CRASH HOTFIX)
// 1. HOTFIX: Added strict type checking (typeof === 'string') inside .map() loops.
// 2. STABILITY: Prevents 'F.includes is not a function' crashes when AI returns objects instead of strings.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Scale, FileText, Swords, Target,
    Gavel, CheckCircle2, BookOpen, Globe, 
    Link as LinkIcon, Clock, Skull, AlertOctagon, BrainCircuit
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CaseAnalysisResult, DeepAnalysisResult } from '../data/types'; 
import { apiService } from '../services/api';

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: CaseAnalysisResult; 
  caseId: string;
  isLoading?: boolean;
}

const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 5px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 3px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); }
`;

// Helper: Safely converts any AI output to a string
const safeString = (val: any): string => {
    if (!val) return "";
    if (typeof val === 'string') return val;
    // If AI returns an object like { "title": "Law", "desc": "..." }, flatten it
    if (typeof val === 'object') return Object.values(val).join(': ');
    return String(val);
};

const cleanLegalText = (text: any): string => {
    let clean = safeString(text);
    clean = clean.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
    clean = clean.replace(/^Ligji\/Neni \(Kosovë\):\s*/i, '');
    clean = clean.replace(/^Konventa \(Global\):\s*/i, '');
    return clean;
};

const renderStructuredCitation = (rawText: any) => {
    const text = safeString(rawText);
    let match = text.match(/^\[(.*?)\]\((.*?)\):?\s*(.*)/s);
    if (!match) match = text.match(/^(.*?)\((doc:\/\/.*?)\):?\s*(.*)/s);

    if (match) {
        const title = match[1].trim();
        const link = match[2].trim(); 
        const body = match[3].trim();

        return (
            <div className="flex flex-col gap-2 w-full">
                <div className="flex items-center gap-2 font-bold text-primary-200 text-xs uppercase tracking-wide cursor-pointer hover:text-white transition-colors group">
                    <LinkIcon size={12} className="text-primary-400 group-hover:text-white" />
                    <span title={link} className="border-b border-dashed border-primary-500/30 pb-0.5">{title}</span>
                </div>
                <div className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed pl-5 border-l border-white/10 ml-0.5">
                    {body.split('\n').map((line, i) => {
                        const trimmed = line.trim();
                        if (!trimmed) return null;
                        if (trimmed.startsWith('Përmbajtja:') || trimmed.startsWith('Relevanca:')) {
                            const splitIdx = trimmed.indexOf(':');
                            const key = trimmed.substring(0, splitIdx);
                            const val = trimmed.substring(splitIdx + 1);
                            return (
                                <div key={i} className="mb-2 last:mb-0">
                                    <span className={`font-semibold text-xs uppercase tracking-wider ${key === 'Relevanca' ? 'text-emerald-400' : 'text-secondary-400'}`}>
                                        {key}
                                    </span>
                                    <div className="mt-0.5 text-gray-200">{val.trim()}</div>
                                </div>
                            );
                        }
                        return <div key={i} className="mb-1">{trimmed}</div>;
                    })}
                </div>
            </div>
        );
    }
    return <span className="leading-relaxed font-mono text-xs whitespace-pre-wrap">{cleanLegalText(text)}</span>;
};

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, caseId, isLoading }) => {
  const { t } = useTranslation();
  
  const [activeTab, setActiveTab] = useState<'legal' | 'war_room'>('legal');
  const [warRoomSubTab, setWarRoomSubTab] = useState<'strategy' | 'adversarial' | 'timeline' | 'contradictions'>('strategy');
  
  const [deepResult, setDeepResult] = useState<DeepAnalysisResult | null>(null);
  const [isDeepLoading, setIsDeepLoading] = useState(false);

  useEffect(() => {
    if (isOpen) { 
        document.body.style.overflow = 'hidden';
        setActiveTab('legal');
        setWarRoomSubTab('strategy');
    } else { 
        document.body.style.overflow = 'unset'; 
    }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  const handleWarRoomEntry = async () => {
      setActiveTab('war_room');
      if (!deepResult && !isDeepLoading) {
          setIsDeepLoading(true);
          try {
              const data = await apiService.analyzeDeepStrategy(caseId);
              setDeepResult(data);
          } catch (error) {
              console.error("Deep Analysis Failed", error);
          } finally {
              setIsDeepLoading(false);
          }
      }
  };

  const {
      summary = "",
      key_issues = [],
      legal_basis = [],
      strategic_analysis = "",
      weaknesses = [],
      action_plan = [],
      risk_level = "MEDIUM"
  } = result || {};

  const getRiskColor = (level: string) => {
      if (level?.includes('HIGH')) return 'bg-red-500/20 text-red-400 border-red-500/50';
      if (level?.includes('LOW')) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
  };

  const getRiskLabel = (level: string) => {
      const l = level?.toUpperCase();
      if (l === 'HIGH') return t('analysis.risk_high', 'I LARTË');
      if (l === 'MEDIUM') return t('analysis.risk_medium', 'I MESËM');
      if (l === 'LOW') return t('analysis.risk_low', 'I ULËT');
      return level;
  };

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-[100] p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.98, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.98, opacity: 0, y: 10 }} className="glass-high w-full h-full sm:h-[90vh] sm:max-w-6xl rounded-none sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-white/10" onClick={(e) => e.stopPropagation()}>
          
          {/* HEADER */}
          <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/5 backdrop-blur-md shrink-0">
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-3 min-w-0">
              <div className="p-2 bg-gradient-to-br from-primary-start to-primary-end rounded-lg shrink-0 shadow-lg shadow-primary-start/20">
                  <Gavel className="text-white h-5 w-5" />
              </div>
              <div className="flex flex-col">
                  <span className="truncate leading-tight tracking-tight">{t('analysis.title', 'Salla e Strategjisë Ligjore')}</span>
                  <div className={`text-[10px] uppercase tracking-widest font-bold mt-1 px-1.5 py-0.5 rounded border w-fit ${getRiskColor(risk_level)}`}>
                      {t('analysis.risk_label', 'RREZIKU')}: {getRiskLabel(risk_level)}
                  </div>
              </div>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-xl transition-colors shrink-0"><X size={20} /></button>
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                 <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div>
                 <h3 className="text-xl font-bold text-white mb-2">{t('analysis.loading_title', 'Duke Analizuar Ligjet & Faktet...')}</h3>
                 <p className="text-text-secondary text-sm max-w-sm mx-auto">{t('analysis.loading_desc', 'Avokati AI po verifikon bazën ligjore.')}</p>
             </div>
          ) : (
             <>
                {/* MAIN TABS */}
                <div className="flex border-b border-white/5 px-6 bg-black/20 shrink-0 overflow-x-auto no-scrollbar gap-6">
                    <button onClick={() => setActiveTab('legal')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'legal' ? 'border-primary-start text-white' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Scale size={16}/> {t('analysis.tab_legal', 'Analiza Ligjore')}
                    </button>
                    <button onClick={handleWarRoomEntry} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'war_room' ? 'border-red-500 text-red-400' : 'border-transparent text-text-secondary hover:text-red-300'}`}>
                        <Swords size={16}/> {t('analysis.tab_war_room', 'Dhoma e Luftës')}
                    </button>
                </div>

                {/* CONTENT AREA */}
                <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-black/10">
                    <style>{scrollbarStyles}</style>

                    {/* --- TAB 1: LEGAL ANALYSIS --- */}
                    {activeTab === 'legal' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="glass-panel p-6 rounded-2xl">
                                <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <FileText size={16}/> {t('analysis.section_summary', 'Përmbledhje Ekzekutive')}
                                </h3>
                                <p className="text-white text-sm leading-relaxed whitespace-pre-line border-l-2 border-white/20 pl-4">{cleanLegalText(summary)}</p>
                            </div>

                            {key_issues && key_issues.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-white/5 bg-white/5">
                                    <h3 className="text-xs font-bold text-primary-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <Swords size={16}/> {t('analysis.section_issues', 'Çështjet Kryesore')}
                                    </h3>
                                    <div className="grid gap-3">
                                        {key_issues.map((issue: any, idx: number) => (
                                            <div key={idx} className="flex items-start gap-3 bg-white/5 p-3 rounded-lg border border-white/10">
                                                <span className="text-primary-400 font-bold mt-0.5">#{idx + 1}</span>
                                                <p className="text-sm text-gray-200 font-medium leading-snug">{cleanLegalText(issue)}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {legal_basis && legal_basis.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-secondary-start/20 bg-secondary-start/5">
                                    <h3 className="text-xs font-bold text-secondary-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <BookOpen size={16}/> {t('analysis.section_rules', 'Baza Ligjore')}
                                    </h3>
                                    <ul className="space-y-3">
                                        {legal_basis.map((law: any, i: number) => {
                                            // PHOENIX FIX: Strict type check before .includes()
                                            const lawStr = safeString(law);
                                            const isGlobal = lawStr.includes("UNCRC") || lawStr.includes("Konventa") || lawStr.includes("KEDNJ");
                                            return (
                                                <li key={i} className={`flex gap-3 text-sm items-start p-4 rounded-xl transition-colors ${isGlobal ? 'bg-indigo-500/10 border border-indigo-500/30' : 'bg-white/5 border border-white/5 hover:border-white/10'}`}>
                                                    {isGlobal ? <Globe size={20} className="text-indigo-400 shrink-0 mt-0.5"/> : <Scale size={20} className="text-secondary-400 shrink-0 mt-0.5"/>}
                                                    {renderStructuredCitation(lawStr)}
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                    
                    {/* --- TAB 2: WAR ROOM (MERGED) --- */}
                    {activeTab === 'war_room' && (
                        <div className="h-full flex flex-col">
                            {/* SUB-TABS for War Room */}
                            <div className="flex gap-2 mb-6 shrink-0 border-b border-white/5 pb-4">
                                <button onClick={() => setWarRoomSubTab('strategy')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${warRoomSubTab === 'strategy' ? 'bg-accent-start text-white shadow-lg shadow-accent-start/20' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <Target size={14} className="inline mr-2" /> {t('analysis.subtab_strategy', 'Plani Strategjik')}
                                </button>
                                <button onClick={() => setWarRoomSubTab('adversarial')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${warRoomSubTab === 'adversarial' ? 'bg-red-500 text-white shadow-lg shadow-red-500/20' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <Skull size={14} className="inline mr-2" /> {t('analysis.subtab_adversarial', 'Simulimi')}
                                </button>
                                <button onClick={() => setWarRoomSubTab('timeline')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${warRoomSubTab === 'timeline' ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <Clock size={14} className="inline mr-2" /> {t('analysis.subtab_timeline', 'Kronologjia')}
                                </button>
                                <button onClick={() => setWarRoomSubTab('contradictions')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${warRoomSubTab === 'contradictions' ? 'bg-yellow-500 text-black shadow-lg shadow-yellow-500/20' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <AlertOctagon size={14} className="inline mr-2" /> {t('analysis.subtab_contradictions', 'Kontradiktat')}
                                </button>
                            </div>

                            <div className="space-y-6 animate-in fade-in">
                                {/* STANDARD STRATEGY CONTENT */}
                                {warRoomSubTab === 'strategy' && (
                                    <div className="space-y-6">
                                        <div className="glass-panel p-6 rounded-2xl border-accent-start/20 bg-accent-start/5">
                                            <h3 className="text-xs font-bold text-accent-start uppercase tracking-wider mb-3">{t('analysis.section_analysis', 'Analiza Strategjike')}</h3>
                                            <p className="text-white text-sm leading-relaxed whitespace-pre-line">{cleanLegalText(strategic_analysis)}</p>
                                        </div>
                                        <div className="glass-panel p-6 rounded-2xl border-red-500/20 bg-red-500/5">
                                            <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-4">{t('analysis.section_weaknesses', 'Dobësitë e Kundërshtarit')}</h3>
                                            <ul className="space-y-3">
                                                {weaknesses.map((w: any, i: number) => (
                                                    <li key={i} className="flex gap-3 text-sm text-red-100 bg-red-500/10 p-3 rounded-lg border border-red-500/20">{cleanLegalText(w)}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="glass-panel p-6 rounded-2xl border-emerald-500/20 bg-emerald-500/5">
                                            <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-4">{t('analysis.section_conclusion', 'Plani i Veprimit')}</h3>
                                            <div className="space-y-3">
                                                {action_plan.map((step: any, i: number) => (
                                                    <div key={i} className="flex gap-4 text-sm text-white bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20">
                                                        <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500 text-black font-bold text-xs shrink-0">{i + 1}</span>
                                                        <span className="leading-relaxed font-medium">{cleanLegalText(step)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* DEEP ANALYSIS CONTENT */}
                                {warRoomSubTab !== 'strategy' && (
                                    isDeepLoading ? (
                                        <div className="flex-1 flex flex-col items-center justify-center text-center py-20">
                                            <BrainCircuit className="w-12 h-12 text-red-500 animate-pulse mb-4" />
                                            <h3 className="text-lg font-bold text-white mb-2">{t('analysis.loading_deep_title', 'Duke Simuluar...')}</h3>
                                        </div>
                                    ) : deepResult ? (
                                        <div className="space-y-6">
                                            {warRoomSubTab === 'adversarial' && (
                                                <div className="space-y-4">
                                                    <div className="glass-panel p-5 rounded-xl border border-red-500/30 bg-red-900/10">
                                                        <h3 className="text-sm font-bold text-red-300 mb-2 uppercase tracking-wide">{t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}</h3>
                                                        <p className="text-white/90 text-sm leading-relaxed">{deepResult.adversarial_simulation.opponent_strategy}</p>
                                                    </div>
                                                    <div className="grid gap-3">
                                                        {deepResult.adversarial_simulation.weakness_attacks.map((attack, i) => (
                                                            <div key={i} className="flex gap-3 bg-white/5 p-3 rounded-lg border border-white/10">
                                                                <Target size={16} className="text-red-400 shrink-0 mt-0.5" />
                                                                <span className="text-sm text-gray-300">{attack}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {warRoomSubTab === 'timeline' && (
                                                <div className="space-y-4 relative border-l-2 border-white/10 ml-3 pl-6 py-2">
                                                    {deepResult.chronology.map((event, i) => (
                                                        <div key={i} className="relative group">
                                                            <div className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-blue-500 border-2 border-black" />
                                                            <div className="flex gap-4">
                                                                <span className="text-blue-400 font-mono text-xs font-bold shrink-0 w-24">{event.date}</span>
                                                                <p className="text-gray-200 text-sm">{event.event}</p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {warRoomSubTab === 'contradictions' && (
                                                <div className="grid gap-4">
                                                    {deepResult.contradictions.length === 0 ? (
                                                        <div className="text-center py-10 text-gray-500">
                                                            <CheckCircle2 size={32} className="mx-auto mb-2 text-green-500/50" />
                                                            <p>{t('analysis.no_contradictions', 'Nuk u gjetën kontradikta.')}</p>
                                                        </div>
                                                    ) : (
                                                        deepResult.contradictions.map((c, i) => (
                                                            <div key={i} className="bg-yellow-500/5 border border-yellow-500/20 p-4 rounded-xl">
                                                                <div className="flex justify-between items-start mb-2">
                                                                    <div className="flex items-center gap-2 text-yellow-400 font-bold text-xs uppercase tracking-wider">{t('analysis.contradiction_label', 'Mospërputhje')}</div>
                                                                    <span className="text-[10px] bg-yellow-500/20 text-yellow-200 px-2 py-0.5 rounded border border-yellow-500/30">{t('analysis.risk_format', `RREZIK ${getRiskLabel(c.severity)}`, { level: getRiskLabel(c.severity) })}</span>
                                                                </div>
                                                                <div className="grid md:grid-cols-2 gap-4 mt-3">
                                                                    <div className="p-3 bg-black/20 rounded-lg">
                                                                        <span className="text-xs text-red-400 font-bold block mb-1">{t('analysis.claim_label', 'DEKLARATA')}</span>
                                                                        <p className="text-sm text-gray-300 italic">"{c.claim}"</p>
                                                                    </div>
                                                                    <div className="p-3 bg-black/20 rounded-lg">
                                                                        <span className="text-xs text-emerald-400 font-bold block mb-1">{t('analysis.evidence_label', 'FAKTI / PROVA')}</span>
                                                                        <p className="text-sm text-gray-300 font-mono">{c.evidence}</p>
                                                                    </div>
                                                                </div>
                                                                <p className="mt-3 text-xs text-gray-400 border-t border-white/5 pt-2">{c.impact}</p>
                                                            </div>
                                                        ))
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="text-center py-20 text-gray-500">
                                            <p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p>
                                        </div>
                                    )
                                )}
                            </div>
                        </div>
                    )}
                </div>
             </>
          )}
          
          <div className="p-4 border-t border-white/5 bg-background-dark/80 backdrop-blur-md text-center shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-10 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 text-white text-sm rounded-xl font-bold transition-all active:scale-95">
                  {t('general.close', 'Mbyll Sallen')}
              </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
  return ReactDOM.createPortal(modalContent, document.body);
};
export default AnalysisModal;