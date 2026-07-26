// FILE: frontend/src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V18.0 (INTEGRATED LAW CITATION LINKS)

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, User, Copy, Check, Scale,
    ThumbsUp, ThumbsDown, RefreshCw, Download, ChevronDown, Sparkles,
    ShieldCheck, Gavel, FileText, Info, ChevronRight
} from 'lucide-react';
import { ChatMessage } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiService } from '../services/api';
import { LawCitationLink } from './LawCitationLink';

export type ChatMode = 'general' | 'document';
export type ReasoningMode = 'FAST' | 'DEEP';
export type Jurisdiction = 'ks' | 'al';
export type LegalDomain = 'automatic' | 'family' | 'corporate' | 'property' | 'labor' | 'obligations' | 'administrative' | 'criminal';

const domainLabels: Record<LegalDomain, string> = {
  automatic: 'Automatik',
  family: 'Familjar',
  corporate: 'Tregtar',
  property: 'Pronësor',
  labor: 'Punës',
  obligations: 'Detyrimeve',
  administrative: 'Administrativ',
  criminal: 'Penal'
};

interface ChatPanelProps {
  messages: ChatMessage[];
  connectionStatus: string;
  reconnect: () => void;
  onSendMessage: (text: string, mode: ChatMode, reasoning: ReasoningMode, domain: LegalDomain, documentIds?: string[], jurisdiction?: Jurisdiction) => void;
  isSendingMessage: boolean;
  onClearChat: () => void;
  onExportChat?: () => void;
  t: TFunction;
  className?: string;
  activeContextId: string;
  isPro?: boolean;
  selectedDocumentCount?: number;
  userSalutation?: string;
  clientPosition?: 'DEFENDANT' | 'PLAINTIFF';
}

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-2">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
    </span>
);

const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';
  
  // Flexible multi-pattern citation regex:
  // Pattern 1: Ligji/Ligjit/Kodi Nr. XXX, Neni YYY
  // Pattern 2: Neni YYY i/e/të Ligjit/Kodit...
  // Pattern 3: Standalone Neni YYY
  const citationRegex = /(?:(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,.]*?)\s*,?\s*(?:Neni|neni|NENI)\s+(\d+))|(?:(?:Neni|neni|NENI)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.]*|[A-Z][a-zçëA-ZÇË\s\d\/L\-]{3,30})?)/gi;

  try {
    return text.replace(citationRegex, (match, lawPrefix, lawNumber, art1, art2, lawName2) => {
      let lawTitle = "";
      let articleNum = "";

      if (lawPrefix && art1) {
        lawTitle = `${lawPrefix} ${lawNumber.trim()}`;
        articleNum = art1.trim();
      } else if (art2) {
        articleNum = art2.trim();
        lawTitle = lawName2 ? lawName2.trim() : "Ligji i Përgjithshëm";
      }

      if (!articleNum) return match;

      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;
      return `[${match.trim()}](${targetUrl})`;
    });
  } catch (err) {
    console.error("Citation replacement failed:", err);
    return String(text);
  }
};

const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
    if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

    const marker = "Sugjerime:";
    const markerIndex = text.lastIndexOf(marker);
    if (markerIndex !== -1) {
        const cleanText = text.substring(0, markerIndex).trim();
        const suggestionsPart = text.substring(markerIndex + marker.length);
        const questions = suggestionsPart
            .split(/\n/)
            .map(line => line.replace(/^\d+[\.\)\-]\s*/, '').trim())
            .filter(q => q.length > 5 && q.endsWith('?'))
            .slice(0, 3);
        return { cleanText, questions };
    }
    return { cleanText: text, questions: [] };
};

const MessageCopyButton: React.FC<{ text: string }> = ({ text }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        try { 
            const { cleanText } = extractFollowUpQuestions(text || '');
            await navigator.clipboard.writeText(cleanText); 
            setCopied(true); 
            setTimeout(() => setCopied(false), 2000); 
        } catch (err) { 
            console.error(err); 
        }
    };
    return (
        <button 
            type="button"
            onClick={handleCopy} 
            className={`absolute top-2 right-2 p-2 rounded-xl transition-all opacity-0 group-hover:opacity-100 shadow-sm hover-lift focus:outline-none ${
                copied 
                  ? 'bg-status-success/20 text-status-success' 
                  : 'bg-surface border border-main text-text-muted hover:text-primary-start'
            }`}
        >
            {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
    );
};

const FeedbackButtons: React.FC<{
    messageIndex: number;
    caseId: string;
    onFeedback: (index: number, feedback: 'up' | 'down') => void;
    disabled?: boolean;
}> = ({ messageIndex, caseId, onFeedback, disabled }) => {
    const [submitting, setSubmitting] = useState<'up' | 'down' | null>(null);
    const [success, setSuccess] = useState(false);

    const handleFeedback = async (feedback: 'up' | 'down') => {
        if (submitting || disabled) return;
        setSubmitting(feedback);
        try {
            await apiService.submitChatFeedback(caseId, messageIndex, feedback);
            setSuccess(true);
            onFeedback(messageIndex, feedback);
            setTimeout(() => setSuccess(false), 2000);
        } catch (error) { console.error('Feedback failed:', error); } finally { setSubmitting(null); }
    };

    return (
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-main">
            <button
                type="button"
                onClick={() => handleFeedback('up')}
                disabled={!!submitting || disabled || success}
                className={`p-1.5 rounded-lg transition-all border hover-lift shadow-sm focus:outline-none ${success ? 'bg-status-success/20 text-status-success border-status-success/30' : 'bg-surface text-text-muted border-main hover:text-status-success hover:border-status-success/50'}`}
                title="Përgjigje e dobishme"
            >
                {submitting === 'up' ? <span className="w-3.5 h-3.5 border-2 border-t-transparent border-current rounded-full animate-spin block" /> : <ThumbsUp size={12} />}
            </button>
            <button
                type="button"
                onClick={() => handleFeedback('down')}
                disabled={!!submitting || disabled || success}
                className={`p-1.5 rounded-lg transition-all border hover-lift shadow-sm focus:outline-none ${success ? 'bg-status-success/20 text-status-success border-status-success/30' : 'bg-surface text-text-muted border-main hover:text-danger-start hover:border-danger-start/50'}`}
                title="Përgjigje e padobishme"
            >
                {submitting === 'down' ? <span className="w-3.5 h-3.5 border-2 border-t-transparent border-current rounded-full animate-spin block" /> : <ThumbsDown size={12} />}
            </button>
        </div>
    );
};

const MarkdownComponents = (_t: TFunction) => ({
    h1: ({node, ...props}: any) => <h1 className="text-lg font-bold text-text-primary mb-2 mt-3 border-b border-main pb-1 uppercase tracking-tight" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-base font-semibold text-primary-start mb-1.5 mt-2" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-sm font-semibold text-text-primary mb-1 mt-1.5 flex items-center gap-2" {...props} />,
    p: ({node, ...props}: any) => <p className="mb-2 last:mb-0 leading-relaxed text-text-secondary" {...props} />, 
    li: ({node, ...props}: any) => <li className="mb-1 leading-relaxed text-text-secondary" {...props} />, 
    a: ({href, children}: any) => {
        if (href?.startsWith('/laws/')) {
            try {
                const url = new URL(href, window.location.origin);
                const lawTitle = url.searchParams.get('lawTitle') || "Ligj i Paidentifikuar";
                const articleNum = url.searchParams.get('articleNumber') || "1";
                const fullMatch = String(children || `${lawTitle} - Neni ${articleNum}`);

                return (
                    <LawCitationLink
                        lawTitle={lawTitle}
                        articleNum={articleNum}
                        fullMatch={fullMatch}
                        targetUrl={href}
                    />
                );
            } catch {
                return (
                    <LawCitationLink
                        lawTitle="Ligj"
                        articleNum="1"
                        fullMatch={String(children || 'Referencë Ligjore')}
                        targetUrl={href}
                    />
                );
            }
        }
        return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-start font-semibold underline decoration-primary-start/30 hover:decoration-primary-start transition-colors">
                {children}
            </a>
        );
    },
});

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages = [], connectionStatus, onSendMessage, isSendingMessage, onClearChat, onExportChat, t, className, activeContextId, selectedDocumentCount = 0, userSalutation = 'Avokat', clientPosition = 'DEFENDANT'
}) => {
  const [input, setInput] = useState('');
  const [reasoningMode] = useState<ReasoningMode>('DEEP');
  const [selectedDomain, setSelectedDomain] = useState<LegalDomain>('automatic');
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const [lastUserMessage, setLastUserMessage] = useState<string>('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);
  
  useEffect(() => {
    if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 250)}px`;
    }
  }, [input]);

  const sendMessage = (text: string) => {
    if (!text.trim() || isSendingMessage) return;
    const mode = activeContextId === 'general' ? 'general' : 'document';
    
    setLastUserMessage(text);
    onSendMessage(text, mode, reasoningMode, selectedDomain, [], 'ks');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { 
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } 
  };
  
  const handleFeedback = (index: number, _feedback: 'up' | 'down') => {
    setFeedbackGiven(prev => new Set(prev).add(index));
  };

  const handleRetry = () => { if (lastUserMessage) sendMessage(lastUserMessage); };

  const safeMessages = Array.isArray(messages) ? messages : [];
  const lastMessage = safeMessages[safeMessages.length - 1];
  const showThinking = isSendingMessage && (!lastMessage || lastMessage.role !== 'ai' || !lastMessage.content?.trim());

  return (
    <div className={`flex flex-col glass-panel overflow-hidden h-full w-full border border-main bg-canvas shadow-sm ${className}`}>
      
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between px-4 sm:px-5 py-3 border-b border-main bg-surface z-50 shrink-0 gap-2.5 sm:gap-0">
        
        {/* Left group */}
        <div className="flex items-center gap-2">
          <h2 className="text-xs sm:text-sm font-bold text-text-primary uppercase tracking-wide leading-none">
            {t('chatPanel.title', 'Asistenti Sokratik')}
          </h2>
          <div className="flex items-center justify-center ml-0.5">
            <span className={`
              w-2 h-2 rounded-full 
              ${connectionStatus === 'CONNECTED' 
                ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse' 
                : 'bg-danger-start animate-pulse'
              }
            `} />
          </div>

          {activeContextId !== 'general' && selectedDocumentCount > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-primary-start/10 border border-primary-start/20 rounded-full shadow-sm">
              <span className="text-[10px] font-semibold text-primary-start uppercase tracking-wide">{selectedDocumentCount} Lëndë</span>
            </div>
          )}
        </div>

        {/* Right group */}
        <div className="flex items-center justify-end gap-2 h-8 sm:h-9">
          <div className="relative group h-8 sm:h-9 flex items-center">
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value as LegalDomain)}
              className="appearance-none h-8 sm:h-9 rounded-xl border border-main bg-surface text-text-primary text-[11px] sm:text-xs font-semibold pl-2.5 pr-7 focus:outline-none focus:ring-2 focus:ring-primary-start/20 hover-lift shadow-sm cursor-pointer transition-all"
            >
              {Object.entries(domainLabels).map(([value, label]) => <option key={value} value={value} className="bg-canvas text-text-primary">{label}</option>)}
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          </div>

          {onExportChat && (
            <button 
                type="button"
                onClick={onExportChat} 
                className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 text-text-muted hover:text-primary-start hover:bg-hover rounded-xl transition-all focus:outline-none" 
                title="Download"
            >
              <Download size={15} />
            </button>
          )}
          <button 
              type="button"
              onClick={onClearChat} 
              className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-xl transition-all focus:outline-none" 
              title="Clear"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* MESSAGE AREA / NATIVE EMBEDDED COMMAND PALETTE */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-canvas/10 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden shadow-[inset_0_1px_8px_rgba(0,0,0,0.01)] border-b border-main flex flex-col justify-start">
        <AnimatePresence initial={false}>
          
          {/* NATIVE EMBEDDED COMMAND PALETTE (VERTICALLY CENTERED WHEN MESSAGES = 0) */}
          {safeMessages.length === 0 && !isSendingMessage && (
            <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-2 sm:p-4 gap-3 sm:gap-4">
              
              <div className="space-y-1.5 max-w-lg">
                <h3 className="text-xs sm:text-base font-black uppercase text-text-primary tracking-tight">
                  Unë jam Agjenti i rastit tuaj, {userSalutation}
                </h3>
                <p className="text-[10px] sm:text-xs text-text-secondary leading-relaxed font-medium">
                  {clientPosition === 'DEFENDANT'
                    ? 'Asistenti juaj ligjor me AI për ndërtimin e mbrojtjes strategjike, rrëzimin e padisë dhe analizën e thellë të dokumenteve të lëndës.'
                    : 'Asistenti juaj ligjor me AI për vërtetimin e kërkesëpadisë, provimin e përgjegjësisë dhe argumentimin e të drejtave të klientit.'}
                </p>

                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-surface border border-main rounded-lg text-[9px] sm:text-[10px] text-text-muted font-medium mt-1">
                  <Info size={11} className="text-primary-start shrink-0" />
                  <span>Përgjigjet e AI shërbejnë për referencë dhe verifikohen nga avokati.</span>
                </div>
              </div>

              {/* 2x2 COMMAND CARDS GRID */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3 w-full max-w-xl text-left mt-1">
                {[
                  {
                    title: clientPosition === 'DEFENDANT' ? 'STRATEGJIA E MBROJTJES' : 'STRATEGJIA E PADISË',
                    badge: clientPosition === 'DEFENDANT' ? 'MBROJTJA & ARGUMENTET' : 'SULMI & PRETEGIMET',
                    icon: ShieldCheck,
                    prompt:
                      clientPosition === 'DEFENDANT'
                        ? 'Identifiko 3 pikat kryesore të pretendimeve mbrojtëse dhe provat mbështetëse në të gjitha dokumentet e lëndës.'
                        : 'Identifiko 3 pikat kryesore ku mbështetet padia jonë dhe provat vendimtare në fashikull.'
                  },
                  {
                    title: 'BAZA LIGJORE & PROCEDURA',
                    badge: 'LPK & KODET LIGJORE',
                    icon: Scale,
                    prompt: 'Analizo përputhshmërinë e veprimeve të palëve me nenet përkatëse të Ligjit për Procedurën Kontestimore (LPK).'
                  },
                  {
                    title: 'PYETËSORI I SEANCËS',
                    badge: 'MARRJA NË PYETJE',
                    icon: Gavel,
                    prompt: 'Gjenero pyetjet kritike dhe kundër-pyetjet taktike për dëgjimin e palëve dhe dëshmitarëve në seancë.'
                  },
                  {
                    title: 'RAPORTI PËR KLIENTIN',
                    badge: 'MEMO TEKNIKE',
                    icon: FileText,
                    prompt: 'Përgatit një përmbledhje ekzekutive të strukturuar mbi rreziqet ligjore dhe hapat e mëtejshëm për informimin e klientit.'
                  }
                ].map((card, idx) => {
                  const IconComponent = card.icon;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => sendMessage(card.prompt)}
                      className="group p-3 sm:p-3.5 bg-surface hover:bg-hover border border-main hover:border-primary-start/60 rounded-2xl text-left transition-all duration-200 shadow-sm flex flex-col justify-between gap-1.5 active:scale-[0.98] cursor-pointer"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[8px] sm:text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-primary-start/10 text-primary-start border border-primary-start/20 tracking-wider">
                          {card.badge}
                        </span>
                        <ChevronRight size={13} className="text-text-muted group-hover:text-primary-start transition-colors" />
                      </div>

                      <div className="flex items-center gap-2 mt-0.5">
                        <IconComponent size={14} className="text-primary-start shrink-0" />
                        <h4 className="text-[11px] sm:text-xs font-black uppercase text-text-primary tracking-wide group-hover:text-primary-start transition-colors">
                          {card.title}
                        </h4>
                      </div>

                      <p className="text-[10px] sm:text-[11px] text-text-secondary leading-relaxed font-normal line-clamp-2">
                        {card.prompt}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {safeMessages.filter(m => m && typeof m.content === 'string' && m.content.trim() !== "").map((msg, idx) => {
            const { cleanText, questions: suggestedQuestions } = extractFollowUpQuestions(msg.content);
            const autoLinkedText = autoLinkLegalCitations(cleanText);
            
            return (
              <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 group ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border shadow-sm ${msg.role === 'ai' ? 'bg-primary-start text-white border-primary-start' : 'bg-surface border-main text-text-secondary'}`}>
                  {msg.role === 'ai' ? <BrainCircuit size={16} /> : <User size={16} />}
                </div>
                
                <div className={`relative max-w-[88%] rounded-xl py-3 px-4 text-xs sm:text-sm shadow-sm border border-main bg-surface text-text-primary ${msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'}`}>
                  <MessageCopyButton text={msg.content} />
                  
                  <div className="markdown-content select-text prose prose-slate max-w-none prose-sm leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents(t)}>{autoLinkedText}</ReactMarkdown>
                  </div>
                  
                  {msg.role === 'ai' && idx === safeMessages.length - 1 && !isSendingMessage && suggestedQuestions.length > 0 && (
                      <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-main animate-in fade-in slide-in-from-bottom-2 duration-300">
                          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                              <Sparkles size={11} className="text-primary-start animate-pulse" /> {t('chat.suggestedFollowUps', 'Pyetje Sugjeruese')}
                          </span>
                          <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                              {suggestedQuestions.map((q, qIdx) => (
                                  <button
                                      key={qIdx}
                                      type="button"
                                      onClick={() => sendMessage(q)}
                                      className="px-3 py-2 bg-surface border border-main hover:border-primary-start/40 text-text-secondary hover:text-text-primary rounded-xl text-xs font-semibold text-left transition-all hover-lift focus:outline-none shadow-sm flex items-center gap-1.5"
                                  >
                                      <span className="w-1.5 h-1.5 bg-primary-start/40 rounded-full shrink-0" />
                                      {q}
                                  </button>
                              ))}
                          </div>
                      </div>
                  )}

                  {msg.role === 'ai' && activeContextId !== 'general' && typeof msg.content === 'string' && !msg.content.startsWith('[Gabim Teknik') && (
                    <FeedbackButtons messageIndex={idx} caseId={activeContextId} onFeedback={(i, f) => handleFeedback(i, f)} disabled={feedbackGiven.has(idx)} />
                  )}
                  {msg.role === 'ai' && typeof msg.content === 'string' && msg.content.startsWith('[Gabim Teknik') && (
                    <button 
                        type="button"
                        onClick={handleRetry} 
                        className="mt-3 px-3 py-2 bg-danger-start/10 text-danger-start rounded-lg text-[10px] font-semibold uppercase flex items-center gap-1.5 hover:bg-danger-start/20 transition-all hover-lift focus:outline-none"
                    >
                      <RefreshCw size={12} /> {t('chat.retry', 'Riprovo')}
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
          {showThinking && (
            <motion.div key="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-3 animate-pulse">
              <div className="w-8 h-8 rounded-lg bg-primary-start text-white flex items-center justify-center shadow-sm"><BrainCircuit size={16} /></div>
              <div className="bg-surface border border-main rounded-xl rounded-tl-sm px-4 py-2.5 shadow-sm flex items-center gap-2">
                <span className="text-xs font-semibold text-primary-start uppercase tracking-wide">{t('chat.thinking', 'Analizimi')}</span>
                <ThinkingDots />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* INPUT AREA */}
      <div className="p-3 sm:p-4 bg-surface shrink-0 z-20">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="max-w-5xl mx-auto">
          <div className="flex items-end gap-2 bg-canvas border border-main rounded-xl p-2 transition-all focus-within:ring-2 focus-within:ring-primary-start/20 focus-within:border-primary-start/50 shadow-sm">
            <textarea 
              ref={textareaRef} 
              value={input} 
              onChange={(e) => setInput(e.target.value)} 
              onKeyDown={handleKeyDown} 
              placeholder={t('chatPanel.inputPlaceholder', 'Shkruaj mesazhin tuaj këtu...')} 
              className="flex-1 p-2 bg-transparent text-xs sm:text-sm leading-relaxed text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[40px] max-h-[200px] border-0 outline-none ring-0 scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden" 
              rows={1} 
            />
            <button 
              type="submit" 
              disabled={!input.trim() || isSendingMessage} 
              className="h-9 w-9 flex items-center justify-center bg-primary-start text-white rounded-lg shadow-md shadow-primary-start/15 hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 mb-0.5 focus:outline-none hover-lift"
            >
              <Send size={15} className="ml-0.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;