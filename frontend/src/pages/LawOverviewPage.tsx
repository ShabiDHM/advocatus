// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - ZERO-TECH ACCESSIBLE SEMANTIC LAW ENGINE V60.0

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft, ArrowRight, FileText, AlertCircle, 
  BookOpen, ExternalLink, Search, X,
  Maximize2, Minimize2, Sparkles, Filter, Lightbulb
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';
import { 
  LEGAL_CATEGORIES, 
  QUICK_HELP_CHIPS,
  performSemanticSearch 
} from '../utils/legalSemanticEngine';

interface LawOverviewData {
  law_title: string;
  source: string;
  article_count: number;
  articles: string[];
  is_official_statute?: boolean;
}

export default function LawOverviewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  
  const [data, setData] = useState<LawOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [articleSearchQuery, setArticleSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [isExpanded, setIsExpanded] = useState(false);
  
  const [showPdfModal, setShowPdfModal] = useState(false);

  const lawTitle = searchParams.get('lawTitle') || '';

  useEffect(() => {
    if (!lawTitle) {
      setError(t('lawOverview.missingTitle', 'Titulli i ligjit mungon.'));
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');

    apiService
      .getLawArticlesByTitle(lawTitle)
      .then((res: any) => setData(res))
      .catch((err) => {
        console.error('Law overview fetch error:', err);
        setError(err.message || t('lawOverview.fetchError', 'Dështoi ngarkimi i ligjit.'));
      })
      .finally(() => setLoading(false));
  }, [lawTitle, t]);

  const pdfUrl = data?.source ? `${API_V1_URL}/laws/pdf/${encodeURIComponent(data.source)}` : null;
  const displayHeaderTitle = lawTitle || data?.law_title || '';

  // REZULTATI I MOTORIT TË KËRKIMIT SEMANTIK DHE FILTRIMIT
  const searchResults = useMemo(() => {
    if (!data?.articles) {
      return {
        filteredArticles: [],
        matchedIntent: null,
        highlightWords: [],
      };
    }

    return performSemanticSearch(
      data.articles,
      articleSearchQuery,
      displayHeaderTitle,
      activeCategory
    );
  }, [data?.articles, articleSearchQuery, displayHeaderTitle, activeCategory]);

  const { filteredArticles, matchedIntent, highlightWords } = searchResults;

  const handleOpenArticle = (article: string) => {
    const highlightParam = highlightWords.length > 0 ? `&highlight=${encodeURIComponent(highlightWords.join(' '))}` : '';
    navigate(
      `/laws/article?lawTitle=${encodeURIComponent(displayHeaderTitle)}&articleNumber=${encodeURIComponent(
        article
      )}${highlightParam}`
    );
  };

  const handleChipClick = (query: string) => {
    setArticleSearchQuery(query);
    setActiveCategory('all');
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-16 h-16 mb-4" />
          <h2 className="text-xl font-black text-text-primary uppercase tracking-tight mb-2">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-sm mb-6">{error || 'Të dhënat nuk u gjetën.'}</p>
          <button
            onClick={() => navigate(-1)}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span>Kthehu mbrapa</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="w-full min-h-screen pb-12 bg-canvas text-text-primary transition-all duration-300"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className={`w-full mx-auto pt-20 sm:pt-24 transition-all duration-300 ${
        isExpanded ? 'max-w-[98vw] px-2 sm:px-4' : 'max-w-7xl px-4 sm:px-6 lg:px-8'
      }`}>
        
        {/* Navigimi 1 Hap Mbrapa / 1 Hap Përpara */}
        <div className="flex items-center gap-2 mb-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="p-2.5 rounded-xl bg-surface border border-main hover:border-primary-start/60 text-text-primary hover:text-primary-start transition-all hover-lift cursor-pointer shadow-sm"
            title="Mbrapa"
          >
            <ArrowLeft size={16} />
          </button>
          <button
            type="button"
            onClick={() => navigate(1)}
            className="p-2.5 rounded-xl bg-surface border border-main hover:border-primary-start/60 text-text-primary hover:text-primary-start transition-all hover-lift cursor-pointer shadow-sm"
            title="Përpara"
          >
            <ArrowRight size={16} />
          </button>
        </div>

        {/* Paneli Kryesor */}
        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface transition-all duration-300">
          
          {/* Header Bar */}
          <div className="bg-canvas px-6 sm:px-10 py-6 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-4">
              <div className="flex items-center justify-between gap-3">
                
                {pdfUrl ? (
                  <button
                    type="button"
                    onClick={() => setShowPdfModal(true)}
                    className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all hover-lift cursor-pointer shadow-sm"
                    title="Hap dokumentin zyrtar PDF"
                  >
                    <FileText size={14} />
                    <span>Shiko PDF të Plotë</span>
                    <ExternalLink size={12} />
                  </button>
                ) : (
                  <div />
                )}

                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-2.5 bg-surface hover:bg-hover text-text-primary border border-main rounded-xl transition-all hover-lift cursor-pointer shadow-sm"
                  title={isExpanded ? 'Zvogëlo pamjen' : 'Zmadho në ekran të plotë'}
                >
                  {isExpanded ? (
                    <Minimize2 size={16} className="text-primary-start" />
                  ) : (
                    <Maximize2 size={16} className="text-primary-start" />
                  )}
                </button>
              </div>

              <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-text-primary leading-tight tracking-tight">
                {displayHeaderTitle}
              </h1>

              <div className="flex items-center gap-2 pt-2 border-t border-main/50">
                <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3 py-1 rounded-xl text-xs font-bold font-mono">
                  <FileText size={14} className="text-primary-start" />
                  <span>{data.article_count} Nene Gjithsej</span>
                </div>
              </div>
            </div>
          </div>

          {/* KËRKUESI INTELIGJENT & NDËRFAQJA E LEHTË */}
          <div className="bg-surface px-4 sm:px-8 pt-5 pb-5 border-b border-main flex flex-col gap-4">
            
            {/* Search Bar */}
            <div className="relative w-full">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-primary-start flex items-center gap-1.5 pointer-events-none">
                <Search size={18} />
                <Sparkles size={14} className="animate-pulse text-amber-500" />
              </div>

              <input
                type="text"
                placeholder="Shkruaj situatën tënde (p.sh. 's'kam pare për gjyq', 'bllokimi i llogarive', 'avokati pa letrën')..."
                value={articleSearchQuery}
                onChange={(e) => setArticleSearchQuery(e.target.value)}
                className="w-full pl-14 pr-10 py-3.5 bg-canvas border border-main rounded-2xl text-xs sm:text-sm font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all shadow-inner"
              />

              {articleSearchQuery && (
                <button
                  type="button"
                  onClick={() => setArticleSearchQuery('')}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-danger-start p-1 cursor-pointer transition-colors"
                  title="Pastro kërkimin"
                >
                  <X size={16} />
                </button>
              )}
            </div>

            {/* BUTONAT ME 1-KLIKIM PËR SITUATAT E ZAKONSHME (ZERO-TECH CHIPS) */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-1.5 text-[11px] font-black text-text-muted uppercase tracking-wider">
                <Lightbulb size={13} className="text-amber-500" />
                <span>Shembuj të Shpejtë (Kliko për të gjetur menjëherë):</span>
              </div>

              <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1 pt-0.5">
                {QUICK_HELP_CHIPS.map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleChipClick(chip.query)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-canvas hover:bg-hover border border-main hover:border-primary-start/60 text-xs font-semibold text-text-primary transition-all cursor-pointer whitespace-nowrap shrink-0 shadow-xs hover-lift"
                  >
                    <span>{chip.icon}</span>
                    <span>{chip.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* FILTRAT SIPAS KATEGORIVE (CATEGORY PILLS) */}
            <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pt-1 border-t border-main/50">
              <div className="text-[11px] font-black text-text-muted uppercase tracking-wider flex items-center gap-1 shrink-0 mr-1">
                <Filter size={12} className="text-primary-start" />
                <span>Kategoritë:</span>
              </div>

              {LEGAL_CATEGORIES.map((cat) => {
                const isActive = activeCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setActiveCategory(cat.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer border shrink-0 ${
                      isActive
                        ? 'bg-primary-start text-white border-primary-start shadow-sm'
                        : 'bg-canvas text-text-secondary border-main hover:border-primary-start/50 hover:text-text-primary'
                    }`}
                    title={cat.description}
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>

            {/* SHPJEGIMI NË GJUHË TË THJESHTË POPULLORE (HUMAN-FRIENDLY BANNER) */}
            <AnimatePresence>
              {matchedIntent && (
                <motion.div
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="bg-primary-start/10 border border-primary-start/30 rounded-2xl p-4 flex items-start gap-3 text-xs shadow-xs"
                >
                  <div className="p-2 bg-primary-start text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                    <Sparkles size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="font-black text-text-primary text-xs sm:text-sm">
                        {matchedIntent.intent}
                      </span>
                      <span className="px-2 py-0.5 bg-primary-start/20 text-primary-start rounded-md font-mono text-[10px] font-black uppercase">
                        Gjetje Automatike
                      </span>
                    </div>

                    {/* Shpjegimi popullor */}
                    <p className="text-text-primary font-medium text-xs leading-relaxed mb-1.5">
                      💡 <strong>Në fjalë të thjeshta:</strong> {matchedIntent.plainLanguageSummary}
                    </p>

                    {/* Shpjegimi ligjor */}
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

          {/* Trupi me Rrjetën e Neneve */}
          <div className="bg-canvas/30 px-4 sm:px-8 py-6 pb-8 flex flex-col">
            
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-black text-text-muted uppercase tracking-wider flex items-center gap-2">
                <BookOpen size={16} className="text-primary-start" />
                Përmbajtja e Neneve ({filteredArticles.length})
              </h2>

              {(articleSearchQuery || activeCategory !== 'all') && (
                <button
                  type="button"
                  onClick={() => {
                    setArticleSearchQuery('');
                    setActiveCategory('all');
                  }}
                  className="text-xs font-bold text-primary-start hover:underline cursor-pointer"
                >
                  Pastro të gjithë filtrat
                </button>
              )}
            </div>

            {/* Rrjeta me Scroll */}
            <div className={`overflow-y-auto custom-finance-scroll p-3 sm:p-5 rounded-2xl border border-main bg-surface/50 shadow-inner transition-all duration-300 ${
              isExpanded ? 'max-h-[75vh]' : 'max-h-[55vh]'
            }`}>
              {filteredArticles.length === 0 ? (
                <div className="py-16 text-center flex flex-col items-center justify-center">
                  <div className="w-12 h-12 rounded-2xl bg-canvas border border-main flex items-center justify-center text-text-muted mb-3">
                    <Search size={22} />
                  </div>
                  <p className="text-xs font-bold text-text-primary">
                    Nuk u gjet asnjë nen për kërkimin "{articleSearchQuery}"
                  </p>
                  <p className="text-[11px] text-text-muted mt-1">
                    Provoni të klikoni një nga butonat e shembujve më lart (p.sh. "S'kam para për taksa gjyqi").
                  </p>
                </div>
              ) : (
                <div className={`grid gap-2.5 sm:gap-3 ${
                  isExpanded
                    ? 'grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10'
                    : 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5'
                }`}>
                  {filteredArticles.map((article) => {
                    const cleanArt = article.replace(/\.$/, '').trim();
                    const isPreamble =
                      cleanArt === '0' || cleanArt.toLowerCase().includes('preambula') || cleanArt.toLowerCase().includes('hyrja');
                    const label = isPreamble ? 'Preambula' : article.startsWith('Lënda') ? article : `Neni ${cleanArt}`;

                    return (
                      <button
                        key={article}
                        onClick={() => handleOpenArticle(article)}
                        className="group flex flex-col items-center justify-center p-3.5 bg-canvas hover:bg-primary-start text-text-primary hover:text-white border border-main hover:border-primary-start rounded-xl transition-all text-xs sm:text-sm font-bold hover-lift active:scale-95 cursor-pointer shadow-xs"
                      >
                        <span className="truncate">{label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

          </div>

        </div>
      </div>

      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: data.source || displayHeaderTitle,
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}