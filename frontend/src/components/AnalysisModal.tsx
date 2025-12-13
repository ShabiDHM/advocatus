// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - WAR ROOM UI V2.1 (OPTIONAL DOC ID)
// 1. FIXED: docId is now optional to support Case-Wide vs Document-Specific analysis.
// 2. LOGIC: Download button is hidden if docId is missing (Case-Wide mode).

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Scale, FileText, User, ShieldAlert, Swords, Target, MessageCircleQuestion, Gavel, Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface LitigationAnalysis {
  summary_analysis?: string;
  conflicting_parties?: Array<{ party_name: string; core_claim: string }>;
  contradictions?: string[];
  suggested_questions?: string[];
  discovery_targets?: string[];
  key_evidence?: string[];
  missing_info?: string[];
}

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: LitigationAnalysis;
  isLoading?: boolean;
  caseId: string;
  docId?: string; // Optional: Only needed for Draft Generation
}

const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
`;

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, isLoading, caseId, docId }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'analysis' | 'strategy'>('analysis');
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (isOpen) { document.body.style.overflow = 'hidden'; } 
    else { document.body.style.overflow = 'unset'; }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  const handleGenerateObjection = async () => {
      if (!docId) return; // Guard clause
      try {
          setIsGenerating(true);
          const token = localStorage.getItem('token'); 
          const response = await fetch(`${import.meta.env.VITE_API_URL}/cases/${caseId}/documents/${docId}/generate-objection`, {
              method: 'GET',
              headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!response.ok) throw new Error('Download failed');
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `Objection_Draft.docx`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
      } catch (error) {
          console.error("Draft generation failed:", error);
          alert("Dështoi gjenerimi i dokumentit.");
      } finally {
          setIsGenerating(false);
      }
  };

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-0 sm:p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[95vh] sm:max-w-6xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0 gap-4">
            <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2 min-w-0">
              <div className="p-1.5 bg-primary-start/10 rounded-lg flex-shrink-0">
                 <Gavel className="text-primary-start h-5 w-5 sm:h-6 sm:w-6" />
              </div>
              <span className="truncate">{t('analysis.modalTitle', 'Salla e Strategjisë (War Room)')}</span>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors flex-shrink-0">
                <X size={24} />
            </button>
          </div>

          {/* Loading State */}
          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6"></div>
                <h3 className="text-xl font-bold text-white mb-2">Duke Kryqëzuar Provat...</h3>
                <p className="text-gray-400">Inteligjenca Artificiale po krahason këtë dokument me të gjithë dosjen.</p>
             </div>
          ) : (
             <>
                {/* Tabs */}
                <div className="flex border-b border-white/10 px-6 bg-black/20">
                    <button onClick={() => setActiveTab('analysis')} className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'analysis' ? 'border-primary-start text-white' : 'border-transparent text-gray-400 hover:text-white'}`}>
                        <Scale size={16}/> Analiza Faktike
                    </button>
                    <button onClick={() => setActiveTab('strategy')} className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'strategy' ? 'border-orange-500 text-orange-400' : 'border-transparent text-gray-400 hover:text-white'}`}>
                        <Swords size={16}/> Strategjia Sulmuese
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar relative bg-background-dark/50">
                    <style>{scrollbarStyles}</style>

                    {/* TAB 1: ANALYSIS */}
                    {activeTab === 'analysis' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <div className="bg-blue-900/10 p-5 rounded-xl border border-blue-500/20">
                                <h3 className="text-sm font-bold text-blue-400 uppercase tracking-wider mb-2 flex items-center gap-2"><FileText size={16}/> {t('analysis.summary', 'Analiza e Besueshmërisë')}</h3>
                                <p className="text-gray-200 text-sm leading-relaxed">{result.summary_analysis || "Nuk ka analizë të disponueshme."}</p>
                            </div>
                            {result.conflicting_parties && result.conflicting_parties.length > 0 && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {result.conflicting_parties.map((party, idx) => (
                                        <div key={idx} className="p-4 rounded-xl border bg-white/5 border-white/10">
                                            <div className="flex items-center gap-2 mb-2"><User size={16} className="text-gray-400" /><h4 className="font-bold text-sm text-gray-200">{party.party_name}</h4></div>
                                            <p className="text-gray-400 text-xs italic">"{party.core_claim}"</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {result.contradictions && result.contradictions.length > 0 && (
                                <div className="bg-orange-900/10 p-5 rounded-xl border border-orange-500/20">
                                    <h3 className="text-sm font-bold text-orange-400 uppercase tracking-wider mb-3 flex items-center gap-2"><ShieldAlert size={16}/> Kontradikta të Gjetura</h3>
                                    <ul className="space-y-2">{result.contradictions.map((c, i) => (<li key={i} className="flex gap-3 text-sm text-gray-300 bg-black/20 p-3 rounded-lg border border-white/5"><span className="text-orange-500 font-bold">•</span><span className="leading-relaxed">{c}</span></li>))}</ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* TAB 2: STRATEGY */}
                    {activeTab === 'strategy' && (
                         <div className="space-y-6 animate-in fade-in slide-in-from-right-2 duration-300">
                             
                             {/* CONDITIONAL RENDER: Only show if docId is present */}
                             {docId && (
                                 <div className="mb-6 flex justify-end">
                                    <button onClick={handleGenerateObjection} disabled={isGenerating} className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg ${isGenerating ? 'bg-gray-600 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white'}`}>
                                        {isGenerating ? (<><div className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin"/>Duke Gjeneruar...</>) : (<><Download size={18} /> Gjenero Kundërshtimin (.docx)</>)}
                                    </button>
                                 </div>
                             )}

                            <div className="bg-purple-900/10 p-5 rounded-xl border border-purple-500/20">
                                <h3 className="text-sm font-bold text-purple-400 uppercase tracking-wider mb-3 flex items-center gap-2"><MessageCircleQuestion size={16}/> Pyetje për Dëshmitarin (Cross-Examination)</h3>
                                {result.suggested_questions && result.suggested_questions.length > 0 ? (<ul className="space-y-3">{result.suggested_questions.map((q, i) => (<li key={i} className="flex gap-3 text-sm text-gray-200 bg-black/20 p-3 rounded-lg border border-purple-500/10 hover:border-purple-500/30 transition-colors"><span className="text-purple-400 font-bold">Q{i+1}:</span><span className="leading-relaxed font-medium">{q}</span></li>))}</ul>) : <p className="text-gray-500 text-sm italic">Nuk u gjeneruan pyetje specifike.</p>}
                            </div>
                             <div className="bg-emerald-900/10 p-5 rounded-xl border border-emerald-500/20">
                                <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Target size={16}/> Kërkesa për Prova (Discovery)</h3>
                                {result.discovery_targets && result.discovery_targets.length > 0 ? (<ul className="space-y-3">{result.discovery_targets.map((d, i) => (<li key={i} className="flex gap-3 text-sm text-gray-200 bg-black/20 p-3 rounded-lg border border-emerald-500/10"><span className="text-emerald-400 font-bold">➢</span><span className="leading-relaxed">{d}</span></li>))}</ul>) : <p className="text-gray-500 text-sm italic">Nuk u identifikuan prova të reja për t'u kërkuar.</p>}
                            </div>
                         </div>
                    )}
                </div>
             </>
          )}

          {/* Footer */}
          <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold transition-all shadow-lg glow-primary">
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