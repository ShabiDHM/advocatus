// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V26.0 (SAFE ADVERSARIAL PROPERTY RESOLUTION)

import React, { useEffect, useState, useRef } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { 
    X, Scale, FileText, Swords, Target,
    Gavel, CheckCircle2, BookOpen, Globe, 
    Link as LinkIcon, Clock, Skull, AlertOctagon,
    Shield, ShieldAlert, ShieldCheck, Percent, Info, AlertTriangle,
    ZoomIn, ZoomOut, User, Landmark, Eye
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { TFunction } from 'i18next';
import { CaseAnalysisResult, DeepAnalysisResult, ChronologyEvent, Contradiction } from '../data/types'; 
import { apiService } from '../services/api';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

export interface AnalysisModalProps {
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
    if (typeof val === 'object') {
        try {
            return val.citizenText || val.lawyerText || val.summary || val.text || val.opponent_strategy || val.strategy || JSON.stringify(val);
        } catch {
            return String(val);
        }
    }
    return String(val);
};

const cleanSummaryHeadings = (raw: string): string => {
    if (!raw) return "";
    let clean = raw;
    
    clean = clean.replace(/###\s*[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]?\s*(UDHËZUESI|ANALIZA|PËRMBLEDHJA|KËSHILLIM).*?(?=\n|$)/giu, '');
    clean = clean.replace(/###\s*.*?(?=\n|$)/g, '');
    clean = clean.replace(/^["'\s{}]+|["'\s{}]+$/g, '');
    clean = clean.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
    
    return clean.trim();
};

const cleanLegalText = (text: any): string => {
    let clean = safeString(text);
    return cleanSummaryHeadings(clean);
};

const splitExecutiveSummary = (text: any): { citizenText: string; lawyerText: string } => {
    if (!text) return { citizenText: "", lawyerText: "" };

    if (typeof text === 'object') {
        const citizen = safeString(text.citizenText || text.citizen_summary || text.summary || text.text || '');
        const lawyer = safeString(text.lawyerText || text.lawyer_summary || text.professional || '');
        if (citizen || lawyer) {
            return { citizenText: cleanSummaryHeadings(citizen), lawyerText: cleanSummaryHeadings(lawyer) };
        }
        return { citizenText: cleanSummaryHeadings(safeString(text)), lawyerText: "" };
    }

    const strText = safeString(text);
    const marker = "### ⚖️ ANALIZA PROFESIONALE";
    const markerIndex = strText.indexOf(marker);
    if (markerIndex !== -1) {
        let citizenText = strText.substring(0, markerIndex).trim();
        let lawyerText = strText.substring(markerIndex + marker.length).trim();
        return { 
            citizenText: cleanSummaryHeadings(citizenText), 
            lawyerText: cleanSummaryHeadings(lawyerText) 
        };
    }
    return { citizenText: cleanSummaryHeadings(strText), lawyerText: "" };
};

const parseLawTitleAndArticle = (titleStr: string, articleStr: string) => {
    let lawTitle = titleStr || "Ligj i Paidentifikuar";
    let articleNum: string | null = null;

    const artMatchInArticle = articleStr ? articleStr.match(/(?:Neni|neni|NENI)?\s*(\d+)/) : null;
    if (artMatchInArticle) {
        articleNum = artMatchInArticle[1];
    }

    if (!articleNum && titleStr) {
        const artMatchInTitle = titleStr.match(/(?:Neni|neni|NENI)\s*(\d+)/i) || titleStr.match(/\b(\d+)\b/);
        if (artMatchInTitle) {
            articleNum = artMatchInTitle[1];
        }
    }

    let cleanLawTitle = lawTitle
        .replace(/(?:Neni|neni|NENI)\s*\d+/gi, '')
        .replace(/^[,\s\-\–]+|[,\s\-\–]+$/g, '')
        .trim();

    if (!cleanLawTitle) cleanLawTitle = lawTitle;

    const targetUrl = articleNum 
        ? `/laws/article?lawTitle=${encodeURIComponent(cleanLawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`
        : `/laws/overview?lawTitle=${encodeURIComponent(cleanLawTitle)}`;

    return { cleanLawTitle, articleNum, targetUrl };
};

const renderTextWithCitations = (text: string) => {
    if (!text) return null;
    const clean = cleanLegalText(text);

    const citationRegex = /(?:Në\s+bazë\s+të\s+)?(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,]*?),\s*(?:Neni|neni)\s+(\d+)/gi;

    const matches: Array<{ fullMatch: string; targetUrl: string; index: number }> = [];
    let match: RegExpExecArray | null;

    while ((match = citationRegex.exec(clean)) !== null) {
        const fullMatch = match[0];
        const lawPrefix = match[1];
        const lawTitle = match[2].trim();
        const articleNum = match[3].trim();
        const fullLawName = `${lawPrefix} ${lawTitle}`;
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(fullLawName)}&articleNumber=${encodeURIComponent(articleNum)}`;

        matches.push({ fullMatch, targetUrl, index: match.index });

        if (match.index === citationRegex.lastIndex) {
            citationRegex.lastIndex++;
        }
    }

    if (matches.length === 0) {
        return clean;
    }

    const elements: React.ReactNode[] = [];
    let lastIndex = 0;

    matches.forEach((m, i) => {
        if (m.index > lastIndex) {
            elements.push(clean.substring(lastIndex, m.index));
        }

        elements.push(
            <Link
                key={`cit-${i}`}
                to={m.targetUrl}
                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-bold transition-all shadow-sm hover:shadow-md hover:scale-[1.02] bg-primary-start/10 text-primary-start border border-primary-start/30 hover:bg-primary-start/20 mx-1 align-middle"
                title={`Hap ${m.fullMatch}`}
            >
                <Scale size={11} className="text-primary-start" />
                <span>{m.fullMatch}</span>
                <Eye size={11} className="opacity-70 ml-0.5" />
            </Link>
        );

        lastIndex = m.index + m.fullMatch.length;
    });

    if (lastIndex < clean.length) {
        elements.push(clean.substring(lastIndex));
    }

    return elements;
};

const renderCitationItem = (item: any) => {
    if (typeof item === 'object' && item !== null && (item.law || item.title)) {
        const rawLawTitle = item.law || item.title || "Ligj i Paidentifikuar";
        const rawArticle = item.article || item.legal_basis || "";
        const body = item.relevance || item.argument || item.description || "";

        const { targetUrl } = parseLawTitleAndArticle(rawLawTitle, rawArticle);

        return (
            <div className="flex flex-col gap-3 w-full">
                <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-2 font-bold text-primary-start text-xs uppercase tracking-wide group">
                        <LinkIcon size={12} className="text-primary-start opacity-70" />
                        <Link 
                            to={targetUrl} 
                            className="border-b border-dashed border-primary-start/60 hover:border-primary-start pb-0.5 text-primary-start hover:text-primary-hover transition-all flex items-center gap-1.5 hover:scale-[1.01]"
                            title={`Hap ${rawLawTitle}`}
                        >
                            <span>{rawLawTitle}</span>
                            <Eye size={12} className="opacity-80 shrink-0" />
                        </Link>
                    </div>
                    {rawArticle && (
                        <span className="px-3 py-1 rounded-lg bg-success-start/10 text-[11px] font-black uppercase tracking-widest text-success-start border border-success-start/20 leading-relaxed">
                            {rawArticle}
                        </span>
                    )}
                </div>
                {body && (
                    <div className="text-text-secondary text-[13px] leading-relaxed pl-5 border-l-2 border-main ml-0.5 mt-1">
                        <span className="text-primary-start opacity-80 text-[11px] font-black uppercase mr-2 tracking-widest">Relevanca:</span>
                        {renderTextWithCitations(body)}
                    </div>
                )}
            </div>
        );
    }

    const rawText = safeString(item);
    return <span className="leading-relaxed text-text-primary">{renderTextWithCitations(rawText)}</span>;
};

const SuccessTooltip: React.FC<{ children: React.ReactNode; t: TFunction }> = ({ children, t }) => {
    const [show, setShow] = useState(false);
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
                        className="absolute top-full left-1/2 transform -translate-x-1/2 mt-3 w-56 p-4 bg-surface text-[12px] font-medium text-text-secondary rounded-xl border border-main shadow-2xl z-[100] text-center leading-relaxed"
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
  const [summaryTab, setSummaryTab] = useState<'citizen' | 'lawyer'>('citizen');
  const [warRoomSubTab, setWarRoomSubTab] = useState<'strategy' | 'adversarial' | 'timeline' | 'contradictions'>('strategy');
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('normal');
  
  const clientPosition = ((result as any)?.client_position || 'DEFENDANT').toUpperCase();

  const [deepResult, setDeepResult] = useState<DeepAnalysisResult | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);
  const [isChronLoading, setIsChronLoading] = useState(false);
  const [isContradictLoading, setIsContradictLoading] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  useLockBodyScroll(isOpen);

  // Hydrate stored War Room deep result directly from MongoDB
  useEffect(() => {
    if (isOpen) { 
        setActiveTab('legal'); 
        setWarRoomSubTab('strategy'); 
        setSummaryTab('citizen'); 

        const existingDeep = (result as any)?.latest_deep_analysis || (result as any)?.deep_analysis || (result as any)?.deep_result;
        if (existingDeep && (existingDeep.adversarial_simulation || existingDeep.chronology || existingDeep.contradictions)) {
            setDeepResult(existingDeep);
        }
    }
  }, [isOpen, result]);

  const handleWarRoomEntry = async () => {
      setActiveTab('war_room');
      
      const existingDeep = deepResult || (result as any)?.latest_deep_analysis || (result as any)?.deep_analysis || (result as any)?.deep_result;
      
      if (existingDeep && (existingDeep.adversarial_simulation || existingDeep.chronology || existingDeep.contradictions)) {
          if (!deepResult) setDeepResult(existingDeep);
          return;
      }

      if (!deepResult && !isSimLoading && !isChronLoading && !isContradictLoading) {
          setIsSimLoading(true); setIsChronLoading(true); setIsContradictLoading(true);

          apiService.analyzeDeepChronology(caseId).then(data => {
              setDeepResult(prev => ({ ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }), chronology: data }));
              setIsChronLoading(false);
          }).catch(() => setIsChronLoading(false));

          apiService.analyzeDeepSimulation(caseId, clientPosition as any).then(data => {
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

  const { citizenText, lawyerText } = splitExecutiveSummary(summary);

  // Safe Property Resolution for Adversarial Simulation
  const simData = deepResult?.adversarial_simulation || {};
  const opponentStrategy = safeString(
      simData.opponent_strategy || simData.strategy || simData.description || 
      (typeof simData === 'string' ? simData : 'Strategjia e kundërshtarit është përpunuar.')
  );
  const weaknessAttacks = Array.isArray(simData.weakness_attacks) ? simData.weakness_attacks : [];

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
          <div className={`flex items-center justify-center gap-2 px-3 py-1.5 rounded-full border ${styles} shadow-sm w-full sm:w-auto`}>
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
            <div className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-full border bg-primary-start/10 text-primary-start border-primary-start/20 shadow-sm w-full sm:w-auto cursor-help">
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
    <div className="flex-1 flex flex-col items-center justify-center text-center py-32 bg-canvas">
        <Spinner size="w-16 h-16" />
        <h3 className="text-lg font-black text-text-primary uppercase tracking-widest mb-3 mt-6">{t('analysis.loading_deep_title', 'Duke Simuluar...')}</h3>
        <p className="text-text-muted text-[12px] font-bold uppercase tracking-widest">{t('analysis.rag_processing', 'Analiza e thellë statutore...')}</p>
    </div>
  );

  if (!isOpen) return null;

  const subTabBaseClass = "px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all border border-main flex items-center justify-center gap-2 cursor-pointer focus:outline-none hover-lift shadow-sm w-full sm:w-auto h-11 sm:h-auto shrink-0";
  const activeSubTabClass = "bg-primary-start border-primary-start text-white shadow-accent-glow";
  const inactiveSubTabClass = "bg-surface text-text-secondary hover:text-text-primary hover:bg-hover";

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
          className="w-full h-full sm:h-[85vh] sm:max-w-7xl bg-canvas border border-main rounded-2xl shadow-2xl overflow-hidden flex flex-col" 
          onClick={(e) => e.stopPropagation()}
        >
          <SpinnerStyles />
          
          <div className="px-6 py-5 border-b border-main flex flex-wrap justify-between items-center bg-surface shrink-0 gap-4">
            <div className="flex items-center gap-4 min-w-0">
              <div className="w-12 h-12 bg-primary-start text-white rounded-2xl flex items-center justify-center shadow-accent-glow shrink-0">
                  <Gavel size={24} />
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-2xl font-black text-text-primary uppercase tracking-tighter truncate">{t('analysis.title', 'Strategjia Ligjore')}</span>
                    
                    <span className="px-3 py-1 rounded-xl bg-primary-start/10 text-primary-start border border-primary-start/30 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
                      {clientPosition === 'PLAINTIFF' ? <Swords size={12} /> : <Shield size={12} />}
                      <span>{clientPosition === 'PLAINTIFF' ? 'Roli: Paditës' : 'Roli: I Paditur'}</span>
                    </span>
                  </div>

                  <div className="hidden sm:flex items-center mt-1 gap-2">{renderRiskBadge(risk_level)} {renderSuccessBadge(success_probability)}</div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={toggleZoom}
                className="p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-lg transition-all focus:outline-none"
                title={zoomLevel === 'normal' ? t('analysis.zoomIn', 'Agrandoni tekstin') : (zoomLevel === 'large' ? t('analysis.zoomMore', 'Më i madh') : t('analysis.zoomOut', 'Teksti standard'))}
              >
                {zoomLevel === 'normal' ? <ZoomIn size={20} /> : (zoomLevel === 'large' ? <ZoomIn size={20} /> : <ZoomOut size={20} />)}
              </button>
              <button 
                type="button"
                onClick={onClose} 
                className="p-3 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 border border-transparent focus:outline-none"
                aria-label="Close modal"
              >
                <X size={24} />
              </button>
            </div>
          </div>
          
          <div className="sm:hidden px-6 py-4 bg-surface border-b border-main flex flex-col sm:flex-row gap-3">
               {renderRiskBadge(risk_level)}
               {renderSuccessBadge(success_probability)}
          </div>

          {!isLoading && (
             <>
                <div className="flex border-b border-main px-8 bg-canvas shrink-0 overflow-x-auto no-scrollbar gap-8">
                    <button type="button" onClick={() => setActiveTab('legal')} className={`py-4 text-[12px] font-black uppercase tracking-widest flex items-center gap-3 border-b-2 transition-all whitespace-nowrap focus:outline-none ${activeTab === 'legal' ? 'border-primary-start text-primary-start' : 'border-transparent text-text-secondary hover:text-text-primary'}`}>
                        <Scale size={16}/> {t('analysis.tab_legal', 'Analiza Ligjore')}
                    </button>
                    <button type="button" onClick={handleWarRoomEntry} className={`py-4 text-[12px] font-black uppercase tracking-widest flex items-center gap-3 border-b-2 transition-all whitespace-nowrap focus:outline-none ${activeTab === 'war_room' ? 'border-primary-start text-primary-start' : 'border-transparent text-text-secondary hover:text-primary-start'}`}>
                        <Swords size={16}/> {t('analysis.tab_war_room', 'Dhoma e Luftës')}
                    </button>
                </div>

                <div 
                  className="flex-1 overflow-y-auto p-6 md:p-10 custom-finance-scroll text-text-primary bg-canvas"
                  style={{ fontSize: getFontSize() }}
                >
                    <div className="max-w-6xl mx-auto space-y-8">
                        {activeTab === 'legal' && (
                            <>
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                    <div className="bg-surface p-6 sm:p-8 rounded-[1.5rem] border border-main shadow-sm hover-lift flex flex-col h-auto">
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-5 border-b border-main pb-3 gap-3">
                                            <h3 className="text-[12px] font-black text-text-secondary uppercase tracking-widest flex items-center gap-2">
                                                <Info size={16} className="text-primary-start"/> {t('analysis.section_summary', 'Përmbledhja e Rastit')}
                                            </h3>
                                            
                                            {lawyerText && (
                                                <div className="flex items-center gap-1 bg-canvas p-1 rounded-xl w-fit">
                                                    <button
                                                        type="button"
                                                        onClick={() => setSummaryTab('citizen')}
                                                        className={`px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all focus:outline-none ${
                                                            summaryTab === 'citizen' ? 'bg-primary-start text-white shadow-sm' : 'text-text-secondary hover:text-text-primary'
                                                        }`}
                                                    >
                                                        <User size={10} className="inline mr-1 -mt-0.5" /> Qytetari
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setSummaryTab('lawyer')}
                                                        className={`px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all focus:outline-none ${
                                                            summaryTab === 'lawyer' ? 'bg-primary-start text-white shadow-sm' : 'text-text-secondary hover:text-text-primary'
                                                        }`}
                                                    >
                                                        <Landmark size={10} className="inline mr-1 -mt-0.5" /> Avokati
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                        <div className="text-text-secondary leading-relaxed border-l-2 border-primary-start/30 pl-5 ml-1 animate-in fade-in duration-300">
                                            {renderCitationItem(summaryTab === 'citizen' ? citizenText : lawyerText)}
                                        </div>
                                    </div>

                                    {burden_of_proof && (
                                        <div className="bg-surface p-6 sm:p-8 rounded-[1.5rem] border border-main shadow-sm hover-lift">
                                            <h3 className="text-[12px] font-black text-text-secondary uppercase tracking-widest mb-5 flex items-center gap-3">
                                                <Gavel size={16} className="text-primary-start"/> {t('analysis.section_burden', 'Barra e Provës')}
                                            </h3>
                                            <div className="text-text-secondary leading-relaxed italic border-l-2 border-main pl-5 ml-1">{renderCitationItem(burden_of_proof)}</div>
                                        </div>
                                    )}
                                </div>

                                {missing_evidence && missing_evidence.length > 0 && (
                                    <div className="bg-danger-start/5 p-6 sm:p-8 rounded-[1.5rem] border border-danger-start/20 shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-danger-start uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <AlertTriangle size={16}/> {t('analysis.section_missing', 'Mungesa e Provave')}
                                        </h3>
                                        <div className="grid gap-3">
                                            {missing_evidence.map((item, idx) => (
                                                <div key={idx} className="flex items-center gap-4 text-text-secondary bg-surface p-4 rounded-xl border border-danger-start/10 shadow-sm">
                                                    <span className="w-2 h-2 rounded-full bg-danger-start shrink-0 animate-pulse" />
                                                    {renderCitationItem(item)}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {key_issues && key_issues.length > 0 && (
                                    <div className="bg-surface p-6 sm:p-8 rounded-[1.5rem] border border-main shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-text-secondary uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <FileText size={16} className="text-primary-start"/> {t('analysis.section_issues', 'Çështjet Kryesore')}
                                        </h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {key_issues.map((issue: any, idx: number) => (
                                                <div key={idx} className="flex items-start gap-4 bg-canvas/30 p-5 rounded-xl border border-main">
                                                    <span className="text-primary-start font-black text-base leading-none opacity-50 mt-0.5">#{idx + 1}</span>
                                                    <div className="text-text-secondary font-medium leading-relaxed">{renderCitationItem(issue)}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {legal_basis && legal_basis.length > 0 && (
                                    <div className="bg-primary-start/5 p-6 sm:p-8 rounded-[1.5rem] border border-primary-start/20 shadow-sm hover-lift">
                                        <h3 className="text-[12px] font-black text-primary-start uppercase tracking-widest mb-5 flex items-center gap-3">
                                            <BookOpen size={16}/> {t('analysis.section_rules', 'Baza Ligjore (Statutore)')}
                                        </h3>
                                        <ul className="space-y-4">
                                            {legal_basis.map((lawItem: any, i: number) => {
                                                const lawStr = typeof lawItem === 'string' ? lawItem : (lawItem.law || "");
                                                const isGlobal = lawStr.includes("UNCRC") || lawStr.includes("Konventa") || lawStr.includes("KEDNJ");
                                                return (
                                                    <li key={i} className={`flex gap-4 text-[13px] items-start p-5 rounded-xl transition-colors shadow-sm bg-surface border ${isGlobal ? 'border-indigo-500/30' : 'border-main'}`}>
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
                                <div className="flex flex-col sm:flex-row flex-wrap gap-3 mb-8 shrink-0 pb-2">
                                    <button type="button" onClick={() => setWarRoomSubTab('strategy')} className={`${subTabBaseClass} ${warRoomSubTab === 'strategy' ? activeSubTabClass : inactiveSubTabClass}`}>
                                        <Target size={14} className="inline shrink-0" /> {t('analysis.subtab_strategy', 'Plani Strategjik')}
                                    </button>
                                    <button type="button" onClick={() => setWarRoomSubTab('adversarial')} className={`${subTabBaseClass} ${warRoomSubTab === 'adversarial' ? activeSubTabClass : inactiveSubTabClass}`}>
                                        <Skull size={14} className="inline shrink-0" /> {t('analysis.subtab_adversarial', 'Simulimi i Palës')}
                                    </button>
                                    <button type="button" onClick={() => setWarRoomSubTab('timeline')} className={`${subTabBaseClass} ${warRoomSubTab === 'timeline' ? activeSubTabClass : inactiveSubTabClass}`}>
                                        <Clock size={14} className="inline shrink-0" /> {t('analysis.subtab_timeline', 'Kronologjia')}
                                    </button>
                                    <button type="button" onClick={() => setWarRoomSubTab('contradictions')} className={`${subTabBaseClass} ${warRoomSubTab === 'contradictions' ? activeSubTabClass : inactiveSubTabClass}`}>
                                        <AlertOctagon size={14} className="inline shrink-0" /> {t('analysis.subtab_contradictions', 'Kontradiktat')}
                                    </button>
                                </div>

                                <div className="space-y-8 animate-in fade-in">
                                    {warRoomSubTab === 'strategy' ? (
                                        <div className="space-y-8">
                                            <div className="bg-surface p-6 sm:p-8 rounded-[1.5rem] border border-main shadow-sm hover-lift">
                                                <h3 className="text-[12px] font-black text-text-secondary uppercase tracking-widest mb-5 flex items-center gap-3"><Target size={16} className="text-primary-start"/> {t('analysis.section_analysis', 'Analiza Strategjike')}</h3>
                                                <div className="text-text-secondary leading-relaxed border-l-2 border-primary-start/30 pl-5 ml-1">{renderCitationItem(strategic_analysis)}</div>
                                            </div>
                                            <div className="bg-danger-start/5 p-6 sm:p-8 rounded-[1.5rem] border border-danger-start/20 shadow-sm">
                                                <h3 className="text-[12px] font-black text-danger-start uppercase tracking-widest mb-5 flex items-center gap-3"><ShieldAlert size={16}/> {t('analysis.section_weaknesses', 'Pikat e Dobëta (Risku)')}</h3>
                                                <ul className="space-y-3">
                                                    {weaknesses.map((w: any, i: number) => (
                                                        <li key={i} className="flex items-center gap-4 text-text-secondary bg-surface p-4 rounded-xl border border-danger-start/10 shadow-sm">
                                                            <span className="w-2 h-2 rounded-full bg-danger-start shrink-0 opacity-50" />
                                                            {renderCitationItem(w)}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            <div className="bg-status-success/5 p-6 sm:p-8 rounded-[1.5rem] border border-status-success/20 shadow-sm">
                                                <h3 className="text-[12px] font-black text-status-success uppercase tracking-widest mb-6 flex items-center gap-3"><CheckCircle2 size={16}/> {t('analysis.section_conclusion', 'Plani i Veprimit (Hapat)')}</h3>
                                                <div className="space-y-4">
                                                    {action_plan.map((step: any, i: number) => (
                                                        <div key={i} className="flex items-start gap-5 text-text-secondary bg-surface p-5 rounded-xl border border-status-success/10 shadow-sm">
                                                            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-status-success/20 text-status-success font-black text-[12px] shrink-0">{i + 1}</span>
                                                            <span className="leading-relaxed font-medium mt-1">{renderCitationItem(step)}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    ) : warRoomSubTab === 'adversarial' ? (
                                        isSimLoading ? renderSubTabLoader() : deepResult?.adversarial_simulation ? (
                                            <div className="space-y-8">
                                                <div className="bg-surface p-6 sm:p-8 rounded-[1.5rem] border border-danger-start/30 shadow-lg shadow-danger-start/5">
                                                    <h3 className="text-[12px] font-black text-danger-start mb-5 uppercase tracking-widest flex items-center gap-3"><Skull size={16}/> {t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}</h3>
                                                    <div className="text-text-secondary leading-relaxed font-medium">{renderCitationItem(opponentStrategy)}</div>
                                                </div>
                                                {weaknessAttacks.length > 0 && (
                                                    <div className="grid gap-4">
                                                        {weaknessAttacks.map((attack: string, i: number) => (
                                                            <div key={i} className="flex gap-4 bg-surface p-5 rounded-xl border border-main shadow-sm">
                                                                <Target size={18} className="text-danger-start shrink-0 mt-0.5" />
                                                                <div className="text-text-secondary leading-relaxed">{renderCitationItem(attack)}</div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-center py-20 text-text-secondary"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit të simulimit.')}</p></div>
                                        )
                                    ) : warRoomSubTab === 'timeline' ? (
                                        isChronLoading ? renderSubTabLoader() : deepResult?.chronology ? (
                                            <div className="space-y-6 relative border-l-2 border-main ml-4 pl-8 py-4">
                                                {deepResult.chronology.map((event: ChronologyEvent, i: number) => (
                                                    <div key={i} className="relative group bg-surface p-5 rounded-xl border border-main shadow-sm hover-lift">
                                                        <div className="absolute -left-[41px] top-6 w-4 h-4 rounded-full bg-canvas border-4 border-indigo-500 shadow-sm" />
                                                        <div className="flex flex-col gap-2">
                                                            <span className="text-indigo-500 font-mono text-[11px] uppercase tracking-widest font-black">{event.date}</span>
                                                            <div className="text-text-secondary leading-relaxed">{renderCitationItem(event.event)}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="text-center py-20 text-text-secondary"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                        )
                                    ) : warRoomSubTab === 'contradictions' ? (
                                        isContradictLoading ? renderSubTabLoader() : deepResult?.contradictions ? (
                                            <div className="grid gap-6">
                                                {deepResult.contradictions.length === 0 ? (
                                                    <div className="bg-surface p-12 rounded-[1.5rem] text-center border border-main shadow-sm">
                                                        <CheckCircle2 size={48} className="mx-auto mb-4 text-status-success/50 animate-bounce" />
                                                        <p className="text-text-primary font-bold text-lg">{t('analysis.no_contradictions', 'Gjithçka e pastër.')}</p>
                                                        <p className="text-text-muted text-[13px] mt-2 font-medium">Nuk u gjetën kontradikta mes deklaratave dhe provave.</p>
                                                    </div>
                                                ) : (
                                                    deepResult.contradictions.map((c: Contradiction, i: number) => (
                                                        <div key={i} className="bg-surface border border-warning-start/30 p-6 rounded-[1.5rem] shadow-lg shadow-warning-start/5">
                                                            <div className="flex justify-between items-start mb-6 pb-4 border-b border-main">
                                                                <div className="flex items-center gap-3 text-warning-start font-black text-[11px] uppercase tracking-widest"><AlertOctagon size={16}/> {t('analysis.contradiction_label', 'Mospërputhje Factual')}</div>
                                                                <span className="text-[10px] font-black bg-warning-start/10 text-warning-start px-2.5 py-1 rounded-md border border-warning-start/20 uppercase tracking-widest">{getRiskLabel(c.severity)}</span>
                                                            </div>
                                                            <div className="grid md:grid-cols-2 gap-6 mb-4">
                                                                <div className="p-5 bg-canvas rounded-xl border border-main">
                                                                    <span className="text-[11px] text-danger-start font-black uppercase tracking-widest mb-3 flex items-center gap-2">
                                                                        <FileText size={14}/> {t('analysis.claim_label', 'Deklarata')}
                                                                    </span>
                                                                    <div className="text-text-secondary leading-relaxed italic">"{renderCitationItem(c.claim)}"</div>
                                                                </div>
                                                                <div className="p-5 bg-canvas rounded-xl border border-main">
                                                                    <span className="text-[11px] text-status-success font-black uppercase tracking-widest mb-3 flex items-center gap-2">
                                                                        <Scale size={14}/> {t('analysis.evidence_label', 'Prova Objektive')}
                                                                    </span>
                                                                    <div className="text-text-secondary font-medium leading-relaxed">{renderCitationItem(c.evidence)}</div>
                                                                </div>
                                                            </div>
                                                            <div className="mt-4 p-4 bg-warning-start/5 rounded-xl border border-warning-start/10">
                                                                <span className="text-[11px] text-warning-start font-black uppercase tracking-widest block mb-1">Impakti</span>
                                                                <div className="text-text-secondary leading-relaxed">{renderCitationItem(c.impact)}</div>
                                                            </div>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-center py-20 text-text-secondary"><p>{t('analysis.error_loading', 'Gabim gjatë ngarkimit.')}</p></div>
                                        )
                                    ) : null}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
             </>
          )}
          
          <div className="px-8 py-5 border-t border-main bg-surface flex flex-col sm:flex-row gap-4 justify-between items-center shrink-0">
              <button 
                  type="button"
                  onClick={handleArchiveStrategy} 
                  disabled={isArchiving || !deepResult}
                  className={`w-full sm:w-auto h-11 px-6 rounded-xl text-[11px] uppercase tracking-widest font-black transition-all flex items-center justify-center gap-3 border focus:outline-none ${
                      isArchiving || !deepResult 
                      ? 'bg-canvas text-text-disabled border-main cursor-not-allowed' 
                      : 'bg-status-success/15 text-status-success border-status-success/20 hover:bg-status-success/20 active:scale-95'
                  }`}
              >
                  {isArchiving ? (
                      <div className="w-4 h-4 border-2 border-status-success border-t-transparent rounded-full spinner-robust" />
                  ) : (
                      <CheckCircle2 size={16} />
                  )}
                  {t('analysis.btn_archive', 'Ruaj Strategjinë në Arkiv')}
              </button>
              
              <button 
                  type="button"
                  onClick={onClose} 
                  className="btn-primary w-full sm:w-auto px-10 h-11 text-[11px] uppercase tracking-widest font-black"
              >
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