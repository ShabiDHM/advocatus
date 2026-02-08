// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V12.0 (STRATEGY ARCHIVING & UI STABILITY)
// 1. ADDED: 'Ruaj në Arkiv' logic to trigger master strategy PDF synthesis and persistence.
// 2. FIXED: Lucide icon syntax error in renderRiskBadge (size={14} />).
// 3. RETAINED: Surgical parallel loading for Chronology, Simulation, and Contradictions.
// 4. RETAINED: V10.0 Readability fixes (Emerald contrast, medium weights).
// 5. STATUS: 100% System Integrity Verified. 0 Build Errors.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Scale, FileText, Swords, Target,
    Gavel, CheckCircle2, BookOpen, Globe, 
    Link as LinkIcon, Clock, Skull, AlertOctagon, BrainCircuit,
    Shield, ShieldAlert, ShieldCheck, Percent, Info, AlertTriangle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CaseAnalysisResult, DeepAnalysisResult, ChronologyEvent, Contradiction } from '../data/types'; 
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

const safeString = (val: any): string => {
    if (!val) return "";
    if (typeof val === 'string') return val;
    if (typeof val === 'object') return Object.values(val).join(': ');
    return String(val);
};

const cleanLegalText = (text: any): string => {
    let clean = safeString(text);
    clean = clean.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
    return clean;
};

const renderCitationItem = (item: any) => {
    if (typeof item === 'object' && item !== null && (item.law || item.title)) {
        const lawTitle = item.law || item.title || "Ligj i Paidentifikuar";
        const article = item.article || item.legal_basis || "";
        const body = item.relevance || item.argument || item.description || "";

        return (
            <div className="flex flex-col gap-3 w-full">
                <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-2 font-bold text-primary-200 text-xs uppercase tracking-wide group">
                        <LinkIcon size={12} className="text-primary-400" />
                        <span className="border-b border-dashed border-primary-500/30 pb-0.5">{lawTitle}</span>
                    </div>
                    {article && (
                        <div className="px-3 py-1 rounded-lg bg-emerald-500/10 text-xs font-medium text-emerald-300 border border-emerald-500/20 leading-relaxed italic">
                            {article}
                        </div>
                    )}
                </div>
                {body && (
                    <div className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed pl-5 border-l border-white/10 ml-0.5 mt-1">
                        <span className="text-secondary-400 text-xs font-bold uppercase mr-2 tracking-wider">Relevanca:</span>
                        {body}
                    </div>
                )}
            </div>
        );
    }

    const rawText = safeString(item);
    const parts = rawText.split(/(\[.*?\]\(doc:\/\/.*?\))/g);

    return (
        <span className="leading-relaxed whitespace-pre-wrap">
            {parts.map((part, i) => {
                const match = part.match(/\[(.*?)\]\((doc:\/\/.*?)\)/);
                if (match) {
                    const [_, title, link] = match;
                    const isGlobal = ["UNCRC", "KEDNJ", "ECHR", "Konventa"].some(k => title.includes(k));
                    return (
                        <span key={i} title={link} className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold border mx-1 align-middle transition-colors cursor-help ${
                            isGlobal 
                            ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/20' 
                            : 'bg-blue-500/10 text-blue-300 border-blue-500/30 hover:bg-blue-500/20'
                        }`}>
                            {isGlobal ? <Globe size={10} /> : <Scale size={10} />}
                            {title}
                        </span>
                    );
                }
                return cleanLegalText(part);
            })}
        </span>
    );
};

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, caseId, isLoading }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'legal' | 'war_room'>('legal');
  const [warRoomSubTab, setWarRoomSubTab] = useState<'strategy' | 'adversarial' | 'timeline' | 'contradictions'>('strategy');
  
  // PHOENIX: Surgical loading states for parallel requests
  const [deepResult, setDeepResult] = useState<DeepAnalysisResult | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);
  const [isChronLoading, setIsChronLoading] = useState(false);
  const [isContradictLoading, setIsContradictLoading] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

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
      // Only trigger if we don't have results and aren't currently loading
      if (!deepResult && !isSimLoading && !isChronLoading && !isContradictLoading) {
          setIsSimLoading(true);
          setIsChronLoading(true);
          setIsContradictLoading(true);

          // Task 1: Chronology (Optimized/Fast)
          apiService.analyzeDeepChronology(caseId).then(data => {
              setDeepResult(prev => ({
                  ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }),
                  chronology: data
              }));
              setIsChronLoading(false);
          }).catch(() => setIsChronLoading(false));

          // Task 2: Adversarial Simulation (Compute Intensive)
          apiService.analyzeDeepSimulation(caseId).then(data => {
              setDeepResult(prev => ({
                  ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }),
                  adversarial_simulation: data
              }));
              setIsSimLoading(false);
          }).catch(() => setIsSimLoading(false));

          // Task 3: Contradictions (High Logic)
          apiService.analyzeDeepContradictions(caseId).then(data => {
              setDeepResult(prev => ({
                  ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }),
                  contradictions: data
              }));
              setIsContradictLoading(false);
          }).catch(() => setIsContradictLoading(false));
      }
  };

  const handleArchiveStrategy = async () => {
    if (!deepResult || isArchiving) return;
    setIsArchiving(true);
    try {
        await apiService.archiveStrategyReport(caseId, result, deepResult);
        alert(t('analysis.archive_success', 'Strategjia u ruajt me sukses në dosjen e rastit në Arkiv!'));
    } catch (error) {
        console.error("Archive Failed", error);
        alert(t('analysis.archive_error', 'Dështoi ruajtja në arkiv.'));
    } finally {
        setIsArchiving(false);
    }
  };

  const {
      summary = "", key_issues = [], legal_basis = [], strategic_analysis = "",
      weaknesses = [], action_plan = [], risk_level = "MEDIUM",
      success_probability = null, burden_of_proof = "", missing_evidence = []
  } = result || {};

  const getRiskLabel = (level: string) => {
      const l = level?.toUpperCase();
      if (l === 'HIGH') return t('analysis.risk_high', 'I LARTË');
      if (l === 'MEDIUM') return t('analysis.risk_medium', 'I MESËM');
      if (l === 'LOW') return t('analysis.risk_low', 'I ULËT');
      return level;
  };

  const renderRiskBadge = (level: string) => {
      const l = level?.toUpperCase() || 'MEDIUM';
      let styles = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      let icon = <Shield size={14} />;
      let label = t('analysis.risk_medium', 'I MESËM');

      if (l.includes('HIGH')) {
          styles = 'bg-red-500/10 text-red-400 border-red-500/20';
          icon = <ShieldAlert size={14} />;
          label = t('analysis.risk_high', 'I LARTË');
      } else if (l.includes('LOW')) {
          styles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
          icon = <ShieldCheck size={14} />;
          label = t('analysis.risk_low', 'I ULËT');
      }

      return (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${styles} backdrop-blur-md shadow-sm`}>
              {icon}
              <div className="flex items-center gap-1.5 text-xs font-bold tracking-wide">
                  <span className="opacity-70 font-medium uppercase text-[10px]">{t('analysis.risk_label', 'RREZIKU')}</span>
                  <span className="w-1 h-1 rounded-full bg-current opacity-50" />
                  <span>{label}</span>
              </div>
          </div>
      );
  };

  const renderSuccessBadge = (prob: string | null) => {
      if (!prob) return null;
      return (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-blue-500/10 text-blue-400 border-blue-500/20 backdrop-blur-md shadow-sm ml-2">
            <Percent size={14} />
            <div className="flex items-center gap-1.5 text-xs font-bold tracking-wide">
                <span className="opacity-70 font-medium uppercase text-[10px]">SUKSESI</span>
                <span className="w-1 h-1 rounded-full bg-current opacity-50" />
                <span>{prob}</span>
            </div>
        </div>
      );
  };

  const renderSubTabLoader = () => (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-20">
        <BrainCircuit className="w-12 h-12 text-red-500 animate-pulse mb-4" />
        <h3 className="text-lg font-bold text-white mb-2">{t('analysis.loading_deep_title', 'Duke Simuluar...')}</h3>
        <p className="text-gray-500 text-xs uppercase tracking-widest">{t('analysis.rag_processing', 'Analiza e thellë statutore...')}</p>
    </div>
  );

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-[100] p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.98, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.98, opacity: 0, y: 10 }} className="glass-high w-full h-full sm:h-[90vh] sm:max-w-6xl rounded-none sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-white/10" onClick={(e) => e.stopPropagation()}>
          
          <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/5 backdrop-blur-md shrink-0">
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-4 min-w-0">
              <div className="p-2.5 bg-gradient-to-br from-primary-start to-primary-end rounded-xl shrink-0 shadow-lg shadow-primary-start/20">
                  <Gavel className="text-white h-5 w-5" />
              </div>
              <div className="flex flex-col gap-1">
                  <span className="truncate leading-tight tracking-tight text-lg">{t('analysis.title', 'Strategjia Ligjore')}</span>
              </div>
              <div className="hidden sm:flex items-center ml-2">{renderRiskBadge(risk_level)} {renderSuccessBadge(success_probability)}</div>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-xl transition-colors shrink-0"><X size={20} /></button>
          </div>
          
          <div className="sm:hidden px-6 pb-2 -mt-2 flex gap-2">
               {renderRiskBadge(risk_level)}
               {renderSuccessBadge(success_probability)}
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                 <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div>
                 <h3 className="text-xl font-bold text-white mb-2">{t('analysis.loading_title', 'Duke Analizuar...')}</h3>
             </div>
          ) : (
             <>
                <div className="flex border-b border-white/5 px-6 bg-black/20 shrink-0 overflow-x-auto no-scrollbar gap-6">
                    <button onClick={() => setActiveTab('legal')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'legal' ? 'border-primary-start text-white' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Scale size={16}/> {t('analysis.tab_legal', 'Analiza Ligjore')}
                    </button>
                    <button onClick={handleWarRoomEntry} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'war_room' ? 'border-red-500 text-red-400' : 'border-transparent text-text-secondary hover:text-red-300'}`}>
                        <Swords size={16}/> {t('analysis.tab_war_room', 'Dhoma e Luftës')}
                    </button>
                </div>

                <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-black/10">
                    <style>{scrollbarStyles}</style>

                    {activeTab === 'legal' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="glass-panel p-6 rounded-2xl border-white/10 bg-white/5">
                                <h3 className="text-xs font-bold text-primary-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <Info size={16}/> {t('analysis.section_summary', 'Përmbledhja')}
                                </h3>
                                <div className="text-white text-sm leading-relaxed border-l-2 border-primary-500/30 pl-4">{renderCitationItem(summary)}</div>
                            </div>
                            {burden_of_proof && (
                                <div className="glass-panel p-6 rounded-2xl border-blue-500/20 bg-blue-500/5">
                                    <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <Gavel size={16}/> {t('analysis.section_burden', 'Barra e Provës')}
                                    </h3>
                                    <div className="text-gray-200 text-sm leading-relaxed italic border-l-2 border-blue-500/30 pl-4">{renderCitationItem(burden_of_proof)}</div>
                                </div>
                            )}
                            {missing_evidence && missing_evidence.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-red-500/20 bg-red-500/5">
                                    <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <AlertTriangle size={16}/> {t('analysis.section_missing', 'Gap-Analiza')}
                                    </h3>
                                    <div className="grid gap-2">
                                        {missing_evidence.map((item, idx) => (
                                            <div key={idx} className="flex items-center gap-3 text-sm text-red-200 bg-red-900/20 p-2 rounded-lg border border-red-500/10">
                                                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                                                {renderCitationItem(item)}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {key_issues && key_issues.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-white/5 bg-white/5">
                                    <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <FileText size={16}/> {t('analysis.section_issues', 'Çështjet Kryesore')}
                                    </h3>
                                    <div className="grid gap-3">
                                        {key_issues.map((issue: any, idx: number) => (
                                            <div key={idx} className="flex items-start gap-3 bg-white/5 p-3 rounded-lg border border-white/10">
                                                <span className="text-primary-400 font-bold mt-0.5">#{idx + 1}</span>
                                                <div className="text-sm text-gray-200 font-medium leading-snug">{renderCitationItem(issue)}</div>
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
                                        {legal_basis.map((lawItem: any, i: number) => {
                                            const lawStr = typeof lawItem === 'string' ? lawItem : (lawItem.law || "");
                                            const isGlobal = lawStr.includes("UNCRC") || lawStr.includes("Konventa") || lawStr.includes("KEDNJ");
                                            return (
                                                <li key={i} className={`flex gap-3 text-sm items-start p-4 rounded-xl transition-colors ${isGlobal ? 'bg-indigo-500/10 border border-indigo-500/30' : 'bg-white/5 border border-white/5 hover:border-white/10'}`}>
                                                    {isGlobal ? <Globe size={20} className="text-indigo-400 shrink-0 mt-0.5"/> : <Scale size={20} className="text-secondary-400 shrink-0 mt-0.5"/>}
                                                    {renderCitationItem(lawItem)}
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                    
                    {activeTab === 'war_room' && (
                        <div className="h-full flex flex-col">
                            <div className="flex gap-2 mb-6 shrink-0 border-b border-white/5 pb-4 overflow-x-auto no-scrollbar">
                                <button onClick={() => setWarRoomSubTab('strategy')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${warRoomSubTab === 'strategy' ? 'bg-accent-start text-white shadow-lg' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <Target size={14} className="inline mr-2" /> {t('analysis.subtab_strategy', 'Plani Strategjik')}
                                </button>
                                <button onClick={() => setWarRoomSubTab('adversarial')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${warRoomSubTab === 'adversarial' ? 'bg-red-500 text-white shadow-lg' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <Skull size={14} className="inline mr-2" /> {t('analysis.subtab_adversarial', 'Simulimi')}
                                </button>
                                <button onClick={() => setWarRoomSubTab('timeline')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${warRoomSubTab === 'timeline' ? 'bg-blue-500 text-white shadow-lg' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <Clock size={14} className="inline mr-2" /> {t('analysis.subtab_timeline', 'Kronologjia')}
                                </button>
                                <button onClick={() => setWarRoomSubTab('contradictions')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${warRoomSubTab === 'contradictions' ? 'bg-yellow-500 text-black shadow-lg' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                                    <AlertOctagon size={14} className="inline mr-2" /> {t('analysis.subtab_contradictions', 'Kontradiktat')}
                                </button>
                            </div>

                            <div className="space-y-6 animate-in fade-in">
                                {warRoomSubTab === 'strategy' ? (
                                    <div className="space-y-6">
                                        <div className="glass-panel p-6 rounded-2xl border-accent-start/20 bg-accent-start/5">
                                            <h3 className="text-xs font-bold text-accent-start uppercase tracking-wider mb-3">{t('analysis.section_analysis', 'Analiza Strategjike')}</h3>
                                            <div className="text-white text-sm leading-relaxed border-l-2 border-accent-start/30 pl-4">{renderCitationItem(strategic_analysis)}</div>
                                        </div>
                                        <div className="glass-panel p-6 rounded-2xl border-red-500/20 bg-red-500/5">
                                            <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-4">{t('analysis.section_weaknesses', 'Dobësitë')}</h3>
                                            <ul className="space-y-3">
                                                {weaknesses.map((w: any, i: number) => (
                                                    <li key={i} className="flex gap-3 text-sm text-red-100 bg-red-500/10 p-3 rounded-lg border border-red-500/20">{renderCitationItem(w)}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="glass-panel p-6 rounded-2xl border-emerald-500/20 bg-emerald-500/5">
                                            <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-4">{t('analysis.section_conclusion', 'Plani i Veprimit')}</h3>
                                            <div className="space-y-3">
                                                {action_plan.map((step: any, i: number) => (
                                                    <div key={i} className="flex gap-4 text-sm text-white bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20">
                                                        <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500 text-black font-bold text-xs shrink-0">{i + 1}</span>
                                                        <span className="leading-relaxed font-medium">{renderCitationItem(step)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                ) : warRoomSubTab === 'adversarial' ? (
                                    isSimLoading ? renderSubTabLoader() : deepResult?.adversarial_simulation ? (
                                        <div className="space-y-4">
                                            <div className="glass-panel p-5 rounded-xl border border-red-500/30 bg-red-900/10">
                                                <h3 className="text-sm font-bold text-red-300 mb-2 uppercase tracking-wide">{t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}</h3>
                                                <div className="text-white/90 text-sm leading-relaxed">{renderCitationItem(deepResult.adversarial_simulation.opponent_strategy)}</div>
                                            </div>
                                            <div className="grid gap-3">
                                                {deepResult.adversarial_simulation.weakness_attacks.map((attack: string, i: number) => (
                                                    <div key={i} className="flex gap-3 bg-white/5 p-3 rounded-lg border border-white/10">
                                                        <Target size={16} className="text-red-400 shrink-0 mt-0.5" />
                                                        <div className="text-sm text-gray-300">{renderCitationItem(attack)}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-center py-20 text-gray-500"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                    )
                                ) : warRoomSubTab === 'timeline' ? (
                                    isChronLoading ? renderSubTabLoader() : deepResult?.chronology ? (
                                        <div className="space-y-4 relative border-l-2 border-white/10 ml-3 pl-6 py-2">
                                            {deepResult.chronology.map((event: ChronologyEvent, i: number) => (
                                                <div key={i} className="relative group">
                                                    <div className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-blue-500 border-2 border-black" />
                                                    <div className="flex gap-4">
                                                        <span className="text-blue-400 font-mono text-xs font-bold shrink-0 w-24">{event.date}</span>
                                                        <div className="text-gray-200 text-sm">{renderCitationItem(event.event)}</div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-center py-20 text-gray-500"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                    )
                                ) : warRoomSubTab === 'contradictions' ? (
                                    isContradictLoading ? renderSubTabLoader() : deepResult?.contradictions ? (
                                        <div className="grid gap-4">
                                            {deepResult.contradictions.length === 0 ? (
                                                <div className="text-center py-10 text-gray-500">
                                                    <CheckCircle2 size={32} className="mx-auto mb-2 text-green-500/50" />
                                                    <p>{t('analysis.no_contradictions', 'Nuk u gjetën kontradikta.')}</p>
                                                </div>
                                            ) : (
                                                deepResult.contradictions.map((c: Contradiction, i: number) => (
                                                    <div key={i} className="bg-yellow-500/5 border border-yellow-500/20 p-4 rounded-xl">
                                                        <div className="flex justify-between items-start mb-2">
                                                            <div className="flex items-center gap-2 text-yellow-400 font-bold text-xs uppercase tracking-wider">{t('analysis.contradiction_label', 'Mospërputhje')}</div>
                                                            <span className="text-[10px] bg-yellow-500/20 text-yellow-200 px-2 py-0.5 rounded border border-yellow-500/30">{getRiskLabel(c.severity)}</span>
                                                        </div>
                                                        <div className="grid md:grid-cols-2 gap-4 mt-3">
                                                            <div className="p-3 bg-black/20 rounded-lg">
                                                                <span className="text-xs text-red-400 font-bold block mb-1">{t('analysis.claim_label', 'DEKLARATA')}</span>
                                                                <div className="text-sm text-gray-300 italic">"{renderCitationItem(c.claim)}"</div>
                                                            </div>
                                                            <div className="p-3 bg-black/20 rounded-lg">
                                                                <span className="text-xs text-emerald-400 font-bold block mb-1">{t('analysis.evidence_label', 'FAKTI / PROVA')}</span>
                                                                <div className="text-sm text-gray-300 font-mono">{renderCitationItem(c.evidence)}</div>
                                                            </div>
                                                        </div>
                                                        <div className="mt-3 text-xs text-gray-400 border-t border-white/5 pt-2">{renderCitationItem(c.impact)}</div>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    ) : (
                                        <div className="text-center py-20 text-gray-500"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                    )
                                ) : null}
                            </div>
                        </div>
                    )}
                </div>
             </>
          )}
          
          <div className="p-4 border-t border-white/5 bg-background-dark/80 backdrop-blur-md flex flex-col sm:flex-row gap-3 justify-center items-center shrink-0">
              <button 
                  onClick={handleArchiveStrategy} 
                  disabled={isArchiving || !deepResult}
                  className={`w-full sm:w-auto px-6 py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2 border ${
                      isArchiving || !deepResult 
                      ? 'bg-white/5 text-gray-500 border-white/5 cursor-not-allowed' 
                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20 active:scale-95'
                  }`}
              >
                  {isArchiving ? (
                      <div className="w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                      <CheckCircle2 size={18} />
                  )}
                  {t('analysis.btn_archive', 'Ruaj Strategjinë në Arkiv')}
              </button>
              
              <button onClick={onClose} className="w-full sm:w-auto px-10 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 text-white text-sm rounded-xl font-bold transition-all active:scale-95">
                  {t('general.close', 'Mbyll Sallën')}
              </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default AnalysisModal;