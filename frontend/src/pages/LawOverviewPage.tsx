// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - LAW OVERVIEW V6.1 (LINTER WARNING CLEANED)

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, FileText, AlertCircle, BookOpen, Search, Hash } from 'lucide-react';
import { motion } from 'framer-motion';

interface LawOverviewData {
  law_title: string;
  source: string;
  article_count: number;
  articles: string[];
}

export default function LawOverviewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [data, setData] = useState<LawOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterTerm, setFilterTerm] = useState('');

  const lawTitle = searchParams.get('lawTitle');

  useEffect(() => {
    if (!lawTitle) {
      setError(t('lawOverview.missingTitle', 'Titulli i ligjit mungon.'));
      setLoading(false);
      return;
    }
    apiService.getLawArticlesByTitle(lawTitle)
      .then(setData)
      .catch((err) => {
        console.error('Law overview fetch error:', err);
        setError(err.message || t('lawOverview.fetchError', 'Dështoi ngarkimi i ligjit.'));
      })
      .finally(() => setLoading(false));
  }, [lawTitle, t]);

  const filteredArticles = useMemo(() => {
    if (!data?.articles) return [];
    if (!filterTerm.trim()) return data.articles;

    const term = filterTerm.toLowerCase().trim();
    return data.articles.filter(article => {
      const cleanArt = article.replace(/\.$/, '').trim();
      const isPreamble = cleanArt === '0' || cleanArt.toLowerCase().includes('preambula') || cleanArt.toLowerCase().includes('hyrja');
      const label = isPreamble ? 'preambula hyrja' : `neni ${cleanArt}`;
      return label.includes(term) || cleanArt.includes(term);
    });
  }, [data?.articles, filterTerm]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 pt-32">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-[2rem] flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-20 h-20 mb-6" />
          <h2 className="text-2xl font-black text-text-primary uppercase tracking-tighter mb-3">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-lg mb-8">{error}</p>
          <button
            onClick={() => navigate('/laws/search')}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm"
          >
            <ArrowLeft size={18} />
            {t('lawOverview.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <motion.div 
        className="w-full min-h-screen pb-16 bg-canvas"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
    >
      <div className="max-w-5xl mx-auto px-6 sm:px-8 pt-28">
        
        {/* Navigation Breadcrumb */}
        <button
          onClick={() => navigate(-1)}
          className="group mb-8 flex items-center gap-3 text-text-muted hover:text-text-primary transition-colors font-bold text-sm uppercase tracking-widest hover-lift"
        >
          <div className="p-2 rounded-lg bg-surface border border-border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          {t('general.back', 'Kthehu Mbrapa')}
        </button>

        {/* Overview Container */}
        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-border-main">
          
          {/* Executive Header */}
          <div className="bg-surface px-8 py-10 sm:px-12 sm:py-12 border-b border-border-main relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
            
            <div className="relative z-10 flex flex-col gap-6">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1.5 rounded-lg">
                        <Scale size={14} />
                        <span className="text-[10px] font-black uppercase tracking-widest">
                        {t('lawOverview.lawTitle', 'KODI LIGJOR')}
                        </span>
                    </div>
                </div>
                
                <h1 className="text-3xl sm:text-5xl font-black text-text-primary leading-tight tracking-tighter">
                {data.law_title}
                </h1>
                
                <div className="flex flex-wrap items-center gap-4 border-t border-border-main/50 pt-6 mt-2">
                    <div className="flex items-center gap-2 bg-canvas text-text-secondary border border-border-main px-4 py-2 rounded-xl">
                        <Calendar size={16} className="text-primary-start" />
                        <span className="text-[11px] font-black uppercase tracking-widest truncate max-w-[200px]">
                        {t('lawOverview.source', 'Burimi')}: {data.source}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 bg-canvas text-text-secondary border border-border-main px-4 py-2 rounded-xl">
                        <FileText size={16} className="text-primary-start" />
                        <span className="text-[11px] font-black uppercase tracking-widest truncate">
                        {data.article_count} {t('lawOverview.articles', 'Nene Gjithsej')}
                        </span>
                    </div>
                </div>
            </div>
          </div>

          {/* Table of Contents Grid & Filter Bar */}
          <div className="bg-canvas/30 px-8 sm:px-12 py-10 shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
              <h2 className="text-[11px] font-black text-text-muted uppercase tracking-widest flex items-center gap-2">
                  <BookOpen size={16} className="text-primary-start" />
                  {t('lawOverview.tableOfContents', 'Përmbajtja e Ligjit (Nenet)')}
              </h2>

              {/* Real-time Filter Input */}
              <div className="relative w-full sm:w-64 h-10">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  placeholder="Filtro nenin..."
                  value={filterTerm}
                  onChange={(e) => setFilterTerm(e.target.value)}
                  className="w-full h-10 pl-9 pr-3 bg-surface border border-border-main rounded-xl text-xs font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-1 focus:ring-primary-start focus:outline-none transition-all"
                />
              </div>
            </div>
            
            {filteredArticles.length === 0 ? (
              <div className="text-center py-12 text-text-muted italic text-xs font-semibold">
                Nuk u gjet asnjë nen për këtë kërkim.
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {filteredArticles.map((article) => {
                  const cleanArt = article.replace(/\.$/, '').trim();
                  const isPreamble = cleanArt === '0' || cleanArt.toLowerCase() === 'preambula' || cleanArt.toLowerCase() === 'hyrja';
                  const label = isPreamble ? 'Preambula' : `Neni ${cleanArt}`;

                  return (
                    <button
                      key={article}
                      onClick={() => navigate(`/laws/article?lawTitle=${encodeURIComponent(data.law_title)}&articleNumber=${encodeURIComponent(article)}`)}
                      className="flex items-center justify-center gap-2 px-4 py-4 bg-surface border border-border-main rounded-xl transition-all text-sm font-black text-text-primary hover:text-primary-start hover:border-primary-start hover:shadow-sm hover-lift"
                    >
                      <Hash size={12} className="text-primary-start/50 shrink-0" />
                      <span>{label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="bg-surface px-8 sm:px-12 py-6 flex justify-between items-center border-t border-border-main">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-[11px] font-black uppercase tracking-widest text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift"
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