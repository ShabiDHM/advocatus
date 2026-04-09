// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V16.1 (FIXED NODEJS.TIMEOUT ERROR)

/* eslint-disable tailwindcss/no-contradicting-classname */

import React, { useEffect, useState, useRef } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Scale, FileText, Swords, Target,
    Gavel, CheckCircle2, BookOpen, Globe, 
    Link as LinkIcon, Clock, Skull, AlertOctagon,
    Shield, ShieldAlert, ShieldCheck, Percent, Info, AlertTriangle,
    ZoomIn, ZoomOut
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { TFunction } from 'i18next';
import { CaseAnalysisResult, DeepAnalysisResult, ChronologyEvent, Contradiction } from '../data/types'; 
import { apiService } from '../services/api';

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: CaseAnalysisResult; 
  caseId: string;
  isLoading?: boolean;
}

type ZoomLevel = 'normal' | 'large' | 'xlarge';

const SpinnerStyles = () => (
  <style>{`
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    .spinner-robust {
      animation: spin 1s linear infinite !important;
    }
  `}</style>
);

const Spinner = ({ size = 'w-20 h-20' }: { size?: string }) => (
  <div
    className={`${size} border-4 border-primary-start border-t-transparent rounded-full spinner-robust`}
  />
);

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
                    <div className="flex items-center gap-2 font-bold text-primary-start text-xs uppercase tracking-wide group">
                        <LinkIcon size={12} className="text-primary-start opacity-70" />
                        <span className="border-b border-dashed border-primary-start/30 pb-0.5">{lawTitle}</span>
                    </div>
                    {article && (
                        <div className="px-3 py-1 rounded-lg bg-success-start/10 text-[11px] font-black uppercase tracking-widest text-success-start border border-success-start/20 leading-relaxed">
                            {article}
                        </div>
                    )}
                </div>
                {body && (
                    <div className="text-gray-700 dark:text-gray-300 text-[13px] leading-relaxed pl-5 border-l-2 border-border-main ml-0.5 mt-1">
                        <span className="text-primary-start opacity-80 text-[11px] font-black uppercase mr-2 tracking-widest">Relevanca:</span>
                        {body}
                    </div>
                )}
            </div>
        );
    }

    const rawText = safeString(item);
    const parts = rawText.split(/(\[.*?\]\(doc:\/\/.*?\))/g);

    return (
        <span className="leading-relaxed text-gray-900 dark:text-gray-100">
            {parts.map((part, i) => {
                const match = part.match(/\[(.*?)\]\((doc:\/\/.*?)\)/);
                if (match) {
                    const [_, title, link] = match;
                    const isGlobal = ["UNCRC", "KEDNJ", "ECHR", "Konventa"].some(k => title.includes(k));
                    return (
                        <span key={i} title={link} className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-black uppercase tracking-widest border mx-1 align-middle transition-colors cursor-help ${
                            isGlobal 
                            ? 'bg-indigo-500/10 text-indigo-500 border-indigo-500/30' 
                            : 'bg-primary-start/10 text-primary-start border-primary-start/30'
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

const SuccessTooltip: React.FC<{ children: React.ReactNode; t: TFunction }> = ({ children, t }) => {
    const [show, setShow] = useState(false);
    // FIXED: Replaced NodeJS.Timeout with ReturnType<typeof setTimeout>
    const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

    const handleMouseEnter = () => { timeoutRef.current = setTimeout(() => setShow(true), 400); };
    const handleMouseLeave = () => { if (timeoutRef.current) clearTimeout(timeoutRef.current); setShow(false); };

    return (
        <div className="relative inline-block" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
            {children}
            <AnimatePresence>
                {show && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="absolute top-full left-1/2 transform -translate-x-1/2 mt-3 w-56 p-4 bg-white dark:bg-gray-800 text-[12px] font-medium text-gray-700 dark:text-gray-300 rounded-xl border border-border-main shadow-lawyer-dark z-[100] text-center leading-relaxed"
                    >
                        {t('analysis.success_tooltip', 'Probabiliteti i suksesit i vlerësuar nga AI bazuar në faktet dhe ligjin.')}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, caseId, isLoading = false }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'legal' | 'war_room'>('legal');
  const [warRoomSubTab, setWarRoomSubTab] = useState<'strategy' | 'adversarial' | 'timeline' | 'contradictions'>('strategy');
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('normal');
  
  const [deepResult, setDeepResult] = useState<DeepAnalysisResult | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);
  const [isChronLoading, setIsChronLoading] = useState(false);
  const [isContradictLoading, setIsContradictLoading] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  useEffect(() => {
    if (isOpen) { document.body.style.overflow = 'hidden'; setActiveTab('legal'); setWarRoomSubTab('strategy'); } 
    else { document.body.style.overflow = 'unset'; }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  const handleWarRoomEntry = async () => {
      setActiveTab('war_room');
      if (!deepResult && !isSimLoading && !isChronLoading && !isContradictLoading) {
          setIsSimLoading(true); setIsChronLoading(true); setIsContradictLoading(true);

          apiService.analyzeDeepChronology(caseId).then(data => {
              setDeepResult(prev => ({ ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }), chronology: data }));
              setIsChronLoading(false);
          }).catch(() => setIsChronLoading(false));

          apiService.analyzeDeepSimulation(caseId).then(data => {
              setDeepResult(prev => ({ ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }), adversarial_simulation: data }));
              setIsSimLoading(false);
          }).catch(() => setIsSimLoading(false));

          apiService.analyzeDeepContradictions(caseId).then(data => {
              setDeepResult(prev => ({ ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }), contradictions: data }));
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
    } catch (error) { alert(t('analysis.archive_error', 'Dështoi ruajtja në arkiv.')); } 
    finally { setIsArchiving(false); }
  };

  const toggleZoom = () => {
    setZoomLevel(prev => {
      if (prev === 'normal') return 'large';
      if (prev === 'large') return 'xlarge';
      return 'normal';
    });
  };

  const getFontSize = () => {
    switch (zoomLevel) {
      case 'large': return '1rem';
      case 'xlarge': return '1.125rem';
      default: return '0.9375rem';
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
      let styles = 'bg-warning-start/10 text-warning-start border-warning-start/20';
      let icon = <Shield size={14} />;
      let label = t('analysis.risk_medium', 'I MESËM');

      if (l.includes('HIGH')) {
          styles = 'bg-danger-start/10 text-danger-start border-danger-start/20';
          icon = <ShieldAlert size={14} />;
          label = t('analysis.risk_high', 'I LARTË');
      } else if (l.includes('LOW')) {
          styles = 'bg-success-start/10 text-success-start border-success-start/20';
          icon = <ShieldCheck size={14} />;
          label = t('analysis.risk_low', 'I ULËT');
      }

      return (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${styles} shadow-sm`}>
              {icon}
              <div className="flex items-center gap-1.5 text-[11px] font-black tracking-widest uppercase">
                  <span className="opacity-70">{t('analysis.risk_label', 'RREZIKU')}</span>
                  <span className="w-1 h-1 rounded-full bg-current opacity-50" />
                  <span>{label}</span>
              </div>
          </div>
      );
  };

  const renderSuccessBadge = (prob: string | null) => {
      if (!prob) return null;
      return (
        <SuccessTooltip t={t}>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-primary-start/10 text-primary-start border-primary-start/20 shadow-sm ml-2 cursor-help">
                <Percent size={14} />
                <div className="flex items-center gap-1.5 text-[11px] font-black tracking-widest uppercase">
                    <span className="opacity-70">SUKSESI</span>
                    <span className="w-1 h-1 rounded-full bg-current opacity-50" />
                    <span>{prob}</span>
                </div>
            </div>
        </SuccessTooltip>
      );
  };

  const renderSubTabLoader = () => (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-32">
        <Spinner size="w-16 h-16" />
        <h3 className="text-lg font-black text-gray-900 dark:text-gray-100 uppercase tracking-widest mb-3 mt-6">{t('analysis.loading_deep_title', 'Duke Simuluar...')}</h3>
        <p className="text-gray-500 dark:text-gray-400 text-[12px] font-bold uppercase tracking-widest">{t('analysis.rag_processing', 'Analiza e thellë statutore...')}</p>
    </div>
  );

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4 sm:p-6" 
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.98, opacity: 0, y: 10 }} 
          animate={{ scale: 1, opacity: 1, y: 0 }} 
          exit={{ scale: 0.98, opacity: 0, y: 10 }} 
          className="w-full h-full sm:h-[85vh] sm:max-w-7xl bg-white dark:bg-gray-900 border border-border-main rounded-2xl shadow-xl overflow-hidden flex flex-col" 
          onClick={(e) => e.stopPropagation()}
        >
          <SpinnerStyles />
          
          <div className="px-6 py-5 border-b border-border-main flex justify-between items-center bg-gray-50 dark:bg-gray-800 shrink-0">
            <h2 className="flex items-center gap-4 min-w-0">
              <div className="w-12 h-12 bg-primary-start text-white rounded-2xl flex items-center justify-center shadow-accent-glow shrink-0">
                  <Gavel size={24} />
              </div>
              <div className="flex flex-col gap-1">
                  <span className="text-2xl font-black text-gray-900 dark:text-gray-100 uppercase tracking-tighter">{t('analysis.title', 'Strategjia Ligjore')}</span>
                  <div className="hidden sm:flex items-center mt-1 gap-2">{renderRiskBadge(risk_level)} {renderSuccessBadge(success_probability)}</div>
              </div>
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleZoom}
                className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all"
                title={zoomLevel === 'normal' ? t('analysis.zoomIn', 'Increase text size') : (zoomLevel === 'large' ? t('analysis.zoomMore', 'Even larger') : t('analysis.zoomOut', 'Reset text size'))}
              >
                {zoomLevel === 'normal' ? <ZoomIn size={20} /> : (zoomLevel === 'large' ? <ZoomIn size={20} /> : <ZoomOut size={20} />)}
              </button>
              <button onClick={onClose} className="p-3 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-all shrink-0 border border-transparent hover:border-border-main"><X size={24} /></button>
            </div>
          </div>
          
          <div className="sm:hidden px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-b border-border-main flex gap-2">
               {renderRiskBadge(risk_level)}
               {renderSuccessBadge(success_probability)}
          </div>

          {isLoading ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-white dark:bg-gray-900/50">
                 <Spinner size="w-20 h-20" />
                 <h3 className="text-xl font-black text-gray-900 dark:text-gray-100 uppercase tracking-widest mb-3 mt-6">{t('analysis.loading_title', 'Duke Analizuar...')}</h3>
                 <p className="text-gray-500 dark:text-gray-400 text-[12px] font-bold uppercase tracking-widest">Kjo mund të marrë disa sekonda</p>
             </div>
          ) : (
             <>
                <div className="flex border-b border-border-main px-8 bg-white dark:bg-gray-900 shrink-0 overflow-x-auto no-scrollbar gap-8">
                    <button onClick={() => setActiveTab('legal')} className={`py-4 text-[12px] font-black uppercase tracking-widest flex items-center gap-3 border-b-2 transition-all whitespace-nowrap ${activeTab === 'legal' ? 'border-primary-start text-primary-start' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}`}>
                        <Scale size={16}/> {t('analysis.tab_legal', 'Analiza Ligjore')}
                    </button>
                    <button onClick={handleWarRoomEntry} className={`py-4 text-[12px] font-black uppercase tracking-widest flex items-center gap-3 border-b-2 transition-all whitespace-nowrap ${activeTab === 'war_room' ? 'border-danger-start text-danger-start' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-danger-start'}`}>
                        <Swords size={16}/> {t('analysis.tab_war_room', 'Dhoma e Luftës')}
                    </button>
                </div>

                <div 
                  className="flex-1 overflow-y-auto p-6 md:p-10 custom-scrollbar text-gray-900 dark:text-gray-100"
                  style={{ fontSize: getFontSize() }}
                >
                    <div className="max-w-6xl mx-auto space-y-8">
                        {activeTab === 'legal' && (
                            <>
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                    <div className="bg-white dark:bg-gray-800 p-8 rounded-[1.5rem] border border-border-main shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <Info size={16} className="text-primary-start"/> {t('analysis.section_summary', 'Përmbledhja e Rastit')}
                                        </h3>
                                        <div className="text-gray-700 dark:text-gray-300 leading-relaxed border-l-2 border-primary-start/30 pl-5 ml-1">{renderCitationItem(summary)}</div>
                                    </div>

                                    {burden_of_proof && (
                                        <div className="bg-gray-50 dark:bg-gray-800/50 p-8 rounded-[1.5rem] border border-border-main shadow-sm hover-lift">
                                            <h3 className="text-[12px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-3">
                                                <Gavel size={16} className="text-primary-start"/> {t('analysis.section_burden', 'Barra e Provës')}
                                            </h3>
                                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed italic border-l-2 border-border-main pl-5 ml-1">{renderCitationItem(burden_of_proof)}</div>
                                        </div>
                                    )}
                                </div>

                                {missing_evidence && missing_evidence.length > 0 && (
                                    <div className="bg-danger-start/5 p-8 rounded-[1.5rem] border border-danger-start/20 shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-danger-start uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <AlertTriangle size={16}/> {t('analysis.section_missing', 'Mungesa e Provave')}
                                        </h3>
                                        <div className="grid gap-3">
                                            {missing_evidence.map((item, idx) => (
                                                <div key={idx} className="flex items-center gap-4 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-4 rounded-xl border border-danger-start/10 shadow-sm">
                                                    <span className="w-2 h-2 rounded-full bg-danger-start shrink-0" />
                                                    {renderCitationItem(item)}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {key_issues && key_issues.length > 0 && (
                                    <div className="bg-white dark:bg-gray-800 p-8 rounded-[1.5rem] border border-border-main shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <FileText size={16} className="text-primary-start"/> {t('analysis.section_issues', 'Çështjet Kryesore')}
                                        </h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {key_issues.map((issue: any, idx: number) => (
                                                <div key={idx} className="flex items-start gap-4 bg-gray-50 dark:bg-gray-800/50 p-5 rounded-xl border border-border-main">
                                                    <span className="text-primary-start font-black text-base leading-none opacity-50 mt-0.5">#{idx + 1}</span>
                                                    <div className="text-gray-700 dark:text-gray-300 font-medium leading-relaxed">{renderCitationItem(issue)}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {legal_basis && legal_basis.length > 0 && (
                                    <div className="bg-primary-start/5 p-8 rounded-[1.5rem] border border-primary-start/20 shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-primary-start uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <BookOpen size={16}/> {t('analysis.section_rules', 'Baza Ligjore (Statutore)')}
                                        </h3>
                                        <ul className="space-y-4">
                                            {legal_basis.map((lawItem: any, i: number) => {
                                                const lawStr = typeof lawItem === 'string' ? lawItem : (lawItem.law || "");
                                                const isGlobal = lawStr.includes("UNCRC") || lawStr.includes("Konventa") || lawStr.includes("KEDNJ");
                                                return (
                                                    <li key={i} className={`flex gap-4 text-[13px] items-start p-5 rounded-xl transition-colors shadow-sm bg-white dark:bg-gray-800 border ${isGlobal ? 'border-indigo-500/30' : 'border-border-main'}`}>
                                                        {isGlobal ? <Globe size={20} className="text-indigo-500 shrink-0 mt-0.5"/> : <Scale size={20} className="text-primary-start shrink-0 mt-0.5"/>}
                                                        {renderCitationItem(lawItem)}
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    </div>
                                )}
                            </>
                        )}
                        
                        {activeTab === 'war_room' && (
                            <div className="h-full flex flex-col">
                                <div className="flex flex-wrap gap-3 mb-8 shrink-0 pb-2">
                                    <button onClick={() => setWarRoomSubTab('strategy')} className={`px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all ${warRoomSubTab === 'strategy' ? 'bg-primary-start text-white shadow-accent-glow' : 'bg-white dark:bg-gray-800 border border-border-main text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}`}>
                                        <Target size={14} className="inline mr-2 -mt-0.5" /> {t('analysis.subtab_strategy', 'Plani Strategjik')}
                                    </button>
                                    <button onClick={() => setWarRoomSubTab('adversarial')} className={`px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all ${warRoomSubTab === 'adversarial' ? 'bg-danger-start text-white shadow-lg shadow-danger-start/30' : 'bg-white dark:bg-gray-800 border border-border-main text-gray-600 dark:text-gray-400 hover:text-danger-start'}`}>
                                        <Skull size={14} className="inline mr-2 -mt-0.5" /> {t('analysis.subtab_adversarial', 'Simulimi i Palës')}
                                    </button>
                                    <button onClick={() => setWarRoomSubTab('timeline')} className={`px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all ${warRoomSubTab === 'timeline' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/30' : 'bg-white dark:bg-gray-800 border border-border-main text-gray-600 dark:text-gray-400 hover:text-indigo-500'}`}>
                                        <Clock size={14} className="inline mr-2 -mt-0.5" /> {t('analysis.subtab_timeline', 'Kronologjia')}
                                    </button>
                                    <button onClick={() => setWarRoomSubTab('contradictions')} className={`px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all ${warRoomSubTab === 'contradictions' ? 'bg-warning-start text-white shadow-lg shadow-warning-start/30' : 'bg-white dark:bg-gray-800 border border-border-main text-gray-600 dark:text-gray-400 hover:text-warning-start'}`}>
                                        <AlertOctagon size={14} className="inline mr-2 -mt-0.5" /> {t('analysis.subtab_contradictions', 'Kontradiktat')}
                                    </button>
                                </div>

                                <div className="space-y-8 animate-in fade-in">
                                    {warRoomSubTab === 'strategy' ? (
                                        <div className="space-y-8">
                                            <div className="bg-white dark:bg-gray-800 p-8 rounded-[1.5rem] border border-border-main shadow-sm hover-lift">
                                                <h3 className="text-[12px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-3"><Target size={16} className="text-primary-start"/> {t('analysis.section_analysis', 'Analiza Strategjike')}</h3>
                                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed border-l-2 border-primary-start/30 pl-5 ml-1">{renderCitationItem(strategic_analysis)}</div>
                                            </div>
                                            <div className="bg-danger-start/5 p-8 rounded-[1.5rem] border border-danger-start/20 shadow-sm">
                                                <h3 className="text-[12px] font-black text-danger-start uppercase tracking-widest mb-5 flex items-center gap-3"><ShieldAlert size={16}/> {t('analysis.section_weaknesses', 'Pikat e Dobëta (Risku)')}</h3>
                                                <ul className="space-y-3">
                                                    {weaknesses.map((w: any, i: number) => (
                                                        <li key={i} className="flex items-center gap-4 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-4 rounded-xl border border-danger-start/10 shadow-sm">
                                                            <span className="w-2 h-2 rounded-full bg-danger-start shrink-0 opacity-50" />
                                                            {renderCitationItem(w)}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            <div className="bg-success-start/5 p-8 rounded-[1.5rem] border border-success-start/20 shadow-sm">
                                                <h3 className="text-[12px] font-black text-success-start uppercase tracking-widest mb-6 flex items-center gap-3"><CheckCircle2 size={16}/> {t('analysis.section_conclusion', 'Plani i Veprimit (Hapat)')}</h3>
                                                <div className="space-y-4">
                                                    {action_plan.map((step: any, i: number) => (
                                                        <div key={i} className="flex items-start gap-5 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-5 rounded-xl border border-success-start/10 shadow-sm">
                                                            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-success-start/20 text-success-start font-black text-[12px] shrink-0">{i + 1}</span>
                                                            <span className="leading-relaxed font-medium mt-1">{renderCitationItem(step)}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    ) : warRoomSubTab === 'adversarial' ? (
                                        isSimLoading ? renderSubTabLoader() : deepResult?.adversarial_simulation ? (
                                            <div className="space-y-8">
                                                <div className="bg-white dark:bg-gray-800 p-8 rounded-[1.5rem] border border-danger-start/30 shadow-lg shadow-danger-start/5">
                                                    <h3 className="text-[12px] font-black text-danger-start mb-5 uppercase tracking-widest flex items-center gap-3"><Skull size={16}/> {t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}</h3>
                                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed font-medium">{renderCitationItem(deepResult.adversarial_simulation.opponent_strategy)}</div>
                                                </div>
                                                <div className="grid gap-4">
                                                    {deepResult.adversarial_simulation.weakness_attacks.map((attack: string, i: number) => (
                                                        <div key={i} className="flex gap-4 bg-white dark:bg-gray-800 p-5 rounded-xl border border-border-main shadow-sm">
                                                            <Target size={18} className="text-danger-start shrink-0 mt-0.5" />
                                                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed">{renderCitationItem(attack)}</div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-center py-20 text-gray-500 dark:text-gray-400"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                        )
                                    ) : warRoomSubTab === 'timeline' ? (
                                        isChronLoading ? renderSubTabLoader() : deepResult?.chronology ? (
                                            <div className="space-y-6 relative border-l-2 border-border-main ml-4 pl-8 py-4">
                                                {deepResult.chronology.map((event: ChronologyEvent, i: number) => (
                                                    <div key={i} className="relative group bg-white dark:bg-gray-800 p-5 rounded-xl border border-border-main shadow-sm hover-lift">
                                                        <div className="absolute -left-[41px] top-6 w-4 h-4 rounded-full bg-white dark:bg-gray-800 border-4 border-indigo-500 shadow-sm" />
                                                        <div className="flex flex-col gap-2">
                                                            <span className="text-indigo-500 font-mono text-[11px] uppercase tracking-widest font-black">{event.date}</span>
                                                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed">{renderCitationItem(event.event)}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="text-center py-20 text-gray-500 dark:text-gray-400"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                        )
                                    ) : warRoomSubTab === 'contradictions' ? (
                                        isContradictLoading ? renderSubTabLoader() : deepResult?.contradictions ? (
                                            <div className="grid gap-6">
                                                {deepResult.contradictions.length === 0 ? (
                                                    <div className="bg-white dark:bg-gray-800 p-12 rounded-[1.5rem] text-center border border-border-main shadow-sm">
                                                        <CheckCircle2 size={48} className="mx-auto mb-4 text-success-start/50" />
                                                        <p className="text-gray-900 dark:text-gray-100 font-bold text-lg">{t('analysis.no_contradictions', 'Gjithçka e pastër.')}</p>
                                                        <p className="text-gray-500 dark:text-gray-400 text-[13px] mt-2">Nuk u gjetën kontradikta mes deklaratave dhe provave.</p>
                                                    </div>
                                                ) : (
                                                    deepResult.contradictions.map((c: Contradiction, i: number) => (
                                                        <div key={i} className="bg-white dark:bg-gray-800 border border-warning-start/30 p-6 rounded-[1.5rem] shadow-lg shadow-warning-start/5">
                                                            <div className="flex justify-between items-start mb-6 pb-4 border-b border-border-main">
                                                                <div className="flex items-center gap-3 text-warning-start font-black text-[11px] uppercase tracking-widest"><AlertOctagon size={16}/> {t('analysis.contradiction_label', 'Mospërputhje Factual')}</div>
                                                                <span className="text-[10px] font-black bg-warning-start/10 text-warning-start px-2.5 py-1 rounded-md border border-warning-start/20 uppercase tracking-widest">{getRiskLabel(c.severity)}</span>
                                                            </div>
                                                            <div className="grid md:grid-cols-2 gap-6 mb-4">
                                                                <div className="p-5 bg-gray-50 dark:bg-gray-900 rounded-xl border border-border-main">
                                                                    <span className="text-[11px] text-danger-start font-black uppercase tracking-widest mb-3 flex items-center gap-2">
                                                                        <FileText size={14}/> {t('analysis.claim_label', 'Deklarata')}
                                                                    </span>
                                                                    <div className="text-gray-700 dark:text-gray-300 leading-relaxed italic">"{renderCitationItem(c.claim)}"</div>
                                                                </div>
                                                                <div className="p-5 bg-gray-50 dark:bg-gray-900 rounded-xl border border-border-main">
                                                                    <span className="text-[11px] text-success-start font-black uppercase tracking-widest mb-3 flex items-center gap-2">
                                                                        <Scale size={14}/> {t('analysis.evidence_label', 'Prova Objektive')}
                                                                    </span>
                                                                    <div className="text-gray-700 dark:text-gray-300 font-medium leading-relaxed">{renderCitationItem(c.evidence)}</div>
                                                                </div>
                                                            </div>
                                                            <div className="mt-4 p-4 bg-warning-start/5 rounded-xl border border-warning-start/10">
                                                                <span className="text-[11px] text-warning-start font-black uppercase tracking-widest block mb-1">Impakti</span>
                                                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">{renderCitationItem(c.impact)}</div>
                                                            </div>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-center py-20 text-gray-500 dark:text-gray-400"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                        )
                                    ) : null}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
             </>
          )}
          
          <div className="px-8 py-5 border-t border-border-main bg-gray-50 dark:bg-gray-800 flex flex-col sm:flex-row gap-4 justify-between items-center shrink-0">
              <button 
                  onClick={handleArchiveStrategy} 
                  disabled={isArchiving || !deepResult}
                  className={`w-full sm:w-auto px-6 py-3.5 rounded-xl text-[11px] uppercase tracking-widest font-black transition-all flex items-center justify-center gap-3 border ${
                      isArchiving || !deepResult 
                      ? 'bg-gray-100 dark:bg-gray-900 text-gray-400 dark:text-gray-500 border-border-main cursor-not-allowed' 
                      : 'bg-success-start/10 text-success-start border-success-start/20 hover:bg-success-start/20 active:scale-95'
                  }`}
              >
                  {isArchiving ? (
                      <div className="w-4 h-4 border-2 border-success-start border-t-transparent rounded-full spinner-robust" />
                  ) : (
                      <CheckCircle2 size={16} />
                  )}
                  {t('analysis.btn_archive', 'Ruaj Strategjinë në Arkiv')}
              </button>
              
              <button onClick={onClose} className="btn-primary w-full sm:w-auto px-10 py-3.5 text-[11px] uppercase tracking-widest font-black">
                  {t('general.close', 'Përfundo Analizën')}
              </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default AnalysisModal;