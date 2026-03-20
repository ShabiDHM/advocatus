// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V7.1 (EXECUTIVE DOMAIN SELECTOR & UNIFIED BUTTON)
// 1. RESTYLED: Domain selector now matches action bar cards (same height, border, bg-surface/10, hover-lift).
// 2. UNIFIED: Send button uses bg-primary-start with brightness hover.
// 3. FIXED: All colors use semantic variables.
// 4. RETAINED: All features (document badge, export, retry, feedback).

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, User, Copy, Check, Zap, GraduationCap, Scale, Lock, Eye,
    ThumbsUp, ThumbsDown, RefreshCw, Download
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

// Map for display labels
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
    <span className="inline-flex items-center ml-1">
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
        <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }} className="w-1 h-1 bg-current rounded-full mx-0.5" />
    </span>
);

const MessageCopyButton: React.FC<{ text: string, isUser: boolean }> = ({ text, isUser }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (err) { console.error(err); }
    };
    return (
        <button onClick={handleCopy} className={`absolute top-2 right-2 p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 ${
            copied ? 'bg-success-start/20 text-success-start' : isUser ? 'bg-white/10 text-white/70' : 'bg-surface/10 text-text-secondary hover:text-text-primary'
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
        } catch (error) {
            console.error('Feedback failed:', error);
        } finally {
            setSubmitting(null);
        }
    };

    return (
        <div className="flex items-center gap-1 mt-2">
            <button
                onClick={() => handleFeedback('up')}
                disabled={!!submitting || disabled || success}
                className={`p-1.5 rounded-lg transition-all ${success ? 'bg-success-start/20 text-success-start' : 'bg-surface/10 text-text-secondary hover:text-text-primary hover:bg-surface/20'}`}
                title="Përgjigje e dobishme"
            >
                {submitting === 'up' ? <span className="w-4 h-4 border-2 border-t-transparent border-current rounded-full animate-spin" /> : <ThumbsUp size={14} />}
            </button>
            <button
                onClick={() => handleFeedback('down')}
                disabled={!!submitting || disabled || success}
                className={`p-1.5 rounded-lg transition-all ${success ? 'bg-success-start/20 text-success-start' : 'bg-surface/10 text-text-secondary hover:text-text-primary hover:bg-surface/20'}`}
                title="Përgjigje e padobishme"
            >
                {submitting === 'down' ? <span className="w-4 h-4 border-2 border-t-transparent border-current rounded-full animate-spin" /> : <ThumbsDown size={14} />}
            </button>
        </div>
    );
};

// Tooltip component for law preview
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

    const handleMouseEnter = () => {
        timeoutRef.current = setTimeout(() => setShow(true), 400);
    };
    const handleMouseLeave = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setShow(false);
    };

    return (
        <div className="relative inline-block" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
            {children}
            <AnimatePresence>
                {show && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 glass-panel text-xs text-text-secondary rounded-xl border border-main shadow-2xl z-50"
                    >
                        {loading ? t('lawPreview.loading', 'Duke ngarkuar...') : preview}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// Custom markdown components
const MarkdownComponents = (t: TFunction) => ({
    h1: ({node, ...props}: any) => <h1 className="text-xl font-bold text-text-primary mb-4 mt-6 border-b border-main pb-2 uppercase tracking-wider" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-lg font-bold text-primary-start mb-3 mt-5" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-md font-bold text-primary-start mb-2 mt-4 flex items-center gap-2" {...props} />,
    p: ({node, ...props}: any) => <p className="mb-3 last:mb-0 leading-relaxed text-text-secondary" {...props} />, 
    a: ({href, children}: any) => {
        if (href?.startsWith('/laws/')) {
            const chunkId = href.split('/').pop();
            return (
                <LawPreviewTooltip chunkId={chunkId} t={t}>
                    <Link
                        to={href}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border transition-all hover:shadow-lg hover:scale-105 bg-primary-start/10 text-primary-start border-primary-start/30"
                    >
                        <Scale size={12} />
                        {children}
                        <Eye size={12} className="opacity-70" />
                    </Link>
                </LawPreviewTooltip>
            );
        }
        return (
            <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-start hover:underline cursor-pointer"
            >
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
  useEffect(() => { if (textareaRef.current) { textareaRef.current.style.height = 'auto'; textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`; } }, [input]);

  const sendMessage = (text: string) => {
    if (!text.trim() || isSendingMessage) return;
    const mode = activeContextId === 'general' ? 'general' : 'document';
    setLastUserMessage(text);
    onSendMessage(text, mode, reasoningMode, selectedDomain, [], 'ks');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } };
  
  const handleFeedback = (index: number, _feedback: 'up' | 'down') => {
    setFeedbackGiven(prev => new Set(prev).add(index));
  };

  const handleRetry = () => {
    if (lastUserMessage) {
      sendMessage(lastUserMessage);
    }
  };

  const lastMessage = messages[messages.length - 1];
  const showThinking = isSendingMessage && (!lastMessage || lastMessage.role !== 'ai' || !lastMessage.content.trim());

  return (
    <div className={`flex flex-col glass-panel rounded-panel overflow-hidden h-full w-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-main bg-surface/5 backdrop-blur-sm z-50">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-success-start shadow-[0_0_10px_#10b981]' : 'bg-danger-start'}`} />
          <h3 className="text-sm font-black text-text-primary">{t('chatPanel.title')}</h3>
          {activeContextId !== 'general' && selectedDocumentCount > 0 && (
            <div className="flex items-center gap-1 bg-surface/20 border border-main rounded-full px-2 py-0.5 text-xs text-text-secondary">
              <span>{selectedDocumentCount} dokumente</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Domain selection dropdown – only visible in deep mode, styled like action cards */}
          {reasoningMode === 'DEEP' && (
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value as LegalDomain)}
              className="h-8 md:h-7 rounded-lg border border-main bg-surface/10 text-text-secondary text-xs font-medium px-2 focus:outline-none focus:ring-1 focus:ring-primary-start/40 hover:bg-surface/20 hover-lift transition-all"
            >
              {Object.entries(domainLabels).map(([value, label]) => (
                <option key={value} value={value} className="bg-surface text-text-primary">{label}</option>
              ))}
            </select>
          )}
          {/* Mode toggle */}
          <div className="flex items-center bg-surface/10 rounded-lg p-0.5 border border-main">
            <button onClick={() => setReasoningMode('FAST')} className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-bold transition-all ${
                reasoningMode === 'FAST' ? 'bg-blue-500/20 text-blue-400' : 'text-text-secondary'
            }`}>
              <Zap size={12} /> {t('chatPanel.modeFast')}
            </button>
            <button onClick={() => isPro && setReasoningMode('DEEP')} disabled={!isPro} className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-bold transition-all ${
                reasoningMode === 'DEEP' ? 'bg-purple-500/20 text-purple-400' : 'text-text-secondary'
            }`}>
              {!isPro ? <Lock size={10} className="mr-1" /> : <GraduationCap size={12} className="mr-1" />}
              {t('chatPanel.modeDeep')}
            </button>
          </div>
          {/* Export button */}
          {onExportChat && (
            <button onClick={onExportChat} className="p-2 text-text-secondary hover:text-primary-start transition-colors" title="Shkarko bisedën">
              <Download size={16} />
            </button>
          )}
          <button onClick={onClearChat} className="p-2 text-text-secondary hover:text-danger-start transition-colors"><Trash2 size={16} /></button>
        </div>
      </div>

      {/* Message area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-10 bg-surface custom-scrollbar">
        <AnimatePresence initial={false}>
          {messages.filter(m => m.content.trim() !== "").map((msg, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg shrink-0"><BrainCircuit className="w-4 h-4 text-white" /></div>}
              <div className={`relative group max-w-[85%] rounded-2xl px-5 py-3.5 text-sm shadow-xl ${
                  msg.role === 'user' 
                      ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' 
                      : 'bg-surface/80 backdrop-blur-sm border border-main text-text-primary rounded-bl-none'
              }`}>
                <MessageCopyButton text={msg.content} isUser={msg.role === 'user'} />
                <div className="markdown-content select-text">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents(t)}>{msg.content}</ReactMarkdown>
                </div>
                {msg.role === 'ai' && activeContextId !== 'general' && !msg.content.startsWith('[Gabim Teknik') && (
                  <FeedbackButtons
                    messageIndex={idx}
                    caseId={activeContextId}
                    onFeedback={handleFeedback}
                    disabled={feedbackGiven.has(idx)}
                  />
                )}
                {msg.role === 'ai' && msg.content.startsWith('[Gabim Teknik') && (
                  <div className="flex items-center gap-2 mt-2">
                    <button
                      onClick={handleRetry}
                      className="px-3 py-1 bg-primary-start/20 hover:bg-primary-start/30 text-primary-start rounded-lg text-xs font-medium transition-all flex items-center gap-1"
                    >
                      <RefreshCw size={12} />
                      {t('chat.retry', 'Provo përsëri')}
                    </button>
                  </div>
                )}
              </div>
              {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-surface/20 flex items-center justify-center border border-main shrink-0"><User className="w-4 h-4 text-text-secondary" /></div>}
            </motion.div>
          ))}

          {showThinking && (
            <motion.div key="thinking-state" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-primary-start flex items-center justify-center shadow-lg"><BrainCircuit className="w-4 h-4 text-white" /></div>
              <div className="bg-surface border border-blue-500/20 text-blue-400 font-bold rounded-2xl px-5 py-3.5 text-sm flex items-center gap-1 shadow-blue-500/5">
                {t('chat.thinking', 'Sokrati duke menduar')}<ThinkingDots />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-main bg-surface/5 backdrop-blur-md">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="relative flex items-end gap-2">
          <textarea ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={t('chatPanel.inputPlaceholder')} className="glass-input w-full p-4 rounded-xl text-sm resize-none custom-scrollbar" rows={1} />
          <button type="submit" disabled={!input.trim() || isSendingMessage} className="h-12 w-12 flex items-center justify-center bg-primary-start text-white rounded-xl shadow-accent-glow hover:brightness-110 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;