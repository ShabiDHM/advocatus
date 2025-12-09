// FILE: src/components/ChatPanel.tsx
import React, { useState, useRef, useEffect, ReactNode, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, BrainCircuit, Trash2, ChevronDown, FileText, Briefcase, Loader2, User 
} from 'lucide-react';
import { ChatMessage, Document } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export type ChatMode = 'general' | 'document';
export type Jurisdiction = 'ks' | 'al';

// --- TYPING EFFECT COMPONENT ---
// Added onComplete callback to notify parent when animation finishes
const TypingMessage: React.FC<{ text: string; onComplete?: () => void }> = ({ text, onComplete }) => {
    const [displayedText, setDisplayedText] = useState("");
    
    useEffect(() => {
        setDisplayedText(""); 
        let index = 0;
        const speed = 10; 

        const intervalId = setInterval(() => {
            setDisplayedText((prev) => {
                if (index >= text.length) {
                    clearInterval(intervalId);
                    if (onComplete) onComplete(); // Notify finished
                    return text;
                }
                const nextChar = text.charAt(index);
                index++;
                return prev + nextChar;
            });
        }, speed);

        return () => clearInterval(intervalId);
    }, [text, onComplete]);

    return (
        <div className="markdown-content space-y-2">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    p: ({node, ...props}) => <p className="mb-1 last:mb-0" {...props} />,
                    strong: ({node, ...props}) => <span className="font-bold text-amber-200" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc pl-4 space-y-1 my-1 marker:text-primary-start" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal pl-4 space-y-1 my-1 marker:text-primary-start" {...props} />,
                }}
            >
                {displayedText}
            </ReactMarkdown>
        </div>
    );
};

// --- DROPDOWN COMPONENT ---
interface DropdownItem { id: string; label: string; icon?: ReactNode; shortLabel?: string; }
interface DropdownProps { trigger: ReactNode; items: DropdownItem[]; onSelect: (id: string) => void; }

const Dropdown: React.FC<DropdownProps> = ({ trigger, items, onSelect }) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) setIsOpen(false);
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);
    const handleSelect = (id: string) => { onSelect(id); setIsOpen(false); };
    
    return (
        <div className="relative" ref={dropdownRef}>
            <div onClick={() => setIsOpen(prev => !prev)} className="cursor-pointer">{trigger}</div>
            <AnimatePresence>
                {isOpen && (
                    <motion.div 
                        initial={{ opacity: 0, y: -5, scale: 0.95 }} 
                        animate={{ opacity: 1, y: 0, scale: 1.0 }} 
                        exit={{ opacity: 0, y: -5, scale: 0.95 }} 
                        transition={{ duration: 0.1 }} 
                        className="absolute right-0 top-full mt-2 w-56 bg-[#1f2937] border border-white/10 rounded-xl shadow-2xl z-[100] overflow-hidden"
                    >
                        {items.map(item => (
                            <button key={item.id} onClick={() => handleSelect(item.id)} className="w-full text-left flex items-center gap-3 px-3 py-2.5 text-sm hover:bg-white/5 text-gray-200 transition-colors border-b border-white/5 last:border-0">
                                {item.icon}
                                <span className="truncate">{item.label}</span>
                            </button>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

interface ChatPanelProps {
  messages: ChatMessage[];
  connectionStatus: string;
  reconnect: () => void;
  onSendMessage: (text: string, mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => void;
  isSendingMessage: boolean;
  caseId: string;
  onClearChat: () => void;
  t: TFunction;
  documents: Document[];
  className?: string;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, onClearChat, t, documents, className 
}) => {
  const [input, setInput] = useState('');
  const [selectedContextId, setSelectedContextId] = useState<string>('general');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // PHOENIX FIX: Strict logic to differentiate History vs New Message vs Re-render
  const prevMessagesLength = useRef(0);
  const [typingIndex, setTypingIndex] = useState<number | null>(null);

  // Auto-scroll to bottom
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);

  // INTELLIGENT TYPING TRIGGER
  useEffect(() => {
      const currentLength = messages.length;
      const prevLength = prevMessagesLength.current;

      if (currentLength > prevLength) {
          // New messages arrived
          if (prevLength === 0) {
              // CASE 1: Initial Load (History). Do NOT animate.
              // Just update ref.
          } else {
              // CASE 2: New message added to existing list. ANIMATE the last one.
              // Check if the last message is AI before deciding to animate
              const lastMsg = messages[currentLength - 1];
              if (lastMsg.role === 'ai') {
                  setTypingIndex(currentLength - 1);
              }
          }
      } else if (currentLength < prevLength) {
          // Messages cleared (Delete or Clear Chat). Reset.
          setTypingIndex(null);
      }
      
      // Always update ref
      prevMessagesLength.current = currentLength;
  }, [messages]);

  // Auto-expand textarea
  useEffect(() => {
    if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const sendMessage = () => {
    if (!input.trim() || isSendingMessage) return;
    const mode: ChatMode = selectedContextId === 'general' ? 'general' : 'document';
    const docId = mode === 'document' ? selectedContextId : undefined;
    onSendMessage(input, mode, docId, 'ks');
    setInput('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
  };

  const contextItems: DropdownItem[] = useMemo(() => [
      { id: 'general', label: t('chatPanel.contextGeneral', 'E gjithë Dosja'), icon: <Briefcase size={14} className="text-amber-400" /> },
      ...(documents || []).map(doc => ({ id: doc.id, label: doc.file_name, icon: <FileText size={14} className="text-blue-400" /> }))
  ], [documents, t]);
  
  const selectedContextItem = contextItems.find(item => item.id === selectedContextId) || contextItems[0];

  const statusDotColor = (status: string) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]';
      case 'CONNECTING': return 'bg-yellow-500 animate-pulse';
      default: return 'bg-red-500';
    }
  };

  return (
    <div className={`flex flex-col relative bg-background-dark/40 backdrop-blur-md border border-white/10 rounded-2xl shadow-xl overflow-hidden h-full ${className}`}>
      
      <div className="flex items-center justify-between px-3 sm:px-4 py-3 border-b border-white/10 bg-white/5 rounded-t-2xl z-50">
        <div className="flex items-center gap-2 sm:gap-3">
            <div className={`w-2.5 h-2.5 rounded-full transition-colors duration-500 ${statusDotColor(connectionStatus)}`} />
            <h3 className="text-sm font-bold text-gray-100 hidden sm:block">{t('chatPanel.title')}</h3>
        </div>
        
        <div className="flex items-center gap-1.5 sm:gap-2">
            <Dropdown 
                items={contextItems} 
                onSelect={setSelectedContextId} 
                trigger={
                    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 hover:border-white/20 text-xs font-medium text-gray-300 transition-all max-w-[140px] sm:max-w-[200px]">
                        {selectedContextItem.icon}
                        <span className="truncate">{selectedContextItem.label}</span>
                        <ChevronDown className="h-3 w-3 opacity-50 flex-shrink-0" />
                    </div>
                } 
            />
            
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
                
                // Only animate if this specific index is marked for typing
                const useTyping = isAi && idx === typingIndex;

                return (
                    <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex items-end gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {isAi && <div className="w-8 h-8 rounded-full bg-black/40 border border-white/10 flex items-center justify-center flex-shrink-0"><BrainCircuit className="w-4 h-4 text-primary-start" /></div>}
                        <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-primary-start text-white rounded-br-none' : 'bg-white/10 text-gray-200 rounded-bl-none border border-white/5'}`}>
                            {msg.role === 'user' ? (
                                msg.content
                            ) : useTyping ? (
                                <TypingMessage 
                                    text={msg.content} 
                                    onComplete={() => setTypingIndex(null)} // Mark as done forever
                                />
                            ) : (
                                <div className="markdown-content space-y-2">
                                    <ReactMarkdown 
                                        remarkPlugins={[remarkGfm]}
                                        components={{
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
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
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
            <button 
                type="submit" 
                disabled={!input.trim() || isSendingMessage} 
                className="absolute right-2 bottom-2 p-2 bg-primary-start hover:bg-primary-end text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Send size={16} />
            </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;