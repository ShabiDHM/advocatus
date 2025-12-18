// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - WAR ROOM UI V4.5 (TEXT SANITIZATION FIX)
// 1. FIX: Upgraded 'sanitizeText' to remove leaked AI placeholders (TARGET/CONTEXT).
// 2. LOGIC: Ensures natural language output (e.g., "Dosja" instead of "CONTEXT").
// 3. STATUS: Polished and ready.

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
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 3px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.25); }
`;

// PHOENIX FIX: Advanced Sanitizer
const sanitizeText = (text: string): string => {
    if (!text) return "";
    return text
        // Fix specific redundant phrases first
        .replace(/Dokumenti i ri TARGET/gi, "Dokumenti i ri")
        .replace(/kontekstin ekzistues CONTEXT/gi, "dosjen ekzistuese")
        // Fix standalone keywords
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
                        <span key={i} className="mx-1 inline-flex items-center px-1 py-px rounded text-[9px] font-bold bg-blue-500/10 text-blue-300 border border-blue-500/20 tracking-wide uppercase break-words whitespace-normal max-w-full leading-none">
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
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/95 backdrop-blur-md flex items-center justify-center z-[100] p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.98, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.98, opacity: 0, y: 10 }} className="bg-background-dark w-full h-full sm:h-[85vh] sm:max-w-5xl rounded-none sm:rounded-xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50" onClick={(e) => e.stopPropagation()}>
          
          {/* Header */}
          <div className="px-4 py-3 border-b border-glass-edge flex justify-between items-center bg-background-light/95 backdrop-blur-md shrink-0">
            <h2 className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2 min-w-0">
              <div className="p-1.5 bg-primary-start/10 rounded-lg shrink-0"><Gavel className="text-primary-start h-4 w-4 sm:h-5 sm:w-5" /></div>
              <div className="flex flex-col">
                  <span className="truncate leading-tight">{t('analysis.warRoomTitle', 'Salla e Strategjisë')}</span>
                  {result.analysis_mode && (
                      <span className="text-[9px] uppercase tracking-widest text-gray-500 font-bold">
                          {getModeLabel(result.analysis_mode)}
                      </span>
                  )}
              </div>
            </h2>
            <button onClick={onClose} className="p-1.5 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors shrink-0"><X size={20} /></button>
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-12 h-12 border-3 border-primary-start border-t-transparent rounded-full animate-spin mb-4"></div>
                <h3 className="text-lg font-bold text-white mb-1">{t('analysis.auditing', 'Duke Audituar Dosjen...')}</h3>
                <p className="text-gray-500 text-xs">{t('analysis.aiWorking', 'Inteligjenca Artificiale po verifikon çdo pretendim faktik.')}</p>
             </div>
          ) : (
             <>
                {/* Tabs */}
                <div className="flex border-b border-white/10 px-4 bg-black/20 shrink-0 overflow-x-auto no-scrollbar">
                    <button onClick={() => setActiveTab('analysis')} className={`px-3 py-2.5 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${activeTab === 'analysis' ? 'border-primary-start text-white' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
                        <Scale size={14}/> {t('analysis.tabFactual', 'Analiza Faktike')}
                    </button>
                    <button onClick={() => setActiveTab('strategy')} className={`px-3 py-2.5 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${activeTab === 'strategy' ? 'border-orange-500 text-orange-400' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
                        <Swords size={14}/> {t('analysis.tabStrategy', 'Strategjia Sulmuese')}
                    </button>
                </div>

                {/* Content Area */}
                <div className="p-4 sm:p-6 overflow-y-auto space-y-4 flex-1 custom-scrollbar relative bg-background-dark/50">
                    <style>{scrollbarStyles}</style>

                    {activeTab === 'analysis' && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                            
                            {judicialObservation && (
                                <div className="bg-indigo-950/30 p-4 rounded-lg border border-indigo-500/20 shadow-sm relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-2 opacity-10"><Gavel size={64}/></div>
                                    <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-1.5 relative z-10">
                                        <FileSearch size={14}/> {t('analysis.judicialObservation', 'Vlerësimi Gjyqësor')}
                                    </h3>
                                    <p className="text-gray-300 text-sm leading-relaxed font-medium italic relative z-10 border-l-2 border-indigo-500/50 pl-3">
                                        "{sanitizeText(judicialObservation)}"
                                    </p>
                                </div>
                            )}

                            {redFlags.length > 0 && (
                                <div className="bg-red-950/20 p-4 rounded-lg border border-red-500/20">
                                    <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"><Siren size={14} className="animate-pulse"/> {t('analysis.redFlags', 'Sinjale Rreziku')}</h3>
                                    <ul className="space-y-1.5">
                                        {redFlags.map((flag: string, idx: number) => (
                                            <li key={idx} className="flex gap-2 text-xs sm:text-sm text-red-200/90 bg-red-900/10 p-2 rounded border border-red-500/10">
                                                <span className="text-red-500 font-bold text-xs mt-0.5">⚠</span>
                                                <span className="leading-snug">{sanitizeText(flag)}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {(silentParties.length > 0 || missingInfo.length > 0) && (
                                <div className="bg-orange-950/20 p-3 rounded-lg border border-orange-500/20 flex flex-col sm:flex-row gap-3 items-start">
                                    <EyeOff className="text-orange-500/70 h-5 w-5 mt-0.5 shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-xs font-bold text-orange-400 uppercase tracking-wider mb-1">{t('analysis.warningMissingInfo', 'Kujdes: Mungesë Informacioni')}</h3>
                                        {silentParties.length > 0 && (<p className="text-gray-400 text-xs mb-1.5"><span className="font-bold text-orange-300/80">{t('analysis.silentParties', 'Palët në Heshtje')}:</span> {silentParties.join(", ")}</p>)}
                                        {missingInfo.length > 0 && (<div className="flex flex-wrap gap-1.5">{missingInfo.map((info, idx) => (<span key={idx} className="bg-orange-900/30 text-orange-200/80 text-[10px] px-1.5 py-0.5 rounded border border-orange-500/10 flex items-center gap-1"><FileWarning size={10}/> {sanitizeText(info)}</span>))}</div>)}
                                    </div>
                                </div>
                            )}

                            <div className="bg-blue-950/10 p-4 rounded-lg border border-blue-500/10">
                                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"><FileText size={14}/> {t('analysis.executiveSummary', 'Përmbledhje Ekzekutive')}</h3>
                                <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-line">{renderTextWithCitations(sanitizeText(result.summary_analysis || ""))}</p>
                            </div>

                            {result.chronology && result.chronology.length > 0 && (
                                <div className="bg-slate-900/30 p-4 rounded-lg border border-slate-700/30">
                                    <h3 className="text-xs font-bold text-cyan-500/90 uppercase tracking-wider mb-4 flex items-center gap-1.5"><Clock size={14}/> {t('analysis.verifiedChronology', 'Kronologjia e Verifikuar')}</h3>
                                    <div className="relative pl-3 border-l border-slate-700/50 space-y-6 ml-1">
                                        {result.chronology.map((event, idx) => (
                                            <div key={idx} className="relative group">
                                                <div className="absolute -left-[16.5px] top-1.5 w-2 h-2 rounded-full bg-cyan-600 shadow-[0_0_8px_rgba(6,182,212,0.4)] border border-background-dark group-hover:bg-cyan-400 transition-colors" />
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="text-cyan-300/90 font-bold text-[10px] tracking-wide uppercase">{event.date}</span>
                                                    <p className="text-gray-300 text-xs sm:text-sm leading-snug font-medium">{renderTextWithCitations(sanitizeText(event.event))}</p>
                                                    {event.source_doc && (<span className="text-slate-500 text-[9px] uppercase tracking-wider font-semibold flex items-center gap-1 mt-0.5"><FileText size={8} />{sanitizeText(event.source_doc)}</span>)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            
                            {result.contradictions && result.contradictions.length > 0 && (
                                <div className="bg-orange-950/10 p-4 rounded-lg border border-orange-500/10">
                                    <h3 className="text-xs font-bold text-orange-400/90 uppercase tracking-wider mb-2 flex items-center gap-1.5"><ShieldAlert size={14}/> {t('analysis.contradictions', 'Kontradikta / Mospërputhje')}</h3>
                                    <ul className="space-y-1.5">
                                        {result.contradictions.map((c, i) => (<li key={i} className="flex gap-2 text-xs sm:text-sm text-gray-400 bg-black/20 p-2 rounded border border-white/5"><span className="text-orange-500/80 font-bold mt-0.5">•</span><span className="leading-snug">{renderTextWithCitations(sanitizeText(c))}</span></li>))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'strategy' && (
                         <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-300">
                            <div className="bg-purple-950/10 p-4 rounded-lg border border-purple-500/20">
                                <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider mb-3 flex items-center gap-1.5"><MessageCircleQuestion size={14}/> {t('analysis.witnessQuestions', 'Pyetje për Dëshmitarin')}</h3>
                                {result.suggested_questions && result.suggested_questions.length > 0 ? (
                                    <ul className="space-y-2">{result.suggested_questions.map((q, i) => (<li key={i} className="flex gap-2 text-xs sm:text-sm text-gray-300 bg-black/20 p-2.5 rounded border border-purple-500/10 hover:border-purple-500/30 transition-colors"><span className="text-purple-400/80 font-bold whitespace-nowrap text-xs mt-0.5">{i+1}.</span><span className="leading-snug font-medium">{renderTextWithCitations(sanitizeText(q))}</span></li>))}</ul>
                                ) : (<p className="text-gray-500 text-xs italic">{t('analysis.noQuestions', 'Nuk u gjeneruan pyetje specifike.')}</p>)}
                            </div>
                             <div className="bg-emerald-950/10 p-4 rounded-lg border border-emerald-500/20">
                                <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-1.5"><Target size={14}/> {t('analysis.discoveryRequests', 'Kërkesa për Prova (Discovery)')}</h3>
                                {result.discovery_targets && result.discovery_targets.length > 0 ? (
                                    <ul className="space-y-2">{result.discovery_targets.map((d, i) => (<li key={i} className="flex gap-2 text-xs sm:text-sm text-gray-300 bg-black/20 p-2.5 rounded border border-emerald-500/10"><span className="text-emerald-400/80 font-bold text-xs mt-0.5">➢</span><span className="leading-snug">{renderTextWithCitations(sanitizeText(d))}</span></li>))}</ul>
                                ) : (<p className="text-gray-500 text-xs italic">{t('analysis.noDiscovery', 'Nuk u identifikuan prova të reja.')}</p>)}
                            </div>
                         </div>
                    )}
                </div>
             </>
          )}
          <div className="p-3 sm:p-4 border-t border-glass-edge bg-background-dark/80 text-center shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-8 py-2 bg-primary-start hover:bg-primary-end text-white text-sm rounded-lg font-bold transition-all shadow-lg glow-primary">{t('general.close', 'Mbyll Sallen')}</button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
  return ReactDOM.createPortal(modalContent, document.body);
};
export default AnalysisModal;