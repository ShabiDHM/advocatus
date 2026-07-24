// FILE: src/pages/LawViewerPage.tsx
// PHOENIX PROTOCOL - LAW VIEWER V6.0 (STANDARDIZED EXECUTIVE SIZE: MAX-W-7XL)

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Calendar, Scale, AlertCircle, BookOpen } from 'lucide-react';
import { motion } from 'framer-motion';

interface LawData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
}

export default function LawViewerPage() {
  const { chunkId } = useParams<{ chunkId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [law, setLaw] = useState<LawData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!chunkId) {
      setError(t('lawViewer.missingId', 'ID e fragmentit mungon.'));
      setLoading(false);
      return;
    }
    apiService.getLawByChunkId(chunkId)
      .then(setLaw)
      .catch((err) => {
        console.error('Law fetch error:', err);
        setError(err.message || t('lawViewer.fetchError', 'Dështoi ngarkimi i ligjit.'));
      })
      .finally(() => setLoading(false));
  }, [chunkId, t]);

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
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm"
          >
            <ArrowLeft size={16} />
            {t('lawViewer.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  if (!law) return null;

  // Format the text into paragraphs
  const paragraphs = law.text.split('\n').filter(p => p.trim() !== '');

  return (
    <motion.div 
        className="w-full min-h-screen pb-16 bg-canvas text-text-primary"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
    >
      {/* STANDARDIZED EXECUTIVE MAX-W-7XL CONTAINER */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        
        {/* Navigation Breadcrumb */}
        <button
          onClick={() => navigate(-1)}
          className="group mb-6 flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift"
        >
          <div className="p-2 rounded-xl bg-surface border border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          <span>{t('general.back', 'Kthehu Mbrapa')}</span>
        </button>

        {/* Law Content Container */}
        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface">
          
          {/* Executive Header Section */}
          <div className="bg-canvas px-6 sm:px-10 py-8 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-5">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
                        <BookOpen size={14} />
                        <span className="text-[10px] font-black uppercase tracking-wider">
                        LIGJI DHE RREGULLORJA
                        </span>
                    </div>
                    <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3 py-1 rounded-lg">
                        <Calendar size={14} />
                        <span className="text-[10px] font-bold uppercase tracking-wider truncate max-w-[250px]">
                        {law.source}
                        </span>
                    </div>
                </div>
                
                <h1 className="text-2xl sm:text-4xl font-black text-text-primary leading-tight tracking-tight">
                {law.law_title}
                </h1>
                
                {law.article_number && (
                    <div className="flex items-center gap-3 border-t border-main/50 pt-4 mt-1">
                        <Scale size={20} className="text-primary-start" />
                        <p className="text-base text-primary-start font-black uppercase tracking-wider">
                            {t('lawViewer.article', 'Neni')} {law.article_number}
                        </p>
                    </div>
                )}
            </div>
          </div>

          {/* The Formal Paper Reading Surface */}
          <div className="bg-canvas/50 px-6 sm:px-12 py-10">
            <div className="max-w-[85ch] mx-auto">
                {paragraphs.map((para, idx) => (
                <p 
                    key={idx} 
                    className="mb-5 text-sm sm:text-base text-text-primary leading-relaxed font-medium text-justify"
                >
                    {para}
                </p>
                ))}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="bg-surface px-6 sm:px-10 py-5 flex justify-between items-center border-t border-main">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift"
            >
              <ArrowLeft size={14} />
              {t('lawViewer.backToSearch', 'Kthehu te kërkimi')}
            </button>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary transition-colors bg-canvas px-3.5 py-1.5 rounded-xl border border-main hover:border-primary-start shadow-sm"
            >
              {t('general.top', 'Kthehu Lart')} ↑
            </button>
          </div>

        </div>
      </div>
    </motion.div>
  );
}