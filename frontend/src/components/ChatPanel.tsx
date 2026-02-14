// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V5.11 (FULLY INTERNATIONALIZED)
// 1. FIXED: All hardcoded strings replaced with translation keys.
// 2. ADDED: Keys for law preview loading/error, thinking state.
// 3. STATUS: Ready for i18n.

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, User, Copy, Check, Zap, GraduationCap, Scale, Lock, Eye
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

interface ChatPanelProps {
  messages: ChatMessage[];
  connectionStatus: string;
  reconnect: () => void;
  onSendMessage: (text: string, mode: ChatMode, reasoning: ReasoningMode, documentId?: string, jurisdiction?: Jurisdiction) => void;
  isSendingMessage: boolean;
  onClearChat: () => void;
  t: TFunction;
  className?: string;
  activeContextId: string;
  isPro?: boolean;
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
        <button onClick={handleCopy} className={`absolute top-2 right-2 p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 ${copied ? 'bg-emerald-500/20 text-emerald-400' : isUser ? 'bg-white/10 text-white/70' : 'bg-white/5 text-gray-400 hover:text-white'}`}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
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
                        className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 glass-high text-xs text-gray-300 rounded-xl border border-white/10 shadow-2xl z-50"
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
    h1: ({node, ...props}: any) => <h1 className="text-xl font-bold text-white mb-4 mt-6 border-b border-white/10 pb-2 uppercase tracking-wider" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-lg font-bold text-primary-start mb-3 mt-5" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-md font-bold text-accent-end mb-2 mt-4 flex items-center gap-2" {...props} />,
    p: ({node, ...props}: any) => <p className="mb-3 last:mb-0 leading-relaxed text-gray-200" {...props} />, 
    a: ({href, children}: any) => {
        // For law links (/laws/...), render as a clickable badge with React Router Link
        if (href?.startsWith('/laws/')) {
            const chunkId = href.split('/').pop();
            return (
                <LawPreviewTooltip chunkId={chunkId} t={t}>
                    <Link
                        to={href}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border transition-all hover:shadow-lg hover:scale-105 bg-secondary-start/20 text-secondary-start border-secondary-start/30"
                    >
                        <Scale size={12} />
                        {children}
                        <Eye size={12} className="opacity-70" />
                    </Link>
                </LawPreviewTooltip>
            );
        }
        // For external links, use normal anchor
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
    messages, connectionStatus, onSendMessage, isSendingMessage, onClearChat, t, className, activeContextId, isPro = false 
}) => {
  const [input, setInput] = useState('');
  const [reasoningMode, setReasoningMode] = useState<ReasoningMode>('FAST');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { if (!isPro && reasoningMode === 'DEEP') setReasoningMode('FAST'); }, [isPro, reasoningMode]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);
  useEffect(() => { if (textareaRef.current) { textareaRef.current.style.height = 'auto'; textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`; } }, [input]);

  const sendMessage = () => {
    if (!input.trim() || isSendingMessage) return;
    onSendMessage(input, activeContextId === 'general' ? 'general' : 'document', reasoningMode, activeContextId === 'general' ? undefined : activeContextId, 'ks');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } };
  
  // Determine if we should show the branded thinking state
  const lastMessage = messages[messages.length - 1];
  const showThinking = isSendingMessage && (!lastMessage || lastMessage.role !== 'ai' || !lastMessage.content.trim());

  return (
    <div className={`flex flex-col glass-panel rounded-2xl overflow-hidden h-full w-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/5 backdrop-blur-sm z-50">
        <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-red-500'}`} />
            <h3 className="text-sm font-bold text-white">{t('chatPanel.title')}</h3>
        </div>
        <div className="flex items-center gap-2">
            <div className="flex items-center bg-black/30 rounded-lg p-0.5 border border-white/5">
                <button onClick={() => setReasoningMode('FAST')} className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-bold transition-all ${reasoningMode === 'FAST' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-500'}`}>
                    <Zap size={12} /> {t('chatPanel.modeFast')}
                </button>
                <button onClick={() => isPro && setReasoningMode('DEEP')} disabled={!isPro} className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-bold transition-all ${reasoningMode === 'DEEP' ? 'bg-purple-500/20 text-purple-400' : 'text-gray-600'}`}>
                    {!isPro ? <Lock size={10} className="mr-1" /> : <GraduationCap size={12} className="mr-1" />}
                    {t('chatPanel.modeDeep')}
                </button>
            </div>
            <button onClick={onClearChat} className="p-2 text-text-secondary hover:text-red-400 transition-colors"><Trash2 size={16} /></button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-black/20 custom-scrollbar relative">
        <AnimatePresence initial={false}>
            {messages.filter(m => m.content.trim() !== "").map((msg, idx) => (
                <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg shrink-0"><BrainCircuit className="w-4 h-4 text-white" /></div>}
                    <div className={`relative group max-w-[85%] rounded-2xl px-5 py-3.5 text-sm shadow-xl ${msg.role === 'user' ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' : 'glass-panel text-text-primary rounded-bl-none'}`}>
                        <MessageCopyButton text={msg.content} isUser={msg.role === 'user'} />
                        <div className="markdown-content select-text">
                            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents(t)}>{msg.content}</ReactMarkdown>
                        </div>
                    </div>
                    {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center border border-white/5 shrink-0"><User className="w-4 h-4 text-text-secondary" /></div>}
                </motion.div>
            ))}

            {showThinking && (
                <motion.div key="thinking-state" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary-start flex items-center justify-center shadow-lg"><BrainCircuit className="w-4 h-4 text-white" /></div>
                    <div className="glass-panel text-blue-400 font-bold rounded-2xl px-5 py-3.5 text-sm flex items-center gap-1 border border-blue-500/20 shadow-blue-500/5">
                        {t('chat.thinking', 'Sokrati duke menduar')}<ThinkingDots />
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
        
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-white/5 bg-white/5 backdrop-blur-md">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(); }} className="relative flex items-end gap-2">
            <textarea ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={t('chatPanel.inputPlaceholder')} className="glass-input w-full p-4 rounded-xl text-sm resize-none custom-scrollbar" rows={1} />
            <button type="submit" disabled={!input.trim() || isSendingMessage} className="p-3 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl shadow-lg shadow-primary-start/20 active:scale-95 transition-all"><Send size={18} /></button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;