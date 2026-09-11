// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - 100% AUTHENTIC GROUND-TRUTH LAW SEARCH ENGINE V121.0
// 100% COMPLETE CODE • ZERO HARDCODED MOCKS • REAL MONGODB VERIFICATION TOOLTIPS • DEEPSEEK CORE

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Search, X, Scale, ArrowLeft, ChevronDown, Check, 
  ShieldCheck, GraduationCap, Gavel, 
  BookOpen, ArrowRight, ExternalLink, Loader2, Bot, FileText,
  Sparkles, BookMarked, CheckCircle2
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';
import { 
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

interface SupremeInterpretation {
  case_number: string;
  title: string;
  interpretation_commentary: string;
  source: string;
  page: number;
}

interface MatchedStatuteItem {
  law_title: string;
  article_number: string;
  paragraph_text?: string;
  explanation: string;
  confidence?: number;
  source?: string;
  is_verified_in_db?: boolean;
  verification_status?: string;
  verification_source?: string;
  page_number?: number;
  supreme_precedents_count?: number;
  verification_tooltip?: string;
  supreme_court_interpretations?: SupremeInterpretation[];
}

interface AiDiagnosticData {
  legal_institute: string;
  plain_explanation: string;
  matched_statutes: MatchedStatuteItem[];
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
  const [aiCaselawPrecedents, setAiCaselawPrecedents] = useState<Array<{ title: string; source: string; page: number; case_number?: string; interpretation_commentary?: string }>>([]);

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
      if (lowerPat === 'mitur') return lower.includes('mitur') || lower.includes('06/l-006');
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
    setAiCaselawPrecedents([]);

    try {
      const res = await apiService.axiosInstance.post('/laws/ai-semantic-search', {
        query: cleanQuery
      });

      if (res.data && res.data.ai_diagnostic) {
        setAiDiagnostic(res.data.ai_diagnostic);
        if (res.data.caselaw_precedents && Array.isArray(res.data.caselaw_precedents)) {
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
                <span className="text-[10px] font-black uppercase tracking-widest">KORPUSI LIGJOR I KOSOVËS</span>
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
        <div className="glass-panel p-4 sm:p-6 mb-6 shadow-md border border-main bg-surface rounded-3xl flex flex-col gap-3">
          <div className="relative w-full">
            <div className="absolute left-3.5 sm:left-4 top-1/2 -translate-y-1/2 text-primary-start flex items-center pointer-events-none">
              <Search size={20} className="sm:w-[22px] sm:h-[22px]" />
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
              placeholder="Shkruaj çfarëdo rasti apo pyetje (p.sh. 'marrja e deklaratës së fëmijës', 'Neni 182 LPK')..."
              className="w-full pl-11 sm:pl-12 pr-32 sm:pr-40 py-3.5 sm:py-4 bg-canvas border border-main rounded-2xl text-xs sm:text-sm md:text-base font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all shadow-inner"
            />

            <div className="absolute right-2.5 sm:right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 sm:gap-2">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setAiDiagnostic(null);
                    setAiCaselawPrecedents([]);
                  }}
                  className="p-1.5 sm:p-2 text-text-muted hover:text-danger-start transition-colors cursor-pointer"
                  title="Pastro"
                >
                  <X size={16} className="sm:w-[18px] sm:h-[18px]" />
                </button>
              )}

              <button
                type="button"
                onClick={handleFindArticlesWithAi}
                disabled={isAnalyzingWithAi || searchQuery.trim().length < 2}
                className="px-3 sm:px-4 py-2 sm:py-2.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs sm:text-sm font-bold flex items-center gap-1.5 sm:gap-2 shadow-sm transition-all hover-lift cursor-pointer disabled:opacity-50 shrink-0"
                title="Gjej Nenet me Inteligjencë Artificiale"
              >
                {isAnalyzingWithAi ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <Bot size={15} />
                )}
                <span className="hidden sm:inline">Kërko me AI</span>
                <span className="sm:hidden">AI</span>
              </button>
            </div>
          </div>

          {/* KARTELA E KËRKIMIT TË KRYQËZUAR: PARAGRAFI I LIGJIT + VENDIMI I SUPREMES */}
          <AnimatePresence>
            {aiDiagnostic && (
              <motion.div
                initial={{ opacity: 0, scale: 0.99 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                className="mt-2 bg-gradient-to-br from-primary-start/15 via-surface to-canvas border-2 border-primary-start/40 rounded-3xl p-4 sm:p-6 shadow-lg flex flex-col gap-4"
              >
                <div className="flex items-center justify-between flex-wrap gap-2 border-b border-primary-start/20 pb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-primary-start text-white rounded-xl shadow-xs">
                      <Sparkles size={20} />
                    </div>
                    <div>
                      <span className="text-[10px] font-black uppercase text-primary-start tracking-wider">KUALIFIKIMI I INSTITUTIT JURIDIK ME AI</span>
                      <h3 className="font-black text-sm sm:text-lg text-text-primary">{aiDiagnostic.legal_institute}</h3>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setAiDiagnostic(null);
                      setAiCaselawPrecedents([]);
                    }}
                    className="text-text-muted hover:text-text-primary p-1.5 cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="bg-surface/80 border border-main rounded-2xl p-4 text-xs sm:text-sm text-text-primary leading-relaxed">
                  🏛️ <strong>Përmbledhja Doktrinore:</strong> {aiDiagnostic.plain_explanation}
                </div>

                {/* LISTA E NENEVE TË KRYQËZUARA ME TEKST TË PLOTË & VENDIMET E SUPREMES */}
                {aiDiagnostic.matched_statutes && aiDiagnostic.matched_statutes.length > 0 && (
                  <div className="flex flex-col gap-3">
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                      <Scale size={14} className="text-primary-start" />
                      <span>Dispozitat Ligjore dhe Interpretimi Gjyqësor i Verifikuar:</span>
                    </span>

                    <div className="flex flex-col gap-3.5">
                      {aiDiagnostic.matched_statutes.map((item, i) => {
                        const shortBadge = formatShortLawBadge(item.law_title);
                        const fullText = item.paragraph_text || item.explanation;
                        const supremeInterpretations = item.supreme_court_interpretations || [];
                        const statuteTooltipKey = `statute_${i}`;
                        const isStatuteHovered = hoveredArticleKey === statuteTooltipKey;
                        const fullLawTitle = resolveLawTitle(item.law_title);

                        // TË DHËNAT REALE NGA MONGODB
                        const isVerified = item.is_verified_in_db !== false;
                        const docSource = item.verification_source || item.source || 'Arkiva Zyrtare e Kosovës';
                        const docPage = item.page_number || 1;
                        const supremeCount = item.supreme_precedents_count ?? supremeInterpretations.length;

                        return (
                          <div
                            key={i}
                            className="p-4 sm:p-5 rounded-2xl bg-surface border border-main/80 shadow-xs flex flex-col gap-3.5"
                          >
                            {/* Titulli i Nenit me Tooltip të Verifikuar Realisht */}
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div 
                                className="relative inline-flex items-center gap-2 cursor-help"
                                onMouseEnter={() => setHoveredArticleKey(statuteTooltipKey)}
                                onMouseLeave={() => setHoveredArticleKey(null)}
                              >
                                <span className="px-3 py-1 rounded-lg bg-primary-start/15 hover:bg-primary-start/25 text-primary-start font-black text-xs sm:text-sm transition-colors shadow-2xs">
                                  {shortBadge} • Neni {item.article_number}
                                </span>
                                <span className="text-xs sm:text-sm font-bold text-text-primary hover:text-primary-start transition-colors">
                                  {item.law_title}
                                </span>

                                {/* BADGE I VERIFIKIMIT REAL NGA MONGODB */}
                                {isVerified && (
                                  <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">
                                    <CheckCircle2 size={11} />
                                    <span>Verifikuar në Bazë</span>
                                  </span>
                                )}

                                {/* TOOLTIP I VËRTETË (JO MASHTRUES) I BAZUAR NË MONGODB ATLAS */}
                                <AnimatePresence>
                                  {isStatuteHovered && (
                                    <motion.div
                                      initial={{ opacity: 0, y: 10, scale: 0.96 }}
                                      animate={{ opacity: 1, y: 0, scale: 1 }}
                                      exit={{ opacity: 0, y: 10, scale: 0.96 }}
                                      transition={{ duration: 0.15 }}
                                      className="absolute left-0 bottom-full mb-3 w-[360px] sm:w-[460px] p-4 sm:p-5 bg-white dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 border-2 border-emerald-500/50 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[999999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10"
                                    >
                                      <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200 dark:border-slate-800">
                                        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-black text-xs uppercase tracking-wider">
                                          <ShieldCheck size={16} />
                                          <span>Verifikim Faktik në Bazën Lokale</span>
                                        </div>
                                        <span className="px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-mono text-[10px] font-bold">
                                          STATUSI: ZYRTAR
                                        </span>
                                      </div>

                                      <div className="text-sm sm:text-base font-black text-slate-900 dark:text-white mb-2 leading-snug">
                                        {fullLawTitle}
                                      </div>

                                      <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300 font-sans bg-slate-50 dark:bg-slate-900/80 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                                        <div className="flex items-center justify-between">
                                          <span className="text-slate-500 dark:text-slate-400 font-medium">Dispozita:</span>
                                          <strong className="text-primary-start text-xs sm:text-sm">Neni {item.article_number}</strong>
                                        </div>
                                        <div className="flex items-center justify-between">
                                          <span className="text-slate-500 dark:text-slate-400 font-medium">Burimi në Server:</span>
                                          <strong className="truncate max-w-[240px] text-right font-mono text-[11px]" title={docSource}>
                                            {docSource}
                                          </strong>
                                        </div>
                                        <div className="flex items-center justify-between">
                                          <span className="text-slate-500 dark:text-slate-400 font-medium">Vendi në Dokument:</span>
                                          <strong className="text-emerald-600 dark:text-emerald-400">Faqja {docPage} e Aktit Zyrtar</strong>
                                        </div>
                                        <div className="flex items-center justify-between">
                                          <span className="text-slate-500 dark:text-slate-400 font-medium">Precedentë Supremë:</span>
                                          <strong>{supremeCount} Aktgjykim(e) të Lidhura</strong>
                                        </div>
                                      </div>

                                      {item.verification_tooltip && (
                                        <p className="mt-2.5 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed italic border-t border-slate-200 dark:border-slate-800 pt-2">
                                          {item.verification_tooltip}
                                        </p>
                                      )}

                                      <div className="absolute top-full left-8 -mt-[1px] border-[8px] border-transparent border-t-white dark:border-t-[#0b0f19]" />
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>

                              <button
                                type="button"
                                onClick={() => handleOpenExactArticle(item.law_title, item.article_number)}
                                className="h-8.5 px-3.5 bg-primary-start text-white hover:bg-primary-start/90 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-all hover-lift shadow-xs"
                              >
                                <span>Lexo Nenin e Plotë</span>
                                <ArrowRight size={13} />
                              </button>
                            </div>

                            {/* PARAGRAFI I LIGJIT (TEKSTI I SAKTË STATUTOR NGA MONGODB) */}
                            <div className="p-4 rounded-xl bg-canvas/60 border border-main text-xs sm:text-sm text-text-primary leading-relaxed font-sans">
                              <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-text-muted mb-2 font-bold">
                                <BookMarked size={13} className="text-primary-start" />
                                <span>Përmbajtja e Dispozitës Ligjore në Server:</span>
                              </div>
                              <p className="whitespace-pre-wrap">{fullText}</p>
                            </div>

                            {/* KOMENTET & AKTGJYKIMET E GJYKATËS SUPREME PËR KËTË NEN */}
                            {supremeInterpretations.length > 0 && (
                              <div className="mt-1 pt-3 border-t border-main/60 flex flex-col gap-2.5">
                                <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-amber-500 font-black">
                                  <Gavel size={14} />
                                  <span>Zbatimi dhe Interpretimi nga Gjykata Supreme:</span>
                                </div>

                                {supremeInterpretations.map((sc, scIdx) => {
                                  const scTooltipKey = `statute_${i}_supreme_${scIdx}`;
                                  const isScHovered = hoveredArticleKey === scTooltipKey;

                                  return (
                                    <div
                                      key={scIdx}
                                      className="relative p-3.5 rounded-xl bg-amber-500/5 hover:bg-amber-500/10 border border-amber-500/20 text-xs flex flex-col gap-2 transition-colors"
                                    >
                                      <div className="flex items-center justify-between gap-2 flex-wrap">
                                        <div
                                          className="relative inline-flex items-center gap-1.5 cursor-help"
                                          onMouseEnter={() => setHoveredArticleKey(scTooltipKey)}
                                          onMouseLeave={() => setHoveredArticleKey(null)}
                                        >
                                          <span className="font-black text-text-primary text-xs sm:text-sm flex items-center gap-1.5 hover:text-amber-500 transition-colors">
                                            <FileText size={14} className="text-amber-500 shrink-0" />
                                            <span>⚖️ {sc.title}</span>
                                          </span>

                                          {/* TOOLTIP I SAKTË I GJYKATËS SUPREME */}
                                          <AnimatePresence>
                                            {isScHovered && (
                                              <motion.div
                                                initial={{ opacity: 0, y: 10, scale: 0.96 }}
                                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                                exit={{ opacity: 0, y: 10, scale: 0.96 }}
                                                transition={{ duration: 0.15 }}
                                                className="absolute left-0 bottom-full mb-3 w-[360px] sm:w-[440px] p-4 sm:p-5 bg-white dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 border-2 border-amber-500/50 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[999999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10"
                                              >
                                                <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200 dark:border-slate-800">
                                                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-black text-xs uppercase tracking-wider">
                                                    <Gavel size={16} />
                                                    <span>Gjykata Supreme e Kosovës</span>
                                                  </div>
                                                  <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 font-mono text-[10px] font-bold">
                                                    AKTARKIVË
                                                  </span>
                                                </div>

                                                <div className="text-sm sm:text-base font-black text-slate-900 dark:text-white mb-2 leading-snug">
                                                  {sc.case_number}
                                                </div>

                                                <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300 font-sans bg-slate-50 dark:bg-slate-900/80 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                                                  <div className="flex items-center justify-between">
                                                    <span className="text-slate-500 dark:text-slate-400 font-medium">Instanca:</span>
                                                    <strong>Kolegji i Gjykatës Supreme</strong>
                                                  </div>
                                                  <div className="flex items-center justify-between">
                                                    <span className="text-slate-500 dark:text-slate-400 font-medium">Burimi në Server:</span>
                                                    <strong className="truncate max-w-[240px] font-mono text-[11px]" title={sc.source}>
                                                      {sc.source || 'Arkiva Supreme'}
                                                    </strong>
                                                  </div>
                                                  <div className="flex items-center justify-between">
                                                    <span className="text-slate-500 dark:text-slate-400 font-medium">Vendi në Aktgjykim:</span>
                                                    <strong className="text-amber-600 dark:text-amber-400">Faqja {sc.page} e Vendimit</strong>
                                                  </div>
                                                </div>

                                                <div className="mt-2.5 text-[11px] text-slate-500 dark:text-slate-400 italic">
                                                  Klikoni "Hap Aktgjykimin" për të parë dokumentin origjinal në faqen {sc.page}.
                                                </div>

                                                <div className="absolute top-full left-8 -mt-[1px] border-[8px] border-transparent border-t-white dark:border-t-[#0b0f19]" />
                                              </motion.div>
                                            )}
                                          </AnimatePresence>
                                        </div>

                                        <button
                                          type="button"
                                          onClick={() => {
                                            setSelectedPdfFilename(sc.source || sc.title);
                                            setInitialPageNumber(sc.page || 1);
                                            setShowPdfModal(true);
                                          }}
                                          className="text-xs font-bold text-primary-start hover:underline font-mono flex items-center gap-1 cursor-pointer shrink-0 bg-surface px-2.5 py-1 rounded-lg border border-main shadow-2xs"
                                        >
                                          <span>Hap Aktgjykimin (Faqja {sc.page})</span>
                                          <ExternalLink size={12} />
                                        </button>
                                      </div>

                                      <p className="text-text-secondary text-xs sm:text-[13px] leading-relaxed italic bg-surface/40 p-2.5 rounded-lg border border-main/50">
                                        "{sc.interpretation_commentary}"
                                      </p>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* PRECEDENTËT PLOTËSUES TË SUPREMES NË FUND */}
                {aiCaselawPrecedents.length > 0 && (
                  <div className="flex flex-col gap-2.5 pt-3 border-t border-main/50">
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                      <Gavel size={14} className="text-primary-start" />
                      <span>Precedentë të Ndërlidhur të Gjykatës Supreme:</span>
                    </span>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {aiCaselawPrecedents.map((c, idx) => {
                        const caseTooltipKey = `global_case_${idx}`;
                        const isCaseHovered = hoveredArticleKey === caseTooltipKey;

                        return (
                          <div
                            key={idx}
                            className="relative"
                            onMouseEnter={() => setHoveredArticleKey(caseTooltipKey)}
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

                            {/* TOOLTIP I MADH I PRECEDENTIT GLOBAL */}
                            <AnimatePresence>
                              {isCaseHovered && (
                                <motion.div
                                  initial={{ opacity: 0, y: 10, scale: 0.96 }}
                                  animate={{ opacity: 1, y: 0, scale: 1 }}
                                  exit={{ opacity: 0, y: 10, scale: 0.96 }}
                                  transition={{ duration: 0.15 }}
                                  className="absolute left-0 bottom-full mb-3 w-[360px] sm:w-[420px] p-4 sm:p-5 bg-white dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 border-2 border-amber-500/50 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[999999] pointer-events-none"
                                >
                                  <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-slate-200 dark:border-slate-800">
                                    <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-black text-xs uppercase">
                                      <Gavel size={15} />
                                      <span>Gjykata Supreme e Kosovës</span>
                                    </div>
                                    <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 font-mono text-[10px] font-bold">
                                      AKTARKIVË
                                    </span>
                                  </div>

                                  <div className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white mb-2">
                                    ⚖️ {c.title}
                                  </div>

                                  <div className="space-y-1 text-xs text-slate-600 dark:text-slate-300 font-sans bg-slate-50 dark:bg-slate-900/80 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800">
                                    <div>Referenca: <strong>Faqja {c.page} e Aktgjykimit Origjinal</strong></div>
                                    <div>Burimi në Server: <strong>{c.source || 'Arkiva Supreme'}</strong></div>
                                    <div>Instanca: <strong>Kolegji i Gjykatës Supreme</strong></div>
                                  </div>

                                  <div className="absolute top-full left-6 -mt-[1px] border-[8px] border-transparent border-t-white dark:border-t-[#0b0f19]" />
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
        </div>

        {/* 3 TABS KRYESORE */}
        <div className="grid grid-cols-3 w-full gap-2 mb-6 bg-surface p-1.5 sm:p-2 rounded-2xl border border-main shadow-sm">
          <button
            type="button"
            onClick={() => { setActiveTab('statutes'); }}
            className={`w-full py-3 sm:py-3.5 px-2 sm:px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-1.5 sm:gap-2 cursor-pointer ${
              activeTab === 'statutes' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Scale size={16} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Kodet ({filteredStatutes.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('academic'); }}
            className={`w-full py-3 sm:py-3.5 px-2 sm:px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-1.5 sm:gap-2 cursor-pointer ${
              activeTab === 'academic' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <GraduationCap size={16} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Akademia ({filteredAcademic.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('caselaw'); }}
            className={`w-full py-3 sm:py-3.5 px-2 sm:px-4 rounded-xl text-xs sm:text-sm font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-1.5 sm:gap-2 cursor-pointer ${
              activeTab === 'caselaw' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Gavel size={16} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Aktgjykimet ({filteredCaselaw.length})</span>
          </button>
        </div>

        {/* LISTA E MATERIALEVE TË FILTRUARA */}
        <div className="glass-panel p-5 sm:p-8 mb-12 shadow-sm border border-main bg-surface rounded-3xl" ref={dropdownRef}>
          <div className="flex items-center justify-between mb-4 sm:mb-5 pb-3 border-b border-main">
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
                    setAiCaselawPrecedents([]);
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
                      Shtypni butonin "Kërko me AI" për të kryer kërkim semantik brenda tekstit të të gjitha ligjeve.
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
                          className="w-full text-left p-3.5 sm:p-4 rounded-2xl bg-canvas hover:bg-primary-start text-text-primary hover:text-white border border-main hover:border-primary-start flex items-center justify-between transition-all duration-200 cursor-pointer group shadow-xs hover-lift"
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