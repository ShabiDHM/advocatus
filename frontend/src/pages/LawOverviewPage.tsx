// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - LAW OVERVIEW V11.0 (CLEAN ACADEMY CASE LABELS & ZERO 'NENI PJESA' ARTIFACTS)

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, FileText, AlertCircle, BookOpen, Search, Hash, ShieldAlert, GraduationCap } from 'lucide-react';
import { motion } from 'framer-motion';

interface LawOverviewData {
  law_title: string;
  source: string;
  article_count: number;
  articles: string[];
  is_official_statute?: boolean;
}

function formatArticleLabel(rawArticle: string, isAcademic: boolean): string {
  const cleanArt = rawArticle.replace(/\.$/, '').trim();
  const lower = cleanArt.toLowerCase();
  
  if (lower === '0' || lower.includes('preambula') || lower.includes('hyrja')) {
    return 'Hyrje & Metodologjia';
  }

  if (isAcademic) {
    if (cleanArt.toLowerCase().startsWith('lënda') || cleanArt.toLowerCase().startsWith('lenda')) return cleanArt;
    if (cleanArt.toLowerCase().startsWith('pjesa')) return cleanArt;
    if (cleanArt.toLowerCase().startsWith('kreu')) return cleanArt;
    if (cleanArt.toLowerCase().includes('statistik')) return 'Të Dhëna Statistikore';
    if (cleanArt.toLowerCase().includes('konkluzion')) return 'Konkluzione';
    return cleanArt;
  }

  return `Neni ${cleanArt}`;
}

export default function LawOverviewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [data, setData] = useState<LawOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterTerm, setFilterTerm] = useState('');

  const lawTitle = searchParams.get('lawTitle') || '';

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

  const isTitleMismatch = useMemo(() => {
    if (!data?.law_title || !lawTitle) return false;
    if (isAcademicDoc) return false;
    
    const reqClean = lawTitle.toLowerCase().replace(/[^a-z0-9]/g, '');
    const fetchedClean = data.law_title.toLowerCase().replace(/[^a-z0-9]/g, '');
    
    const reqNum = lawTitle.match(/\d+[\/\-L\s]+\d+/i);
    const fetchNum = data.law_title.match(/\d+[\/\-L\s]+\d+/i);

    if (reqNum && fetchNum) {
      return reqNum[0].replace(/[^0-9]/g, '') !== fetchNum[0].replace(/[^0-9]/g, '');
    }
    return !fetchedClean.includes(reqClean) && !reqClean.includes(fetchedClean);
  }, [data?.law_title, lawTitle, isAcademicDoc]);

  const filteredArticles = useMemo(() => {
    if (!data?.articles) return [];
    if (!filterTerm.trim()) return data.articles;

    const term = filterTerm.toLowerCase().trim();
    return data.articles.filter(article => {
      const formatted = formatArticleLabel(article, isAcademicDoc).toLowerCase();
      return formatted.includes(term) || article.toLowerCase().includes(term);
    });
  }, [data?.articles, filterTerm, isAcademicDoc]);

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

  const displayHeaderTitle = isAcademicDoc 
    ? "PËRMBLEDHJE LËNDËSH TË PËRZGJEDHURA NGA PRAKTIKA GJYQËSORE (AKADEMIA E DREJTËSISË)" 
    : (lawTitle || data.law_title);

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

        {isTitleMismatch && (
          <div className="mb-6 p-5 bg-rose-500/10 border-2 border-rose-500/40 rounded-2xl flex items-start gap-4 shadow-md text-rose-600 dark:text-rose-400">
            <ShieldAlert size={28} className="shrink-0 mt-0.5 text-rose-500" />
            <div className="flex flex-col gap-1">
              <h4 className="text-sm font-black uppercase tracking-wider text-rose-600 dark:text-rose-400">
                Kujdes: Mospërputhje e të dhënave të ligjit
              </h4>
              <p className="text-xs sm:text-sm font-medium leading-relaxed text-text-primary">
                Keni kërkuar <strong className="underline">{lawTitle}</strong>, por baza e të dhënave ka kthyer përmbajtjen e <strong className="underline">{data.law_title}</strong>. Ju lutemi provoni përsëri nga biblioteka ligjore.
              </p>
            </div>
          </div>
        )}

        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface">
          
          <div className="bg-canvas px-6 sm:px-10 py-8 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-5">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
                        {isAcademicDoc ? <GraduationCap size={14} /> : <Scale size={14} />}
                        <span className="text-[10px] font-black uppercase tracking-wider">
                        {isAcademicDoc ? 'AKADEMIA E DREJTËSISË & UNODC — 25 LËNDË TË PRAKTIKËS GJYQËSORE' : t('lawOverview.lawTitle', 'KODI LIGJOR')}
                        </span>
                    </div>
                </div>
                
                <h1 className="text-2xl sm:text-3xl font-black text-text-primary leading-tight tracking-tight">
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
                        {data.article_count} {isAcademicDoc ? 'Lëndë & Seksione' : t('lawOverview.articles', 'Nene Gjithsej')}
                        </span>
                    </div>
                </div>
            </div>
          </div>

          <div className="bg-canvas/40 px-6 sm:px-10 py-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
              <h2 className="text-xs font-black text-text-muted uppercase tracking-wider flex items-center gap-2">
                  <BookOpen size={16} className="text-primary-start" />
                  {isAcademicDoc ? '25 Lëndët dhe Seksionet e Praktikës Gjyqësore' : t('lawOverview.tableOfContents', 'Përmbajtja e Ligjit (Nenet)')}
              </h2>

              <div className="relative w-full sm:w-64 h-10">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  placeholder={isAcademicDoc ? "Filtro lëndën..." : "Filtro nenin..."}
                  value={filterTerm}
                  onChange={(e) => setFilterTerm(e.target.value)}
                  className="w-full h-10 pl-9 pr-3 bg-surface border border-main rounded-xl text-xs font-semibold text-text-primary placeholder:text-text-muted focus:border-primary-start focus:ring-1 focus:ring-primary-start focus:outline-none transition-all"
                />
              </div>
            </div>
            
            {filteredArticles.length === 0 ? (
              <div className="text-center py-12 text-text-muted italic text-xs font-semibold">
                Nuk u gjet asnjë nen apo lëndë për këtë kërkim.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {filteredArticles.map((article) => {
                  const label = formatArticleLabel(article, isAcademicDoc);
                  const targetLawTitle = displayHeaderTitle;

                  return (
                    <button
                      key={article}
                      onClick={() => navigate(`/laws/article?lawTitle=${encodeURIComponent(targetLawTitle)}&articleNumber=${encodeURIComponent(article)}`)}
                      className="flex items-center justify-start gap-3 px-4 py-3.5 bg-surface border border-main rounded-xl transition-all text-xs sm:text-sm font-bold text-text-primary hover:text-primary-start hover:border-primary-start hover:shadow-sm hover-lift active:scale-95 cursor-pointer text-left"
                    >
                      {isAcademicDoc ? <GraduationCap size={16} className="text-primary-start/80 shrink-0" /> : <Hash size={14} className="text-primary-start/50 shrink-0" />}
                      <span className="truncate">{label}</span>
                    </button>
                  );
                })}
              </div>
            )}
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