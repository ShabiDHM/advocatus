// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V13.0 (INTERACTIVE FOLLOW-UP PILLS)
// FIX: Added dynamic client-side parsing to extract and render 3 interactive, clickable follow-up question pills.
// FIX: Spacing hierarchy fully optimized for high-density reading.

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, User, Copy, Check, Scale, Eye,
    ThumbsUp, ThumbsDown, RefreshCw, Download, ChevronDown, Sparkles
} from 'lucide-react';
import { ChatMessage } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';

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
}

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-2">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
    </span>
);

// Helper to split AI response into clean Markdown content and structured follow-up questions
const extractFollowUpQuestions = (text: string): { cleanText: string; questions: string[] } => {
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

const MessageCopyButton: React.FC<{ text: string, isUser: boolean }> = ({ text, isUser }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        try { 
            const { cleanText } = extractFollowUpQuestions(text);
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
                  : isUser 
                    ? 'bg-white/20 text-white hover:bg-white/30' 
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

const LawPreviewTooltip: React.FC<{ chunkId: string; children: React.ReactNode; t: TFunction }> = ({ chunkId, children, t }) => {
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [show, setShow] = useState(false);
    const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

    useEffect(() => {
        if (show && !preview && !loading) {
            setLoading(true);
            apiService.getLawByChunkId(chunkId)
                .then(data => setPreview(data.text.substring(0, 200) + '...'))
                .catch(() => setPreview(t('lawPreview.error', 'Nuk u ngarkua')))
                .finally(() => setLoading(false));
        }
    }, [show, chunkId, preview, loading, t]);

    return (
        <div className="relative inline-block" onMouseEnter={() => { timeoutRef.current = setTimeout(() => setShow(true), 400); }} onMouseLeave={() => { if (timeoutRef.current) clearTimeout(timeoutRef.current); setShow(false); }}>
            {children}
            <AnimatePresence>
                {show && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 w-72 p-4 bg-surface text-sm text-text-secondary rounded-2xl border border-main shadow-2xl z-50 leading-relaxed"
                    >
                        <p className="text-xs font-bold text-primary-start uppercase tracking-wide mb-2 border-b border-main pb-2 flex items-center gap-2">
                            <Scale size={12}/> {t('chat.lawReference', 'Referencë Ligjore')}
                        </p>
                        {loading ? t('lawPreview.loading', 'Duke ngarkuar...') : preview}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const MarkdownComponents = (t: TFunction) => ({
    h1: ({node, ...props}: any) => <h1 className="text-lg font-bold text-text-primary mb-2 mt-3 border-b border-main pb-1 uppercase tracking-tight" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-base font-semibold text-primary-start mb-1.5 mt-2" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-sm font-semibold text-text-primary mb-1 mt-1.5 flex items-center gap-2" {...props} />,
    p: ({node, ...props}: any) => <p className="mb-2 last:mb-0 leading-relaxed text-text-secondary" {...props} />, 
    li: ({node, ...props}: any) => <li className="mb-1 leading-relaxed text-text-secondary" {...props} />, 
    a: ({href, children}: any) => {
        if (href?.startsWith('/laws/')) {
            const chunkId = href.split('/').pop();
            return (
                <LawPreviewTooltip chunkId={chunkId || ''} t={t}>
                    <Link
                        to={href}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide border transition-all hover:shadow-sm hover:scale-[1.02] bg-primary-start/5 text-primary-start border-primary-start/20 hover:bg-primary-start/10"
                    >
                        <Scale size={10} />
                        {children}
                        <Eye size={10} className="opacity-50" />
                    </Link>
                </LawPreviewTooltip>
            );
        }
        return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-start font-semibold underline decoration-primary-start/30 hover:decoration-primary-start transition-colors">
                {children}
            </a>
        );
    },
});

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, onClearChat, onExportChat, t, className, activeContextId, selectedDocumentCount = 0
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
    
    // PHOENIX SYSTEM CONTEXT ANCHOR: Directs DeepSeek to always append exactly 3 short follow-up questions
    const enrichedQuery = `${text}\n\n(Ju lutem, në fund të përgjigjes suaj, shtoni një seksion të titulluar 'Sugjerime:' dhe rreshtoni saktësisht 3 pyetje të shkurtra vijuese që unë mund t'i bëj më pas në lidhje me këtë përgjigje. Formatizo si: \nSugjerime:\n1. Pyetja e parë?\n2. Pyetja e dytë?\n3. Pyetja e tretë?)`;
    
    setLastUserMessage(text);
    onSendMessage(enrichedQuery, mode, reasoningMode, selectedDomain, [], 'ks');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { 
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } 
  };
  
  const handleFeedback = (index: number, _feedback: 'up' | 'down') => {
    setFeedbackGiven(prev => new Set(prev).add(index));
  };

  const handleRetry = () => { if (lastUserMessage) sendMessage(lastUserMessage); };

  const lastMessage = messages[messages.length - 1];
  const showThinking = isSendingMessage && (!lastMessage || lastMessage.role !== 'ai' || !lastMessage.content.trim());

  return (
    <div className={`flex flex-col glass-panel overflow-hidden h-full w-full border border-main bg-canvas shadow-sm ${className}`}>
      
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between px-5 py-3.5 border-b border-main bg-surface z-50 shrink-0 gap-3 sm:gap-0">
        
        {/* Left group */}
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wide leading-none">
            {t('chatPanel.title')}
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
        <div className="flex items-center justify-end gap-2 h-9">
          <div className="relative group h-9 flex items-center">
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value as LegalDomain)}
              className="appearance-none h-9 rounded-xl border border-main bg-surface text-text-primary text-xs font-semibold pl-2.5 pr-7 focus:outline-none focus:ring-2 focus:ring-primary-start/20 hover-lift shadow-sm cursor-pointer transition-all"
            >
              {Object.entries(domainLabels).map(([value, label]) => <option key={value} value={value} className="bg-canvas text-text-primary">{label}</option>)}
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          </div>

          {onExportChat && (
            <button 
                type="button"
                onClick={onExportChat} 
                className="flex items-center justify-center w-9 h-9 text-text-muted hover:text-primary-start hover:bg-hover rounded-xl transition-all focus:outline-none" 
                title="Download"
            >
              <Download size={16} />
            </button>
          )}
          <button 
              type="button"
              onClick={onClearChat} 
              className="flex items-center justify-center w-9 h-9 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-xl transition-all focus:outline-none" 
              title="Clear"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* MESSAGE STREAM */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-canvas/10 custom-finance-scroll shadow-[inset_0_1px_8px_rgba(0,0,0,0.01)] border-b border-main">
        <AnimatePresence initial={false}>
          {messages.filter(m => m.content.trim() !== "").map((msg, idx) => {
            // Extract the clean Markdown content and the 3 follow-up questions
            const { cleanText, questions: suggestedQuestions } = extractFollowUpQuestions(msg.content);
            
            return (
              <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 group ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border shadow-sm ${msg.role === 'ai' ? 'bg-primary-start text-white border-primary-start' : 'bg-surface border-main text-text-secondary'}`}>
                  {msg.role === 'ai' ? <BrainCircuit size={16} /> : <User size={16} />}
                </div>
                <div className={`relative max-w-[88%] rounded-xl py-3 px-4 text-xs sm:text-sm shadow-sm border ${msg.role === 'user' ? 'bg-primary-start text-white border-primary-start rounded-tr-sm' : 'bg-surface border-main text-text-primary rounded-tl-sm'}`}>
                  <MessageCopyButton text={msg.content} isUser={msg.role === 'user'} />
                  
                  {/* Clean AI response (without raw suggestions text) */}
                  <div className="markdown-content select-text prose prose-slate max-w-none prose-sm leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents(t)}>{cleanText}</ReactMarkdown>
                  </div>
                  
                  {/* DYNAMIC INTERACTIVE FOLLOW-UP QUESTIONS */}
                  {msg.role === 'ai' && idx === messages.length - 1 && !isSendingMessage && suggestedQuestions.length > 0 && (
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
                                      <span className="w-1.5 h-1.5 bg-primary-start/40 rounded-full shrink-0 group-hover:bg-primary-start" />
                                      {q}
                                  </button>
                              ))}
                          </div>
                      </div>
                  )}

                  {msg.role === 'ai' && activeContextId !== 'general' && !msg.content.startsWith('[Gabim Teknik') && (
                    <FeedbackButtons messageIndex={idx} caseId={activeContextId} onFeedback={(i, f) => handleFeedback(i, f)} disabled={feedbackGiven.has(idx)} />
                  )}
                  {msg.role === 'ai' && msg.content.startsWith('[Gabim Teknik') && (
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
      <div className="p-4 bg-surface shrink-0">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="relative flex items-end gap-2 max-w-5xl mx-auto">
          <textarea 
            ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} 
            placeholder={t('chatPanel.inputPlaceholder')} 
            className="w-full p-3.5 pr-14 bg-canvas border border-main rounded-xl text-xs sm:text-sm leading-relaxed text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all resize-none custom-finance-scroll min-h-[50px]" 
            rows={1} 
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isSendingMessage} 
            className="absolute right-2 bottom-2 h-8 w-8 flex items-center justify-center bg-primary-start text-white rounded-lg shadow-lg shadow-primary-start/15 hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed z-10 hover-lift focus:outline-none"
          >
            <Send size={15} className="ml-0.5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;