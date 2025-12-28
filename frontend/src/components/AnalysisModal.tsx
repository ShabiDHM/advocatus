// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V5.0 (GLASS STYLE)
// 1. VISUALS: Full Glassmorphism adoption (glass-high, glass-panel).
// 2. UX: Enhanced tab switching and content containers with ambient depth.
// 3. LOGIC: Preserved text sanitization and data mapping logic.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Scale, FileText, ShieldAlert, Swords, Target, MessageCircleQuestion, Gavel, Clock, FileWarning, EyeOff, Siren, FileSearch } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CaseAnalysisResult } from '../data/types'; 

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: CaseAnalysisResult; 
  isLoading?: boolean;
}

const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 5px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 3px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); }
`;

const sanitizeText = (text: string): string => {
    if (!text) return "";
    return text
        .replace(/Dokumenti i ri TARGET/gi, "Dokumenti i ri")
        .replace(/kontekstin ekzistues CONTEXT/gi, "dosjen ekzistuese")
        .replace(/\bTARGET\b/g, "Dokumenti")
        .replace(/\bCONTEXT\b/g, "Dosja")
        .replace(/\bTarget\b/g, "Dokumenti")
        .replace(/\bContext\b/g, "Dosja");
};

const renderTextWithCitations = (text: string) => {
    const parts = text.split(/(\[\[?[^\]]+\]?\])/g);
    return (
        <span>
            {parts.map((part, i) => {
                if ((part.startsWith('[[') || part.startsWith('[')) && (part.endsWith(']]') || part.endsWith(']'))) {
                    const clean = part.replace(/[\[\]]/g, '');
                    return (
                        <span key={i} className="mx-1 inline-flex items-center px-1 py-px rounded text-[9px] font-bold bg-primary-start/20 text-primary-300 border border-primary-start/30 tracking-wide uppercase break-words whitespace-normal max-w-full leading-none">
                            {clean}
                        </span>
                    );
                }
                return <span key={i}>{part}</span>;
            })}
        </span>
    );
};

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, isLoading }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'analysis' | 'strategy'>('analysis');

  useEffect(() => {
    if (isOpen) { document.body.style.overflow = 'hidden'; } 
    else { document.body.style.overflow = 'unset'; }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  const silentParties = result.silent_parties || [];
  const missingInfo = result.missing_info || [];
  
  const judicialObservation = (result as any).judicial_observation;
  const redFlags = (result as any).red_flags || [];

  const getModeLabel = (mode?: string) => {
      switch(mode) {
          case 'FULL_CASE_AUDIT': return t('analysis.modeAudit', 'AUDITIM I PLOTË');
          case 'CROSS_EXAMINATION': return t('analysis.modeCross', 'KRYQËZIM DOKUMENTESH');
          default: return t('analysis.modeStandard', 'ANALIZË STANDARDE');
      }
  };

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-[100] p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.98, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.98, opacity: 0, y: 10 }} className="glass-high w-full h-full sm:h-[85vh] sm:max-w-5xl rounded-none sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-white/10" onClick={(e) => e.stopPropagation()}>
          
          {/* Header */}
          <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/5 backdrop-blur-md shrink-0">
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-3 min-w-0">
              <div className="p-2 bg-gradient-to-br from-primary-start to-primary-end rounded-lg shrink-0 shadow-lg shadow-primary-start/20">
                  <Gavel className="text-white h-5 w-5" />
              </div>
              <div className="flex flex-col">
                  <span className="truncate leading-tight tracking-tight">{t('analysis.warRoomTitle', 'Salla e Strategjisë')}</span>
                  {result.analysis_mode && (
                      <span className="text-[10px] uppercase tracking-widest text-primary-300 font-bold mt-0.5">
                          {getModeLabel(result.analysis_mode)}
                      </span>
                  )}
              </div>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-xl transition-colors shrink-0"><X size={20} /></button>
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div>
                <h3 className="text-xl font-bold text-white mb-2">{t('analysis.auditing', 'Duke Audituar Dosjen...')}</h3>
                <p className="text-text-secondary text-sm max-w-sm mx-auto">{t('analysis.aiWorking', 'Inteligjenca Artificiale po verifikon çdo pretendim faktik.')}</p>
             </div>
          ) : (
             <>
                {/* Tabs */}
                <div className="flex border-b border-white/5 px-6 bg-black/20 shrink-0 overflow-x-auto no-scrollbar gap-6">
                    <button onClick={() => setActiveTab('analysis')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'analysis' ? 'border-primary-start text-white' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Scale size={16}/> {t('analysis.tabFactual', 'Analiza Faktike')}
                    </button>
                    <button onClick={() => setActiveTab('strategy')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'strategy' ? 'border-accent-start text-accent-start' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Swords size={16}/> {t('analysis.tabStrategy', 'Strategjia Sulmuese')}
                    </button>
                </div>

                {/* Content Area */}
                <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-black/10">
                    <style>{scrollbarStyles}</style>

                    {activeTab === 'analysis' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            
                            {judicialObservation && (
                                <div className="glass-panel p-6 rounded-2xl relative overflow-hidden bg-primary-start/5 border-primary-start/20">
                                    <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none"><Gavel size={120} /></div>
                                    <h3 className="text-xs font-bold text-primary-300 uppercase tracking-wider mb-3 flex items-center gap-2 relative z-10">
                                        <FileSearch size={16}/> {t('analysis.judicialObservation', 'Vlerësimi Gjyqësor')}
                                    </h3>
                                    <p className="text-white text-sm leading-relaxed font-medium italic relative z-10 border-l-2 border-primary-start pl-4 py-1">
                                        "{sanitizeText(judicialObservation)}"
                                    </p>
                                </div>
                            )}

                            {redFlags.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-red-500/20 bg-red-500/5">
                                    <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Siren size={16} className="animate-pulse"/> {t('analysis.redFlags', 'Sinjale Rreziku')}</h3>
                                    <ul className="space-y-2">
                                        {redFlags.map((flag: string, idx: number) => (
                                            <li key={idx} className="flex gap-3 text-sm text-red-100 bg-red-500/10 p-3 rounded-xl border border-red-500/20">
                                                <span className="text-red-500 font-bold mt-0.5">⚠</span>
                                                <span className="leading-relaxed">{sanitizeText(flag)}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {(silentParties.length > 0 || missingInfo.length > 0) && (
                                <div className="glass-panel p-5 rounded-2xl border-accent-start/20 bg-accent-start/5 flex flex-col sm:flex-row gap-4 items-start">
                                    <EyeOff className="text-accent-start h-6 w-6 mt-0.5 shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-xs font-bold text-accent-start uppercase tracking-wider mb-2">{t('analysis.warningMissingInfo', 'Kujdes: Mungesë Informacioni')}</h3>
                                        {silentParties.length > 0 && (<p className="text-text-secondary text-sm mb-2"><span className="font-bold text-white">{t('analysis.silentParties', 'Palët në Heshtje')}:</span> {silentParties.join(", ")}</p>)}
                                        {missingInfo.length > 0 && (<div className="flex flex-wrap gap-2">{missingInfo.map((info, idx) => (<span key={idx} className="bg-accent-start/10 text-accent-200 text-xs px-2 py-1 rounded-lg border border-accent-start/20 flex items-center gap-1.5"><FileWarning size={12}/> {sanitizeText(info)}</span>))}</div>)}
                                    </div>
                                </div>
                            )}

                            <div className="glass-panel p-6 rounded-2xl">
                                <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2"><FileText size={16}/> {t('analysis.executiveSummary', 'Përmbledhje Ekzekutive')}</h3>
                                <p className="text-white text-sm leading-relaxed whitespace-pre-line">{renderTextWithCitations(sanitizeText(result.summary_analysis || ""))}</p>
                            </div>

                            {result.chronology && result.chronology.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-white/5 bg-white/5">
                                    <h3 className="text-xs font-bold text-secondary-300 uppercase tracking-wider mb-6 flex items-center gap-2"><Clock size={16}/> {t('analysis.verifiedChronology', 'Kronologjia e Verifikuar')}</h3>
                                    <div className="relative pl-4 border-l border-white/10 space-y-8 ml-2">
                                        {result.chronology.map((event, idx) => (
                                            <div key={idx} className="relative group">
                                                <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full bg-secondary-start shadow-[0_0_10px_rgba(124,58,237,0.5)] border border-background-dark group-hover:scale-125 transition-transform" />
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-secondary-300 font-bold text-[10px] tracking-wide uppercase bg-secondary-500/10 px-2 py-0.5 rounded w-fit">{event.date}</span>
                                                    <p className="text-gray-200 text-sm leading-snug font-medium mt-1">{renderTextWithCitations(sanitizeText(event.event))}</p>
                                                    {event.source_doc && (<span className="text-text-secondary text-[10px] uppercase tracking-wider font-semibold flex items-center gap-1.5 mt-1 opacity-60"><FileText size={10} />{sanitizeText(event.source_doc)}</span>)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            
                            {result.contradictions && result.contradictions.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-accent-start/10 bg-accent-start/5">
                                    <h3 className="text-xs font-bold text-accent-start uppercase tracking-wider mb-3 flex items-center gap-2"><ShieldAlert size={16}/> {t('analysis.contradictions', 'Kontradikta / Mospërputhje')}</h3>
                                    <ul className="space-y-2">
                                        {result.contradictions.map((c, i) => (<li key={i} className="flex gap-3 text-sm text-text-secondary bg-black/20 p-3 rounded-xl border border-white/5"><span className="text-accent-start font-bold mt-0.5">•</span><span className="leading-relaxed">{renderTextWithCitations(sanitizeText(c))}</span></li>))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'strategy' && (
                         <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                            <div className="glass-panel p-6 rounded-2xl border-secondary-start/20 bg-secondary-start/5">
                                <h3 className="text-xs font-bold text-secondary-300 uppercase tracking-wider mb-4 flex items-center gap-2"><MessageCircleQuestion size={16}/> {t('analysis.witnessQuestions', 'Pyetje për Dëshmitarin')}</h3>
                                {result.suggested_questions && result.suggested_questions.length > 0 ? (
                                    <ul className="space-y-3">{result.suggested_questions.map((q, i) => (<li key={i} className="flex gap-3 text-sm text-white bg-secondary-500/10 p-3.5 rounded-xl border border-secondary-500/20 hover:border-secondary-500/40 transition-colors"><span className="text-secondary-400 font-bold whitespace-nowrap mt-0.5">{i+1}.</span><span className="leading-relaxed">{renderTextWithCitations(sanitizeText(q))}</span></li>))}</ul>
                                ) : (<p className="text-text-secondary text-sm italic">{t('analysis.noQuestions', 'Nuk u gjeneruan pyetje specifike.')}</p>)}
                            </div>
                             <div className="glass-panel p-6 rounded-2xl border-success-start/20 bg-success-start/5">
                                <h3 className="text-xs font-bold text-success-400 uppercase tracking-wider mb-4 flex items-center gap-2"><Target size={16}/> {t('analysis.discoveryRequests', 'Kërkesa për Prova (Discovery)')}</h3>
                                {result.discovery_targets && result.discovery_targets.length > 0 ? (
                                    <ul className="space-y-3">{result.discovery_targets.map((d, i) => (<li key={i} className="flex gap-3 text-sm text-white bg-success-500/10 p-3.5 rounded-xl border border-success-500/20"><span className="text-success-400 font-bold mt-0.5">➢</span><span className="leading-relaxed">{renderTextWithCitations(sanitizeText(d))}</span></li>))}</ul>
                                ) : (<p className="text-text-secondary text-sm italic">{t('analysis.noDiscovery', 'Nuk u identifikuan prova të reja.')}</p>)}
                            </div>
                         </div>
                    )}
                </div>
             </>
          )}
          <div className="p-4 border-t border-white/5 bg-background-dark/80 backdrop-blur-md text-center shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-10 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 text-white text-sm rounded-xl font-bold transition-all active:scale-95">{t('general.close', 'Mbyll Sallen')}</button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
  return ReactDOM.createPortal(modalContent, document.body);
};
export default AnalysisModal;