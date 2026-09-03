// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - UNIVERSAL AI-POWERED LEGAL DIAGNOSTIC & DISCOVERY HUB V91.0

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Search, X, Scale, ArrowLeft, ChevronDown, Check, 
  ShieldCheck, GraduationCap, Gavel, Sparkles, Lightbulb, 
  BookOpen, ArrowRight, ExternalLink, Loader2, Bot, FileText
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

interface AiDiagnosticData {
  legal_institute: string;
  plain_explanation: string;
  matched_statutes: Array<{
    law_title: string;
    article_number: string;
    explanation: string;
    confidence: number;
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

  // AI DIAGNOSTIC STATE
  const [isAnalyzingWithAi, setIsAnalyzingWithAi] = useState(false);
  const [aiDiagnostic, setAiDiagnostic] = useState<AiDiagnosticData | null>(null);
  const [aiCaselawPrecedents, setAiCaselawPrecedents] = useState<Array<{ title: string; source: string; page: number }>>([]);

  const dropdownRef = useRef<HTMLDivElement>(null);

  // Hapja direkte e PDF-së në faqen e saktë
  const openPrecedentDirectly = useCallback(async (queryOrTitle: string, availableCaselaw: string[]) => {
    const cleanQuery = queryOrTitle.trim();
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

  // MATRICA LOKALE E INTELIGJENCËS (0.001s)
  const matchedIntent: SemanticIntentRule | null = useMemo(() => {
    const clean = sanitizeSearchText(searchQuery);
    if (!clean || clean.length < 3) return null;

    for (const rule of SEMANTIC_INTENT_MATRIX) {
      const isMatch = rule.keywords.some((kw) => {
        const sanitizedKw = sanitizeSearchText(kw);
        return clean.includes(sanitizedKw) || sanitizedKw.includes(clean);
      });
      if (isMatch) return rule;
    }
    return null;
  }, [searchQuery]);

  // THIRRJA E THELLË ME AI PËR GJETJEN E NENEVE
  const handleFindArticlesWithAi = async () => {
    if (!searchQuery.trim() || isAnalyzingWithAi) return;
    setIsAnalyzingWithAi(true);
    setAiDiagnostic(null);

    try {
      const res = await apiService.axiosInstance.post('/laws/ai-semantic-search', {
        query: searchQuery.trim()
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

  // Filtruesit e listës
  const filterListByQuery = useCallback((list: string[]) => {
    if (!searchQuery.trim()) return list;
    const cleanQ = sanitizeSearchText(searchQuery);
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
      const queryParam = searchQuery.trim() ? `&highlight=${encodeURIComponent(searchQuery.trim())}` : '';
      navigate(`/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}${queryParam}`);
    }
  };

  const handleChipClick = (queryText: string) => {
    setSearchQuery(queryText);
    setIsListExpanded(true);
    setAiDiagnostic(null);
  };

  const handleOpenExactArticle = (lawTitle: string, articleNumber: string) => {
    const cleanArt = articleNumber.replace(/\D+/g, '') || articleNumber;
    navigate(`/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(cleanArt)}&highlight=${encodeURIComponent(searchQuery)}`);
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
      <div className="max-w-4xl mx-auto px-4 sm:px-8 pt-24 sm:pt-28">
        
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
                <span className="text-[10px] font-black uppercase tracking-widest">VERIFIKIM ZYRTAR & PRAKTIKË SUPREME</span>
              </div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-black text-text-primary tracking-tight">
                Qendra e Kërkimit Ligjor & AI
              </h1>
            </div>
            
            <div className="px-4 py-2 bg-primary-start/10 border border-primary-start/20 rounded-xl text-primary-start font-mono text-xs font-bold">
              {isLoadingData ? 'Duke u ngarkuar...' : `${statuteTitles.length + academicTitles.length + caselawTitles.length} Dokumente Gjithsej`}
            </div>
          </div>
        </div>

        {/* SHIRITI I KËRKIMIT UNIVERSAL SEMANTIK */}
        <div className="glass-panel p-5 sm:p-6 mb-6 shadow-md border border-main bg-surface rounded-3xl flex flex-col gap-3.5">
          <div className="relative w-full">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-primary-start flex items-center gap-1.5 pointer-events-none">
              <Search size={20} />
              <Sparkles size={16} className="text-amber-500 animate-pulse" />
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
              placeholder="Shkruaj çfarëdo rasti apo pyetje (p.sh. 'bleva një banesë me defekt', 'bllokimi i bankave')..."
              className="w-full pl-14 pr-36 py-4 bg-canvas border border-main rounded-2xl text-xs sm:text-sm md:text-base font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all shadow-inner"
            />

            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setAiDiagnostic(null);
                  }}
                  className="p-1.5 text-text-muted hover:text-danger-start transition-colors cursor-pointer"
                  title="Pastro"
                >
                  <X size={16} />
                </button>
              )}

              {/* BUTONI: GJEJ NENET ME AI */}
              {searchQuery.trim().length >= 3 && (
                <button
                  type="button"
                  onClick={handleFindArticlesWithAi}
                  disabled={isAnalyzingWithAi}
                  className="px-3 py-2 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all hover-lift cursor-pointer disabled:opacity-50"
                  title="Gjej Nenet me Inteligjencë Artificiale"
                >
                  {isAnalyzingWithAi ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Bot size={14} />
                  )}
                  <span>Gjej Nenet me AI</span>
                </button>
              )}
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-canvas hover:bg-hover border border-main hover:border-primary-start text-xs font-semibold text-text-primary transition-all cursor-pointer whitespace-nowrap shrink-0 shadow-xs hover-lift active:scale-95"
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
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                className="mt-2 bg-gradient-to-br from-primary-start/15 via-surface to-canvas border-2 border-primary-start/40 rounded-3xl p-5 shadow-lg flex flex-col gap-3.5"
              >
                <div className="flex items-center justify-between flex-wrap gap-2 border-b border-primary-start/20 pb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 bg-primary-start text-white rounded-xl shadow-xs">
                      <Bot size={18} />
                    </div>
                    <div>
                      <span className="text-[10px] font-black uppercase text-primary-start tracking-wider">KUALIFIKIMI I NENEVE ME AI</span>
                      <h3 className="font-black text-sm sm:text-base text-text-primary">{aiDiagnostic.legal_institute}</h3>
                    </div>
                  </div>

                  <button
                    onClick={() => setAiDiagnostic(null)}
                    className="text-text-muted hover:text-text-primary p-1 cursor-pointer"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Shpjegimi popullor */}
                <div className="bg-surface/80 border border-main rounded-2xl p-3.5 text-xs text-text-primary leading-relaxed">
                  💡 <strong>Në fjalë të thjeshta:</strong> {aiDiagnostic.plain_explanation}
                </div>

                {/* Nenet e gjetura me 1-klikim */}
                {aiDiagnostic.matched_statutes && aiDiagnostic.matched_statutes.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-wider">
                      📜 Nenet e Identifikuara nga Ligji i Kosovës (Kliko për hapje direkte):
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {aiDiagnostic.matched_statutes.map((item, i) => (
                        <button
                          key={i}
                          onClick={() => handleOpenExactArticle(item.law_title, item.article_number)}
                          className="px-3.5 py-2 bg-primary-start text-white hover:bg-primary-start/90 rounded-xl text-xs font-bold flex items-center gap-2 transition-all hover-lift active:scale-95 cursor-pointer shadow-sm"
                        >
                          <Scale size={14} />
                          <span>{item.law_title} • Neni {item.article_number}</span>
                          <ArrowRight size={13} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Precedentët e Supremes */}
                {aiCaselawPrecedents.length > 0 && (
                  <div className="flex flex-col gap-2 pt-2 border-t border-main/50">
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-wider">
                      ⚖️ Precedentët e Gjetur të Gjykatës Supreme:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {aiCaselawPrecedents.map((c, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSelectedPdfFilename(c.source || c.title);
                            setInitialPageNumber(c.page || 1);
                            setShowPdfModal(true);
                          }}
                          className="px-3 py-1.5 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-xl text-xs font-medium text-text-primary flex items-center gap-1.5 transition-all cursor-pointer hover-lift"
                        >
                          <FileText size={13} className="text-primary-start" />
                          <span className="truncate max-w-[240px]">{c.title}</span>
                          <ExternalLink size={11} className="text-text-muted" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* KARTELA SEMANTIKE E SHPEJTË */}
          <AnimatePresence>
            {!aiDiagnostic && matchedIntent && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-1 bg-primary-start/10 border border-primary-start/30 rounded-2xl p-4 flex items-start gap-3.5 text-xs shadow-xs"
              >
                <div className="p-2.5 bg-primary-start text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                  <Sparkles size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-black text-text-primary text-xs sm:text-sm flex items-center gap-2 flex-wrap mb-1">
                    <span>🎯 {matchedIntent.intent}</span>
                    <span className="px-2 py-0.5 bg-primary-start/20 text-primary-start rounded-md text-[10px] font-black uppercase">
                      Përputhje Semantike
                    </span>
                  </div>
                  <p className="text-text-primary font-medium text-xs leading-relaxed mb-1.5">
                    💡 <strong>Në fjalë të thjeshta:</strong> {matchedIntent.plainLanguageSummary}
                  </p>
                  {matchedIntent.suggestedArticles.map((sug, i) => (
                    <p key={i} className="text-text-secondary text-[11px] leading-relaxed">
                      📜 <strong>Baza Ligjore:</strong> {sug.explanation}
                    </p>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* 3 TABS KRYESORE */}
        <div className="grid grid-cols-3 w-full gap-1.5 mb-6 bg-surface p-1.5 rounded-2xl border border-main shadow-sm">
          <button
            type="button"
            onClick={() => { setActiveTab('statutes'); }}
            className={`w-full py-3 px-1 sm:px-4 rounded-xl text-[11px] sm:text-xs font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === 'statutes' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Scale size={15} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Kodet ({filteredStatutes.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('academic'); }}
            className={`w-full py-3 px-1 sm:px-4 rounded-xl text-[11px] sm:text-xs font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === 'academic' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <GraduationCap size={15} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Akademia ({filteredAcademic.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('caselaw'); }}
            className={`w-full py-3 px-1 sm:px-4 rounded-xl text-[11px] sm:text-xs font-black uppercase tracking-tight sm:tracking-wider transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === 'caselaw' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Gavel size={15} className="shrink-0 hidden xs:inline" />
            <span className="truncate">Aktgjykimet ({filteredCaselaw.length})</span>
          </button>
        </div>

        {/* LISTA E MATERIALEVE TË FILTRUARA */}
        <div className="glass-panel p-5 sm:p-7 mb-12 shadow-sm border border-main bg-surface rounded-3xl" ref={dropdownRef}>
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-main">
            <button
              type="button"
              onClick={() => setIsListExpanded(!isListExpanded)}
              className="flex items-center gap-2 text-xs font-black text-text-primary uppercase tracking-wider hover:text-primary-start transition-colors cursor-pointer"
            >
              <BookOpen size={16} className="text-primary-start" />
              <span>
                {activeTab === 'statutes' ? 'Kodet Zyrtare të Kosovës' : activeTab === 'academic' ? 'Manualet e Akademisë së Drejtësisë' : 'Precedentët & Aktgjykimet e Gjykatës Supreme'}
              </span>
              <ChevronDown size={16} className={`transition-transform duration-200 ${isListExpanded ? 'rotate-180 text-primary-start' : ''}`} />
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
                className="max-h-[500px] overflow-y-auto custom-scrollbar space-y-2 pr-1"
              >
                {activeList.length === 0 ? (
                  <div className="py-12 text-center flex flex-col items-center justify-center">
                    <Search size={24} className="text-text-muted mb-2" />
                    <p className="text-xs font-bold text-text-primary">
                      Nuk u gjet asnjë material në këtë kategori për "{searchQuery}"
                    </p>
                    <p className="text-[11px] text-text-muted mt-1">
                      Provoni të shtypni butonin "Gjej Nenet me AI" më lart ose zgjidhni një skedë tjetër.
                    </p>
                  </div>
                ) : (
                  activeList.map((lawTitle, idx) => {
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
                  })
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