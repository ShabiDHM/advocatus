// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V2.4 (COPY FEATURE)
// 1. FEATURE: Added 'MessageCopyButton' for AI responses.
// 2. UX: Button appears on hover, allows copying specific message content.
// 3. STATUS: Clean and user-friendly.

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, Loader2, User, Copy, Check 
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
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-black/20 text-gray-400 hover:text-white hover:bg-black/40 opacity-0 group-hover:opacity-100'
            }`}
            title={copied ? "Copied!" : "Copy text"}
        >
            {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
    );
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
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ p: ({node, ...props}) => <p className="mb-1 last:mb-0" {...props} />, strong: ({node, ...props}) => <span className="font-bold text-amber-200" {...props} />, ul: ({node, ...props}) => <ul className="list-disc pl-4 space-y-1 my-1 marker:text-primary-start" {...props} />, ol: ({node, ...props}) => <ol className="list-decimal pl-4 space-y-1 my-1 marker:text-primary-start" {...props} />, }} >{displayedText}</ReactMarkdown>
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
      case 'CONNECTED': return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]';
      case 'CONNECTING': return 'bg-yellow-500 animate-pulse';
      default: return 'bg-red-500';
    }
  };

  return (
    <div className={`flex flex-col relative bg-background-dark/40 backdrop-blur-md border border-white/10 rounded-2xl shadow-xl overflow-hidden h-full w-full ${className}`}>
      
      <div className="flex items-center justify-between px-3 sm:px-4 py-3 border-b border-white/10 bg-white/5 rounded-t-2xl z-50">
        <div className="flex items-center gap-2 sm:gap-3">
            <div className={`w-2.5 h-2.5 rounded-full transition-colors duration-500 ${statusDotColor(connectionStatus)}`} />
            <h3 className="text-sm font-bold text-gray-100 hidden sm:block">{t('chatPanel.title')}</h3>
        </div>
        
        <div className="flex items-center gap-1.5 sm:gap-2">
            <button onClick={onClearChat} className="p-1.5 text-gray-500 hover:text-red-400 transition-colors" title={t('chatPanel.confirmClear')}>
                <Trash2 size={16} />
            </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar z-0 relative min-h-0">
        {messages.length === 0 && !isSendingMessage ? (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-40">
                <BrainCircuit size={48} className="mb-4 text-primary-start" />
                <p className="text-sm text-gray-400 max-w-xs">{t('chatPanel.welcomeMessage')}</p>
            </div>
        ) : (
            messages.map((msg, idx) => {
                const isAi = msg.role === 'ai';
                const useTyping = isAi && idx === typingIndex;

                return (
                    <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex items-end gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {isAi && <div className="w-8 h-8 rounded-full bg-black/40 border border-white/10 flex items-center justify-center flex-shrink-0"><BrainCircuit className="w-4 h-4 text-primary-start" /></div>}
                        
                        {/* PHOENIX FIX: Added 'relative group' for positioning the copy button */}
                        <div className={`relative group max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm break-words ${msg.role === 'user' ? 'bg-primary-start text-white rounded-br-none' : 'bg-white/10 text-gray-200 rounded-bl-none border border-white/5 pr-10'}`}>
                            {/* PHOENIX: Copy Button (Only for AI messages or non-empty content) */}
                            {isAi && !useTyping && <MessageCopyButton text={msg.content} />}

                            {msg.role === 'user' ? (
                                msg.content
                            ) : useTyping ? (
                                <TypingMessage text={msg.content} onComplete={() => setTypingIndex(null)} />
                            ) : (
                                <div className="markdown-content space-y-2 break-words">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ 
                                        p: ({node, ...props}) => <p className="mb-1 last:mb-0" {...props} />, 
                                        strong: ({node, ...props}) => <span className="font-bold text-amber-200" {...props} />, 
                                        em: ({node, ...props}) => <span className="italic text-gray-300" {...props} />, 
                                        ul: ({node, ...props}) => <ul className="list-disc pl-4 space-y-1 my-1 marker:text-primary-start" {...props} />, 
                                        ol: ({node, ...props}) => <ol className="list-decimal pl-4 space-y-1 my-1 marker:text-primary-start" {...props} />, 
                                        li: ({node, ...props}) => <li className="pl-1" {...props} />, 
                                        blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-primary-start pl-3 py-1 my-1 bg-white/5 rounded-r text-gray-400 italic" {...props} />, 
                                        code: ({node, ...props}) => <code className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-pink-300" {...props} />, 
                                        a: ({node, ...props}) => <a className="text-blue-400 hover:underline cursor-pointer" target="_blank" rel="noopener noreferrer" {...props} />, 
                                        table: ({node, ...props}) => <div className="overflow-x-auto my-2"><table className="min-w-full border-collapse border border-white/10 text-xs" {...props} /></div>, 
                                        th: ({node, ...props}) => <th className="border border-white/10 px-2 py-1 bg-white/5 font-bold text-left" {...props} />, 
                                        td: ({node, ...props}) => <td className="border border-white/10 px-2 py-1" {...props} />, 
                                    }} >{msg.content}</ReactMarkdown>
                                </div>
                            )}
                        </div>
                         {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-black/40 border border-white/10 flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-gray-300" /></div>}
                    </motion.div>
                );
            })
        )}
        {isSendingMessage && (
            <div className="flex items-start gap-2">
                <div className="w-8 h-8 rounded-full bg-black/40 border border-white/10 flex items-center justify-center flex-shrink-0"><BrainCircuit className="w-4 h-4 text-primary-start animate-pulse" /></div>
                <div className="bg-white/5 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" /> {t('chatPanel.thinking')}
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-white/10 bg-white/5 rounded-b-2xl z-10">
        <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
            <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chatPanel.inputPlaceholder')}
                rows={1}
                className="w-full bg-black/40 border border-white/10 text-white rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-primary-start/50 focus:ring-1 focus:ring-primary-start/50 transition-all placeholder:text-gray-600 text-sm resize-none custom-scrollbar"
                style={{ maxHeight: '150px' }}
            />
            <button type="submit" disabled={!input.trim() || isSendingMessage} className="absolute right-2 bottom-2 p-2 bg-primary-start hover:bg-primary-end text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                <Send size={16} />
            </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;