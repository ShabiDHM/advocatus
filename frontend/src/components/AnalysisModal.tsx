// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V7.6 (CLEAN CODE)
// 1. CLEANUP: Removed unused 'sanitizeText' function to resolve TS warning.
// 2. LOGIC: 'cleanLegalText' handles all text sanitization now.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Scale, FileText, Swords, Target, MessageCircleQuestion, 
    Gavel, ShieldAlert, CheckCircle2, BookOpen, AlertTriangle, Globe, Link as LinkIcon
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

// Helper: Consolidates all cleaning logic
const cleanLegalText = (text: string | undefined | null): string => {
    if (!text) return "";
    let clean = text.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
    // Strip common AI prefixes to keep UI clean
    clean = clean.replace(/^Ligji\/Neni \(Kosovë\):\s*/i, '');
    clean = clean.replace(/^Konventa \(Global\):\s*/i, '');
    return clean;
};

// SMART RENDERER: Handles [Title](Link) OR Title(doc://Link) formats
const renderStructuredCitation = (text: string) => {
    // 1. Try strict Markdown: [Title](Link): Body
    let match = text.match(/^\[(.*?)\]\((.*?)\):?\s*(.*)/s);
    
    // 2. Try loose format: Title(doc://Link): Body
    if (!match) {
        match = text.match(/^(.*?)\((doc:\/\/.*?)\):?\s*(.*)/s);
    }

    if (match) {
        const title = match[1].trim();
        const link = match[2].trim(); 
        const body = match[3].trim();

        return (
            <div className="flex flex-col gap-2 w-full">
                {/* Header (Title) */}
                <div className="flex items-center gap-2 font-bold text-primary-200 text-xs uppercase tracking-wide cursor-pointer hover:text-white transition-colors group">
                    <LinkIcon size={12} className="text-primary-400 group-hover:text-white" />
                    <span title={link} className="border-b border-dashed border-primary-500/30 pb-0.5">{title}</span>
                </div>
                
                {/* Body (Content/Relevance) */}
                <div className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed pl-5 border-l border-white/10 ml-0.5">
                    {body.split('\n').map((line, i) => {
                        const trimmed = line.trim();
                        if (!trimmed) return null;
                        
                        // Highlight Keys
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
    
    // Fallback: Just show clean text if parsing fails completely
    return <span className="leading-relaxed font-mono text-xs whitespace-pre-wrap">{cleanLegalText(text)}</span>;
};

const isGlobalCitation = (text: string) => {
    const globalKeywords = ["UNCRC", "KEDNJ", "ECHR", "Konventa", "Convention", "Strasburg", "Global", "International", "OKB"];
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
                  <span className="truncate leading-tight tracking-tight">{t('analysis.title', 'Salla e Strategjisë Ligjore')}</span>
                  <div className={`text-[10px] uppercase tracking-widest font-bold mt-1 px-1.5 py-0.5 rounded border w-fit ${getRiskColor(risk_level)}`}>
                      {t('analysis.risk_label', 'RREZIKU')}: {risk_level}
                  </div>
              </div>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-xl transition-colors shrink-0"><X size={20} /></button>
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                 <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div>
                 <h3 className="text-xl font-bold text-white mb-2">{t('analysis.loading_title', 'Duke Analizuar Ligjet & Faktet...')}</h3>
                 <p className="text-text-secondary text-sm max-w-sm mx-auto">{t('analysis.loading_desc', 'Avokati AI po verifikon bazën ligjore dhe po kërkon dobësitë e kundërshtarit.')}</p>
             </div>
          ) : (
             <>
                {/* TABS */}
                <div className="flex border-b border-white/5 px-6 bg-black/20 shrink-0 overflow-x-auto no-scrollbar gap-6">
                    <button onClick={() => setActiveTab('legal')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'legal' ? 'border-primary-start text-white' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Scale size={16}/> {t('analysis.tab_legal', 'Analiza Ligjore')}
                    </button>
                    <button onClick={() => setActiveTab('action')} className={`py-4 text-xs sm:text-sm font-bold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${activeTab === 'action' ? 'border-accent-start text-accent-start' : 'border-transparent text-text-secondary hover:text-white'}`}>
                        <Target size={16}/> {t('analysis.tab_strategic', 'Plani Strategjik')}
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
                                    <FileText size={16}/> {t('analysis.section_summary', 'Përmbledhje Ekzekutive')}
                                </h3>
                                <p className="text-white text-sm leading-relaxed whitespace-pre-line border-l-2 border-white/20 pl-4">
                                    {cleanLegalText(summary || t('analysis.no_summary', 'Nuk ka përmbledhje të disponueshme.'))}
                                </p>
                            </div>

                            {/* KEY ISSUES */}
                            {key_issues && key_issues.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-white/5 bg-white/5">
                                    <h3 className="text-xs font-bold text-primary-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <Swords size={16}/> {t('analysis.section_issues', 'Çështjet Kryesore (Issues)')}
                                    </h3>
                                    <div className="grid gap-3">
                                        {key_issues.map((issue: string, idx: number) => (
                                            <div key={idx} className="flex items-start gap-3 bg-white/5 p-3 rounded-lg border border-white/10">
                                                <span className="text-primary-400 font-bold mt-0.5">#{idx + 1}</span>
                                                <p className="text-sm text-gray-200 font-medium leading-snug">{cleanLegalText(issue)}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* LEGAL BASIS */}
                            {legal_basis && legal_basis.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-secondary-start/20 bg-secondary-start/5">
                                    <h3 className="text-xs font-bold text-secondary-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <BookOpen size={16}/> {t('analysis.section_rules', 'Baza Ligjore (Rules)')}
                                    </h3>
                                    <ul className="space-y-3">
                                        {legal_basis.map((law: string, i: number) => {
                                            const isGlobal = isGlobalCitation(law);
                                            return (
                                                <li key={i} className={`flex gap-3 text-sm items-start p-4 rounded-xl transition-colors ${isGlobal ? 'bg-indigo-500/10 border border-indigo-500/30' : 'bg-white/5 border border-white/5 hover:border-white/10'}`}>
                                                    {isGlobal ? (
                                                        <Globe size={20} className="text-indigo-400 shrink-0 mt-0.5"/>
                                                    ) : (
                                                        <Scale size={20} className="text-secondary-400 shrink-0 mt-0.5"/>
                                                    )}
                                                    {renderStructuredCitation(law)}
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
                                        <MessageCircleQuestion size={16}/> {t('analysis.section_analysis', 'Analiza Strategjike (Analysis)')}
                                    </h3>
                                    <p className="text-white text-sm leading-relaxed whitespace-pre-line">{cleanLegalText(strategic_analysis)}</p>
                                </div>
                            )}
                            
                            {/* WEAKNESSES */}
                            {weaknesses && weaknesses.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-red-500/20 bg-red-500/5">
                                    <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <ShieldAlert size={16}/> {t('analysis.section_weaknesses', 'Dobësitë e Kundërshtarit')}
                                    </h3>
                                    <ul className="space-y-3">
                                        {weaknesses.map((w: string, i: number) => (
                                            <li key={i} className="flex gap-3 text-sm text-red-100 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
                                                <AlertTriangle size={16} className="text-red-500 shrink-0"/>
                                                <span className="leading-relaxed">{cleanLegalText(w)}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            
                            {/* ACTION PLAN */}
                            {action_plan && action_plan.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl border-emerald-500/20 bg-emerald-500/5">
                                    <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <CheckCircle2 size={16}/> {t('analysis.section_conclusion', 'Plani i Veprimit (Conclusion)')}
                                    </h3>
                                    <div className="space-y-3">
                                        {action_plan.map((step: string, i: number) => (
                                            <div key={i} className="flex gap-4 text-sm text-white bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors">
                                                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500 text-black font-bold text-xs shrink-0">
                                                    {i + 1}
                                                </span>
                                                <span className="leading-relaxed font-medium">{cleanLegalText(step)}</span>
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