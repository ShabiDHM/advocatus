// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V5.5 (VISUAL & BUILD SYNC)
// 1. RESTORED: 'FileCheck' and 'Lock' icons in the JSX tree to resolve TS6133 without losing features.
// 2. ENFORCED: Visual distinction for Evidence vs Law badges using icons.
// 3. STATUS: 0 Build Errors. Professional UI + Senior Partner Intelligence fully aligned.

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, Loader2, User, Copy, Check, Zap, GraduationCap, Scale, Globe, FileCheck, Lock 
} from 'lucide-react';
import { ChatMessage } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

const MarkdownComponents = {
    h1: ({node, ...props}: any) => <h1 className="text-xl font-bold text-white mb-4 mt-6 border-b border-white/10 pb-2 uppercase tracking-wider" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-lg font-bold text-primary-start mb-3 mt-5" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-md font-bold text-accent-end mb-2 mt-4 flex items-center gap-2" {...props} />,
    p: ({node, ...props}: any) => <p className="mb-3 last:mb-0 leading-relaxed text-gray-200" {...props} />, 
    a: ({href, children}: any) => {
        const getText = (child: any): string => {
            if (!child) return '';
            if (typeof child === 'string') return child;
            if (Array.isArray(child)) return child.map(getText).join('');
            return '';
        };
        const contentStr = getText(children);
        if (href?.startsWith('doc://')) {
            const isGlobal = ["UNCRC", "KEDNJ", "ECHR", "Konventa"].some(k => contentStr.includes(k));
            const isEvidence = contentStr.includes("Burimi") || contentStr.includes("Dokument");
            
            // PHOENIX RESTORATION: Use FileCheck for Evidence, Scale/Globe for Laws
            return (
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-bold border mx-1 align-middle transition-all shadow-sm ${
                    isEvidence ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                    isGlobal ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30' : 'bg-blue-500/10 text-blue-300 border-blue-500/30'
                }`}>
                    {isEvidence ? <FileCheck size={12} /> : isGlobal ? <Globe size={12} /> : <Scale size={12} />}
                    {children}
                </span>
            );
        }
        return <a className="text-primary-start hover:underline cursor-pointer" target="_blank" rel="noopener noreferrer" href={href}>{children}</a>;
    },
};

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
                <button onClick={() => setReasoningMode('FAST')} className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-bold transition-all ${reasoningMode === 'FAST' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-500'}`}><Zap size={12} /> FAST</button>
                <button onClick={() => isPro && setReasoningMode('DEEP')} disabled={!isPro} className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-bold transition-all ${reasoningMode === 'DEEP' ? 'bg-purple-500/20 text-purple-400' : 'text-gray-600'}`}>
                    {!isPro ? <Lock size={10} className="mr-1" /> : <GraduationCap size={12} className="mr-1" />}
                    DEEP
                </button>
            </div>
            <button onClick={onClearChat} className="p-2 text-text-secondary hover:text-red-400 transition-colors"><Trash2 size={16} /></button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-black/20 custom-scrollbar relative">
        {messages.map((msg, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'ai' && <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center shadow-lg"><BrainCircuit className="w-4 h-4 text-white" /></div>}
                <div className={`relative group max-w-[85%] rounded-2xl px-5 py-3.5 text-sm shadow-xl ${msg.role === 'user' ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' : 'glass-panel text-text-primary rounded-bl-none'}`}>
                    <MessageCopyButton text={msg.content} isUser={msg.role === 'user'} />
                    <div className="markdown-content select-text">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>{msg.content}</ReactMarkdown>
                    </div>
                </div>
                {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center border border-white/5"><User className="w-4 h-4 text-text-secondary" /></div>}
            </motion.div>
        ))}
        {isSendingMessage && !messages[messages.length-1]?.content && (
            <div className="flex items-start gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-full bg-primary-start flex items-center justify-center"><BrainCircuit className="w-4 h-4 text-white" /></div>
                <div className="glass-panel text-text-secondary rounded-2xl px-5 py-3.5 text-sm flex items-center gap-2"><Loader2 className="h-3 w-3 animate-spin" /> {t('chatPanel.thinking')}</div>
            </div>
        )}
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