// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - UNIFIED LAYOUT & MODERN TYPOGRAPHY V3 (ADVANCED TEXT SANITIZATION)

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

// ========== PHOENIX: ADVANCED TEXT SANITIZATION FOR PROFESSIONAL READING ==========
/**
 * Normalizes raw law article text by removing page markers, repetitive law headers,
 * and cleaning up whitespace for a smooth reading experience.
 */
const normalizeText = (raw: string): string => {
  if (!raw) return '';

  // Step 1: Remove page markers like "--- [FAQJA 3] ---" or "--- FAQJA 3 ---" (case-insensitive)
  let cleaned = raw.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');

  // Step 2: Remove repetitive law headers that appear mid-text
  // Pattern: "LIGJI NR. 04/L-123 PËR PRONËSINË ..." at line start or after newline
  const lawHeaderRegex = /(?:^|\n)\s*LIGJI\s+NR\.\s+\d+[\/\-]?[A-Z]?\d*\s+[A-ZËÇSHQËWXYZ].*?(?=\n|$)/gi;
  cleaned = cleaned.replace(lawHeaderRegex, '');

  // Step 3: Collapse 3 or more consecutive newlines into exactly 2 newlines (paragraph break)
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  // Step 4: Trim leading/trailing whitespace
  cleaned = cleaned.trim();

  // Step 5: Apply existing paragraph splitting and single-newline-to-space conversion
  const paragraphs = cleaned.split(/\n\n+/);
  const normalizedParagraphs = paragraphs.map(para =>
    para.replace(/\n/g, ' ').trim()
  );
  return normalizedParagraphs.filter(p => p.length > 0).join('\n\n');
};

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
    const cleanText = rawExplanation.replace(/\n\n---\n\*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë\.\*/g, '');
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
      .then((data: ArticleData) => {
        // Normalize the article text to remove unwanted line breaks and artifacts
        const normalizedText = normalizeText(data.text);
        setArticle({
          ...data,
          text: normalizedText,
        });
      })
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

  const handleBack = () => {
    navigate('/business/briefing', { state: { activeMode: 'library' } });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-3xl mx-auto px-6 pt-32">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-[2rem] flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-20 h-20 mb-6" />
          <h2 className="text-2xl font-black text-text-primary uppercase tracking-tighter mb-3">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-lg mb-8">{error}</p>
          <button onClick={handleBack} className="btn-primary flex items-center gap-2 hover-lift shadow-sm"><ArrowLeft size={18} /> {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}</button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="w-full min-h-screen pt-24 pb-12 bg-canvas flex flex-col"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 w-full flex-1 flex flex-col">
        <div className="glass-panel p-6 sm:p-8 md:p-10 flex flex-col flex-1 shadow-lawyer-dark border border-border-main">
          
          <button
            onClick={handleBack}
            className="group mb-8 flex items-center gap-3 text-text-muted hover:text-text-primary transition-colors font-bold text-sm uppercase tracking-widest hover-lift w-max"
          >
            <div className="p-2 rounded-lg bg-surface border border-border-main group-hover:border-primary-start transition-colors">
              <ArrowLeft size={16} className="text-primary-start" />
            </div>
            {t('general.back', 'Kthehu Mbrapa')}
          </button>

          <div className="p-0 flex flex-col overflow-hidden shadow-sm border border-border-main rounded-2xl">
            
            {/* Header */}
            <div className="bg-surface px-8 py-10 border-b border-border-main relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
              <div className="relative z-10 flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1.5 rounded-lg">
                      <BookOpen size={14} />
                      <span className="text-xs font-black uppercase tracking-widest">{t('lawArticle.lawTitle', 'LIGJI')}</span>
                    </div>
                    <div className="flex items-center gap-2 bg-canvas text-text-secondary border border-border-main px-3 py-1.5 rounded-lg">
                      <Calendar size={14} />
                      <span className="text-xs font-bold uppercase tracking-widest truncate max-w-[150px] sm:max-w-[200px]">{article.source}</span>
                    </div>
                  </div>
                  <button
                    onClick={handleAiExplain}
                    disabled={isExplaining}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm hover-lift ${
                      isExplaining
                        ? 'bg-canvas text-text-muted cursor-not-allowed border border-border-main'
                        : 'btn-primary'
                    }`}
                  >
                    {isExplaining ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                    {isExplaining ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.aiExplain', 'Analizo me AI')}
                  </button>
                </div>
                <h1 className="text-2xl sm:text-3xl font-black text-text-primary leading-tight tracking-tighter">{article.law_title}</h1>
                <div className="flex items-center gap-4 border-t border-border-main/50 pt-6 mt-2">
                  <Scale size={24} className="text-primary-start" />
                  <p className="text-lg font-black text-primary-start uppercase tracking-widest">{t('lawArticle.article', 'Neni')} {article.article_number}</p>
                </div>
              </div>
            </div>

            {/* Reading Surface - Normalized text with advanced sanitization */}
            <div className="bg-surface/50 px-8 sm:px-12 py-12 shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
              <div className="max-w-[75ch] mx-auto">
                <div className="text-base sm:text-lg text-text-primary leading-relaxed font-medium whitespace-pre-wrap text-justify">
                  {article.text}
                </div>
              </div>
            </div>

            {/* AI PERSPECTIVE AREA */}
            <AnimatePresence>
              {(rawExplanation || isExplaining || aiError) && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  ref={aiSectionRef}
                  className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden"
                >
                  <div className="p-8 sm:p-12 relative">
                    
                    {/* Switcher */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-6 border-b border-border-main/50 pb-6">
                      <div className="flex bg-surface p-1.5 rounded-2xl border border-border-main shadow-inner w-full sm:w-auto">
                        <button
                          onClick={() => setActivePerspective('senior')}
                          className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                            activePerspective === 'senior'
                              ? 'bg-primary-start text-white shadow-sm'
                              : 'text-text-muted hover:text-text-primary hover:bg-canvas'
                          }`}
                        >
                          <BrainCircuit size={16} /> Analiza Profesionale
                        </button>
                        <button
                          onClick={() => setActivePerspective('citizen')}
                          className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                            activePerspective === 'citizen'
                              ? 'bg-primary-start text-white shadow-sm'
                              : 'text-text-muted hover:text-text-primary hover:bg-canvas'
                          }`}
                        >
                          <User size={16} /> Për Qytetarin
                        </button>
                      </div>
                      <button
                        onClick={() => { setRawExplanation(''); setAiError(''); }}
                        className="p-3 bg-surface border border-border-main rounded-xl text-text-muted hover:text-danger-start hover:border-danger-start/30 transition-colors hover-lift self-end sm:self-auto"
                      >
                        <X size={20} />
                      </button>
                    </div>

                    {/* Error State */}
                    {aiError && (
                      <div className="bg-danger-start/5 border border-danger-start/20 rounded-xl p-6 text-danger-start text-sm font-medium flex items-center gap-3">
                        <AlertCircle size={18} /> {aiError}
                      </div>
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
                        <div className="whitespace-pre-wrap text-text-secondary leading-loose font-medium text-base space-y-4">
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
              <button
                onClick={handleBack}
                className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift"
              >
                <ArrowLeft size={14} /> {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}
              </button>
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors bg-canvas px-4 py-2 rounded-lg border border-border-main hover:border-primary-start hover-lift shadow-sm"
              >
                {t('general.top', 'Lart')} ↑
              </button>
            </div>

          </div>
        </div>
      </div>
    </motion.div>
  );
}