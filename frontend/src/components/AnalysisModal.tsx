// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V7.1 (GLOBAL CITATION AWARE)
// 1. UI UPDATE: Detects and highlights Global Citations (UNCRC, ECHR) with distinct iconography.
// 2. DATA MAPPING: Remains aligned with Backend JSON.
// 3. UX: 'Risk Level' badge visual improvements.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Scale, FileText, Swords, Target, MessageCircleQuestion, 
    Gavel, ShieldAlert, CheckCircle2, BookOpen, AlertTriangle, Globe
} from 'lucide-react';
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

const sanitizeText = (text: string | undefined | null): string => {
    if (!text) return "";
    return text.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
};

// Helper to detect global laws
const isGlobalCitation = (text: string) => {
    const globalKeywords = ["UNCRC", "KEDNJ", "ECHR", "Konventa", "Convention", "Strasburg", "Global", "International"];
    return globalKeywords.some(keyword => text.includes(keyword));
};

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, isLoading }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'legal' | 'action'>('legal');

  useEffect(() => {
    if (isOpen) { 
        document.body.style.overflow = 'hidden';
        setActiveTab('legal');
    } else { 
        document.body.style.overflow = 'unset'; 
    }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  // SAFE DESTRUCTURING (New Backend Schema)
  const {
      summary = "",
      key_issues = [],
      legal_basis = [],
      strategic_analysis = "",
      weaknesses = [],
      action_plan = [],
      risk_level = "MEDIUM"
  } = result || {};

  // Risk Badge Logic
  const getRiskColor = (level: string) => {
      if (level?.includes('HIGH')) return 'bg-red-500/20 text-red-400 border-red-500/50';
      if (level?.includes('LOW')) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
  };

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-[100] p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.98, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.98, opacity: 0, y: 10 }} className="glass-high w-full h-full sm:h-[85vh] sm:max-w-5xl rounded-none sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-white/10" onClick={(e) => e.stopPropagation()}>
          
          {/* HEADER */}
          <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/5 backdrop-blur-md shrink-0">
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-3 min-w-0">
              <div className="p-2 bg-gradient-to-br from-primary-start to-primary-end rounded-lg shrink-0 shadow-lg shadow-primary-start/20">
                  <Gavel className="text-white h-5 w-5" />
              </div>
              <div className="flex flex-col">
                  <span className="truncate leading-tight tracking-tight">Salla e Strategjisë Ligjore</span>
                  <div className={`text-[10px] uppercase tracking-widest font-bold mt-1 px-1.5 py-0.5 rounded border w-fit ${getRiskColor(risk_level)}`}>
                      RREZIKU: {risk_level}
                  </div>
              </div>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-xl transition-colors shrink-0"><X size={20} /></button>
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center"><div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div><h3 className="text-xl font-bold text-white mb-2">Duke Analizuar Ligjet & Faktet...</h3><p className="text-text-secondary text-sm max-w-sm mx-auto">Avokati AI po verifikon bazën ligjore, përfshirë Konventat Ndërkombëtare.</p></div>
          ) : (
             <>
                {/* TABS */}
                <div className="flex border-b border-white/5 px-6 bg-black/20 shrink-0 overflow-x-auto no-scrollbar gap-6">
                    <button onClick={() => setActiveTab('legal')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'legal' ? 'border-primary-start text-white' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Scale size={16}/> Analiza Ligjore
                    </button>
                    <button onClick={() => setActiveTab('action')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'action' ? 'border-accent-start text-accent-start' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Target size={16}/> Plani Strategjik
                    </button>
                </div>

                {/* CONTENT */}
                <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-black/10">
                    <style>{scrollbarStyles}</style>

                    {activeTab === 'legal' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            
                            {/* SUMMARY */}
                            <div className="glass-panel p-6 rounded-2xl">
                                <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <FileText size={16}/> Përmbledhje Ekzekutive
                                </h3>
                                <p className="text-white text-sm leading-relaxed whitespace-pre-line border-l-2 border-white/20 pl-4">
                                    {sanitizeText(summary || "Nuk ka përmbledhje të disponueshme.")}
                                </p>
                            </div>

                            {/* KEY ISSUES */}
                            {key_issues && key_issues.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-white/5 bg-white/5">
                                    <h3 className="text-xs font-bold text-primary-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <Swords size={16}/> Çështjet Kryesore (Issues)
                                    </h3>
                                    <div className="grid gap-3">
                                        {key_issues.map((issue: string, idx: number) => (
                                            <div key={idx} className="flex items-start gap-3 bg-white/5 p-3 rounded-lg border border-white/10">
                                                <span className="text-primary-400 font-bold mt-0.5">#{idx + 1}</span>
                                                <p className="text-sm text-gray-200 font-medium leading-snug">{sanitizeText(issue)}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* LEGAL BASIS */}
                            {legal_basis && legal_basis.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-secondary-start/20 bg-secondary-start/5">
                                    <h3 className="text-xs font-bold text-secondary-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <BookOpen size={16}/> Baza Ligjore (Rules)
                                    </h3>
                                    <ul className="space-y-2">
                                        {legal_basis.map((law: string, i: number) => {
                                            const isGlobal = isGlobalCitation(law);
                                            return (
                                                <li key={i} className={`flex gap-3 text-sm items-center p-2 rounded-lg transition-colors ${isGlobal ? 'bg-indigo-500/10 border border-indigo-500/30' : ''}`}>
                                                    {isGlobal ? (
                                                        <Globe size={16} className="text-indigo-400 shrink-0"/>
                                                    ) : (
                                                        <Scale size={16} className="text-secondary-400 shrink-0"/>
                                                    )}
                                                    <span className={`leading-relaxed font-mono text-xs ${isGlobal ? 'text-indigo-200' : 'text-secondary-100'}`}>
                                                        {sanitizeText(law)}
                                                    </span>
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'action' && (
                         <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                            
                            {/* STRATEGIC ANALYSIS */}
                            {strategic_analysis && (
                                <div className="glass-panel p-6 rounded-2xl border-accent-start/20 bg-accent-start/5">
                                    <h3 className="text-xs font-bold text-accent-start uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <MessageCircleQuestion size={16}/> Analiza Strategjike (Analysis)
                                    </h3>
                                    <p className="text-white text-sm leading-relaxed">{sanitizeText(strategic_analysis)}</p>
                                </div>
                            )}
                            
                            {/* WEAKNESSES */}
                            {weaknesses && weaknesses.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-red-500/20 bg-red-500/5">
                                    <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <ShieldAlert size={16}/> Dobësitë e Kundërshtarit
                                    </h3>
                                    <ul className="space-y-3">
                                        {weaknesses.map((w: string, i: number) => (
                                            <li key={i} className="flex gap-3 text-sm text-red-100 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
                                                <AlertTriangle size={16} className="text-red-500 shrink-0"/>
                                                <span className="leading-relaxed">{sanitizeText(w)}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            
                            {/* ACTION PLAN */}
                            {action_plan && action_plan.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-emerald-500/20 bg-emerald-500/5">
                                    <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <CheckCircle2 size={16}/> Plani i Veprimit (Conclusion)
                                    </h3>
                                    <div className="space-y-3">
                                        {action_plan.map((step: string, i: number) => (
                                            <div key={i} className="flex gap-4 text-sm text-white bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors">
                                                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500 text-black font-bold text-xs shrink-0">
                                                    {i + 1}
                                                </span>
                                                <span className="leading-relaxed font-medium">{sanitizeText(step)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
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