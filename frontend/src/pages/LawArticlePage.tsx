// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE PAGE V21.0 (MOBILE-SAFE PDF EMBED REPAIR)

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft, Scale, AlertCircle, BookOpen, Sparkles, 
  Loader2, X, BrainCircuit, Send, MessageCircle, FileText, ExternalLink, Download,
  ChevronLeft, ChevronRight, Search, Minus, Maximize2, ShieldCheck
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
}

interface ArticleData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
  source_info?: SourceInfo;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'auditor';
  content: string;
  timestamp: Date;
}

const normalizeText = (raw: string, articleNum?: string): string => {
  if (!raw) return '';

  let cleaned = raw;

  cleaned = cleaned.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');
  cleaned = cleaned.replace(/GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/FLETORJA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+SHQIPËRISË.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/(?:KODI|LIGJI|UDHËZIMI|UDHËZIM)\s+Nr\.\s*[\d\/L\-]+\s+[A-ZËÇSHQËWXYZ\s\-]+(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/^\s*\d{1,3}\s*$/gm, '');

  const cleanNumStr = (articleNum || '').replace(/\.$/, '').trim();
  const numMatch = cleanNumStr.match(/\d+/);
  const currentNum = numMatch ? parseInt(numMatch[0], 10) : 0;
  const isPreamble = currentNum === 0 || cleanNumStr.toLowerCase() === 'preambula' || cleanNumStr.toLowerCase() === 'hyrja';

  if (isPreamble) {
    const neni1Match = cleaned.match(/(?:^|\n)\s*(?:Neni|NENI)\s+1\b/i);
    if (neni1Match && neni1Match.index !== undefined) {
      cleaned = cleaned.substring(0, neni1Match.index).trim();
    }
  } else if (currentNum > 0) {
    const currentArticleRegex = new RegExp(`(?:^|\\n)\\s*(?:Neni|NENI)\\s+${currentNum}\\b`, 'i');
    const startMatch = cleaned.match(currentArticleRegex);
    if (startMatch && startMatch.index !== undefined) {
      cleaned = cleaned.substring(startMatch.index).trim();
    }

    const nextNum = currentNum + 1;
    const nextArticleRegex = new RegExp(`(?:^|\\n)\\s*(?:Neni|NENI)\\s+${nextNum}\\b`, 'i');
    const endMatch = cleaned.match(nextArticleRegex);
    if (endMatch && endMatch.index !== undefined) {
      cleaned = cleaned.substring(0, endMatch.index).trim();
    }

    cleaned = cleaned.replace(new RegExp(`^(?:Neni|NENI)\\s+${currentNum}\\b[:\\.\\-]*\\s*`, 'i'), '').trim();
  }

  const lines = cleaned.split('\n');
  const mergedLines: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const currentLine = lines[i].trim();
    if (!currentLine) {
      mergedLines.push(currentLine);
      continue;
    }

    if (mergedLines.length > 0 && mergedLines[mergedLines.length - 1] === currentLine) {
      continue;
    }
    
    const endsMidSentence = !/[.!?:;]$/.test(currentLine);
    const nextLine = lines[i + 1]?.trim() || '';
    const nextStartsLowercase = /^[a-zëç]/i.test(nextLine) && !/^\d+\./.test(nextLine);
    
    if (endsMidSentence && nextStartsLowercase && nextLine) {
      lines[i + 1] = currentLine + ' ' + nextLine;
    } else {
      mergedLines.push(currentLine);
    }
  }
  
  cleaned = mergedLines.join('\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  const paragraphs = cleaned.split(/\n\n+/);
  const normalizedParagraphs = paragraphs
    .map(para => para.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
    .filter((para, index, arr) => para.length > 0 && (index === 0 || para !== arr[index - 1]));
  
  return normalizedParagraphs.join('\n\n');
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
            <p key={i} className="mb-4 text-base sm:text-lg text-text-primary leading-relaxed font-medium">
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

  // Detect mobile device to bypass buggy mobile iframe PDF embeds
  const isMobile = typeof window !== 'undefined' && (/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || window.innerWidth < 768);

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
        
        setSourceInfo(data.source_info || null);
        setArticle({
          law_title: data.law_title,
          article_number: data.article_number || articleNumber,
          source: data.source || `${lawTitle}.pdf`,
          text: normalizedText,
          chunk_id: chunkId,
          source_info: data.source_info,
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
          <button onClick={handleBackToLibrary} className="btn-primary flex items-center gap-2 hover-lift shadow-sm">
            <ArrowLeft size={16} /> {t('lawArticle.backToSearch', 'Kthehu te Biblioteka Ligjore')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="w-full min-h-screen pt-24 pb-12 bg-canvas flex flex-col text-text-primary"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* STANDARDIZED EXECUTIVE MAX-W-7XL CONTAINER */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 flex-1 flex flex-col">
        <div className="glass-panel p-6 sm:p-8 md:p-10 flex flex-col flex-1 shadow-sm border border-main rounded-3xl bg-surface">
          
          <div className="flex flex-wrap items-center justify-between mb-8 gap-4">
            <button
              onClick={handleBackToLibrary}
              className="group flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift"
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
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none"
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
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-canvas border border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none"
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
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm hover-lift bg-primary-start hover:bg-primary-start/90 text-white"
              >
                {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
                {isSummarizing ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.auditBtn', 'Auditimi Ligjor')}
              </button>
            ) : (
              <button
                onClick={() => { setChatVisible(false); setMessages([]); setSummaryContent(''); }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm bg-canvas border border-main text-text-primary hover:border-danger-start hover:text-danger-start"
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
                    <BookOpen size={14} />
                    <span className="text-[10px] font-black uppercase tracking-wider">{t('lawArticle.lawTitle', 'LIGJI')}</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => { setShowPdfModal(true); setIsPdfMinimized(false); }}
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
                        const cleanNum = (article.article_number || articleNumber || '').replace(/\.$/, '').trim();
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
                        className="p-2 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start transition-colors"
                        title="Neni i Mëparshëm"
                      >
                        <ChevronLeft size={16} />
                      </button>
                    )}
                    {nextArticleNum !== null && (
                      <button
                        type="button"
                        onClick={() => navigateToArticleNum(nextArticleNum)}
                        className="p-2 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start transition-colors"
                        title="Neni i Ardhshëm"
                      >
                        <ChevronRight size={16} />
                      </button>
                    )}
                  </div>
                </div>

                {/* EXACT MATCH SOURCE VERIFICATION CARD */}
                {sourceInfo && (
                  <div className="mt-2 p-4 rounded-2xl bg-surface border border-main shadow-sm font-mono text-xs text-text-primary">
                    {/* Row 1: Status + Match Score */}
                    <div className="flex flex-wrap items-center justify-between pb-2.5 mb-2.5 border-b border-main/70 gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{sourceInfo.confidence?.icon || '✅'}</span>
                        <span className="font-black text-xs uppercase tracking-wider text-text-primary">
                          {sourceInfo.confidence?.label || 'E verifikuar'}
                        </span>
                      </div>
                      {sourceInfo.confidence?.score !== undefined && sourceInfo.confidence.score > 0 && (
                        <span className="text-xs font-mono font-black px-2.5 py-1 rounded-lg bg-canvas border border-main text-text-primary shadow-inner">
                          {Math.round(sourceInfo.confidence.score * 100)}% përputhje
                        </span>
                      )}
                    </div>

                    {/* Row 2: Official Law Name */}
                    <div className="font-bold text-xs sm:text-sm text-text-primary leading-relaxed mb-1 font-sans">
                      {sourceInfo.matched_law || article.law_title}
                    </div>

                    {/* Row 3: Article Number */}
                    <div className="text-xs font-bold text-primary-start mb-2">
                      Neni {sourceInfo.matched_article || article.article_number}
                    </div>

                    {/* Row 4: Search Mapping (If Mapped) */}
                    {sourceInfo.was_mapped && sourceInfo.mapped_from && (
                      <div className="text-xs text-amber-600 dark:text-amber-400 font-medium mb-2 flex items-center gap-1.5">
                        <span>📌</span>
                        <span>Kërkuar si: ({sourceInfo.mapped_from})</span>
                      </div>
                    )}

                    {/* Multiple Matches Warning */}
                    {sourceInfo.multiple_matches && sourceInfo.matching_laws?.length > 0 && (
                      <div className="text-xs text-rose-600 dark:text-rose-400 font-medium mb-2 flex items-center gap-1.5">
                        <span>⚠️</span>
                        <span>Ky nen ekziston në {sourceInfo.matching_laws.length} ligje të ndryshme në bazë</span>
                      </div>
                    )}

                    {/* Row 5: Verification Hint */}
                    <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium border-t border-main/50 pt-2.5 mt-2 flex items-center gap-1.5 font-sans">
                      <ShieldCheck size={15} className="shrink-0 text-emerald-500" />
                      <span>{sourceInfo.verification_hint || 'Ky nen korrespondon saktësisht me kërkimin.'}</span>
                    </div>
                  </div>
                )}

              </div>
            </div>

            <div className="bg-canvas/50 px-6 sm:px-12 py-10">
              <div className="max-w-[85ch] mx-auto">
                <div className="text-sm sm:text-base text-text-primary leading-relaxed font-medium whitespace-pre-wrap text-justify">
                  {article.text}
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
                        className="p-2 bg-surface border border-main rounded-xl text-text-muted hover:text-danger-start hover:border-danger-start/30 transition-colors hover-lift self-end sm:self-auto"
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

            {/* UNIFIED NEUTRAL CHAT BUBBLES */}
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
                        className="h-11 w-11 flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-start/90 transition-all shadow-sm"
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
                className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift"
              >
                <ArrowLeft size={14} /> Biblioteka Ligjore
              </button>

              <div className="flex items-center gap-3">
                {prevArticleNum !== null && (
                  <button
                    type="button"
                    onClick={() => navigateToArticleNum(prevArticleNum)}
                    className="flex items-center gap-2 px-3.5 py-1.5 bg-canvas hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary hover:border-primary-start transition-all shadow-sm"
                  >
                    <ChevronLeft size={14} />
                    <span>{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                  </button>
                )}

                {nextArticleNum !== null && (
                  <button
                    type="button"
                    onClick={() => navigateToArticleNum(nextArticleNum)}
                    className="flex items-center gap-2 px-3.5 py-1.5 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 rounded-xl text-xs font-bold text-primary-start transition-all shadow-sm uppercase tracking-wider"
                  >
                    <span>{`Neni ${nextArticleNum}`}</span>
                    <ChevronRight size={14} />
                  </button>
                )}
              </div>

              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary transition-colors bg-canvas px-3.5 py-1.5 rounded-xl border border-main hover:border-primary-start shadow-sm"
              >
                {t('general.top', 'Lart')} ↑
              </button>
            </div>

          </div>
        </div>
      </div>

      {/* PDF DOCUMENT FULLSCREEN MODAL (STANDARDIZED: 95VW x 92VH) */}
      <AnimatePresence>
        {showPdfModal && pdfUrl && (
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
                    className="h-9 px-4 bg-surface border border-main hover:border-primary-start text-text-primary rounded-xl transition-all focus:outline-none flex items-center gap-2 text-xs font-bold uppercase tracking-wider"
                    title="Shkarko PDF"
                  >
                    <Download size={14} />
                    <span className="hidden sm:inline">Shkarko PDF</span>
                  </a>

                  <button 
                    type="button"
                    onClick={() => setIsPdfMinimized(true)} 
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none"
                    aria-label="Minimize PDF viewer"
                    title="Minimizo"
                  >
                    <Minus size={18} />
                  </button>

                  <button 
                    type="button"
                    onClick={() => { setShowPdfModal(false); setIsPdfMinimized(false); }} 
                    className="p-2 bg-surface border border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none"
                    aria-label="Close PDF viewer"
                    title="Mbyll"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              <div className="flex-1 w-full h-full bg-slate-900 relative flex items-center justify-center p-4">
                {isMobile ? (
                  // MOBILE FALLBACK CARD: Bypasses Android Chrome iframe/pdf native viewer trap
                  <div className="flex flex-col items-center justify-center text-center p-6 bg-canvas rounded-2xl border border-main max-w-sm w-full shadow-2xl">
                    <div className="w-16 h-16 rounded-2xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center mb-4">
                      <FileText size={32} className="text-primary-start" />
                    </div>
                    <h4 className="text-sm font-bold text-text-primary mb-2 truncate max-w-xs">
                      {article.source}
                    </h4>
                    <p className="text-xs text-text-muted mb-6">
                      Pajisjet celulare nuk lejojnë shfaqjen e PDF brenda kornizave. Klikoni më poshtë për ta hapur direkt:
                    </p>
                    <div className="flex flex-col gap-3 w-full">
                      <a 
                        href={pdfUrl} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="btn-primary py-3 rounded-xl flex items-center justify-center gap-2 font-medium text-xs sm:text-sm shadow-lg"
                      >
                        <ExternalLink size={16} /> Hap PDF në Shfletues
                      </a>
                      <a 
                        href={pdfUrl} 
                        download={article.source}
                        className="py-3 rounded-xl bg-surface hover:bg-hover border border-main text-text-primary flex items-center justify-center gap-2 font-medium text-xs sm:text-sm"
                      >
                        <Download size={16} /> Shkarko PDF
                      </a>
                    </div>
                  </div>
                ) : (
                  // DESKTOP IFRAME VIEWER
                  <iframe 
                    src={pdfUrl} 
                    title={article.source} 
                    className="w-full h-full border-none rounded-2xl"
                  />
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showPdfModal && isPdfMinimized && article && (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 50, opacity: 0 }}
            className="fixed bottom-6 right-6 z-[250] flex items-center gap-3 p-3.5 bg-surface border border-main rounded-2xl shadow-2xl backdrop-blur-md max-w-md"
          >
            <div className="p-2.5 bg-primary-start/15 text-primary-start rounded-xl shrink-0 border border-primary-start/20">
              <FileText size={18} />
            </div>
            
            <div 
              className="min-w-0 flex-1 cursor-pointer" 
              onClick={() => setIsPdfMinimized(false)}
            >
              <p className="text-xs font-black text-text-primary uppercase truncate tracking-tight">
                {article.law_title}
              </p>
              <p className="text-[10px] text-text-muted font-mono truncate">
                {article.source}
              </p>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => setIsPdfMinimized(false)}
                className="p-2 bg-canvas hover:bg-hover border border-main text-primary-start rounded-xl transition-all focus:outline-none shadow-sm"
                title="Zgjero (Full Screen)"
              >
                <Maximize2 size={14} />
              </button>

              <button
                type="button"
                onClick={() => { setShowPdfModal(false); setIsPdfMinimized(false); }}
                className="p-2 bg-canvas hover:bg-hover border border-main text-text-muted hover:text-danger-start rounded-xl transition-all focus:outline-none shadow-sm"
                title="Mbyll"
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  );
}