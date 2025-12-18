// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - WAR ROOM UI V4.3 (LINTER FIX & CITATION UPGRADE)
// 1. FIX: Removed unused 'User' and 'validParties' to clear linter errors.
// 2. LOGIC: Upgraded 'renderTextWithCitations' to support full document names.
// 3. STATUS: Clean build, fully functional.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Scale, FileText, ShieldAlert, Swords, Target, MessageCircleQuestion, Gavel, Clock, FileWarning, EyeOff, Siren } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CaseAnalysisResult } from '../data/types'; 

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: CaseAnalysisResult; 
  isLoading?: boolean;
}

const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
`;

const sanitizeText = (text: string): string => {
    if (!text) return "";
    return text.replace(/Target/g, "Dokumenti").replace(/Context/g, "Dosja");
};

// PHOENIX: Upgraded Citation Renderer
const renderTextWithCitations = (text: string) => {
    // Regex matches [[Burimi: ...]] or standard [Burimi: ...] brackets
    const parts = text.split(/(\[\[?[^\]]+\]?\])/g);
    return (
        <span>
            {parts.map((part, i) => {
                if ((part.startsWith('[[') || part.startsWith('[')) && (part.endsWith(']]') || part.endsWith(']'))) {
                    // Clean brackets
                    const clean = part.replace(/[\[\]]/g, '');
                    return (
                        <span key={i} className="mx-1 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 tracking-wide uppercase break-words whitespace-normal max-w-full">
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

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[100] p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.95, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.95, opacity: 0, y: 20 }} className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[95vh] sm:max-w-6xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50" onClick={(e) => e.stopPropagation()}>
          
          <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0 gap-4">
            <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2 min-w-0">
              <div className="p-1.5 bg-primary-start/10 rounded-lg flex-shrink-0"><Gavel className="text-primary-start h-5 w-5 sm:h-6 sm:w-6" /></div>
              <div className="flex flex-col"><span className="truncate">{t('analysis.modalTitle', 'Salla e Strategjisë (War Room)')}</span></div>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors flex-shrink-0"><X size={24} /></button>
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div>
                <h3 className="text-xl font-bold text-white mb-2">Duke Audituar Dosjen...</h3>
                <p className="text-gray-400">Inteligjenca Artificiale po verifikon çdo pretendim faktik.</p>
             </div>
          ) : (
             <>
                <div className="flex border-b border-white/10 px-6 bg-black/20">
                    <button onClick={() => setActiveTab('analysis')} className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'analysis' ? 'border-primary-start text-white' : 'border-transparent text-gray-400 hover:text-white'}`}><Scale size={16}/> Analiza Faktike</button>
                    <button onClick={() => setActiveTab('strategy')} className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'strategy' ? 'border-orange-500 text-orange-400' : 'border-transparent text-gray-400 hover:text-white'}`}><Swords size={16}/> Strategjia Sulmuese</button>
                </div>

                <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-background-dark/50">
                    <style>{scrollbarStyles}</style>

                    {activeTab === 'analysis' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                            
                            {/* PHOENIX: JUDICIAL OBSERVATION (Judge's Chamber) */}
                            {judicialObservation && (
                                <div className="bg-indigo-900/20 p-5 rounded-xl border border-indigo-500/30 shadow-lg">
                                    <h3 className="text-sm font-bold text-indigo-300 uppercase tracking-wider mb-2 flex items-center gap-2"><Gavel size={16}/> Vlerësimi Gjyqësor (Judicial Logic)</h3>
                                    <p className="text-gray-200 text-sm leading-relaxed font-medium italic">"{judicialObservation}"</p>
                                </div>
                            )}

                            {/* PHOENIX: RED FLAGS (Detective's Corner) */}
                            {redFlags.length > 0 && (
                                <div className="bg-red-950/20 p-5 rounded-xl border border-red-500/30">
                                    <h3 className="text-sm font-bold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Siren size={16} className="animate-pulse"/> Sinjale Rreziku (Red Flags)</h3>
                                    <ul className="space-y-2">
                                        {redFlags.map((flag: string, idx: number) => (
                                            <li key={idx} className="flex gap-3 text-sm text-red-200 bg-red-900/20 p-3 rounded-lg border border-red-500/10">
                                                <span className="text-red-500 font-bold">⚠</span>
                                                <span>{flag}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* SILENT PARTY WARNING */}
                            {(silentParties.length > 0 || missingInfo.length > 0) && (
                                <div className="bg-orange-950/30 p-4 rounded-xl border border-orange-500/30 flex flex-col sm:flex-row gap-4 items-start">
                                    <div className="p-2 bg-orange-500/20 rounded-lg shrink-0"><EyeOff className="text-orange-400 h-6 w-6" /></div>
                                    <div className="flex-1">
                                        <h3 className="text-sm font-bold text-orange-400 uppercase tracking-wider mb-1">Kujdes: Mungesë Informacioni</h3>
                                        {silentParties.length > 0 && (<p className="text-gray-300 text-sm mb-2"><span className="font-bold text-orange-300">Palët në Heshtje:</span> {silentParties.join(", ")} nuk kanë dorëzuar dokumente.</p>)}
                                        {missingInfo.length > 0 && (<div className="flex flex-wrap gap-2 mt-2">{missingInfo.map((info, idx) => (<span key={idx} className="bg-orange-900/50 text-orange-200 text-xs px-2 py-1 rounded border border-orange-500/20 flex items-center gap-1"><FileWarning size={12}/> {info}</span>))}</div>)}
                                    </div>
                                </div>
                            )}

                            {/* SUMMARY */}
                            <div className="bg-blue-900/10 p-5 rounded-xl border border-blue-500/20">
                                <h3 className="text-sm font-bold text-blue-400 uppercase tracking-wider mb-2 flex items-center gap-2"><FileText size={16}/> Përmbledhje Ekzekutive</h3>
                                <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-line">{renderTextWithCitations(sanitizeText(result.summary_analysis || ""))}</p>
                            </div>

                            {/* TIMELINE */}
                            {result.chronology && result.chronology.length > 0 && (
                                <div className="bg-slate-900/40 p-5 rounded-xl border border-slate-700/50">
                                    <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider mb-5 flex items-center gap-2"><Clock size={16}/> Kronologjia e Verifikuar</h3>
                                    <div className="relative pl-4 border-l-2 border-slate-700/50 space-y-8 ml-2">
                                        {result.chronology.map((event, idx) => (
                                            <div key={idx} className="relative group">
                                                <div className="absolute -left-[23px] top-1 w-3.5 h-3.5 rounded-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)] border-2 border-background-dark group-hover:bg-cyan-400 transition-colors" />
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-cyan-300 font-bold text-xs tracking-wide bg-cyan-950/30 px-2 py-0.5 rounded-md w-fit border border-cyan-900/50">{event.date}</span>
                                                    <p className="text-gray-200 text-sm leading-relaxed font-medium mt-1">{renderTextWithCitations(sanitizeText(event.event))}</p>
                                                    {event.source_doc && (<span className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold flex items-center gap-1"><FileText size={10} />{event.source_doc}</span>)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            
                            {/* CONTRADICTIONS */}
                            {result.contradictions && result.contradictions.length > 0 && (
                                <div className="bg-orange-900/10 p-5 rounded-xl border border-orange-500/20">
                                    <h3 className="text-sm font-bold text-orange-400 uppercase tracking-wider mb-3 flex items-center gap-2"><ShieldAlert size={16}/> Kontradikta / Mospërputhje</h3>
                                    <ul className="space-y-2">
                                        {result.contradictions.map((c, i) => (<li key={i} className="flex gap-3 text-sm text-gray-300 bg-black/20 p-3 rounded-lg border border-white/5"><span className="text-orange-500 font-bold mt-1">•</span><span className="leading-relaxed">{renderTextWithCitations(sanitizeText(c))}</span></li>))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* TAB 2: STRATEGY */}
                    {activeTab === 'strategy' && (
                         <div className="space-y-6 animate-in fade-in slide-in-from-right-2 duration-300">
                            <div className="bg-purple-900/10 p-5 rounded-xl border border-purple-500/20">
                                <h3 className="text-sm font-bold text-purple-400 uppercase tracking-wider mb-3 flex items-center gap-2"><MessageCircleQuestion size={16}/> Pyetje për Dëshmitarin</h3>
                                {result.suggested_questions && result.suggested_questions.length > 0 ? (
                                    <ul className="space-y-3">{result.suggested_questions.map((q, i) => (<li key={i} className="flex gap-3 text-sm text-gray-200 bg-black/20 p-3 rounded-lg border border-purple-500/10 hover:border-purple-500/30 transition-colors"><span className="text-purple-400 font-bold whitespace-nowrap">Pyetje {i+1}:</span><span className="leading-relaxed font-medium">{renderTextWithCitations(sanitizeText(q))}</span></li>))}</ul>
                                ) : (<p className="text-gray-500 text-sm italic">Nuk u gjeneruan pyetje specifike.</p>)}
                            </div>
                             <div className="bg-emerald-900/10 p-5 rounded-xl border border-emerald-500/20">
                                <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Target size={16}/> Kërkesa për Prova (Discovery)</h3>
                                {result.discovery_targets && result.discovery_targets.length > 0 ? (
                                    <ul className="space-y-3">{result.discovery_targets.map((d, i) => (<li key={i} className="flex gap-3 text-sm text-gray-200 bg-black/20 p-3 rounded-lg border border-emerald-500/10"><span className="text-emerald-400 font-bold">➢</span><span className="leading-relaxed">{renderTextWithCitations(sanitizeText(d))}</span></li>))}</ul>
                                ) : (<p className="text-gray-500 text-sm italic">Nuk u identifikuan prova të reja për t'u kërkuar.</p>)}
                            </div>
                         </div>
                    )}
                </div>
             </>
          )}
          <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold transition-all shadow-lg glow-primary">{t('general.close', 'Mbyll Sallen')}</button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
  return ReactDOM.createPortal(modalContent, document.body);
};
export default AnalysisModal;