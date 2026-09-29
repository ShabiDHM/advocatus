// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - LAW OVERVIEW V64.0.1
//
// V64.0.1: FIX TS6133 — hequr `AnimatePresence` (i papërdorur).
//
// V64.0: FIX repeals + prioritet kanonik + AbortController.
//   - O1: Shtuar RepealedWarning (is_repealed + warning)
//   - O2: LawOverviewData importohet nga lawLibraryTypes (jo inline)
//   - O5: HEQUR navigate(1) — dead button
//   - O6: Prioritet `data.law_title` (kanonik) mbi URL param
//   - O7: Kalon `data.law_title` (kanonik) në /laws/article
//   - O8: Shtuar AbortController në useEffect
//   - O13: Debounce në search (200ms)
//   - O19: Përdor lawService (jo apiService direkt)
//
// V63.0: Versioni i vjetër.

import { useEffect, useState, useMemo, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { API_V1_URL } from '../services/api';
import { lawService } from '../services/lawService';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft, FileText, AlertCircle,
  BookOpen, ExternalLink, Search, X,
  Maximize2, Minimize2, Sparkles,
} from 'lucide-react';
import { motion } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';
import { RepealedWarning } from '../components/law/RepealedWarning';
import { performSemanticSearch } from '../utils/legalSemanticEngine';
import type { LawOverviewData } from '../components/law/lawLibraryTypes';

// ═══════════════════════════════════════════════════════════════════════════
// DEBOUNCE HOOK
// ═══════════════════════════════════════════════════════════════════════════

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState<T>(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export default function LawOverviewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [data, setData] = useState<LawOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [articleSearchQuery, setArticleSearchQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [showPdfModal, setShowPdfModal] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const lawTitleFromUrl = searchParams.get('lawTitle') || '';

  // ═══════════════════════════════════════════════════════════════════════
  // FETCH DATA
  // ═══════════════════════════════════════════════════════════════════════

  useEffect(() => {
    if (!lawTitleFromUrl) {
      setError(t('lawOverview.missingTitle', 'Titulli i ligjit mungon.'));
      setLoading(false);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError('');

    lawService
      .getLawArticlesByTitle(lawTitleFromUrl, controller.signal)
      .then((res) => {
        if (controller.signal.aborted) return;
        setData(res);
      })
      .catch((err: any) => {
        if (err?.name === 'CanceledError' || err?.name === 'AbortError') return;
        console.error('[LawOverviewPage] Fetch error:', err);
        if (!controller.signal.aborted) {
          setError(
            err?.response?.data?.detail ||
            err?.message ||
            t('lawOverview.fetchError', 'Dështoi ngarkimi i ligjit.'),
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [lawTitleFromUrl, t]);

  // ═══════════════════════════════════════════════════════════════════════
  // PRIORITET KANONIK
  // ═══════════════════════════════════════════════════════════════════════

  // V64: `data.law_title` (kanonik nga DB) preferohet mbi URL param
  const displayHeaderTitle = data?.law_title || lawTitleFromUrl;

  // ═══════════════════════════════════════════════════════════════════════
  // SEARCH (me debounce)
  // ═══════════════════════════════════════════════════════════════════════

  const debouncedQuery = useDebounced(articleSearchQuery, 200);

  const searchResults = useMemo(() => {
    if (!data?.articles) {
      return { filteredArticles: [], matchedIntent: null, highlightWords: [] };
    }
    return performSemanticSearch(data.articles, debouncedQuery);
  }, [data?.articles, debouncedQuery]);

  const { filteredArticles, highlightWords } = searchResults;

  // ═══════════════════════════════════════════════════════════════════════
  // PDF URL
  // ═══════════════════════════════════════════════════════════════════════

  const pdfUrl = useMemo(() => {
    if (!data?.source) return null;
    const encoded = encodeURIComponent(data.source);
    return `${API_V1_URL}/laws/pdf/${encoded}`;
  }, [data?.source]);

  // ═══════════════════════════════════════════════════════════════════════
  // OPEN ARTICLE
  // ═══════════════════════════════════════════════════════════════════════

  const handleOpenArticle = (article: string) => {
    const cleanArt = article.replace(/^neni\s*/i, '').replace(/\.$/, '').trim();
    const highlightParam = highlightWords.length > 0
      ? `&highlight=${encodeURIComponent(highlightWords.join(' '))}`
      : '';
    // V64: përdor `data.law_title` (kanonik) — jo URL
    navigate(
      `/laws/article?lawTitle=${encodeURIComponent(displayHeaderTitle)}` +
      `&articleNumber=${encodeURIComponent(cleanArt)}${highlightParam}`,
    );
  };

  // ═══════════════════════════════════════════════════════════════════════
  // LOADING
  // ═══════════════════════════════════════════════════════════════════════

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">
          {t('general.loading', 'Duke ngarkuar...')}
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-16 h-16 mb-4" />
          <h2 className="text-xl font-black text-text-primary uppercase tracking-tight mb-2">
            {t('general.error', 'Gabim')}
          </h2>
          <p className="text-text-secondary text-sm mb-6">
            {error || 'Të dhënat nuk u gjetën.'}
          </p>
          <button
            onClick={() => navigate(-1)}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span>{t('general.back', 'Kthehu mbrapa')}</span>
          </button>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════

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

        <div className="flex items-center gap-2 mb-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="p-2.5 rounded-xl bg-surface border border-main hover:border-primary-start/60 text-text-primary hover:text-primary-start transition-all hover-lift cursor-pointer shadow-sm"
            title={t('general.back', 'Kthehu')}
          >
            <ArrowLeft size={16} />
          </button>
        </div>

        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface transition-all duration-300">
          <div className="bg-canvas px-5 sm:px-8 lg:px-10 py-5 sm:py-6 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-3 sm:gap-4">
              <div className="flex items-center justify-between gap-3">
                {pdfUrl ? (
                  <button
                    type="button"
                    onClick={() => setShowPdfModal(true)}
                    className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all hover-lift cursor-pointer shadow-sm"
                    title={t('lawOverview.openPdf', 'Hap dokumentin zyrtar PDF')}
                  >
                    <FileText size={14} />
                    <span>{t('lawOverview.viewFullPdf', 'Shiko PDF të Plotë')}</span>
                    <ExternalLink size={12} />
                  </button>
                ) : (
                  <div />
                )}

                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-2.5 bg-surface hover:bg-hover text-text-primary border border-main rounded-xl transition-all hover-lift cursor-pointer shadow-sm"
                  title={isExpanded
                    ? t('lawOverview.minimize', 'Zvogëlo pamjen')
                    : t('lawOverview.maximize', 'Zmadho në ekran të plotë')}
                >
                  {isExpanded ? (
                    <Minimize2 size={16} className="text-primary-start" />
                  ) : (
                    <Maximize2 size={16} className="text-primary-start" />
                  )}
                </button>
              </div>

              <h1 className="text-lg sm:text-2xl md:text-3xl font-black text-text-primary leading-tight tracking-tight">
                {displayHeaderTitle}
              </h1>

              <div className="flex items-center gap-2 pt-2 border-t border-main/50">
                <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3 py-1 rounded-xl text-xs font-bold font-mono">
                  <FileText size={14} className="text-primary-start" />
                  <span>
                    {data.article_count} {t('lawOverview.totalArticles', 'Nene Gjithsej')}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* V64: Repealed warning */}
          {data.is_repealed && (
            <div className="px-5 sm:px-8 lg:px-10 pt-4">
              <RepealedWarning info={data.repealed_info} warning={data.warning} />
            </div>
          )}

          <div className="bg-surface px-4 sm:px-8 py-4 sm:py-5 border-b border-main flex flex-col gap-3">
            <div className="relative w-full">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-primary-start flex items-center pointer-events-none">
                <Search size={18} />
              </div>

              <input
                type="text"
                placeholder={t('lawOverview.searchPlaceholder', 'Kërko nene sipas fjalëve kyçe, temës apo numrit të nenit...')}
                value={articleSearchQuery}
                onChange={(e) => setArticleSearchQuery(e.target.value)}
                className="w-full pl-11 sm:pl-12 pr-10 py-3 sm:py-3.5 bg-canvas border border-main rounded-2xl text-xs sm:text-sm font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all shadow-inner"
              />

              {articleSearchQuery && (
                <button
                  type="button"
                  onClick={() => setArticleSearchQuery('')}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-danger-start p-1 cursor-pointer transition-colors"
                  title={t('lawOverview.clearSearch', 'Pastro kërkimin')}
                >
                  <X size={16} />
                </button>
              )}
            </div>

            {/* V64: nëse query është e gjatë, trego hint për AI search */}
            {articleSearchQuery.trim().length > 4 && filteredArticles.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-primary-start/10 border border-primary-start/30 rounded-2xl p-4 flex items-start gap-3 text-xs shadow-xs mt-1"
              >
                <div className="p-2 bg-primary-start text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                  <Sparkles size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-text-primary text-xs sm:text-sm mb-1">
                    {t('lawOverview.tryAiSearch', 'Provo kërkimin semantik me AI')}
                  </p>
                  <p className="text-text-secondary leading-relaxed text-[11px]">
                    {t('lawOverview.aiSearchHint', 'Ky filtër lokal kërkon vetëm numra nenesh. Për kërkim semantik (p.sh. "marrja e deklaratës së fëmijës") përdorni /laws/search me "Kërko me AI".')}
                  </p>
                </div>
              </motion.div>
            )}
          </div>

          <div className="bg-canvas/30 px-4 sm:px-8 py-5 sm:py-6 pb-8 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-black text-text-muted uppercase tracking-wider flex items-center gap-2">
                <BookOpen size={16} className="text-primary-start" />
                {t('lawOverview.articleList', 'Përmbajtja e Neneve')} ({filteredArticles.length})
              </h2>

              {articleSearchQuery && (
                <button
                  type="button"
                  onClick={() => setArticleSearchQuery('')}
                  className="text-xs font-bold text-primary-start hover:underline cursor-pointer"
                >
                  {t('lawOverview.clearSearch', 'Pastro kërkimin')}
                </button>
              )}
            </div>

            <div className={`overflow-y-auto custom-finance-scroll p-3 sm:p-5 rounded-2xl border border-main bg-surface/50 shadow-inner transition-all duration-300 ${
              isExpanded ? 'max-h-[75vh]' : 'max-h-[55vh]'
            }`}>
              {filteredArticles.length === 0 ? (
                <div className="py-16 text-center flex flex-col items-center justify-center">
                  <div className="w-12 h-12 rounded-2xl bg-canvas border border-main flex items-center justify-center text-text-muted mb-3">
                    <Search size={22} />
                  </div>
                  <p className="text-xs font-bold text-text-primary">
                    {t('lawOverview.noArticlesFound', 'Nuk u gjet asnjë nen për kërkimin')} "{articleSearchQuery}"
                  </p>
                  <p className="text-[11px] text-text-muted mt-1">
                    {t('lawOverview.noArticlesHint', 'Provoni fjalë kyçe të tjera ose numrin specifik të nenit.')}
                  </p>
                </div>
              ) : (
                <div className={`grid gap-2 sm:gap-2.5 md:gap-3 ${
                  isExpanded
                    ? 'grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10'
                    : 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5'
                }`}>
                  {filteredArticles.map((article) => {
                    const cleanArt = article.replace(/^neni\s*/i, '').replace(/\.$/, '').trim();
                    const isPreamble =
                      cleanArt === '0' ||
                      cleanArt.toLowerCase().includes('preambula') ||
                      cleanArt.toLowerCase().includes('hyrja');
                    const label = isPreamble
                      ? t('lawArticle.preamble', 'Preambula')
                      : article.startsWith('Lënda')
                        ? article
                        : `${t('lawArticle.article', 'Neni')} ${cleanArt}`;

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