// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - LAW OVERVIEW V28.0 (PINNED COMPACT LAYOUT WITH INTERNAL SCROLL & INSTANT ARTICLE SEARCH)

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, FileText, AlertCircle, BookOpen, GraduationCap, ExternalLink, Search, X } from 'lucide-react';
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
  
  const [showPdfModal, setShowPdfModal] = useState(false);

  const lawTitle = searchParams.get('lawTitle') || '';

  const isAcademicDoc = useMemo(() => {
    if (!data) return false;
    const raw = (data.law_title || data.source || lawTitle).toUpperCase();
    return (
      raw.includes('AKADEMIA') ||
      raw.includes('CASE_LAW') ||
      raw.includes('DORACAK') ||
      raw.includes('UDHEZUES') ||
      raw.includes('LËNDËSH') ||
      data.is_official_statute === false
    );
  }, [data, lawTitle]);

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
            onClick={() => navigate('/laws/search')}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer"
          >
            <ArrowLeft size={16} />
            {t('lawOverview.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="w-full min-h-screen pb-12 bg-canvas text-text-primary"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-24">
        
        {/* Butoni Kthehu */}
        <button
          onClick={() => navigate('/laws/search')}
          className="group mb-5 flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift cursor-pointer"
        >
          <div className="p-2 rounded-xl bg-surface border border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          <span>{t('general.back', 'Kthehu te Biblioteka')}</span>
        </button>

        {/* Paneli Kryesor Kompakt */}
        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface">
          
          {/* Header Bar */}
          <div className="bg-canvas px-6 sm:px-10 py-6 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
                  {isAcademicDoc ? <GraduationCap size={14} /> : <Scale size={14} />}
                  <span className="text-[10px] font-black uppercase tracking-wider">
                    {isAcademicDoc ? 'UDHËZUES I AKADEMISË SË DREJTËSISË' : 'KODI LIGJOR ZYRTAR'}
                  </span>
                </div>

                {pdfUrl && (
                  <button
                    type="button"
                    onClick={() => setShowPdfModal(true)}
                    className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all hover-lift cursor-pointer"
                  >
                    <FileText size={14} />
                    <span>Shiko PDF të Plotë</span>
                    <ExternalLink size={12} />
                  </button>
                )}
              </div>

              <h1 className="text-xl sm:text-3xl font-black text-text-primary leading-tight tracking-tight">
                {displayHeaderTitle}
              </h1>

              <div className="flex flex-wrap items-center gap-3 border-t border-main/50 pt-4">
                <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3 py-1 rounded-xl text-xs font-bold font-mono">
                  <Calendar size={14} className="text-primary-start" />
                  <span className="truncate max-w-[250px]">{data.source}</span>
                </div>
                <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3 py-1 rounded-xl text-xs font-bold font-mono">
                  <FileText size={14} className="text-primary-start" />
                  <span>{data.article_count} Nene Gjithsej</span>
                </div>
              </div>
            </div>
          </div>

          {/* Trupi me Kërkim dhe Scroll të Brendshëm */}
          <div className="bg-canvas/30 px-6 sm:px-10 py-6 flex flex-col">
            
            {/* Shiriti i Kërkimit të Shpejtë të Nenit */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mb-5">
              <h2 className="text-xs font-black text-text-muted uppercase tracking-wider flex items-center gap-2">
                <BookOpen size={16} className="text-primary-start" />
                Përmbajtja e Neneve ({filteredArticles.length})
              </h2>

              <div className="relative w-full sm:w-64">
                <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-primary-start pointer-events-none" />
                <input
                  type="text"
                  placeholder="Kërko nenin (p.sh. 390)..."
                  value={articleSearchQuery}
                  onChange={(e) => setArticleSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-8 py-2 bg-surface border border-main rounded-xl text-xs font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 transition-all"
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

            {/* KUTIA ME SCROLL TË BRENDSHËM (ZERO PAGE STRETCHING) */}
            <div className="max-h-[55vh] overflow-y-auto custom-finance-scroll p-3 sm:p-4 rounded-2xl border border-main bg-surface/50 shadow-inner">
              {filteredArticles.length === 0 ? (
                <div className="py-12 text-center text-xs font-bold text-text-muted">
                  Nuk u gjet asnjë nen për kërkimin "{articleSearchQuery}"
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2.5">
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
                        className="flex items-center justify-center gap-2 px-3 py-3 bg-canvas hover:bg-primary-start hover:text-white border border-main hover:border-primary-start rounded-xl transition-all text-xs font-bold text-text-primary hover-lift active:scale-95 cursor-pointer shadow-xs"
                      >
                        <span className="truncate">{label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

          </div>

          {/* Footer Bar */}
          <div className="bg-surface px-6 sm:px-10 py-4 flex justify-between items-center border-t border-main">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift cursor-pointer"
            >
              <ArrowLeft size={14} />
              {t('lawOverview.backToSearch', 'Kthehu te Biblioteka')}
            </button>
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