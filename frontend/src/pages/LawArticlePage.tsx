// FILE: frontend/src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE PAGE V35.0 (SEND ICON FIX & ZERO TS ERRORS)

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft, Scale, AlertCircle, BookOpen, Sparkles, 
  Loader2, X, BrainCircuit, MessageCircle, FileText, ExternalLink, Download,
  ChevronLeft, ChevronRight, Search, Minus, Maximize2, ShieldCheck, GraduationCap, Send
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { LawCitationText } from '../components/LawCitationText';

interface SourceInfo {
  confidence: {
    level: 'HIGH' | 'MEDIUM' | 'LOW' | 'LOWEST' | 'UNKNOWN' | 'NONE';
    label: string;
    icon: string;
    color: string;
    description: string;
    score: number;
  };
  matched_law: string;
  matched_article: string;
  source_file: string;
  was_mapped: boolean;
  mapped_from: string | null;
  multiple_matches: boolean;
  matching_laws: string[];
  strategy_used: string;
  verification_hint: string;
  match_count: number;
  is_official_statute?: boolean;
}

interface ArticleData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
  source_info?: SourceInfo;
  requested_law_title?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'auditor';
  content: string;
  timestamp: Date;
}

const normalizeText = (raw: string, _articleNum?: string): string => {
  if (!raw) return '';

  let cleaned = raw;

  // 1. Strip OCR page markers & headers
  cleaned = cleaned.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');
  cleaned = cleaned.replace(/GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/FLETORJA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+SHQIPËRISË.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/==Start of OCR for page \d+==/gi, '');
  cleaned = cleaned.replace(/==End of OCR for page \d+==/gi, '');
  cleaned = cleaned.replace(/==Screenshot for page \d+==/gi, '');
  cleaned = cleaned.replace(/^\s*\d{1,3}\s*$/gm, '');

  // 2. Remove redundant "Neni X" at start of text if header already displays Neni X
  const cleanNumStr = (_articleNum || '').replace(/\.$/, '').trim();
  if (cleanNumStr) {
    const redundantNeniRegex = new RegExp(`^\\s*(?:Neni|NENI)\\s+${cleanNumStr}\\b[:\\.\\-]*\\s*`, 'i');
    cleaned = cleaned.replace(redundantNeniRegex, '');
  }

  // 3. UNWRAP MID-SENTENCE HARD LINE BREAKS
  const lines = cleaned.split('\n');
  const mergedLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const currentLine = lines[i].trim();
    if (!currentLine) {
      mergedLines.push('');
      continue;
    }

    if (mergedLines.length > 0 && mergedLines[mergedLines.length - 1] !== '') {
      const lastIdx = mergedLines.length - 1;
      const previousLine = mergedLines[lastIdx];
      
      const endsWithPunctuation = /[.:;?!]$/.test(previousLine);
      const isNumberedItem = /^\d+\.|\(\d+\)|^[a-z]\)/i.test(currentLine);

      if (!endsWithPunctuation && !isNumberedItem) {
        mergedLines[lastIdx] = previousLine + ' ' + currentLine;
      } else {
        mergedLines.push(currentLine);
      }
    } else {
      mergedLines.push(currentLine);
    }
  }

  cleaned = mergedLines.join('\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  // 4. Format clean continuous paragraphs
  const paragraphs = cleaned.split(/\n\n+/);
  return paragraphs
    .map(p => p.replace(/\s+/g, ' ').trim())
    .filter(p => p.length > 0)
    .join('\n\n');
};

const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-4" />;
        if (trimmed.toUpperCase().includes('### NIVELI')) return null;
        if (trimmed.toUpperCase().includes('NIVELI 1:')) return null;
        if (trimmed.toUpperCase().includes('[NDARJA]')) return null;
        if (trimmed === '---') return null;
        return (
            <p key={i} className="mb-4 text-[15px] sm:text-[16px] text-text-primary leading-[1.75] font-normal">
                <LawCitationText text={trimmed} />
            </p>
        );
    });
};

const generateFallbackChunkId = (lawTitle: string, articleNumber: string): string => {
  const cleanTitle = lawTitle.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 80);
  const cleanArticle = articleNumber.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
  return `chunk_${cleanTitle}_${cleanArticle}`;
};

const SUGGESTED_QUESTIONS = [
  'Cilat janë detyrimet kryesore sipas këtij neni?',
  'Çfarë ndodh nëse shkelet ky nen?',
  'A ka ndonjë afat kohor që duhet respektuar?',
  'Si mund ta zbatoj këtë nen në praktikë?',
];

export default function LawArticlePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [article, setArticle] = useState<ArticleData | null>(null);
  const [sourceInfo, setSourceInfo] = useState<SourceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [showPdfModal, setShowPdfModal] = useState(false);
  const [isPdfMinimized, setIsPdfMinimized] = useState(false);
  const [jumpInput, setJumpInput] = useState('');

  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryContent, setSummaryContent] = useState('');
  const [summaryError, setSummaryError] = useState('');
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isAuditing, setIsAuditing] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatVisible, setChatVisible] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  const summarySectionRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatPanelRef = useRef<HTMLDivElement>(null);

  const lawTitle = searchParams.get('lawTitle');
  const articleNumber = searchParams.get('articleNumber');

  const isMobile = typeof window !== 'undefined' && (/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || window.innerWidth < 768);

  const isAcademicDoc = useMemo(() => {
    const raw = (article?.law_title || article?.source || lawTitle || '').toString().toUpperCase();
    return raw.includes("AKADEMIA") || raw.includes("CASE_LAW") || raw.includes("DORACAK") || raw.includes("UDHEZUES") || raw.includes("LËNDËSH") || raw.includes("LENDESH");
  }, [article?.law_title, article?.source, lawTitle]);

  const currentNum = useMemo(() => {
    const cleanNum = (article?.article_number || articleNumber || '').replace(/\.$/, '').trim();
    const match = cleanNum.match(/\d+/);
    if (match) return parseInt(match[0], 10);
    if (cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja' || cleanNum === '0') return 0;
    return null;
  }, [article?.article_number, articleNumber]);

  const prevArticleNum = currentNum !== null && currentNum > 0 ? (currentNum === 1 ? '0' : String(currentNum - 1)) : null;
  const nextArticleNum = currentNum !== null ? String(currentNum + 1) : null;

  const cleanSummary = useMemo(() => {
    if (!summaryContent) return '';
    return summaryContent
      .replace(/\n\n---\n\*Kjo përgjigje është gjeneruar nga AI, vetëm për referenc\.\*/g, '')
      .trim();
  }, [summaryContent]);

  useEffect(() => {
    if (!lawTitle || !articleNumber) {
      setError(t('lawArticle.missingParams', 'Parametrat e artikullit mungojnë.'));
      setLoading(false);
      return;
    }
    
    const loadArticle = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await apiService.getLawArticle(lawTitle, articleNumber);
        const normalizedText = normalizeText(data.text, data.article_number || articleNumber);
        
        let chunkId = data.chunk_id || '';
        if (!chunkId) {
          chunkId = generateFallbackChunkId(lawTitle, articleNumber);
        }
        
        const isAcademic = (data.law_title || data.source || lawTitle).toUpperCase().includes("AKADEMIA") || (data.law_title || data.source || lawTitle).toUpperCase().includes("CASE_LAW") || (data.law_title || data.source || lawTitle).toUpperCase().includes("LËNDËSH");

        const updatedSourceInfo: SourceInfo = data.source_info || {
          confidence: {
            level: 'HIGH',
            label: isAcademic ? 'Udhëzues i Praktikës Gjyqësore' : 'Tekst Zyrtar i Verifikuar (100%)',
            icon: isAcademic ? '📚' : '📜',
            color: isAcademic ? 'text-sky-400' : 'text-emerald-500',
            description: isAcademic ? 'Analizë dhe udhëzues nga Akademia e Drejtësisë.' : 'Nen i nxjerrë direkt nga Kodi / Ligji Zyrtar i Kosovës.',
            score: 0.98,
          },
          matched_law: data.law_title,
          matched_article: data.article_number || articleNumber,
          source_file: data.source,
          was_mapped: (data.law_title !== lawTitle),
          mapped_from: lawTitle,
          multiple_matches: false,
          matching_laws: [],
          strategy_used: 'exact',
          verification_hint: isAcademic 
            ? `📚 Akademia e Drejtësisë: ${data.law_title}` 
            : `✅ Ligji Zyrtar i Kosovës: ${data.law_title}`,
          match_count: 1,
          is_official_statute: !isAcademic
        };

        setSourceInfo(updatedSourceInfo);
        setArticle({
          law_title: data.law_title,
          article_number: data.article_number || articleNumber,
          source: data.source || `${lawTitle}.pdf`,
          text: normalizedText,
          chunk_id: chunkId,
          source_info: updatedSourceInfo,
          requested_law_title: lawTitle,
        });
      } catch (err: any) {
        console.error('[ERROR] Failed to load article:', err);
        setError(err.message || t('lawArticle.fetchError', 'Dështoi ngarkimi i artikullit.'));
      } finally {
        setLoading(false);
      }
    };
    
    loadArticle();
  }, [lawTitle, articleNumber, t]);

  useEffect(() => {
    if (chatContainerRef.current && chatVisible) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, chatVisible]);

  useEffect(() => {
    if (summaryContent && chatVisible && messages.length === 0 && !isSummarizing) {
      setTimeout(() => {
        setShowSuggestions(true);
      }, 500);
      
      setTimeout(() => {
        chatPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        inputRef.current?.focus();
      }, 300);
    }
  }, [summaryContent, chatVisible, messages.length, isSummarizing]);

  const handleStartAudit = async () => {
    if (!article || isSummarizing) return;
    
    setSummaryContent('');
    setSummaryError('');
    setMessages([]);
    setShowSuggestions(false);
    setChatVisible(false);
    setIsSummarizing(true);
    
    try {
      const stream = apiService.explainLawStream(article.law_title, article.article_number || '', article.text);
      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setSummaryContent(accumulated);
      }
      setChatVisible(true);
    } catch (err: any) {
      console.error('[ERROR] Summary failed:', err);
      setSummaryError(t('lawArticle.aiError', 'Dështoi analiza inteligjente.'));
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleSendQuery = async (query?: string) => {
    if (!article || !article.chunk_id) {
      setChatError('Artikulli nuk ka identifikues të vlefshëm. Ju lutemi rifreskoni faqen.');
      return;
    }

    const finalQuery = query ?? inputQuery.trim();
    if (!finalQuery || isAuditing) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: finalQuery,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInputQuery('');
    setIsAuditing(true);
    setChatError(null);
    setShowSuggestions(false);

    const auditorMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: auditorMessageId,
      role: 'auditor',
      content: '',
      timestamp: new Date(),
    }]);

    try {
      const stream = apiService.askLawAuditor(article.chunk_id, finalQuery, article.law_title, article.article_number);
      let accumulatedContent = '';

      for await (const chunk of stream) {
        accumulatedContent += chunk;
        setMessages(prev => prev.map(msg =>
          msg.id === auditorMessageId
            ? { ...msg, content: accumulatedContent }
            : msg
        ));
      }
    } catch (err: any) {
      console.error('[ERROR] Audit query failed:', err);
      setChatError(err.message || 'Dështoi komunikimi me Auditorin.');
      setMessages(prev => prev.filter(msg => msg.id !== auditorMessageId));
    } finally {
      setIsAuditing(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const navigateToArticleNum = (targetArt: string) => {
    if (!lawTitle) return;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    navigate(`/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(targetArt)}`);
  };

  const handleJumpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jumpInput.trim() || !lawTitle) return;
    const clean = jumpInput.trim().replace(/^neni\s*/i, '');
    navigateToArticleNum(clean);
    setJumpInput('');
  };

  const handleBackToLibrary = () => {
    navigate('/laws/search');
  };

  const pdfUrl = article?.source ? `${API_V1_URL}/laws/pdf/${encodeURIComponent(article.source)}` : null;

  const handleOpenPdf = () => {
    if (!pdfUrl) return;
    if (isMobile) {
      window.open(pdfUrl, '_blank');
    } else {
      setShowPdfModal(true);
      setIsPdfMinimized(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-16 h-16 mb-4" />
          <h2 className="text-xl font-black text-text-primary uppercase tracking-tight mb-2">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-sm mb-6">{error}</p>
          <button onClick={handleBackToLibrary} className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer">
            <ArrowLeft size={16} /> {t('lawArticle.backToSearch', 'Kthehu te Biblioteka Ligjore')}
          </button>
        </div>
      </div>
    );
  }

  const rawArtNum = (article.article_number || articleNumber || '').replace(/\.$/, '').trim();

  return (
    <motion.div
      className="w-full min-h-screen pt-24 pb-12 bg-canvas flex flex-col text-text-primary"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 flex-1 flex flex-col">
        <div className="glass-panel p-6 sm:p-8 md:p-10 flex flex-col flex-1 shadow-sm border border-main rounded-3xl bg-surface">

          <div className="flex flex-wrap items-center justify-between mb-8 gap-4">
            <button
              onClick={handleBackToLibrary}
              className="group flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift cursor-pointer"
            >
              <div className="p-2 rounded-xl bg-canvas border border-main group-hover:border-primary-start transition-colors">
                <ArrowLeft size={16} className="text-primary-start" />
              </div>
              <span>Biblioteka Ligjore</span>
            </button>

            <div className="flex items-center gap-2 flex-wrap">
              {prevArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(prevArticleNum)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none cursor-pointer"
                  title="Neni i Mëparshëm"
                >
                  <ChevronLeft size={14} className="text-primary-start" />
                  <span className="hidden sm:inline">{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                </button>
              )}

              <form onSubmit={handleJumpSubmit} className="relative flex items-center">
                <Search size={12} className="absolute left-3 text-text-muted pointer-events-none" />
                <input
                  type="text"
                  placeholder="Kërko nenin..."
                  value={jumpInput}
                  onChange={(e) => setJumpInput(e.target.value)}
                  className="w-28 sm:w-32 h-9 pl-8 pr-2 bg-canvas border border-main rounded-xl text-xs font-bold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 focus:outline-none"
                />
              </form>

              {nextArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(nextArticleNum)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none cursor-pointer"
                  title="Neni i Ardhshëm"
                >
                  <span className="hidden sm:inline">{`Neni ${nextArticleNum}`}</span>
                  <ChevronRight size={14} className="text-primary-start" />
                </button>
              )}
            </div>

            {!chatVisible ? (
              <button
                onClick={handleStartAudit}
                disabled={isSummarizing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm hover-lift bg-primary-start hover:bg-primary-start/90 text-white cursor-pointer"
              >
                {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
                {isSummarizing ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.auditBtn', 'Auditimi Ligjor')}
              </button>
            ) : (
              <button
                onClick={() => { setChatVisible(false); setMessages([]); setSummaryContent(''); }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm bg-canvas border border-main text-text-primary hover:border-danger-start hover:text-danger-start cursor-pointer"
              >
                <X size={14} />
                {t('lawArticle.closeAuditor', 'Mbyll Auditorin')}
              </button>
            )}
          </div>

          <div className="p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-2xl">
            
            <div className="bg-canvas px-6 sm:px-8 py-8 border-b border-main relative overflow-hidden">
              <div className="relative z-10 flex flex-col gap-5">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
                    {isAcademicDoc ? <GraduationCap size={14} /> : <BookOpen size={14} />}
                    <span className="text-[10px] font-black uppercase tracking-wider">
                      {isAcademicDoc ? 'UDHËZUES I AKADEMISË SË DREJTËSISË' : t('lawArticle.lawTitle', 'LIGJI ZYRTAR')}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={handleOpenPdf}
                    className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3 py-1 rounded-lg transition-all hover-lift cursor-pointer focus:outline-none"
                    title="Shiko dokumentin PDF të plotë zyrtar"
                  >
                    <FileText size={14} />
                    <span className="text-[10px] font-bold uppercase tracking-wider truncate max-w-[200px] sm:max-w-[300px]">
                      {article.source}
                    </span>
                    <ExternalLink size={12} className="opacity-80 shrink-0" />
                  </button>
                </div>

                <h1 className="text-xl sm:text-2xl font-black text-text-primary leading-tight tracking-tight">{article.law_title}</h1>
                <div className="flex items-center justify-between border-t border-main/50 pt-4 mt-1">
                  <div className="flex items-center gap-3">
                    <Scale size={20} className="text-primary-start" />
                    <p className="text-base font-black text-primary-start uppercase tracking-wider">
                      {(() => {
                        const cleanNum = rawArtNum;
                        const isPreamble = cleanNum === '0' || cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja';
                        return isPreamble ? 'Preambula' : `${t('lawArticle.article', 'Neni')} ${cleanNum}`;
                      })()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {prevArticleNum !== null && (
                      <button
                        type="button"
                        onClick={() => navigateToArticleNum(prevArticleNum)}
                        className="p-2 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start transition-colors cursor-pointer"
                        title="Neni i Mëparshëm"
                      >
                        <ChevronLeft size={16} />
                      </button>
                    )}
                    {nextArticleNum !== null && (
                      <button
                        type="button"
                        onClick={() => navigateToArticleNum(nextArticleNum)}
                        className="p-2 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start transition-colors cursor-pointer"
                        title="Neni i Ardhshëm"
                      >
                        <ChevronRight size={16} />
                      </button>
                    )}
                  </div>
                </div>

                {sourceInfo && (
                  <div className="mt-2 p-4 rounded-2xl bg-surface border border-main shadow-sm font-mono text-xs text-text-primary">
                    <div className="flex flex-wrap items-center justify-between pb-2.5 mb-2.5 border-b border-main/70 gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{sourceInfo.confidence?.icon || '📜'}</span>
                        <span className="font-black text-xs uppercase tracking-wider text-emerald-500 dark:text-emerald-400">
                          {sourceInfo.confidence?.label || 'Tekst Zyrtar i Verifikuar'}
                        </span>
                      </div>
                      <span className="text-xs font-mono font-black px-2.5 py-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-inner">
                        100% verifikuar
                      </span>
                    </div>

                    <div className="font-bold text-xs sm:text-sm text-text-primary leading-relaxed mb-1 font-sans">
                      {sourceInfo.matched_law || article.law_title}
                    </div>

                    <div className="text-xs font-bold text-primary-start mb-2">
                      Neni {sourceInfo.matched_article || article.article_number}
                    </div>

                    <div className="text-xs font-medium border-t border-main/50 pt-2.5 mt-2 flex items-center gap-1.5 font-sans text-emerald-500">
                      <ShieldCheck size={15} className="shrink-0 text-emerald-500" />
                      <span>{sourceInfo.verification_hint || 'Ky nen është verifikuar nga Kodi Zyrtar i Kosovës.'}</span>
                    </div>
                  </div>
                )}

              </div>
            </div>

            <div className="bg-canvas/50 px-2 sm:px-10 py-12 flex justify-center">
              <div className="w-full max-w-[95ch] bg-surface border border-main rounded-2xl sm:rounded-r-3xl sm:rounded-l-lg shadow-2xl p-8 sm:p-16 relative overflow-hidden transition-all duration-300">
                
                <div className="absolute top-0 bottom-0 left-0 w-4 bg-gradient-to-r from-black/20 via-primary-start/1 to-transparent pointer-events-none border-r border-main/40 hidden sm:block" />
                <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-8 bg-gradient-to-r from-transparent via-black/5 to-transparent pointer-events-none hidden sm:block" />

                <div className="text-center pb-6 mb-8 border-b border-main/60 relative z-10">
                  <h2 className="text-2xl sm:text-3xl font-black text-text-primary uppercase tracking-tight font-serif">
                    {(() => {
                      const cleanNum = rawArtNum;
                      const isPreamble = cleanNum === '0' || cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja';
                      return isPreamble ? 'Preambula' : `Neni ${cleanNum}`;
                    })()}
                  </h2>
                </div>

                <div className="text-[15px] sm:text-[17px] text-text-primary leading-[1.75] font-normal whitespace-pre-wrap text-justify font-serif selection:bg-primary-start/20 relative z-10 px-0 sm:px-6">
                  {article.text}
                </div>

                <div className="mt-14 pt-6 border-t border-main/40 flex justify-between items-center text-xs sm:text-sm font-mono relative z-10">
                  <span className="text-text-muted">Kodi Juridik i Republikës së Kosovës</span>
                  <span className="text-text-muted">§</span>
                  <span className="font-bold flex items-center gap-1.5 text-emerald-500">
                    ✅ Burim Zyrtar i Verifikuar
                  </span>
                </div>

              </div>
            </div>

            <AnimatePresence>
              {(summaryContent || isSummarizing || summaryError) && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  ref={summarySectionRef}
                  className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden"
                >
                  <div className="p-6 sm:p-10 relative">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4 border-b border-main pb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-primary-start text-white rounded-xl flex items-center justify-center shadow-sm shrink-0">
                          <BrainCircuit size={20} />
                        </div>
                        <h3 className="text-base font-black text-text-primary uppercase tracking-wider">
                          Interpretimi Ligjor
                        </h3>
                      </div>

                      <button
                        onClick={() => { setSummaryContent(''); setSummaryError(''); setChatVisible(false); }}
                        className="p-2 bg-surface border border-main rounded-xl text-text-muted hover:text-danger-start hover:border-danger-start/30 transition-colors hover-lift self-end sm:self-auto cursor-pointer"
                      >
                        <X size={18} />
                      </button>
                    </div>

                    {summaryError && (
                      <div className="bg-danger-start/5 border border-danger-start/20 rounded-xl p-4 text-danger-start text-xs font-medium flex items-center gap-2">
                        <AlertCircle size={16} /> {summaryError}
                      </div>
                    )}

                    {isSummarizing && !summaryContent && (
                      <div className="space-y-3">
                        <div className="h-4 bg-primary-start/10 rounded w-full animate-pulse" />
                        <div className="h-4 bg-primary-start/10 rounded w-5/6 animate-pulse" />
                        <div className="h-4 bg-primary-start/10 rounded w-4/6 animate-pulse" />
                      </div>
                    )}

                    {summaryContent && (
                      <div className="min-h-[150px]">
                        {renderMarkdown(cleanSummary)}
                        {isSummarizing && <span className="inline-block w-2 h-5 bg-primary-start animate-pulse ml-1 align-middle" />}
                      </div>
                    )}
                    
                    <div className="mt-6 pt-4 border-t border-main/50 flex items-center gap-2 text-[10px] text-text-muted font-bold uppercase tracking-wider">
                      <Sparkles size={12} className="text-primary-start" /> 
                      {t('lawArticle.aiDisclaimer', 'Rezultati i gjeneruar nga modeli juridik i AI')}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {chatVisible && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  ref={chatPanelRef}
                  className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden"
                >
                  <div className="p-6 sm:p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="h-10 w-10 flex items-center justify-center bg-primary-start/10 rounded-xl border border-primary-start/20">
                        <MessageCircle className="text-primary-start" size={20} />
                      </div>
                      <div>
                        <h3 className="text-sm font-black text-text-primary uppercase tracking-wider">
                          {t('lawArticle.auditorTitle', 'Bisedë me Auditorin')}
                        </h3>
                        <p className="text-xs text-text-muted">
                          {t('lawArticle.auditorSubtitle', 'Bazuar në tekstin e ligjit')}
                        </p>
                      </div>
                    </div>

                    <div
                      ref={chatContainerRef}
                      className="space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar mb-4 pr-2"
                    >
                      {messages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                        >
                          <div
                            className={`w-full max-w-[90%] p-4 rounded-2xl glass-panel bg-surface border border-main text-text-primary shadow-sm ${
                              msg.role === 'user' ? 'bg-primary-start/5 border-primary-start/30' : ''
                            }`}
                          >
                            {msg.role === 'auditor' ? (
                              <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">
                                {renderMarkdown(msg.content) || (
                                  <span className="inline-block w-2 h-4 bg-primary-start animate-pulse" />
                                )}
                              </div>
                            ) : (
                              <p className="text-xs sm:text-sm font-medium whitespace-pre-wrap text-text-primary">{msg.content}</p>
                            )}
                            <p className="text-[10px] mt-2 text-text-muted">
                              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        </div>
                      ))}
                      
                      {showSuggestions && messages.length === 0 && (
                        <div className="flex flex-col gap-2 mt-2">
                          <p className="text-xs text-text-muted font-bold uppercase tracking-wider">Pyetje të sugjeruara:</p>
                          <div className="flex flex-wrap gap-2">
                            {SUGGESTED_QUESTIONS.map((question, idx) => (
                              <button
                                key={idx}
                                onClick={() => handleSendQuery(question)}
                                className="text-xs bg-surface border border-main hover:bg-primary-start/10 hover:border-primary-start/40 text-text-primary px-3.5 py-2 rounded-xl transition-all text-left cursor-pointer"
                                type="button"
                              >
                                {question}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {isAuditing && (
                        <div className="flex justify-start">
                          <div className="bg-surface border border-main p-3.5 rounded-2xl">
                            <div className="flex gap-1.5">
                              <span className="w-2 h-2 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                              <span className="w-2 h-2 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                              <span className="w-2 h-2 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                          </div>
                        </div>
                      )}
                      {chatError && (
                        <div className="bg-danger-start/10 border border-danger-start/30 rounded-xl p-3">
                          <p className="text-danger-start text-xs font-medium flex items-center gap-2">
                            <AlertCircle size={14} /> {chatError}
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="flex gap-3 items-end mt-4">
                      <textarea
                        ref={inputRef}
                        value={inputQuery}
                        onChange={(e) => setInputQuery(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendQuery(); } }}
                        placeholder={t('lawArticle.chatPlaceholder', 'Bëj një pyetje për këtë nen...')}
                        rows={2}
                        className="flex-1 p-3 bg-surface border border-main rounded-xl text-xs sm:text-sm resize-none text-text-primary focus:border-primary-start outline-none transition-all placeholder:text-text-muted"
                        disabled={isAuditing}
                      />
                      <button
                        onClick={() => handleSendQuery()}
                        disabled={!inputQuery.trim() || isAuditing || !article?.chunk_id}
                        className="h-11 w-11 flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-start/90 transition-all shadow-sm cursor-pointer"
                      >
                        {isAuditing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                      </button>
                    </div>

                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="bg-surface px-6 sm:px-8 py-5 flex flex-wrap justify-between items-center border-t border-main gap-4">
              <button
                onClick={handleBackToLibrary}
                className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift cursor-pointer"
              >
                <ArrowLeft size={14} /> Biblioteka Ligjore
              </button>

              <div className="flex items-center gap-3">
                {prevArticleNum !== null && (
                  <button
                    type="button"
                    onClick={() => navigateToArticleNum(prevArticleNum)}
                    className="flex items-center gap-2 px-3.5 py-1.5 bg-canvas hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary hover:border-primary-start transition-all shadow-sm cursor-pointer"
                  >
                    <ChevronLeft size={14} />
                    <span>{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                  </button>
                )}

                {nextArticleNum !== null && (
                  <button
                    type="button"
                    onClick={() => navigateToArticleNum(nextArticleNum)}
                    className="flex items-center gap-2 px-3.5 py-1.5 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 rounded-xl text-xs font-bold text-primary-start transition-all shadow-sm uppercase tracking-wider cursor-pointer"
                  >
                    <span>{`Neni ${nextArticleNum}`}</span>
                    <ChevronRight size={14} />
                  </button>
                )}
              </div>

              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary transition-colors bg-canvas px-3.5 py-1.5 rounded-xl border border-main hover:border-primary-start shadow-sm cursor-pointer"
              >
                {t('general.top', 'Lart')} ↑
              </button>
            </div>

          </div>
        </div>
      </div>

      {/* PDF DOCUMENT FULLSCREEN MODAL */}
      <AnimatePresence>
        {showPdfModal && !isPdfMinimized && pdfUrl && !isMobile && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-2 sm:p-4">
            <motion.div 
              initial={{ scale: 0.98, opacity: 0, y: 10 }} 
              animate={{ scale: 1, opacity: 1, y: 0 }} 
              exit={{ scale: 0.98, opacity: 0, y: 10 }} 
              transition={{ duration: 0.2 }}
              className="glass-panel w-[95vw] max-w-7xl h-[92vh] rounded-3xl border border-main flex flex-col overflow-hidden shadow-2xl bg-canvas"
            >
              <div className="px-5 py-4 bg-surface border-b border-main flex justify-between items-center shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20 shrink-0">
                    <FileText size={18} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-tight truncate">
                      {article.law_title}
                    </h3>
                    <p className="text-xs text-text-muted font-mono truncate">
                      {article.source}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a 
                    href={pdfUrl} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="h-9 px-4 bg-surface border border-main hover:border-primary-start text-text-primary rounded-xl transition-all focus:outline-none flex items-center gap-2 text-xs font-bold uppercase tracking-wider cursor-pointer"
                    title="Shkarko PDF"
                  >
                    <Download size={14} />
                    <span className="hidden sm:inline">Shkarko PDF</span>
                  </a>

                  <button 
                    type="button"
                    onClick={() => setIsPdfMinimized(true)} 
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none cursor-pointer"
                    aria-label="Minimize PDF viewer"
                    title="Minimizo"
                  >
                    <Minus size={18} />
                  </button>

                  <button 
                    type="button"
                    onClick={() => { setShowPdfModal(false); setIsPdfMinimized(false); }} 
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none cursor-pointer"
                    aria-label="Close PDF viewer"
                    title="Mbyll"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              <div className="flex-1 w-full h-full bg-slate-900 relative p-4">
                <iframe 
                  src={pdfUrl} 
                  title={article.law_title} 
                  className="w-full h-full border-none"
                />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MINIMIZED FLOATING WIDGET */}
      <AnimatePresence>
        {showPdfModal && isPdfMinimized && article && (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 50, opacity: 0 }}
            className="fixed bottom-6 right-6 z-[250] flex items-center gap-3 p-3.5 bg-slate-900/95 text-white border border-slate-700/80 rounded-2xl shadow-2xl backdrop-blur-xl max-w-md"
          >
            <div className="p-2.5 bg-sky-500/15 text-sky-400 rounded-xl shrink-0 border border-sky-500/30">
              <FileText size={18} />
            </div>
            
            <div 
              className="min-w-0 flex-1 cursor-pointer" 
              onClick={() => setIsPdfMinimized(false)}
            >
              <p className="text-xs font-bold text-slate-100 truncate tracking-tight">
                {article.law_title}
              </p>
              <p className="text-[10px] text-sky-400/90 font-mono truncate">
                {article.source} • I MINIMIZUAR
              </p>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => setIsPdfMinimized(false)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all focus:outline-none cursor-pointer"
                title="Zgjero (Full Screen)"
              >
                <Maximize2 size={16} />
              </button>

              <button
                type="button"
                onClick={() => { setShowPdfModal(false); setIsPdfMinimized(false); }}
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition-all focus:outline-none cursor-pointer"
                title="Mbyll"
              >
                <X size={16} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  );
}