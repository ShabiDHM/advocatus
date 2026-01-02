// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V3.1 (CITATION BADGES)
// 1. VISUALS: Custom renderer for 'doc://' links to create highlighted badges.
// 2. STATUS: Legal citations now appear as distinct, beautiful elements.

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, Loader2, User, Copy, Check, BookOpen 
} from 'lucide-react';
import { ChatMessage } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export type ChatMode = 'general' | 'document';
export type Jurisdiction = 'ks' | 'al';

// --- HELPER: COPY BUTTON ---
const MessageCopyButton: React.FC<{ text: string }> = ({ text }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    };

    return (
        <button 
            onClick={handleCopy} 
            className={`absolute top-2 right-2 p-1.5 rounded-lg transition-all duration-200 ${
                copied 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 opacity-0 group-hover:opacity-100'
            }`}
            title={copied ? "Copied!" : "Copy text"}
        >
            {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
    );
};

// --- HELPER: CUSTOM MARKDOWN COMPONENTS ---
// PHOENIX: Custom Renderers for Beautiful Citations
const MarkdownComponents = {
    p: ({node, ...props}: any) => <p className="mb-2 last:mb-0 leading-relaxed" {...props} />, 
    strong: ({node, ...props}: any) => <span className="font-bold text-accent-end" {...props} />, 
    em: ({node, ...props}: any) => <span className="italic text-text-secondary" {...props} />, 
    ul: ({node, ...props}: any) => <ul className="list-disc pl-4 space-y-1 my-2 marker:text-primary-start" {...props} />, 
    ol: ({node, ...props}: any) => <ol className="list-decimal pl-4 space-y-1 my-2 marker:text-primary-start" {...props} />, 
    li: ({node, ...props}: any) => <li className="pl-1" {...props} />, 
    blockquote: ({node, ...props}: any) => <blockquote className="border-l-2 border-primary-start pl-3 py-1 my-2 bg-white/5 rounded-r text-text-secondary italic" {...props} />, 
    code: ({node, ...props}: any) => <code className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-accent-end" {...props} />, 
    
    // PHOENIX: The Citation Badge Logic
    a: ({node, href, children, ...props}: any) => {
        const isDocCitation = href?.startsWith('doc://');
        
        if (isDocCitation) {
            return (
                <span className="inline-flex items-center gap-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-1.5 py-0.5 rounded-[4px] text-xs font-bold tracking-wide hover:bg-yellow-500/20 cursor-default transition-colors mx-0.5">
                    <BookOpen size={10} className="flex-shrink-0" />
                    {children}
                </span>
            );
        }
        
        return <a className="text-primary-start hover:underline cursor-pointer" target="_blank" rel="noopener noreferrer" href={href} {...props}>{children}</a>;
    },

    table: ({node, ...props}: any) => <div className="overflow-x-auto my-3"><table className="min-w-full border-collapse border border-white/10 text-xs" {...props} /></div>, 
    th: ({node, ...props}: any) => <th className="border border-white/10 px-2 py-1.5 bg-white/10 font-bold text-left text-white" {...props} />, 
    td: ({node, ...props}: any) => <td className="border border-white/10 px-2 py-1.5" {...props} />, 
};

const TypingMessage: React.FC<{ text: string; onComplete?: () => void }> = ({ text, onComplete }) => {
    const [displayedText, setDisplayedText] = useState("");
    useEffect(() => {
        setDisplayedText(""); let index = 0; const speed = 10;
        const intervalId = setInterval(() => {
            setDisplayedText((prev) => {
                if (index >= text.length) { clearInterval(intervalId); if (onComplete) onComplete(); return text; }
                const nextChar = text.charAt(index); index++; return prev + nextChar;
            });
        }, speed);
        return () => clearInterval(intervalId);
    }, [text, onComplete]);

    return (
        <div className="markdown-content space-y-2 break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>{displayedText}</ReactMarkdown>
        </div>
    );
};

interface ChatPanelProps {
  messages: ChatMessage[];
  connectionStatus: string;
  reconnect: () => void;
  onSendMessage: (text: string, mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => void;
  isSendingMessage: boolean;
  onClearChat: () => void;
  t: TFunction;
  className?: string;
  activeContextId: string; 
}

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, onClearChat, t, className, activeContextId
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const prevMessagesLength = useRef(0);
  const [typingIndex, setTypingIndex] = useState<number | null>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);

  useEffect(() => {
      const currentLength = messages.length;
      const prevLength = prevMessagesLength.current;
      if (currentLength > prevLength) {
          if (prevLength > 0) {
              const lastMsg = messages[currentLength - 1];
              if (lastMsg.role === 'ai') setTypingIndex(currentLength - 1);
          }
      } else if (currentLength < prevLength) {
          setTypingIndex(null);
      }
      prevMessagesLength.current = currentLength;
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const sendMessage = () => {
    if (!input.trim() || isSendingMessage) return;
    const mode: ChatMode = activeContextId === 'general' ? 'general' : 'document';
    const docId = mode === 'document' ? activeContextId : undefined;
    onSendMessage(input, mode, docId, 'ks');
    setInput('');
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); sendMessage(); };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } };

  const statusDotColor = (status: string) => {
    switch (status) {
      case 'CONNECTED': return 'bg-emerald-500 shadow-[0_0_10px_#10b981]';
      case 'CONNECTING': return 'bg-accent-start animate-pulse';
      default: return 'bg-red-500';
    }
  };

  return (
    <div className={`flex flex-col relative glass-panel rounded-2xl overflow-hidden h-full w-full ${className}`}>
      
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/5 backdrop-blur-sm z-50">
        <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full transition-colors duration-500 ${statusDotColor(connectionStatus)}`} />
            <h3 className="text-sm font-bold text-white hidden sm:block">{t('chatPanel.title')}</h3>
        </div>
        
        <div className="flex items-center gap-2">
            <button onClick={onClearChat} className="p-2 text-text-secondary hover:text-red-400 transition-colors hover:bg-white/5 rounded-lg" title={t('chatPanel.confirmClear')}>
                <Trash2 size={16} />
            </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar z-0 relative min-h-0 bg-black/20">
        {messages.length === 0 && !isSendingMessage ? (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-50">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                    <BrainCircuit size={32} className="text-primary-start" />
                </div>
                <p className="text-sm text-text-secondary max-w-xs">{t('chatPanel.welcomeMessage')}</p>
            </div>
        ) : (
            messages.map((msg, idx) => {
                const isAi = msg.role === 'ai';
                const useTyping = isAi && idx === typingIndex;

                return (
                    <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex items-end gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {isAi && (
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary-start/20">
                                <BrainCircuit className="w-4 h-4 text-white" />
                            </div>
                        )}
                        
                        <div className={`relative group max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-lg ${msg.role === 'user' ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none shadow-primary-start/20' : 'glass-panel text-text-primary rounded-bl-none pr-10'}`}>
                            
                            {isAi && !useTyping && <MessageCopyButton text={msg.content} />}

                            {msg.role === 'user' ? (
                                msg.content
                            ) : useTyping ? (
                                <TypingMessage text={msg.content} onComplete={() => setTypingIndex(null)} />
                            ) : (
                                <div className="markdown-content space-y-2 break-words">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>{msg.content}</ReactMarkdown>
                                </div>
                            )}
                        </div>
                         {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-white/10 border border-white/5 flex items-center justify-center flex-shrink-0">
                                <User className="w-4 h-4 text-text-secondary" />
                            </div>
                         )}
                    </motion.div>
                );
            })
        )}
        {isSendingMessage && (
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

      {/* Input Area */}
      <div className="p-4 border-t border-white/5 bg-white/5 backdrop-blur-md z-10">
        <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
            <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chatPanel.inputPlaceholder')}
                rows={1}
                className="glass-input w-full pl-4 pr-12 py-3.5 rounded-xl text-sm resize-none custom-scrollbar"
                style={{ maxHeight: '150px' }}
            />
            <button type="submit" disabled={!input.trim() || isSendingMessage} className="absolute right-2 bottom-2 p-2 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0">
                <Send size={18} />
            </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;