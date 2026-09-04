// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - UNIFIED STATUTE & SUPREME CASELAW FORENSIC ENGINE V115.0 (THEME-AWARE SOLID TOOLTIPS)

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Search, X, Scale, ArrowLeft, ChevronDown, Check, 
  ShieldCheck, GraduationCap, Gavel, Lightbulb, 
  BookOpen, ArrowRight, ExternalLink, Loader2, Bot, FileText,
  CheckCircle2
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';
import { 
  QUICK_HELP_CHIPS, 
  SEMANTIC_INTENT_MATRIX, 
  sanitizeSearchText, 
  SemanticIntentRule 
} from '../utils/legalSemanticEngine';

function normalizeForDisplay(title: string): string {
  return title.trim().replace(/\s+/g, ' ');
}

function formatShortLawBadge(lawTitle: string): string {
  const lower = lawTitle.toLowerCase();
  if (lower.includes('kontestimore') || lower.includes('03/l-006') || lower.includes('03 l 006')) return 'LPK';
  if (lower.includes('detyrimeve') || lower.includes('04/l-077') || lower.includes('04 l 077')) return 'LMD';
  if (lower.includes('tregtare') || lower.includes('06/l-016') || lower.includes('06 l 016')) return 'LSHT';
  if (lower.includes('permbarimore') || lower.includes('përmbarimore') || lower.includes('04/l-139')) return 'LPP';
  if (lower.includes('penal') && !lower.includes('procedur')) return 'Kodi Penal';
  if (lower.includes('procedur') && lower.includes('penal')) return 'Kodi i Proc. Penale';
  if (lower.includes('punës') || lower.includes('punes')) return 'Ligji i Punës';
  if (lower.includes('mitur')) return 'Kodi i të Miturve';
  if (lower.includes('familjen')) return 'Ligji për Familjen';
  if (lower.includes('kushtetut')) return 'Kushtetuta';
  return lawTitle.length > 20 ? `${lawTitle.substring(0, 18)}...` : lawTitle;
}

interface AiDiagnosticData {
  legal_institute: string;
  plain_explanation: string;
  matched_statutes: Array<{
    law_title: string;
    article_number: string;
    explanation: string;
    confidence: number;
    source?: string;
  }>;
}

export default function LawSearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [activeTab, setActiveTab] = useState<'statutes' | 'academic' | 'caselaw'>('statutes');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [statuteTitles, setStatuteTitles] = useState<string[]>([]);
  const [academicTitles, setAcademicTitles] = useState<string[]>([]);
  const [caselawTitles, setCaselawTitles] = useState<string[]>([]);
  const [isLoadingData, setIsLoadingData] = useState<boolean>(true);
  
  const [isListExpanded, setIsListExpanded] = useState(true);
  const [selectedPdfFilename, setSelectedPdfFilename] = useState<string | null>(null);
  const [initialPageNumber, setInitialPageNumber] = useState<number>(1);
  const [showPdfModal, setShowPdfModal] = useState(false);

  // FORENSIC TOOLTIP STATE
  const [hoveredArticleKey, setHoveredArticleKey] = useState<string | null>(null);

  // AI DIAGNOSTIC STATE
  const [isAnalyzingWithAi, setIsAnalyzingWithAi] = useState(false);
  const [aiDiagnostic, setAiDiagnostic] = useState<AiDiagnosticData | null>(null);
  const [aiCaselawPrecedents, setAiCaselawPrecedents] = useState<Array<{ title: string; source: string; page: number }>>([]);

  const dropdownRef = useRef<HTMLDivElement>(null);

  const openPrecedentDirectly = useCallback(async (queryOrTitle: string, availableCaselaw: string[]) => {
    const cleanQuery = queryOrTitle.trim().replace(/^["']|["']$/g, '');
    if (!cleanQuery) return;

    setActiveTab('caselaw');

    let targetFilename = cleanQuery;
    const lowerQ = cleanQuery.toLowerCase();
    const matchedFromList = availableCaselaw.find(t => t.toLowerCase().includes(lowerQ));
    if (matchedFromList) {
      targetFilename = matchedFromList;
    }

    setSelectedPdfFilename(targetFilename);

    try {
      const res = await apiService.axiosInstance.get('/laws/case-page', { params: { law_title: cleanQuery } });
      if (res.data && res.data.page) {
        setInitialPageNumber(res.data.page);
        if (res.data.law_title && res.data.law_title.toLowerCase().endsWith('.pdf')) {
          setSelectedPdfFilename(res.data.law_title);
        }
      } else {
        setInitialPageNumber(1);
      }
    } catch {
      setInitialPageNumber(1);
    }

    setShowPdfModal(true);
  }, []);

  useEffect(() => {
    const queryFromUrl = searchParams.get('q');
    setIsLoadingData(true);

    apiService.getLawTitles()
      .then((res: any) => {
        if (res) {
          const loadedStatutes = (res.statutes && Array.isArray(res.statutes)) ? res.statutes : [];
          const loadedAcademic = (res.academic_manuals && Array.isArray(res.academic_manuals)) ? res.academic_manuals : [];
          const loadedCaselaw = (res.case_law && Array.isArray(res.case_law)) ? res.case_law : [];

          setStatuteTitles(loadedStatutes);
          setAcademicTitles(loadedAcademic);
          setCaselawTitles(loadedCaselaw);

          if (queryFromUrl) {
            openPrecedentDirectly(queryFromUrl, loadedCaselaw);
          }
        }
      })
      .catch((err) => {
        console.error("[LawSearchPage] Error loading database titles:", err);
      })
      .finally(() => {
        setIsLoadingData(false);
      });
  }, [searchParams, openPrecedentDirectly]);

  const matchedIntent: SemanticIntentRule | null = useMemo(() => {
    const clean = sanitizeSearchText(searchQuery).replace(/["']/g, '');
    if (!clean || clean.length < 3) return null;

    const sortedRules = [...SEMANTIC_INTENT_MATRIX].sort((a, b) => b.priority - a.priority);

    for (const rule of sortedRules) {
      const isMatch = rule.keywords.some((kw) => {
        const sanitizedKw = sanitizeSearchText(kw);
        return clean.includes(sanitizedKw) || sanitizedKw.includes(clean);
      });
      if (isMatch) return rule;
    }
    return null;
  }, [searchQuery]);

  const resolveLawTitle = useCallback((pattern?: string): string => {
    if (!pattern) return statuteTitles[0] || 'Ligji';
    const lowerPat = pattern.toLowerCase();

    const matched = statuteTitles.find((t) => {
      const lower = t.toLowerCase();
      if (lowerPat === 'lpk') return lower.includes('kontestimore') || lower.includes('03/l-006') || lower.includes('03 l 006');
      if (lowerPat === 'lmd') return lower.includes('detyrimeve') || lower.includes('04/l-077') || lower.includes('04 l 077');
      if (lowerPat === 'lsht') return lower.includes('tregtare') || lower.includes('06/l-016') || lower.includes('06 l 016');
      if (lowerPat === 'lpp') return lower.includes('permbarimore') || lower.includes('përmbarimore') || lower.includes('04/l-139');
      if (lowerPat === 'kpk' || lowerPat === 'kprk') return lower.includes('penal') && !lower.includes('procedur');
      if (lowerPat === 'kpprk') return lower.includes('procedur') && lower.includes('penal');
      if (lowerPat === 'lp') return lower.includes('punës') || lower.includes('punes');
      return lower.includes(lowerPat);
    });

    return matched || pattern;
  }, [statuteTitles]);

  const handleOpenExactArticle = (lawPattern: string, articleNumber: string) => {
    const cleanArt = articleNumber.replace(/\D+/g, '') || articleNumber;
    const targetTitle = resolveLawTitle(lawPattern);
    const cleanHighlight = searchQuery.replace(/["']/g, '').trim();
    navigate(`/laws/article?lawTitle=${encodeURIComponent(targetTitle)}&articleNumber=${encodeURIComponent(cleanArt)}&highlight=${encodeURIComponent(cleanHighlight)}`);
  };

  const handleFindArticlesWithAi = async () => {
    const cleanQuery = searchQuery.trim().replace(/^["']|["']$/g, '');
    if (!cleanQuery || isAnalyzingWithAi) return;
    setIsAnalyzingWithAi(true);
    setAiDiagnostic(null);

    try {
      const res = await apiService.axiosInstance.post('/laws/ai-semantic-search', {
        query: cleanQuery
      });

      if (res.data && res.data.ai_diagnostic) {
        setAiDiagnostic(res.data.ai_diagnostic);
        if (res.data.caselaw_precedents) {
          setAiCaselawPrecedents(res.data.caselaw_precedents);
        }
      }
    } catch (err) {
      console.error("[AI Find Articles Error]:", err);
    } finally {
      setIsAnalyzingWithAi(false);
    }
  };

  const filterListByQuery = useCallback((list: string[]) => {
    if (!searchQuery.trim()) return list;
    const cleanQ = sanitizeSearchText(searchQuery).replace(/["']/g, '');
    const tokens = cleanQ.split(/\s+/).filter(t => t.length > 1);

    return list.filter((title) => {
      const sanitizedTitle = sanitizeSearchText(title);
      const matchesTokens = tokens.some(tok => sanitizedTitle.includes(tok));
      if (matchesTokens) return true;

      if (matchedIntent) {
        return matchedIntent.keywords.some(kw => sanitizedTitle.includes(sanitizeSearchText(kw))) ||
               sanitizedTitle.includes(cleanQ);
      }

      return false;
    });
  }, [searchQuery, matchedIntent]);

  const filteredStatutes = useMemo(() => filterListByQuery(statuteTitles), [filterListByQuery, statuteTitles]);
  const filteredAcademic = useMemo(() => filterListByQuery(academicTitles), [filterListByQuery, academicTitles]);
  const filteredCaselaw = useMemo(() => filterListByQuery(caselawTitles), [filterListByQuery, caselawTitles]);

  const activeList = useMemo(() => {
    if (activeTab === 'academic') return filteredAcademic;
    if (activeTab === 'caselaw') return filteredCaselaw;
    return filteredStatutes;
  }, [activeTab, filteredStatutes, filteredAcademic, filteredCaselaw]);

  const handleSelectLaw = async (lawTitle: string) => {
    if (activeTab === 'academic' || activeTab === 'caselaw' || lawTitle.toLowerCase().endsWith('.pdf')) {
      setSelectedPdfFilename(lawTitle);

      try {
        const res = await apiService.axiosInstance.get('/laws/case-page', { params: { law_title: lawTitle } });
        if (res.data && res.data.page) {
          setInitialPageNumber(res.data.page);
        } else {
          setInitialPageNumber(1);
        }
      } catch {
        setInitialPageNumber(1);
      }

      setShowPdfModal(true);
    } else {
      const cleanHighlight = searchQuery.replace(/["']/g, '').trim();
      const queryParam = cleanHighlight ? `&highlight=${encodeURIComponent(cleanHighlight)}` : '';
      navigate(`/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}${queryParam}`);
    }
  };

  const handleChipClick = (queryText: string) => {
    setSearchQuery(queryText);
    setIsListExpanded(true);
    setAiDiagnostic(null);
  };

  const pdfUrl = useMemo(() => {
    if (!selectedPdfFilename) return null;
    
    const nameWithPdf = selectedPdfFilename.toLowerCase().endsWith('.pdf') 
      ? selectedPdfFilename 
      : `${selectedPdfFilename}.pdf`;

    const encoded = encodeURIComponent(nameWithPdf);

    if (activeTab === 'academic') {
      return `${API_V1_URL}/laws/academia/pdf/${encoded}`;
    }
    if (activeTab === 'caselaw') {
      return `${API_V1_URL}/laws/caselaw/pdf/${encoded}`;
    }
    return `${API_V1_URL}/laws/pdf/${encoded}`;
  }, [selectedPdfFilename, activeTab]);

  const modalFilename = useMemo(() => {
    if (!selectedPdfFilename) return 'DokumentLigjor.pdf';
    return selectedPdfFilename.toLowerCase().endsWith('.pdf')
      ? selectedPdfFilename
      : `${selectedPdfFilename}.pdf`;
  }, [selectedPdfFilename]);

  return (
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        
        {/* Navigation & Header */}
        <div className="flex flex-col gap-4 mb-6">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface/40 border border-main text-text-secondary hover:text-text-primary transition-colors hover-lift shadow-sm w-fit cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span className="text-xs font-black uppercase tracking-widest">{t('general.back', 'Kthehu')}</span>
          </button>

          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 text-primary-start mb-1">
                <ShieldCheck size={18} />
                <span className="text-[10px] font-black uppercase tracking-widest">SISTEM FORENZIK I VERIFIKUAR (100%)</span>
              </div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-black text-text-primary tracking-tight">
                Qendra e Kërkimit Ligjor & AI
              </h1>
            </div>
            
            <div className="px-4 py-2 bg-primary-start/10 border border-primary-start/20 rounded-xl text-primary-start font-mono text-xs font-bold">
              {isLoadingData ? 'Duke u ngarkuar...' : `${statuteTitles.length + academicTitles.length + caselawTitles.length} Dokumente Zyrtare`}
            </div>
          </div>
        </div>

        {/* SHIRITI I KËRKIMIT UNIVERSAL */}
        <div className="glass-panel p-5 sm:p-7 mb-6 shadow-md border border-main bg-surface rounded-3xl flex flex-col gap-4">
          <div className="relative w-full">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-primary-start flex items-center pointer-events-none">
              <Search size={22} />
            </div>

            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsListExpanded(true);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleFindArticlesWithAi();
              }}
              placeholder="Shkruaj çfarëdo rasti apo pyetje (p.sh. 'bleva një banesë me defekt', 'prapësimi ndaj urdhrit përmbarimor')..."
              className="w-full pl-12 pr-40 py-4 bg-canvas border border-main rounded-2xl text-xs sm:text-sm md:text-base font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all shadow-inner"
            />

            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setAiDiagnostic(null);
                  }}
                  className="p-2 text-text-muted hover:text-danger-start transition-colors cursor-pointer"
                  title="Pastro"
                >
                  <X size={18} />
                </button>
              )}

              <button
                type="button"
                onClick={handleFindArticlesWithAi}
                disabled={isAnalyzingWithAi || searchQuery.trim().length < 3}
                className="px-4 py-2.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 shadow-sm transition-all hover-lift cursor-pointer disabled:opacity-50"
                title="Gjej Nenet me Inteligjencë Artificiale"
              >
                {isAnalyzingWithAi ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Bot size={16} />
                )}
                <span>Gjej Nenet me AI</span>
              </button>
            </div>
          </div>

          {/* SHEMBUJ TË GATSHËM ME 1-KLIKIM */}
          <div className="flex flex-col gap-1.5 pt-0.5">
            <div className="flex items-center gap-1.5 text-[11px] font-black text-text-muted uppercase tracking-wider">
              <Lightbulb size={13} className="text-amber-500" />
              <span>Zgjidhje të Shpejta me 1-Kliko:</span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1">
              {QUICK_HELP_CHIPS.map((chip, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleChipClick(chip.query)}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-canvas hover:bg-hover border border-main hover:border-primary-start text-xs font-semibold text-text-primary transition-all cursor-pointer whitespace-nowrap shrink-0 shadow-xs hover-lift active:scale-95"
                >
                  <span>{chip.icon}</span>
                  <span>{chip.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* KARTELA E GJETJES SË NENEVE ME AI */}
          <AnimatePresence>
            {aiDiagnostic && (
              <motion.div
                initial={{ opacity: 0, scale: 0.99 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                className="mt-2 bg-gradient-to-br from-primary-start/15 via-surface to-canvas border-2 border-primary-start/40 rounded-3xl p-6 shadow-lg flex flex-col gap-4"
              >
                <div className="flex items-center justify-between flex-wrap gap-2 border-b border-primary-start/20 pb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-primary-start text-white rounded-xl shadow-xs">
                      <Bot size={20} />
                    </div>
                    <div>
                      <span className="text-[10px] font-black uppercase text-primary-start tracking-wider">KUALIFIKIMI I NENEVE ME AI</span>
                      <h3 className="font-black text-sm sm:text-lg text-text-primary">{aiDiagnostic.legal_institute}</h3>
                    </div>
                  </div>

                  <button
                    onClick={() => setAiDiagnostic(null)}
                    className="text-text-muted hover:text-text-primary p-1.5 cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="bg-surface/80 border border-main rounded-2xl p-4 text-xs sm:text-sm text-text-primary leading-relaxed">
                  💡 <strong>Në fjalë të thjeshta:</strong> {aiDiagnostic.plain_explanation}
                </div>

                {/* NENET ME TOOLTIP TË SOLIDIZUAR DHE THEME-AWARE */}
                {aiDiagnostic.matched_statutes && aiDiagnostic.matched_statutes.length > 0 && (
                  <div className="flex flex-col gap-2.5">
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                      <Scale size={14} className="text-primary-start" />
                      <span>Nenet e Identifikuara nga Ligji i Kosovës (Kliko për hapje direkte):</span>
                    </span>

                    <div className="flex flex-wrap gap-2.5 relative">
                      {aiDiagnostic.matched_statutes.map((item, i) => {
                        const shortBadge = formatShortLawBadge(item.law_title);
                        const tooltipKey = `ai_${i}`;
                        const isHovered = hoveredArticleKey === tooltipKey;
                        const fullLawTitle = resolveLawTitle(item.law_title);

                        return (
                          <div
                            key={i}
                            className="relative inline-block"
                            onMouseEnter={() => setHoveredArticleKey(tooltipKey)}
                            onMouseLeave={() => setHoveredArticleKey(null)}
                          >
                            <button
                              onClick={() => handleOpenExactArticle(item.law_title, item.article_number)}
                              className="h-10 px-3.5 bg-primary-start text-white hover:bg-primary-start/90 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all hover-lift active:scale-95 cursor-pointer shadow-sm group"
                            >
                              <Scale size={14} className="shrink-0" />
                              <span className="truncate">{shortBadge} • Neni {item.article_number}</span>
                              <ArrowRight size={13} className="shrink-0 group-hover:translate-x-0.5 transition-transform" />
                            </button>

                            {/* TOOLTIP 100% SOLID, JO-TRANSPARENT & THEME-AWARE */}
                            <AnimatePresence>
                              {isHovered && (
                                <motion.div
                                  initial={{ opacity: 0, y: 8, scale: 0.95 }}
                                  animate={{ opacity: 1, y: 0, scale: 1 }}
                                  exit={{ opacity: 0, y: 8, scale: 0.95 }}
                                  transition={{ duration: 0.12 }}
                                  className="absolute left-0 bottom-full mb-3 w-80 p-4 bg-white dark:bg-[#0f172a] text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.35)] z-[99999] pointer-events-none ring-1 ring-black/5 dark:ring-white/10"
                                >
                                  <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-100 dark:border-slate-800">
                                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                                      <CheckCircle2 size={15} />
                                      <span>Tekst Zyrtar i Verifikuar</span>
                                    </div>
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold">
                                      100% AUTHENTIC
                                    </span>
                                  </div>

                                  <div className="text-xs font-bold text-slate-900 dark:text-white mb-1 leading-snug">
                                    ✅ Ligji: {fullLawTitle}
                                  </div>
                                  <div className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed mb-2.5">
                                    Nen i nxjerrë direkt nga Kodi / Ligji Zyrtar i Kosovës i shpallur në Gazetën Zyrtare.
                                  </div>
                                  
                                  <div className="flex items-center justify-between text-[10px] font-mono bg-slate-50 dark:bg-slate-950 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                                    <span>Neni: <strong>{item.article_number}</strong></span>
                                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">Verifikuar ✓</span>
                                  </div>

                                  {/* Shigjeta poshtë */}
                                  <div className="absolute top-full left-6 -mt-[1px] border-[7px] border-transparent border-t-white dark:border-t-[#0f172a]" />
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* PRECEDENTËT E SUPREMES ME TOOLTIP TË SOLIDIZUAR */}
                {aiCaselawPrecedents.length > 0 && (
                  <div className="flex flex-col gap-2.5 pt-3 border-t border-main/50">
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                      <Gavel size={14} className="text-primary-start" />
                      <span>Precedentët e Gjetur të Gjykatës Supreme:</span>
                    </span>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {aiCaselawPrecedents.map((c, idx) => {
                        const tooltipKey = `case_${idx}`;
                        const isHovered = hoveredArticleKey === tooltipKey;

                        return (
                          <div
                            key={idx}
                            className="relative"
                            onMouseEnter={() => setHoveredArticleKey(tooltipKey)}
                            onMouseLeave={() => setHoveredArticleKey(null)}
                          >
                            <button
                              onClick={() => {
                                setSelectedPdfFilename(c.source || c.title);
                                setInitialPageNumber(c.page || 1);
                                setShowPdfModal(true);
                              }}
                              className="w-full h-11 px-3.5 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-xl text-xs font-medium text-text-primary flex items-center justify-between gap-2 transition-all cursor-pointer hover-lift text-left shadow-2xs"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <FileText size={14} className="text-primary-start shrink-0" />
                                <span className="truncate font-bold text-xs">{c.title}</span>
                              </div>
                              <ExternalLink size={12} className="text-text-muted shrink-0" />
                            </button>

                            {/* TOOLTIP 100% SOLID PËR AKTGJYKIMET */}
                            <AnimatePresence>
                              {isHovered && (
                                <motion.div
                                  initial={{ opacity: 0, y: 8, scale: 0.95 }}
                                  animate={{ opacity: 1, y: 0, scale: 1 }}
                                  exit={{ opacity: 0, y: 8, scale: 0.95 }}
                                  transition={{ duration: 0.12 }}
                                  className="absolute left-0 bottom-full mb-3 w-80 p-4 bg-white dark:bg-[#0f172a] text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.35)] z-[99999] pointer-events-none ring-1 ring-black/5 dark:ring-white/10"
                                >
                                  <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-100 dark:border-slate-800">
                                    <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-bold text-xs">
                                      <CheckCircle2 size={15} />
                                      <span>Precedent i Verifikuar</span>
                                    </div>
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400 font-bold">
                                      SUPREME COURT
                                    </span>
                                  </div>

                                  <div className="text-xs font-bold text-slate-900 dark:text-white mb-1 truncate">
                                    ⚖️ {c.title}
                                  </div>
                                  <div className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed mb-2.5">
                                    Hapje e drejtpërdrejtë e vendimit në <strong>Faqen {c.page}</strong> të Dokumentit Zyrtar nga Arkiva e Gjykatës Supreme.
                                  </div>

                                  <div className="flex items-center justify-between text-[10px] font-mono bg-slate-50 dark:bg-slate-950 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                                    <span>Gjykata Supreme e Kosovës</span>
                                    <span className="text-amber-600 dark:text-amber-400 font-bold">Autentik ✓</span>
                                  </div>

                                  {/* Shigjeta poshtë */}
                                  <div className="absolute top-full left-6 -mt-[1px] border-[7px] border-transparent border-t-white dark:border-t-[#0f172a]" />
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* KARTELA SEMANTIKE ME NENE TË KLIKUESHME (1-KLIKIM) */}
          <AnimatePresence>
            {!aiDiagnostic && matchedIntent && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-1 bg-primary-start/10 border border-primary-start/30 rounded-2xl p-5 flex items-start gap-4 text-xs shadow-xs"
              >
                <div className="p-2.5 bg-primary-start text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                  <Scale size={20} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-black text-text-primary text-xs sm:text-base flex items-center gap-2 flex-wrap mb-1.5">
                    <span>🎯 {matchedIntent.intent}</span>
                    <span className="px-2 py-0.5 bg-primary-start/20 text-primary-start rounded-md text-[10px] font-black uppercase">
                      Përputhje Semantike
                    </span>
                  </div>
                  <p className="text-text-primary font-medium text-xs sm:text-sm leading-relaxed mb-3">
                    💡 <strong>Në fjalë të thjeshta:</strong> {matchedIntent.plainLanguageSummary}
                  </p>

                  <div className="space-y-2.5 pt-2 border-t border-primary-start/20">
                    {matchedIntent.suggestedArticles.map((sug, i) => {
                      const lawBadge = sug.lawPattern || 'LPK';
                      const fullLawTitle = resolveLawTitle(lawBadge);

                      return (
                        <div key={i} className="flex flex-col gap-2">
                          <p className="text-text-secondary text-xs leading-relaxed">
                            📜 <strong>Baza Ligjore:</strong> {sug.explanation}
                          </p>
                          
                          <div className="flex flex-wrap items-center gap-2 pt-1 relative">
                            <span className="text-[10px] font-bold text-text-muted uppercase">Hap direkt:</span>
                            {sug.articles.map((artNum, aIdx) => {
                              const tooltipKey = `intent_${i}_${aIdx}`;
                              const isHovered = hoveredArticleKey === tooltipKey;

                              return (
                                <div
                                  key={aIdx}
                                  className="relative inline-block"
                                  onMouseEnter={() => setHoveredArticleKey(tooltipKey)}
                                  onMouseLeave={() => setHoveredArticleKey(null)}
                                >
                                  <button
                                    type="button"
                                    onClick={() => handleOpenExactArticle(lawBadge, artNum)}
                                    className="h-9 px-3.5 bg-primary-start text-white hover:bg-primary-start/90 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all hover-lift active:scale-95 cursor-pointer shadow-xs group"
                                  >
                                    <Scale size={13} className="shrink-0" />
                                    <span>{lawBadge} • Neni {artNum}</span>
                                    <ArrowRight size={12} className="shrink-0 group-hover:translate-x-0.5 transition-transform" />
                                  </button>

                                  {/* TOOLTIP 100% SOLID DHE THEME-AWARE PËR NENET E SUGJERUARA */}
                                  <AnimatePresence>
                                    {isHovered && (
                                      <motion.div
                                        initial={{ opacity: 0, y: 8, scale: 0.95 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        exit={{ opacity: 0, y: 8, scale: 0.95 }}
                                        transition={{ duration: 0.12 }}
                                        className="absolute left-0 bottom-full mb-3 w-80 p-4 bg-white dark:bg-[#0f172a] text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.35)] z-[99999] pointer-events-none ring-1 ring-black/5 dark:ring-white/10"
                                      >
                                        <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-100 dark:border-slate-800">
                                          <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                                            <CheckCircle2 size={15} />
                                            <span>Tekst Zyrtar i Verifikuar</span>
                                          </div>
                                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold">
                                            100% AUTHENTIC
                                          </span>
                                        </div>

                                        <div className="text-xs font-bold text-slate-900 dark:text-white mb-1 leading-snug">
                                          ✅ Ligji: {fullLawTitle}
                                        </div>
                                        <div className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed mb-2.5">
                                          Nen i nxjerrë direkt nga Kodi / Ligji Zyrtar i Kosovës i shpallur në Gazetën Zyrtare.
                                        </div>
                                        
                                        <div className="flex items-center justify-between text-[10px] font-mono bg-slate-50 dark:bg-slate-950 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                                          <span>Neni: <strong>{artNum}</strong></span>
                                          <span className="text-emerald-600 dark:text-emerald-400 font-bold">Verifikuar ✓</span>
                                        </div>

                                        {/* Shigjeta poshtë */}
                                        <div className="absolute top-full left-6 -mt-[1px] border-[7px] border-transparent border-t-white dark:border-t-[#0f172a]" />
                                      </motion.div>
                                    )}
                                  </AnimatePresence>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* 3 TABS KRYESORE */}
        <div className="grid grid-cols-3 w-full gap-2 mb-6 bg-surface p-2 rounded-2xl border border-main shadow-sm">
          <button
            type="button"
            onClick={() => { setActiveTab('statutes'); }}
            className={`w-full py-3.5 px-2 sm:px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'statutes' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Scale size={16} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Kodet ({filteredStatutes.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('academic'); }}
            className={`w-full py-3.5 px-2 sm:px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'academic' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <GraduationCap size={16} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Akademia ({filteredAcademic.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('caselaw'); }}
            className={`w-full py-3.5 px-2 sm:px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'caselaw' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Gavel size={16} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Aktgjykimet ({filteredCaselaw.length})</span>
          </button>
        </div>

        {/* LISTA E MATERIALEVE TË FILTRUARA ME 2 KOLONA NË DESKTOP */}
        <div className="glass-panel p-6 sm:p-8 mb-12 shadow-sm border border-main bg-surface rounded-3xl" ref={dropdownRef}>
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-main">
            <button
              type="button"
              onClick={() => setIsListExpanded(!isListExpanded)}
              className="flex items-center gap-2 text-xs sm:text-sm font-black text-text-primary uppercase tracking-wider hover:text-primary-start transition-colors cursor-pointer"
            >
              <BookOpen size={18} className="text-primary-start" />
              <span>
                {activeTab === 'statutes' ? 'Kodet Zyrtare të Kosovës' : activeTab === 'academic' ? 'Manualet e Akademisë së Drejtësisë' : 'Precedentët & Aktgjykimet e Gjykatës Supreme'}
              </span>
              <ChevronDown size={18} className={`transition-transform duration-200 ${isListExpanded ? 'rotate-180 text-primary-start' : ''}`} />
            </button>

            <div className="flex items-center gap-3">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setAiDiagnostic(null);
                  }}
                  className="text-xs font-bold text-primary-start hover:underline cursor-pointer"
                >
                  Pastro kërkimin
                </button>
              )}
            </div>
          </div>

          <AnimatePresence>
            {isListExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="max-h-[550px] overflow-y-auto custom-scrollbar pr-1"
              >
                {activeList.length === 0 ? (
                  <div className="py-16 text-center flex flex-col items-center justify-center">
                    <Search size={28} className="text-text-muted mb-2" />
                    <p className="text-xs sm:text-sm font-bold text-text-primary">
                      Nuk u gjet asnjë material në këtë kategori për "{searchQuery}"
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      Provoni të shtypni butonin "Gjej Nenet me AI" më lart ose zgjidhni një skedë tjetër.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {activeList.map((lawTitle, idx) => {
                      const displayTitle = normalizeForDisplay(lawTitle);
                      const isPdf = activeTab === 'academic' || activeTab === 'caselaw' || lawTitle.toLowerCase().endsWith('.pdf');

                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectLaw(lawTitle)}
                          className="w-full text-left p-4 rounded-2xl bg-canvas hover:bg-primary-start text-text-primary hover:text-white border border-main hover:border-primary-start flex items-center justify-between transition-all duration-200 cursor-pointer group shadow-xs hover-lift"
                        >
                          <div className="flex items-center gap-3.5 min-w-0 pr-3">
                            <div className="p-2.5 rounded-xl bg-surface group-hover:bg-white/20 border border-main group-hover:border-white/20 shrink-0 transition-colors">
                              {activeTab === 'academic' ? (
                                <GraduationCap size={18} className="text-primary-start group-hover:text-white" />
                              ) : activeTab === 'caselaw' ? (
                                <Gavel size={18} className="text-primary-start group-hover:text-white" />
                              ) : (
                                <Scale size={18} className="text-primary-start group-hover:text-white" />
                              )}
                            </div>
                            <div className="min-w-0">
                              <span className="font-bold text-xs sm:text-sm block truncate leading-relaxed">
                                {displayTitle}
                              </span>
                              <span className="text-[10px] text-text-muted group-hover:text-white/80 font-mono flex items-center gap-1.5 mt-0.5">
                                {isPdf ? (
                                  <>
                                    <ExternalLink size={11} />
                                    <span>Dokument PDF • Hapje e menjëhershme</span>
                                  </>
                                ) : (
                                  <>
                                    <Check size={11} className="text-emerald-500 group-hover:text-white" />
                                    <span>Kodi Zyrtar • Shiko të gjitha nenet</span>
                                  </>
                                )}
                              </span>
                            </div>
                          </div>

                          <ArrowRight size={18} className="text-text-muted group-hover:text-white group-hover:translate-x-1 transition-all shrink-0" />
                        </button>
                      );
                    })}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>

      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: modalFilename,
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          initialPage={initialPageNumber}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}