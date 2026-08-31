// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - CLEAN & MINIMALIST LAW OVERVIEW WITH STEP HISTORY NAVIGATION

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft, ArrowRight, FileText, AlertCircle, 
  BookOpen, ExternalLink, Search, X,
  Maximize2, Minimize2
} from 'lucide-react';
import { motion } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';

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

  const filteredArticles = useMemo(() => {
    if (!data?.articles) return [];
    if (!articleSearchQuery.trim()) return data.articles;
    const cleanQuery = articleSearchQuery.toLowerCase().trim().replace(/^neni\s*/i, '');
    return data.articles.filter((art) => {
      const cleanArt = art.toLowerCase().replace(/^neni\s*/i, '').trim();
      return cleanArt.includes(cleanQuery) || art.toLowerCase().includes(cleanQuery);
    });
  }, [data?.articles, articleSearchQuery]);

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
        
        {/* Navigimi me dy ikona të pastra (1 Hap Mbrapa / 1 Hap Përpara) */}
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
          
          {/* Header Bar i Pastër */}
          <div className="bg-canvas px-6 sm:px-10 py-6 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-4">
              <div className="flex items-center justify-between gap-3">
                
                {/* Butoni Shiko PDF të Plotë */}
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

                {/* Butoni Vetëm me Ikonë për Zmadhimin e Ekranit */}
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

              {/* Titulli Kryesor i Ligjit */}
              <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-text-primary leading-tight tracking-tight">
                {displayHeaderTitle}
              </h1>

              {/* Numri total i neneve */}
              <div className="flex items-center gap-2 pt-2 border-t border-main/50">
                <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3 py-1 rounded-xl text-xs font-bold font-mono">
                  <FileText size={14} className="text-primary-start" />
                  <span>{data.article_count} Nene Gjithsej</span>
                </div>
              </div>
            </div>
          </div>

          {/* Trupi me Rrjetën e Neneve */}
          <div className="bg-canvas/30 px-4 sm:px-8 py-6 pb-8 flex flex-col">
            
            {/* Shiriti i Kërkimit të Nenit */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mb-4">
              <h2 className="text-xs font-black text-text-muted uppercase tracking-wider flex items-center gap-2">
                <BookOpen size={16} className="text-primary-start" />
                Përmbajtja e Neneve ({filteredArticles.length})
              </h2>

              <div className="relative w-full sm:w-72">
                <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-primary-start pointer-events-none" />
                <input
                  type="text"
                  placeholder="Kërko nenin (p.sh. 390)..."
                  value={articleSearchQuery}
                  onChange={(e) => setArticleSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-8 py-2.5 bg-surface border border-main rounded-xl text-xs font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 transition-all"
                />
                {articleSearchQuery && (
                  <button
                    type="button"
                    onClick={() => setArticleSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary p-0.5"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>

            {/* Rrjeta me Scroll */}
            <div className={`overflow-y-auto custom-finance-scroll p-3 sm:p-5 rounded-2xl border border-main bg-surface/50 shadow-inner transition-all duration-300 ${
              isExpanded ? 'max-h-[75vh]' : 'max-h-[55vh]'
            }`}>
              {filteredArticles.length === 0 ? (
                <div className="py-12 text-center text-xs font-bold text-text-muted">
                  Nuk u gjet asnjë nen për kërkimin "{articleSearchQuery}"
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
                        onClick={() =>
                          navigate(
                            `/laws/article?lawTitle=${encodeURIComponent(displayHeaderTitle)}&articleNumber=${encodeURIComponent(
                              article
                            )}`
                          )
                        }
                        className="flex items-center justify-center gap-2 px-3 py-3.5 bg-canvas hover:bg-primary-start hover:text-white border border-main hover:border-primary-start rounded-xl transition-all text-xs sm:text-sm font-bold text-text-primary hover-lift active:scale-95 cursor-pointer shadow-xs"
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