// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V31.6 (SUFFIX AWARE & SAFE HEADER CLEANER)

import React, { useEffect, useState, useRef } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Scale, FileText, Swords, Target,
    Gavel, CheckCircle2, BookOpen, Globe, 
    Clock, Skull, AlertOctagon,
    Shield, ShieldAlert, ShieldCheck, Percent, Info, AlertTriangle,
    ZoomIn, ZoomOut, User, Landmark, Maximize2, Minimize2
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { TFunction } from 'i18next';
import { CaseAnalysisResult, DeepAnalysisResult, ChronologyEvent, Contradiction } from '../data/types'; 
import { apiService } from '../services/api';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';
import { LawCitationLink } from './LawCitationLink';

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
    
    // Safely remove structural markdown headings without risking paragraph lines
    clean = clean.replace(/###\s*[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]?\s*(UDHËZUESI|ANALIZA|PËRMBLEDHJA|KËSHILLIM|STRATEGJIA|OPINIONI|KËSHILLË).*?(?=\r?\n|$)/giu, '');
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

    const artMatchInArticle = articleStr ? articleStr.match(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)?\s*(\d+)/) : null;
    if (artMatchInArticle) {
        articleNum = artMatchInArticle[1];
    }

    if (!articleNum && titleStr) {
        const artMatchInTitle = titleStr.match(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)\s*(\d+)/i) || titleStr.match(/\b(\d+)\b/);
        if (artMatchInTitle) {
            articleNum = artMatchInTitle[1];
        }
    }

    let cleanLawTitle = lawTitle
        .replace(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)\s*\d+/gi, '')
        .replace(/^[,\s\-\–]+|[,\s\-\–]+$/g, '')
        .trim();

    if (!cleanLawTitle) cleanLawTitle = lawTitle;

    const targetUrl = articleNum 
        ? `/laws/article?lawTitle=${encodeURIComponent(cleanLawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`
        : `/laws/overview?lawTitle=${encodeURIComponent(cleanLawTitle)}`;

    return { cleanLawTitle, articleNum, targetUrl };
};

// ============================================================
// FLEXIBLE MULTI-PATTERN CITATION PARSER (ALBANIAN SUFFIX AWARE)
// ============================================================
const renderTextWithCitations = (text: string) => {
    if (!text) return null;
    const clean = cleanLegalText(text);

    // Suffix aware: neni, nenit, nenin, nene, nenet
    const citationRegex = /(?:(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,.]*?)\s*,?\s*(?:Neni|neni|NENI|nenit|nenit|Nenit|NENIT|nenin|Nenin|NENIN|nene|Nene|NENE|nenet|Nenet|NENET)\s+(\d+))|(?:(?:Neni|neni|NENI|nenit|nenit|Nenit|NENIT|nenin|Nenin|NENIN|nene|Nene|NENE|nenet|Nenet|NENET)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.]*|[A-Z][a-zçëA-ZÇË\s\d\/L\-]{3,30})?)/gi;

    const matches: Array<{ 
        fullMatch: string; 
        targetUrl: string; 
        index: number;
        lawTitle: string;
        articleNum: string;
    }> = [];

    let match: RegExpExecArray | null;

    while ((match = citationRegex.exec(clean)) !== null) {
        const fullMatch = match[0];
        let lawTitle = "";
        let articleNum = "";

        if (match[1] && match[3]) {
            const lawPrefix = match[1];
            const lawNumber = match[2].trim();
            lawTitle = `${lawPrefix} ${lawNumber}`;
            articleNum = match[3].trim();
        } else if (match[4]) {
            articleNum = match[4].trim();
            lawTitle = match[5] ? match[5].trim() : "Ligji i Përgjithshëm";
        }

        if (!articleNum) continue;

        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;

        matches.push({ 
            fullMatch, 
            targetUrl, 
            index: match.index,
            lawTitle,
            articleNum
        });

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
            <LawCitationLink
                key={`cit-${i}-${m.index}`}
                lawTitle={m.lawTitle}
                articleNum={m.articleNum}
                fullMatch={m.fullMatch}
                targetUrl={m.targetUrl}
            />
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

        const { cleanLawTitle, articleNum, targetUrl } = parseLawTitleAndArticle(rawLawTitle, rawArticle);

        return (
            <div className="flex flex-col gap-3 w-full">
                <div className="flex flex-wrap items-center gap-2">
                    <LawCitationLink
                        lawTitle={cleanLawTitle}
                        articleNum={articleNum || "1"}
                        fullMatch={`${rawLawTitle}${rawArticle ? ` - ${rawArticle}` : ''}`}
                        targetUrl={targetUrl}
                    />
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
  const [isFullScreen, setIsFullScreen] = useState(false);
  
  const clientPosition = ((result as any)?.client_position || 'DEFENDANT').toUpperCase();

  const [deepResult, setDeepResult] = useState<DeepAnalysisResult | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);
  const [isChronLoading, setIsChronLoading] = useState(false);
  const [isContradictLoading, setIsContradictLoading] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  useLockBodyScroll(isOpen);

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
      summary = result?.summary || (result as any)?.executive_summary || (result as any)?.citizen_summary || (result as any)?.citizenText || "",
      key_issues = [], legal_basis = [], strategic_analysis = "",
      weaknesses = [], action_plan = [], risk_level = "MEDIUM",
      success_probability = null, burden_of_proof = "", missing_evidence = []
  } = result || {};

  const { citizenText, lawyerText } = splitExecutiveSummary(summary);

  const simObj = ((deepResult as any)?.adversarial_simulation?.adversarial_simulation || (deepResult as any)?.adversarial_simulation || {}) as any;
  const opponentStrategy = safeString(
      simObj.opponent_strategy || simObj.strategy || simObj.description || 
      (typeof simObj === 'string' ? simObj : 'Strategjia e kundërshtarit është përpunuar.')
  );
  const weaknessAttacks = Array.isArray(simObj.weakness_attacks) ? simObj.weakness_attacks : [];

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
        className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-2 sm:p-4" 
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.98, opacity: 0, y: 10 }} 
          animate={{ scale: 1, opacity: 1, y: 0 }} 
          exit={{ scale: 0.98, opacity: 0, y: 10 }} 
          transition={{ duration: 0.2 }}
          className={`glass-panel w-[95vw] rounded-3xl shadow-2xl border border-main bg-canvas flex flex-col overflow-hidden transition-all duration-300 ${
            isFullScreen ? 'w-full h-full max-w-none rounded-none' : 'max-w-7xl h-[92vh]'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <SpinnerStyles />
          
          <div className="p-4 sm:p-5 border-b border-main flex flex-wrap justify-between items-center bg-surface shrink-0 gap-4">
            <div className="flex items-center gap-4 min-w-0">
              <div className="w-10 h-10 bg-primary-start text-white rounded-xl flex items-center justify-center shadow-accent-glow shrink-0">
                  <Gavel size={20} />
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">{t('analysis.title', 'Strategjia Ligjore')}</span>
                    
                    <span className="px-2.5 py-0.5 rounded-md bg-primary-start/10 text-primary-start border border-primary-start/30 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
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
                {zoomLevel === 'normal' ? <ZoomIn size={18} /> : (zoomLevel === 'large' ? <ZoomIn size={18} /> : <ZoomOut size={18} />)}
              </button>

              <button
                type="button"
                onClick={() => setIsFullScreen(!isFullScreen)}
                className="p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-lg transition-all focus:outline-none"
                title={isFullScreen ? 'Zvogëlo' : 'Zmadho në Ekran të Plotë'}
              >
                {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
              </button>

              <button 
                type="button"
                onClick={onClose} 
                className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>
          </div>
          
          <div className="sm:hidden px-6 py-3 bg-surface border-b border-main flex flex-col sm:flex-row gap-2">
               {renderRiskBadge(risk_level)}
               {renderSuccessBadge(success_probability)}
          </div>

          {!isLoading && (
             <>
                <div className="flex border-b border-main px-6 bg-canvas shrink-0 overflow-x-auto no-scrollbar gap-6">
                    <button type="button" onClick={() => setActiveTab('legal')} className={`py-3 text-[11px] font-black uppercase tracking-widest flex items-center gap-2 border-b-2 transition-all whitespace-nowrap focus:outline-none ${activeTab === 'legal' ? 'border-primary-start text-primary-start' : 'border-transparent text-text-secondary hover:text-text-primary'}`}>
                        <Scale size={15}/> {t('analysis.tab_legal', 'Analiza Ligjore')}
                    </button>
                    <button type="button" onClick={handleWarRoomEntry} className={`py-3 text-[11px] font-black uppercase tracking-widest flex items-center gap-2 border-b-2 transition-all whitespace-nowrap focus:outline-none ${activeTab === 'war_room' ? 'border-primary-start text-primary-start' : 'border-transparent text-text-secondary hover:text-primary-start'}`}>
                        <Swords size={15}/> {t('analysis.tab_war_room', 'Dhoma e Luftës')}
                    </button>
                </div>

                <div 
                  className="flex-1 overflow-y-auto p-4 sm:p-8 custom-finance-scroll text-text-primary bg-canvas"
                  style={{ fontSize: getFontSize() }}
                >
                    <div className={`mx-auto space-y-6 transition-all duration-300 ${isFullScreen ? 'max-w-none px-4 sm:px-12' : 'max-w-6xl'}`}>
                        {activeTab === 'legal' && (
                            <>
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm flex flex-col h-auto">
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 border-b border-main pb-3 gap-2">
                                            <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest flex items-center gap-2">
                                                <Info size={15} className="text-primary-start"/> {t('analysis.section_summary', 'Përmbledhja e Rastit')}
                                            </h3>
                                            
                                            {lawyerText && (
                                                <div className="flex items-center gap-1 bg-canvas p-1 rounded-xl w-fit">
                                                    <button
                                                        type="button"
                                                        onClick={() => setSummaryTab('citizen')}
                                                        className={`px-3 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all focus:outline-none ${
                                                            summaryTab === 'citizen' ? 'bg-primary-start text-white shadow-sm' : 'text-text-secondary hover:text-text-primary'
                                                        }`}
                                                    >
                                                        <User size={10} className="inline mr-1 -mt-0.5" /> Qytetari
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setSummaryTab('lawyer')}
                                                        className={`px-3 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all focus:outline-none ${
                                                            summaryTab === 'lawyer' ? 'bg-primary-start text-white shadow-sm' : 'text-text-secondary hover:text-text-primary'
                                                        }`}
                                                    >
                                                        <Landmark size={10} className="inline mr-1 -mt-0.5" /> Avokati
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                        <div className="text-text-secondary leading-relaxed border-l-2 border-primary-start/30 pl-4 ml-1 animate-in fade-in duration-300">
                                            {renderCitationItem(summaryTab === 'citizen' ? citizenText : lawyerText)}
                                        </div>
                                    </div>

                                    {burden_of_proof && (
                                        <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm">
                                            <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest mb-4 flex items-center gap-2">
                                                <Gavel size={15} className="text-primary-start"/> {t('analysis.section_burden', 'Barra e Provës')}
                                            </h3>
                                            <div className="text-text-secondary leading-relaxed italic border-l-2 border-main pl-4 ml-1">{renderCitationItem(burden_of_proof)}</div>
                                        </div>
                                    )}
                                </div>

                                {missing_evidence && missing_evidence.length > 0 && (
                                    <div className="bg-danger-start/5 p-6 rounded-2xl border border-danger-start/20 shadow-sm">
                                        <h3 className="text-[11px] font-black text-danger-start uppercase tracking-widest mb-4 flex items-center gap-2">
                                            <AlertTriangle size={15}/> {t('analysis.section_missing', 'Mungesa e Provave')}
                                        </h3>
                                        <div className="grid gap-3">
                                            {missing_evidence.map((item, idx) => (
                                                <div key={idx} className="flex items-center gap-3 text-text-secondary bg-surface p-4 rounded-xl border border-danger-start/10 shadow-sm">
                                                    <span className="w-2 h-2 rounded-full bg-danger-start shrink-0 animate-pulse" />
                                                    {renderCitationItem(item)}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {key_issues && key_issues.length > 0 && (
                                    <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm">
                                        <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest mb-4 flex items-center gap-2">
                                            <FileText size={15} className="text-primary-start"/> {t('analysis.section_issues', 'Çështjet Kryesore')}
                                        </h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {key_issues.map((issue: any, idx: number) => (
                                                <div key={idx} className="flex items-start gap-3 bg-canvas/30 p-4 rounded-xl border border-main">
                                                    <span className="text-primary-start font-black text-sm leading-none opacity-50 mt-0.5">#{idx + 1}</span>
                                                    <div className="text-text-secondary font-medium leading-relaxed">{renderCitationItem(issue)}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {legal_basis && legal_basis.length > 0 && (
                                    <div className="bg-primary-start/5 p-6 rounded-2xl border border-primary-start/20 shadow-sm">
                                        <h3 className="text-[11px] font-black text-primary-start uppercase tracking-widest mb-4 flex items-center gap-2">
                                            <BookOpen size={15}/> {t('analysis.section_rules', 'Baza Ligjore (Statutore)')}
                                        </h3>
                                        <ul className="space-y-3">
                                            {legal_basis.map((lawItem: any, i: number) => {
                                                const lawStr = typeof lawItem === 'string' ? lawItem : (lawItem.law || "");
                                                const isGlobal = lawStr.includes("UNCRC") || lawStr.includes("Konventa") || lawStr.includes("KEDNJ");
                                                return (
                                                    <li key={i} className={`flex gap-3 text-xs items-start p-4 rounded-xl transition-colors shadow-sm bg-surface border ${isGlobal ? 'border-indigo-500/30' : 'border-main'}`}>
                                                        {isGlobal ? <Globe size={18} className="text-indigo-500 shrink-0 mt-0.5"/> : <Scale size={18} className="text-primary-start shrink-0 mt-0.5"/>}
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
                                <div className="flex flex-col sm:flex-row flex-wrap gap-2 mb-6 shrink-0 pb-1">
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

                                <div className="space-y-6 animate-in fade-in">
                                    {warRoomSubTab === 'strategy' ? (
                                        <div className="space-y-6">
                                            <div className="bg-surface p-6 rounded-2xl border border-main shadow-sm">
                                                <h3 className="text-[11px] font-black text-text-secondary uppercase tracking-widest mb-4 flex items-center gap-2"><Target size={15} className="text-primary-start"/> {t('analysis.section_analysis', 'Analiza Strategjike')}</h3>
                                                <div className="text-text-secondary leading-relaxed border-l-2 border-primary-start/30 pl-4 ml-1">{renderCitationItem(strategic_analysis)}</div>
                                            </div>
                                            <div className="bg-danger-start/5 p-6 rounded-2xl border border-danger-start/20 shadow-sm">
                                                <h3 className="text-[11px] font-black text-danger-start uppercase tracking-widest mb-4 flex items-center gap-2"><ShieldAlert size={15}/> {t('analysis.section_weaknesses', 'Pikat e Dobëta (Risku)')}</h3>
                                                <ul className="space-y-3">
                                                    {weaknesses.map((w: any, i: number) => (
                                                        <li key={i} className="flex items-center gap-3 text-text-secondary bg-surface p-3.5 rounded-xl border border-danger-start/10 shadow-sm">
                                                            <span className="w-2 h-2 rounded-full bg-danger-start shrink-0 opacity-50" />
                                                            {renderCitationItem(w)}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            <div className="bg-status-success/5 p-6 rounded-2xl border border-status-success/20 shadow-sm">
                                                <h3 className="text-[11px] font-black text-status-success uppercase tracking-widest mb-4 flex items-center gap-2"><CheckCircle2 size={15}/> {t('analysis.section_conclusion', 'Plani i Veprimit (Hapat)')}</h3>
                                                <div className="space-y-3">
                                                    {action_plan.map((step: any, i: number) => (
                                                        <div key={i} className="flex items-start gap-4 text-text-secondary bg-surface p-4 rounded-xl border border-status-success/10 shadow-sm">
                                                            <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-status-success/20 text-status-success font-black text-xs shrink-0">{i + 1}</span>
                                                            <span className="leading-relaxed font-medium mt-0.5">{renderCitationItem(step)}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    ) : warRoomSubTab === 'adversarial' ? (
                                        isSimLoading ? renderSubTabLoader() : deepResult?.adversarial_simulation ? (
                                            <div className="space-y-6">
                                                <div className="bg-surface p-6 rounded-2xl border border-danger-start/30 shadow-lg shadow-danger-start/5">
                                                    <h3 className="text-[11px] font-black text-danger-start mb-4 uppercase tracking-widest flex items-center gap-2"><Skull size={15}/> {t('analysis.opponent_strategy_title', 'Strategjia e Kundërshtarit')}</h3>
                                                    <div className="text-text-secondary leading-relaxed font-medium">{renderCitationItem(opponentStrategy)}</div>
                                                </div>
                                                {weaknessAttacks.length > 0 && (
                                                    <div className="grid gap-3">
                                                        {weaknessAttacks.map((attack: string, i: number) => (
                                                            <div key={i} className="flex gap-3 bg-surface p-4 rounded-xl border border-main shadow-sm">
                                                                <Target size={16} className="text-danger-start shrink-0 mt-0.5" />
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
                                            <div className="space-y-5 relative border-l-2 border-main ml-4 pl-6 py-2">
                                                {deepResult.chronology.map((event: ChronologyEvent, i: number) => (
                                                    <div key={i} className="relative group bg-surface p-4 rounded-xl border border-main shadow-sm">
                                                        <div className="absolute -left-[33px] top-5 w-3.5 h-3.5 rounded-full bg-canvas border-4 border-indigo-500 shadow-sm" />
                                                        <div className="flex flex-col gap-1.5">
                                                            <span className="text-indigo-500 font-mono text-[10px] uppercase tracking-widest font-black">{event.date}</span>
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
                                            <div className="grid gap-5">
                                                {deepResult.contradictions.length === 0 ? (
                                                    <div className="bg-surface p-10 rounded-2xl text-center border border-main shadow-sm">
                                                        <CheckCircle2 size={40} className="mx-auto mb-3 text-status-success/50 animate-bounce" />
                                                        <p className="text-text-primary font-bold text-base">{t('analysis.no_contradictions', 'Gjithçka e pastër.')}</p>
                                                        <p className="text-text-muted text-xs mt-1 font-medium">Nuk u gjetën kontradikta mes deklaratave dhe provave.</p>
                                                    </div>
                                                ) : (
                                                    deepResult.contradictions.map((c: Contradiction, i: number) => (
                                                        <div key={i} className="bg-surface border border-warning-start/30 p-5 rounded-2xl shadow-md shadow-warning-start/5">
                                                            <div className="flex justify-between items-start mb-4 pb-3 border-b border-main">
                                                                <div className="flex items-center gap-2 text-warning-start font-black text-xs uppercase tracking-widest"><AlertOctagon size={15}/> {t('analysis.contradiction_label', 'Mospërputhje Factual')}</div>
                                                                <span className="text-[10px] font-black bg-warning-start/10 text-warning-start px-2 py-0.5 rounded border border-warning-start/20 uppercase tracking-widest">{getRiskLabel(c.severity)}</span>
                                                            </div>
                                                            <div className="grid md:grid-cols-2 gap-4 mb-3">
                                                                <div className="p-4 bg-canvas rounded-xl border border-main">
                                                                    <span className="text-[10px] text-danger-start font-black uppercase tracking-widest mb-2 flex items-center gap-1.5">
                                                                        <FileText size={13}/> {t('analysis.claim_label', 'Deklarata')}
                                                                    </span>
                                                                    <div className="text-text-secondary leading-relaxed italic text-xs">"{renderCitationItem(c.claim)}"</div>
                                                                </div>
                                                                <div className="p-4 bg-canvas rounded-xl border border-main">
                                                                    <span className="text-[10px] text-status-success font-black uppercase tracking-widest mb-2 flex items-center gap-1.5">
                                                                        <Scale size={13}/> {t('analysis.evidence_label', 'Prova Objektive')}
                                                                    </span>
                                                                    <div className="text-text-secondary font-medium leading-relaxed text-xs">{renderCitationItem(c.evidence)}</div>
                                                                </div>
                                                            </div>
                                                            <div className="mt-3 p-3 bg-warning-start/5 rounded-xl border border-warning-start/10 text-xs">
                                                                <span className="text-[10px] text-warning-start font-black uppercase tracking-widest block mb-1">Impakti</span>
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
          
          <div className="p-3.5 sm:p-4 border-t border-main bg-surface flex flex-col sm:flex-row gap-3 justify-between items-center shrink-0">
              <button 
                  type="button"
                  onClick={handleArchiveStrategy} 
                  disabled={isArchiving || !deepResult}
                  className={`w-full sm:w-auto h-10 px-5 rounded-xl text-xs uppercase tracking-wider font-bold transition-all flex items-center justify-center gap-2 border focus:outline-none ${
                      isArchiving || !deepResult 
                      ? 'bg-canvas text-text-disabled border-main cursor-not-allowed' 
                      : 'bg-status-success/15 text-status-success border-status-success/20 hover:bg-status-success/20 active:scale-95'
                  }`}
              >
                  {isArchiving ? (
                      <div className="w-4 h-4 border-2 border-status-success border-t-transparent rounded-full spinner-robust" />
                  ) : (
                      <CheckCircle2 size={15} />
                  )}
                  {t('analysis.btn_archive', 'Ruaj Strategjinë në Arkiv')}
              </button>
              
              <button 
                  type="button"
                  onClick={onClose} 
                  className="h-10 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-md shadow-primary-start/15 transition-all w-full sm:w-auto"
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