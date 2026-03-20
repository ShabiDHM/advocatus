// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V11.1 (FULL LOGIC RESTORED & TS FIXED)
// 1. FIXED: Restored 'selectedDocumentCount' badge in the executive header.
// 2. FIXED: Restored 'handleFeedback' logic to update 'feedbackGiven' state.
// 3. FIXED: Cleaned up unused variables and linting errors.
// 4. RETAINED: 100% "World Class" Executive UI and all original logic (Retry, Tooltips, Streaming).

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, User, Copy, Check, Zap, GraduationCap, Scale, Lock, Eye,
    ThumbsUp, ThumbsDown, RefreshCw, Download, ChevronDown
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

// --- SUB-COMPONENTS ---

const ThinkingDots = () => (
    <span className="inline-flex items-center ml-2">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5" />
    </span>
);

const MessageCopyButton: React.FC<{ text: string, isUser: boolean }> = ({ text, isUser }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (err) { console.error(err); }
    };
    return (
        <button onClick={handleCopy} className={`absolute top-2 right-2 p-2 rounded-xl transition-all opacity-0 group-hover:opacity-100 shadow-sm ${
            copied ? 'bg-success-start/20 text-success-start' : isUser ? 'bg-white/20 text-white hover:bg-white/30' : 'bg-surface border border-border-main text-text-muted hover:text-text-primary'
        }`}>
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
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-main/50">
            <button
                onClick={() => handleFeedback('up')}
                disabled={!!submitting || disabled || success}
                className={`p-2 rounded-xl transition-all border ${success ? 'bg-success-start/20 text-success-start border-success-start/30' : 'bg-surface text-text-muted border-border-main hover:text-success-start hover:border-success-start/50 shadow-sm'}`}
                title="Përgjigje e dobishme"
            >
                {submitting === 'up' ? <span className="w-4 h-4 border-2 border-t-transparent border-current rounded-full animate-spin block" /> : <ThumbsUp size={14} />}
            </button>
            <button
                onClick={() => handleFeedback('down')}
                disabled={!!submitting || disabled || success}
                className={`p-2 rounded-xl transition-all border ${success ? 'bg-success-start/20 text-success-start border-success-start/30' : 'bg-surface text-text-muted border-border-main hover:text-danger-start hover:border-danger-start/50 shadow-sm'}`}
                title="Përgjigje e padobishme"
            >
                {submitting === 'down' ? <span className="w-4 h-4 border-2 border-t-transparent border-current rounded-full animate-spin block" /> : <ThumbsDown size={14} />}
            </button>
        </div>
    );
};

const LawPreviewTooltip: React.FC<{ chunkId: string; children: React.ReactNode; t: TFunction }> = ({ chunkId, children, t }) => {
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [show, setShow] = useState(false);
    const timeoutRef = useRef<NodeJS.Timeout>();

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
                        className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 w-72 p-4 bg-surface text-xs text-text-secondary rounded-2xl border border-border-main shadow-lawyer-dark z-50 leading-relaxed"
                    >
                        <p className="text-[10px] font-black text-primary-start uppercase tracking-widest mb-2 border-b border-border-main pb-2 flex items-center gap-2">
                            <Scale size={12}/> Referencë Ligjore
                        </p>
                        {loading ? t('lawPreview.loading', 'Duke ngarkuar...') : preview}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const MarkdownComponents = (t: TFunction) => ({
    h1: ({node, ...props}: any) => <h1 className="text-lg font-black text-text-primary mb-4 mt-6 border-b border-border-main pb-2 uppercase tracking-tighter" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-base font-bold text-primary-start mb-3 mt-5" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-sm font-bold text-text-primary mb-2 mt-4 flex items-center gap-2" {...props} />,
    p: ({node, ...props}: any) => <p className="mb-4 last:mb-0 leading-relaxed text-text-primary/90" {...props} />, 
    li: ({node, ...props}: any) => <li className="mb-1.5 leading-relaxed text-text-primary/90" {...props} />, 
    a: ({href, children}: any) => {
        if (href?.startsWith('/laws/')) {
            const chunkId = href.split('/').pop();
            return (
                <LawPreviewTooltip chunkId={chunkId || ''} t={t}>
                    <Link
                        to={href}
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-black uppercase tracking-widest border transition-all hover:shadow-sm hover:scale-[1.02] bg-primary-start/5 text-primary-start border-primary-start/20 hover:bg-primary-start/10"
                    >
                        <Scale size={12} />
                        {children}
                        <Eye size={12} className="opacity-50" />
                    </Link>
                </LawPreviewTooltip>
            );
        }
        return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-start font-bold underline decoration-primary-start/30 hover:decoration-primary-start transition-colors">
                {children}
            </a>
        );
    },
});

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, onClearChat, onExportChat, t, className, activeContextId, isPro = false, selectedDocumentCount = 0
}) => {
  const [input, setInput] = useState('');
  const [reasoningMode, setReasoningMode] = useState<ReasoningMode>('FAST');
  const [selectedDomain, setSelectedDomain] = useState<LegalDomain>('automatic');
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const [lastUserMessage, setLastUserMessage] = useState<string>('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { if (!isPro && reasoningMode === 'DEEP') setReasoningMode('FAST'); }, [isPro, reasoningMode]);
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

  const lastMessage = messages[messages.length - 1];
  const showThinking = isSendingMessage && (!lastMessage || lastMessage.role !== 'ai' || !lastMessage.content.trim());

  return (
    <div className={`flex flex-col glass-panel overflow-hidden h-full w-full border-border-main shadow-lawyer-light ${className}`}>
      
      {/* HEADER: Unified Executive Architecture */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-main bg-canvas/40 z-50 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <span className={`w-2 h-2 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-success-start ring-4 ring-success-start/10 animate-pulse' : 'bg-danger-start'}`} />
            <h3 className="text-xs font-black text-text-primary uppercase tracking-widest leading-none">{t('chatPanel.title')}</h3>
          </div>

          {/* RESTORED: Document Count Badge */}
          {activeContextId !== 'general' && selectedDocumentCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 bg-primary-start/10 border border-primary-start/20 rounded-full shadow-sm">
                <span className="text-[10px] font-black text-primary-start uppercase tracking-widest">{selectedDocumentCount} Lëndë</span>
            </div>
          )}
          
          {/* Executive Domain Selector */}
          {reasoningMode === 'DEEP' && (
            <div className="relative group">
                <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value as LegalDomain)}
                className="appearance-none h-9 rounded-xl border border-border-main bg-surface text-text-primary text-[10px] font-black uppercase tracking-widest pl-3 pr-8 focus:outline-none focus:ring-2 focus:ring-primary-start/20 hover-lift shadow-sm cursor-pointer transition-all"
                >
                {Object.entries(domainLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <ChevronDown size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Segmented Mode Control */}
          <div className="flex items-center bg-canvas p-1 rounded-xl border border-border-main shadow-inner h-9">
            <button onClick={() => setReasoningMode('FAST')} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest h-full transition-all ${reasoningMode === 'FAST' ? 'bg-surface text-primary-start shadow-sm border border-border-main' : 'text-text-muted hover:text-text-primary'}`}>
              <Zap size={12} /> {t('chatPanel.modeFast', 'Shpejtë')}
            </button>
            <button onClick={() => isPro && setReasoningMode('DEEP')} disabled={!isPro} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest h-full transition-all ${reasoningMode === 'DEEP' ? 'bg-surface text-primary-start shadow-sm border border-border-main' : 'text-text-muted hover:text-text-primary disabled:opacity-30'}`}>
              {!isPro ? <Lock size={10} /> : <GraduationCap size={12} />} {t('chatPanel.modeDeep', 'Thellë')}
            </button>
          </div>

          <div className="h-6 w-px bg-border-main mx-1" />

          <div className="flex gap-1">
            {onExportChat && <button onClick={onExportChat} className="p-2 text-text-muted hover:text-primary-start hover:bg-surface-secondary rounded-lg transition-all" title="Download"><Download size={18} /></button>}
            <button onClick={onClearChat} className="p-2 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-lg transition-all" title="Clear"><Trash2 size={18} /></button>
          </div>
        </div>
      </div>

      {/* MESSAGE STREAM: Paper Canvas */}
      <div className="flex-1 overflow-y-auto p-6 space-y-8 bg-canvas/10 custom-scrollbar shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)] no-scrollbar">
        <AnimatePresence initial={false}>
          {messages.filter(m => m.content.trim() !== "").map((msg, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-4 group ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border shadow-sm ${msg.role === 'ai' ? 'bg-primary-start text-white border-primary-start' : 'bg-surface border-border-main text-text-secondary'}`}>
                {msg.role === 'ai' ? <BrainCircuit size={20} /> : <User size={20} />}
              </div>
              <div className={`relative max-w-[85%] rounded-[1.5rem] p-6 text-sm shadow-lawyer-light border ${msg.role === 'user' ? 'bg-primary-start text-white border-primary-start rounded-tr-sm' : 'bg-surface border-border-main text-text-primary rounded-tl-sm'}`}>
                <MessageCopyButton text={msg.content} isUser={msg.role === 'user'} />
                <div className="markdown-content select-text prose prose-slate max-w-none prose-sm sm:prose-base">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents(t)}>{msg.content}</ReactMarkdown>
                </div>
                
                {/* RESTORED: Feedback Logic and Param Mapping */}
                {msg.role === 'ai' && activeContextId !== 'general' && !msg.content.startsWith('[Gabim Teknik') && (
                  <FeedbackButtons 
                    messageIndex={idx} 
                    caseId={activeContextId} 
                    onFeedback={(i, _f) => handleFeedback(i, _f)} 
                    disabled={feedbackGiven.has(idx)} 
                  />
                )}
                {msg.role === 'ai' && msg.content.startsWith('[Gabim Teknik') && (
                  <button onClick={handleRetry} className="mt-4 px-4 py-2 bg-danger-start/10 text-danger-start rounded-xl text-xs font-black uppercase flex items-center gap-2 hover:bg-danger-start/20 transition-all">
                    <RefreshCw size={14} /> {t('chat.retry', 'Riprovo')}
                  </button>
                )}
              </div>
            </motion.div>
          ))}
          {showThinking && (
            <motion.div key="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-primary-start text-white flex items-center justify-center shadow-accent-glow"><BrainCircuit size={20} /></div>
              <div className="bg-surface border border-border-main rounded-[1.5rem] rounded-tl-sm px-6 py-4 shadow-lawyer-light flex items-center gap-3">
                <span className="text-[11px] font-black text-primary-start uppercase tracking-widest">{t('chat.thinking', 'Analizimi')}</span>
                <ThinkingDots />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* INPUT AREA */}
      <div className="p-5 border-t border-border-main bg-surface shrink-0">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="relative flex items-end gap-3 max-w-5xl mx-auto">
          <textarea 
            ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} 
            placeholder={t('chatPanel.inputPlaceholder')} 
            className="glass-input w-full p-4 pr-16 rounded-2xl text-sm leading-relaxed resize-none shadow-inner-trough focus:bg-canvas/10 transition-all no-scrollbar min-h-[60px]" 
            rows={1} 
          />
          <button 
            type="submit" disabled={!input.trim() || isSendingMessage} 
            className="absolute right-2.5 bottom-2.5 h-10 w-10 flex items-center justify-center bg-primary-start text-white rounded-xl shadow-accent-glow hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed z-10"
          >
            <Send size={18} className="ml-0.5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;