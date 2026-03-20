// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE V5.0 (EXECUTIVE READING SURFACE)
// 1. FIXED: Removed 'text-white' and 'prose-invert' for perfect Light/Dark visibility.
// 2. ENHANCED: Article body now uses 'bg-paper' (Warm Ivory/Deep Midnight) for optimal legal reading.
// 3. FIXED: Header uses high-fidelity 'bg-surface' and 'border-border-main' architecture.
// 4. RETAINED: 100% of fetching, parsing, and error-handling logic.

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, AlertCircle, BookOpen } from 'lucide-react';
import { motion } from 'framer-motion';

interface ArticleData {
  law_title: string;
  article_number: string;
  source: string;
  text: string;
}

export default function LawArticlePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [article, setArticle] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const lawTitle = searchParams.get('lawTitle');
  const articleNumber = searchParams.get('articleNumber');

  useEffect(() => {
    if (!lawTitle || !articleNumber) {
      setError(t('lawArticle.missingParams', 'Parametrat e artikullit mungojnë.'));
      setLoading(false);
      return;
    }
    apiService.getLawArticle(lawTitle, articleNumber)
      .then(setArticle)
      .catch((err) => {
        console.error('Article fetch error:', err);
        setError(err.message || t('lawArticle.fetchError', 'Dështoi ngarkimi i artikullit.'));
      })
      .finally(() => setLoading(false));
  }, [lawTitle, articleNumber, t]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-accent-glow"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 pt-32">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-[2rem] flex flex-col items-center text-center shadow-lg shadow-danger-start/10">
          <AlertCircle className="text-danger-start w-20 h-20 mb-6" />
          <h2 className="text-2xl font-black text-text-primary uppercase tracking-tighter mb-3">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-lg mb-8">{error}</p>
          <button
            onClick={() => navigate('/laws/search')}
            className="btn-primary flex items-center gap-2"
          >
            <ArrowLeft size={18} />
            {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  if (!article) return null;

  // Split text into paragraphs (double newline separated)
  const paragraphs = article.text.split('\n\n').filter(p => p.trim() !== '');

  return (
    <motion.div 
        className="w-full min-h-screen pb-16"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
    >
      <div className="max-w-4xl mx-auto px-6 sm:px-8 pt-28">
        
        {/* Navigation Breadcrumb */}
        <button
          onClick={() => navigate(-1)}
          className="group mb-8 flex items-center gap-3 text-text-muted hover:text-text-primary transition-colors font-bold text-sm uppercase tracking-widest"
        >
          <div className="p-2 rounded-lg bg-surface border border-border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          {t('general.back', 'Kthehu Mbrapa')}
        </button>

        {/* Article Container */}
        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-lawyer-dark border-border-main">
          
          {/* Executive Header */}
          <div className="bg-surface px-8 py-10 border-b border-border-main relative overflow-hidden">
            {/* Decorative background accent */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
            
            <div className="relative z-10 flex flex-col gap-6">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1.5 rounded-lg">
                        <BookOpen size={14} />
                        <span className="text-[10px] font-black uppercase tracking-widest">
                        {t('lawArticle.lawTitle', 'LIGJI')}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 bg-surface-secondary text-text-secondary border border-border-main px-3 py-1.5 rounded-lg">
                        <Calendar size={14} />
                        <span className="text-[10px] font-bold uppercase tracking-widest truncate max-w-[200px]">
                        {article.source}
                        </span>
                    </div>
                </div>
                
                <h1 className="text-3xl sm:text-4xl font-black text-text-primary leading-tight tracking-tighter">
                {article.law_title}
                </h1>
                
                <div className="flex items-center gap-4 border-t border-border-main/50 pt-6 mt-2">
                    <Scale size={24} className="text-primary-start" />
                    <p className="text-xl text-primary-start font-black uppercase tracking-widest">
                        {t('lawArticle.article', 'Neni')} {article.article_number}
                    </p>
                </div>
            </div>
          </div>

          {/* The Paper Reading Surface */}
          <div className="bg-paper px-8 sm:px-12 py-12 shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
            <div className="max-w-[75ch] mx-auto">
                {paragraphs.map((para, idx) => (
                <p 
                    key={idx} 
                    className="mb-6 text-[17px] text-text-primary leading-relaxed font-serif first-letter:text-4xl first-letter:font-black first-letter:text-primary-start first-letter:mr-1 first-letter:float-left"
                >
                    {para}
                </p>
                ))}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="bg-surface px-8 py-6 flex justify-between items-center border-t border-border-main">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-primary-start transition-colors flex items-center gap-2"
            >
              <ArrowLeft size={14} />
              {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}
            </button>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors bg-canvas px-4 py-2 rounded-lg border border-border-main hover:border-primary-start"
            >
              {t('general.top', 'Lart')} ↑
            </button>
          </div>

        </div>
      </div>
    </motion.div>
  );
}