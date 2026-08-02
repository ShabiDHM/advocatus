// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - LAW OVERVIEW V15.0 (MINIMALIST X CLOSE BUTTON & CLEAN HEADER)

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, FileText, AlertCircle, BookOpen, GraduationCap, X } from 'lucide-react';
import { motion } from 'framer-motion';

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

  const lawTitle = searchParams.get('lawTitle') || '';

  const isMobile = typeof window !== 'undefined' && (/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || window.innerWidth < 768);

  useEffect(() => {
    if (!lawTitle) {
      setError(t('lawOverview.missingTitle', 'Titulli i ligjit mungon.'));
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');

    apiService.getLawArticlesByTitle(lawTitle)
      .then((res: any) => {
        setData(res);
      })
      .catch((err) => {
        console.error('Law overview fetch error:', err);
        setError(err.message || t('lawOverview.fetchError', 'Dështoi ngarkimi i ligjit.'));
      })
      .finally(() => setLoading(false));
  }, [lawTitle, t]);

  const isAcademicDoc = useMemo(() => {
    const raw = (data?.law_title || data?.source || lawTitle).toString().toUpperCase();
    return raw.includes("AKADEMIA") || raw.includes("CASE_LAW") || raw.includes("DORACAK") || raw.includes("UDHEZUES") || raw.includes("LËNDËSH") || raw.includes("LENDESH");
  }, [data?.law_title, data?.source, lawTitle]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-16 h-16 mb-4" />
          <h2 className="text-xl font-black text-text-primary uppercase tracking-tight mb-2">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-sm mb-6">{error}</p>
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

  if (!data) return null;

  const displayHeaderTitle = lawTitle || data.law_title;
  const pdfStreamUrl = `${API_V1_URL}/laws/pdf/${encodeURIComponent(data.source || `${lawTitle}.pdf`)}`;

  // DIRECT EXPANDED B2 PDF STREAM FOR ACADEMY DOCUMENTS
  if (isAcademicDoc) {
    return (
      <motion.div 
          className="w-full min-h-screen pb-6 bg-canvas text-text-primary"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
      >
        <div className="max-w-[98vw] w-full mx-auto px-2 sm:px-4 pt-20 sm:pt-22">
          
          <div className="glass-panel p-4 sm:p-5 rounded-3xl border border-main bg-surface shadow-2xl flex flex-col gap-4">
            
            {/* Header with Minimalist X Close Button */}
            <div className="flex items-center justify-between border-b border-main pb-3 gap-3">
              <div className="flex items-center gap-3.5 min-w-0">
                <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20 shrink-0">
                  <GraduationCap size={22} />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-black text-primary-start uppercase tracking-wider block mb-0.5">
                    AKADEMIA E DREJTËSISË & UNODC
                  </span>
                  <h1 className="text-base sm:text-lg font-black text-text-primary leading-tight truncate">
                    {displayHeaderTitle}
                  </h1>
                </div>
              </div>

              {/* Single Minimalist X Close Button */}
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="p-2.5 bg-canvas border border-main hover:bg-hover text-text-muted hover:text-danger-start rounded-2xl transition-all focus:outline-none cursor-pointer shrink-0 shadow-sm"
                title="Mbyll"
              >
                <X size={20} />
              </button>
            </div>

            {/* Mobile vs Desktop View */}
            {isMobile ? (
              <div className="flex flex-col items-center justify-center p-8 bg-canvas rounded-2xl text-center border border-main">
                <div className="w-16 h-16 rounded-2xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center mb-4">
                  <FileText size={32} className="text-primary-start" />
                </div>
                <h3 className="text-base font-bold text-text-primary mb-2 max-w-sm truncate">
                  {displayHeaderTitle}
                </h3>
                <p className="text-xs text-text-muted mb-6 max-w-xs leading-relaxed">
                  Përvojë optimale leximi në celular. Klikoni më poshtë për ta hapur direkt.
                </p>
                <a
                  href={pdfStreamUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-wider shadow-lg w-full max-w-xs"
                >
                  Hap PDF në Shfletues
                </a>
              </div>
            ) : (
              <div className="w-full h-[88vh] rounded-2xl overflow-hidden border border-main bg-slate-900 shadow-2xl relative">
                <iframe
                  src={pdfStreamUrl}
                  title={displayHeaderTitle}
                  className="w-full h-full border-none"
                />
              </div>
            )}

          </div>
        </div>
      </motion.div>
    );
  }

  // STANDARD STATUTORY OVERVIEW
  return (
    <motion.div 
        className="w-full min-h-screen pb-16 bg-canvas text-text-primary"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        
        <button
          onClick={() => navigate(-1)}
          className="group mb-6 flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift cursor-pointer"
        >
          <div className="p-2 rounded-xl bg-surface border border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          <span>{t('general.back', 'Kthehu Mbrapa')}</span>
        </button>

        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface">
          
          <div className="bg-canvas px-6 sm:px-10 py-8 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-5">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
                        <Scale size={14} />
                        <span className="text-[10px] font-black uppercase tracking-wider">
                          KODI LIGJOR ZYRTAR
                        </span>
                    </div>
                </div>
                
                <h1 className="text-2xl sm:text-4xl font-black text-text-primary leading-tight tracking-tight">
                  {displayHeaderTitle}
                </h1>
                
                <div className="flex flex-wrap items-center gap-3 border-t border-main/50 pt-5 mt-1">
                    <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3.5 py-1.5 rounded-xl">
                        <Calendar size={15} className="text-primary-start" />
                        <span className="text-xs font-bold uppercase tracking-wider truncate max-w-[250px]">
                        {t('lawOverview.source', 'Burimi')}: {data.source}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3.5 py-1.5 rounded-xl">
                        <FileText size={15} className="text-primary-start" />
                        <span className="text-xs font-bold uppercase tracking-wider truncate">
                        {data.article_count} {t('lawOverview.articles', 'Nene Gjithsej')}
                        </span>
                    </div>
                </div>
            </div>
          </div>

          <div className="bg-canvas/40 px-6 sm:px-10 py-8">
            <div className="mb-6">
              <h2 className="text-xs font-black text-text-muted uppercase tracking-wider flex items-center gap-2">
                <BookOpen size={16} className="text-primary-start" />
                {t('lawOverview.tableOfContents', 'Përmbajtja e Ligjit (Nenet)')}
              </h2>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {data.articles.map((article) => {
                const cleanArt = article.replace(/\.$/, '').trim();
                const isPreamble = cleanArt === '0' || cleanArt.toLowerCase().includes('preambula') || cleanArt.toLowerCase().includes('hyrja');
                const label = isPreamble ? 'Preambula' : `Neni ${cleanArt}`;

                return (
                  <button
                    key={article}
                    onClick={() => navigate(`/laws/article?lawTitle=${encodeURIComponent(displayHeaderTitle)}&articleNumber=${encodeURIComponent(article)}`)}
                    className="flex items-center justify-center gap-2 px-3.5 py-3.5 bg-surface border border-main rounded-xl transition-all text-xs sm:text-sm font-bold text-text-primary hover:text-primary-start hover:border-primary-start hover-lift active:scale-95 cursor-pointer shadow-xs"
                  >
                    <span>{label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="bg-surface px-6 sm:px-10 py-5 flex justify-between items-center border-t border-main">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift cursor-pointer"
            >
              <ArrowLeft size={14} />
              {t('lawOverview.backToSearch', 'Kthehu te kërkimi')}
            </button>
          </div>

        </div>
      </div>
    </motion.div>
  );
}