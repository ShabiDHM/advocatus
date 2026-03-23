// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE V8.2 (ROBUST PARSING FIX)
// 1. FIXED: Splits text using the [NDARJA] marker to avoid AI Disclaimer collision.
// 2. ENHANCED: Cleanly strips the raw disclaimer from the text block.
// 3. RETAINED: 100% of Original UI and functionality.

import { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, AlertCircle, BookOpen, Sparkles, Loader2, X, BrainCircuit, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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

  // --- AI STATE ---
  const [isExplaining, setIsExplaining] = useState(false);
  const [rawExplanation, setRawExplanation] = useState('');
  const [activePerspective, setActivePerspective] = useState<'senior' | 'citizen'>('senior');
  const [aiError, setAiError] = useState('');
  const aiSectionRef = useRef<HTMLDivElement>(null);

  const lawTitle = searchParams.get('lawTitle');
  const articleNumber = searchParams.get('articleNumber');

  // --- PHOENIX: ROBUST DUAL PERSPECTIVE PARSING ---
  const perspectives = useMemo(() => {
    // 1. Strip the server's hardcoded disclaimer to prevent it from bleeding into the Citizen tab
    const cleanText = rawExplanation.replace(/\n\n---\n\*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë\.\*/g, '');
    
    // 2. Split exactly by our new backend marker
    const parts = cleanText.split('[NDARJA]');
    return {
        senior: parts[0] ? parts[0].trim() : '',
        citizen: parts[1] ? parts[1].trim() : ''
    };
  }, [rawExplanation]);

  useEffect(() => {
    if (!lawTitle || !articleNumber) {
      setError(t('lawArticle.missingParams', 'Parametrat e artikullit mungojnë.'));
      setLoading(false);
      return;
    }
    apiService.getLawArticle(lawTitle, articleNumber)
      .then(setArticle)
      .catch((err) => {
        setError(err.message || t('lawArticle.fetchError', 'Dështoi ngarkimi i artikullit.'));
      })
      .finally(() => setLoading(false));
  }, [lawTitle, articleNumber, t]);

  const handleAiExplain = async () => {
    if (!article || isExplaining) return;
    
    setIsExplaining(true);
    setRawExplanation('');
    setAiError('');
    setActivePerspective('senior');
    
    try {
        const stream = apiService.explainLawStream(article.law_title, article.article_number, article.text);
        setTimeout(() => aiSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 300);

        for await (const chunk of stream) {
            setRawExplanation(prev => prev + chunk);
        }
    } catch (err: any) {
        setAiError(t('lawArticle.aiError', 'Dështoi analiza inteligjente.'));
    } finally {
        setIsExplaining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-accent-glow"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-3xl mx-auto px-6 pt-32">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-[2rem] flex flex-col items-center text-center shadow-lg shadow-danger-start/10">
          <AlertCircle className="text-danger-start w-20 h-20 mb-6" />
          <h2 className="text-2xl font-black text-text-primary uppercase tracking-tighter mb-3">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-lg mb-8">{error}</p>
          <button onClick={() => navigate('/laws/search')} className="btn-primary flex items-center gap-2"><ArrowLeft size={18} /> {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}</button>
        </div>
      </div>
    );
  }

  const paragraphs = article.text.split('\n\n').filter(p => p.trim() !== '');

  return (
    <motion.div className="w-full min-h-screen pb-16" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div className="max-w-4xl mx-auto px-6 sm:px-8 pt-28">
        
        <button onClick={() => navigate(-1)} className="group mb-8 flex items-center gap-3 text-text-muted hover:text-text-primary transition-colors font-bold text-sm uppercase tracking-widest">
          <div className="p-2 rounded-lg bg-surface border border-border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          {t('general.back', 'Kthehu Mbrapa')}
        </button>

        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-lawyer-dark border-border-main">
          
          {/* Header */}
          <div className="bg-surface px-8 py-10 border-b border-border-main relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
            <div className="relative z-10 flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1.5 rounded-lg">
                            <BookOpen size={14} />
                            <span className="text-[10px] font-black uppercase tracking-widest">{t('lawArticle.lawTitle', 'LIGJI')}</span>
                        </div>
                        <div className="flex items-center gap-2 bg-surface-secondary text-text-secondary border border-border-main px-3 py-1.5 rounded-lg">
                            <Calendar size={14} />
                            <span className="text-[10px] font-bold uppercase tracking-widest truncate max-w-[150px] sm:max-w-[200px]">{article.source}</span>
                        </div>
                    </div>
                    <button onClick={handleAiExplain} disabled={isExplaining} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm ${isExplaining ? 'bg-canvas text-text-muted cursor-not-allowed border border-border-main' : 'bg-primary-start text-white hover:bg-primary-hover shadow-accent-glow hover:-translate-y-0.5'}`}>
                        {isExplaining ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                        {isExplaining ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.aiExplain', 'Analizo me AI')}
                    </button>
                </div>
                <h1 className="text-3xl sm:text-4xl font-black text-text-primary leading-tight tracking-tighter">{article.law_title}</h1>
                <div className="flex items-center gap-4 border-t border-border-main/50 pt-6 mt-2">
                    <Scale size={24} className="text-primary-start" />
                    <p className="text-xl text-primary-start font-black uppercase tracking-widest">{t('lawArticle.article', 'Neni')} {article.article_number}</p>
                </div>
            </div>
          </div>

          {/* Reading Surface */}
          <div className="bg-paper px-8 sm:px-12 py-12 shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
            <div className="max-w-[75ch] mx-auto">
                {paragraphs.map((para, idx) => (
                <p key={idx} className="mb-6 text-[17px] text-text-primary leading-relaxed font-serif whitespace-pre-wrap">{para}</p>
                ))}
            </div>
          </div>

          {/* AI PERSPECTIVE AREA */}
          <AnimatePresence>
            {(rawExplanation || isExplaining || aiError) && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} ref={aiSectionRef} className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden">
                    <div className="p-8 sm:p-12 relative">
                        
                        {/* Switcher */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-6 border-b border-border-main/50 pb-6">
                            <div className="flex bg-surface p-1.5 rounded-2xl border border-border-main shadow-inner w-full sm:w-auto">
                                <button onClick={() => setActivePerspective('senior')} className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${activePerspective === 'senior' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary hover:bg-canvas'}`}>
                                    <BrainCircuit size={16} /> Analiza Profesionale
                                </button>
                                <button onClick={() => setActivePerspective('citizen')} className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${activePerspective === 'citizen' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary hover:bg-canvas'}`}>
                                    <User size={16} /> Për Qytetarin
                                </button>
                            </div>
                            <button onClick={() => {setRawExplanation(''); setAiError('');}} className="p-3 bg-surface border border-border-main rounded-xl text-text-muted hover:text-danger-start hover:border-danger-start/30 transition-colors self-end sm:self-auto"><X size={20} /></button>
                        </div>

                        {/* Error State */}
                        {aiError && (
                            <div className="bg-danger-start/5 border border-danger-start/20 rounded-xl p-6 text-danger-start text-sm font-medium flex items-center gap-3"><AlertCircle size={18} /> {aiError}</div>
                        )}

                        {/* Shimmer */}
                        {isExplaining && !rawExplanation && (
                            <div className="space-y-4">
                                <div className="h-4 bg-primary-start/10 rounded w-full animate-pulse" />
                                <div className="h-4 bg-primary-start/10 rounded w-5/6 animate-pulse" />
                                <div className="h-4 bg-primary-start/10 rounded w-4/6 animate-pulse" />
                            </div>
                        )}

                        {/* Result */}
                        {rawExplanation && (
                            <div className="prose prose-sm max-w-none prose-slate min-h-[150px]">
                                <div className="whitespace-pre-wrap text-text-secondary leading-loose font-medium text-[16px] space-y-4">
                                    {activePerspective === 'senior' 
                                        ? perspectives.senior 
                                        : perspectives.citizen || (isExplaining ? "Duke përgatitur shpjegimin e thjeshtësuar..." : "")
                                    }
                                    {isExplaining && <span className="inline-block w-2 h-5 bg-primary-start animate-pulse ml-1 align-middle" />}
                                </div>
                            </div>
                        )}
                        
                        {/* Footer Disclaimer */}
                        <div className="mt-8 pt-6 border-t border-border-main/30 flex items-center gap-2 text-[10px] text-text-muted font-black uppercase tracking-widest">
                            <Sparkles size={12} className="text-primary-start" /> {t('lawArticle.aiDisclaimer', 'Rezultati i gjeneruar nga modeli juridik i AI')}
                        </div>
                    </div>
                </motion.div>
            )}
          </AnimatePresence>

          {/* Footer Actions */}
          <div className="bg-surface px-8 py-6 flex justify-between items-center border-t border-border-main">
            <button onClick={() => navigate('/laws/search')} className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-primary-start transition-colors flex items-center gap-2"><ArrowLeft size={14} /> {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}</button>
            <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors bg-canvas px-4 py-2 rounded-lg border border-border-main hover:border-primary-start">{t('general.top', 'Lart')} ↑</button>
          </div>

        </div>
      </div>
    </motion.div>
  );
}