// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V5.0 (STREAMING TRANSITION FIX)
// 1. FIX: Spinner now hides automatically once tokens start arriving (hasContent check).
// 2. FIX: Optimized rendering for real-time streams to prevent double-typing artifacts.
// 3. STATUS: 100% Compatibility with Token Streaming and Pro Gatekeeper.

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, Loader2, User, Copy, Check, FileCheck, Zap, GraduationCap, Scale, Globe, Lock 
} from 'lucide-react';
import { ChatMessage } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export type ChatMode = 'general' | 'document';
export type ReasoningMode = 'FAST' | 'DEEP';
export type Jurisdiction = 'ks' | 'al';

// --- HELPER: CLEAN TEXT ---
const cleanChatText = (text: string) => {
    let clean = text.replace(/([^(]+)\(doc:\/\/[^)]+\):?/g, '$1');
    clean = clean.replace(/^Ligji\/Neni \(Kosovë\):\s*/gm, '');
    clean = clean.replace(/^Konventa \(Global\):\s*/gm, '');
    return clean;
};

// --- HELPER: COPY BUTTON ---
const MessageCopyButton: React.FC<{ text: string, isUser: boolean }> = ({ text, isUser }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (err) { console.error(err); }
    };
    return (
        <button onClick={handleCopy} className={`absolute top-2 right-2 p-1.5 rounded-lg transition-all duration-200 opacity-0 group-hover:opacity-100 ${copied ? 'bg-emerald-500/20 text-emerald-400' : isUser ? 'bg-white/10 text-white/70 hover:text-white hover:bg-white/20' : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'}`} title={copied ? "Copied!" : "Copy text"}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
    );
};

// --- MARKDOWN COMPONENTS ---
const MarkdownComponents = {
    p: ({node, ...props}: any) => <p className="mb-2 last:mb-0 leading-relaxed whitespace-pre-wrap" {...props} />, 
    strong: ({node, ...props}: any) => <span className="font-bold text-accent-end" {...props} />, 
    em: ({node, ...props}: any) => <span className="italic text-text-secondary" {...props} />, 
    ul: ({node, ...props}: any) => <ul className="list-disc pl-4 space-y-1 my-2 marker:text-primary-start" {...props} />, 
    ol: ({node, ...props}: any) => <ol className="list-decimal pl-4 space-y-1 my-2 marker:text-primary-start" {...props} />, 
    li: ({node, ...props}: any) => <li className="pl-1" {...props} />, 
    blockquote: ({node, ...props}: any) => <blockquote className="border-l-2 border-primary-start pl-3 py-1 my-2 bg-white/5 rounded-r text-text-secondary italic" {...props} />, 
    code: ({node, ...props}: any) => <code className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-accent-end" {...props} />, 
    a: ({href, children}: any) => {
        const getText = (child: any): string => {
            if (!child) return '';
            if (typeof child === 'string') return child;
            if (Array.isArray(child)) return child.map(getText).join('');
            if (child.props && child.props.children) return getText(child.props.children);
            return '';
        };
        const contentStr = getText(children);
        const isDocLink = href?.startsWith('doc://');
        if (isDocLink) {
            const isGlobal = ["UNCRC", "KEDNJ", "ECHR", "Konventa"].some(k => contentStr.includes(k));
            const isEvidence = contentStr.includes("PROVA") || contentStr.includes("Dokument");
            if (isEvidence) return (<span className="inline-flex items-center gap-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-2 py-0.5 rounded-md text-xs font-bold tracking-wide hover:bg-yellow-500/20 cursor-default mx-1 align-middle"><FileCheck size={12} className="flex-shrink-0" />{children}</span>);
            return (<span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-bold border mx-1 align-middle cursor-help transition-colors ${isGlobal ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/20' : 'bg-blue-500/10 text-blue-300 border-blue-500/30 hover:bg-blue-500/20'}`}>{isGlobal ? <Globe size={12} /> : <Scale size={12} />}{children}</span>);
        }
        return <a className="text-primary-start hover:underline cursor-pointer" target="_blank" rel="noopener noreferrer" href={href}>{children}</a>;
    },
    table: ({node, ...props}: any) => <div className="overflow-x-auto my-3"><table className="min-w-full border-collapse border border-white/10 text-xs" {...props} /></div>, 
    th: ({node, ...props}: any) => <th className="border border-white/10 px-2 py-1.5 bg-white/10 font-bold text-left text-white" {...props} />, 
    td: ({node, ...props}: any) => <td className="border border-white/10 px-2 py-1.5" {...props} />, 
};

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

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, onClearChat, t, className, activeContextId, isPro = false 
}) => {
  const [input, setInput] = useState('');
  const [reasoningMode, setReasoningMode] = useState<ReasoningMode>('FAST');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // If user loses Pro status while in DEEP mode, revert to FAST
  useEffect(() => {
      if (!isPro && reasoningMode === 'DEEP') {
          setReasoningMode('FAST');
      }
  }, [isPro, reasoningMode]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);
  
  useEffect(() => { if (textareaRef.current) { textareaRef.current.style.height = 'auto'; textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`; } }, [input]);

  const sendMessage = () => {
    if (!input.trim() || isSendingMessage) return;
    const mode: ChatMode = activeContextId === 'general' ? 'general' : 'document';
    const docId = mode === 'document' ? activeContextId : undefined;
    onSendMessage(input, mode, reasoningMode, docId, 'ks');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } };
  const statusDotColor = (status: string) => { switch (status) { case 'CONNECTED': return 'bg-emerald-500 shadow-[0_0_10px_#10b981]'; case 'CONNECTING': return 'bg-accent-start animate-pulse'; default: return 'bg-red-500'; } };
  const getPlaceholder = () => { if (reasoningMode === 'DEEP') return t('chatPanel.inputPlaceholderDeep', "Shkruaj për hulumtim të thellë..."); return t('chatPanel.inputPlaceholder', "Shkruaj mesazhin tuaj këtu..."); };

  // PHOENIX: Check if we are currently receiving a stream to hide the loader
  const lastMessage = messages[messages.length - 1];
  const isCurrentlyStreaming = isSendingMessage && lastMessage?.role === 'ai' && lastMessage.content.length > 0;

  return (
    <div className={`flex flex-col relative glass-panel rounded-2xl overflow-hidden h-full w-full ${className}`}>
      
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/5 backdrop-blur-sm z-50">
        <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full transition-colors duration-500 ${statusDotColor(connectionStatus)}`} />
            <h3 className="text-sm font-bold text-white hidden sm:block">{t('chatPanel.title')}</h3>
        </div>
        
        <div className="flex items-center gap-2">
            <div className="flex items-center bg-black/30 rounded-lg p-0.5 mr-2 border border-white/5">
                <button
                    onClick={() => setReasoningMode('FAST')}
                    className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold transition-all ${reasoningMode === 'FAST' ? 'bg-blue-500/20 text-blue-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    <Zap size={12} /> {t('chatPanel.modeFast', 'Shpejtë')}
                </button>
                <button
                    onClick={() => isPro && setReasoningMode('DEEP')}
                    disabled={!isPro}
                    className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold transition-all ${
                        reasoningMode === 'DEEP' 
                        ? 'bg-purple-500/20 text-purple-400 shadow-sm' 
                        : !isPro
                            ? 'text-gray-600 opacity-60 cursor-not-allowed'
                            : 'text-gray-500 hover:text-gray-300'
                    }`}
                >
                    {!isPro ? <Lock size={10} className="mr-0.5" /> : <GraduationCap size={12} />}
                    {t('chatPanel.modeDeep', 'Thellë')}
                </button>
            </div>

            <button onClick={onClearChat} className="p-2 text-text-secondary hover:text-red-400 transition-colors hover:bg-white/5 rounded-lg">
                <Trash2 size={16} />
            </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar z-0 relative min-h-0 bg-black/20">
        {messages.length === 0 && !isSendingMessage ? (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-50">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4"><BrainCircuit size={32} className="text-primary-start" /></div>
                <p className="text-sm text-text-secondary max-w-xs">{t('chatPanel.welcomeMessage')}</p>
            </div>
        ) : (
            messages.map((msg, idx) => {
                const isAi = msg.role === 'ai'; 
                const cleanContent = cleanChatText(msg.content);
                // Don't render empty AI bubbles if we are still waiting for the loader
                if (isAi && !cleanContent && isSendingMessage) return null;

                return (
                    <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex items-end gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {isAi && (<div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary-start/20"><BrainCircuit className="w-4 h-4 text-white" /></div>)}
                        <div className={`relative group max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-lg select-text ${msg.role === 'user' ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none shadow-primary-start/20' : 'glass-panel text-text-primary rounded-bl-none pr-10'}`}>
                            {cleanContent && <MessageCopyButton text={cleanContent} isUser={msg.role === 'user'} />}
                            <div className="markdown-content space-y-2 break-words select-text cursor-text">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>{cleanContent}</ReactMarkdown>
                            </div>
                        </div>
                         {msg.role === 'user' && (<div className="w-8 h-8 rounded-full bg-white/10 border border-white/5 flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-text-secondary" /></div>)}
                    </motion.div>
                );
            })
        )}
        
        {/* PHOENIX: Thinking Indicator - Only shows while wait for FIRST token */}
        {isSendingMessage && !isCurrentlyStreaming && (
            <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center flex-shrink-0 animate-pulse">
                    <BrainCircuit className="w-4 h-4 text-white" />
                </div>
                <div className="glass-panel text-text-secondary rounded-2xl rounded-bl-none px-5 py-3.5 text-sm flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" /> {t('chatPanel.thinking')}
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/5 bg-white/5 backdrop-blur-md z-10">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(); }} className="relative flex items-end gap-2">
            <textarea ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={getPlaceholder()} rows={1} className={`glass-input w-full pl-4 pr-12 py-3.5 rounded-xl text-sm resize-none custom-scrollbar transition-colors duration-300 ${reasoningMode === 'DEEP' ? 'border-purple-500/30 focus:border-purple-500/50' : ''}`} style={{ maxHeight: '150px' }} />
            <button type="submit" disabled={!input.trim() || isSendingMessage} className={`absolute right-2 bottom-2 p-2 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0 ${reasoningMode === 'DEEP' ? 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:shadow-lg hover:shadow-purple-500/20' : 'bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20'}`}><Send size={18} /></button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;