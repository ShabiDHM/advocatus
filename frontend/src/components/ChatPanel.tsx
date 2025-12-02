// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - DROPDOWN & DISPLAY FIX V9.1
// 1. DISPLAY FIX: Corrected logic to ensure selected dropdown item is always displayed.
// 2. STABILITY: Simplified state management to prevent race conditions.

import React, { useState, useRef, useEffect, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, Bot, RefreshCw, Trash2, MapPin, ChevronDown, FileText, Briefcase 
} from 'lucide-react';
import { ChatMessage, Document } from '../data/types';
import { TFunction } from 'i18next';

export type ChatMode = 'general' | 'document';
export type Jurisdiction = 'ks' | 'al';

// --- ROBUST DROPDOWN COMPONENT ---
interface DropdownItem {
    id: string;
    label: string;
    icon?: ReactNode;
}

interface DropdownProps {
    trigger: ReactNode;
    items: DropdownItem[];
    onSelect: (id: string) => void;
}

const Dropdown: React.FC<DropdownProps> = ({ trigger, items, onSelect }) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleSelect = (id: string) => {
        onSelect(id);
        setIsOpen(false);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <div onClick={() => setIsOpen(prev => !prev)} className="cursor-pointer">
                {trigger}
            </div>
            <AnimatePresence>
                {isOpen && (
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95 }} 
                        animate={{ opacity: 1, scale: 1.0 }} 
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.1 }}
                        className="absolute right-0 top-full mt-2 w-56 bg-[#1f2937] border border-glass-edge rounded-xl shadow-2xl z-50 overflow-hidden"
                    >
                        {items.map(item => (
                            <button 
                                key={item.id} 
                                onClick={() => handleSelect(item.id)} 
                                className="w-full text-left flex items-center gap-3 px-3 py-2 text-sm hover:bg-white/5 text-gray-200"
                            >
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
  // PHOENIX STATE: 'general' is the ID for Case, otherwise it's a doc ID
  const [selectedContextId, setSelectedContextId] = useState<string>('general');
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>('ks');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSendingMessage]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSendingMessage) return;
    const mode: ChatMode = selectedContextId === 'general' ? 'general' : 'document';
    const docId = mode === 'document' ? selectedContextId : undefined;
    onSendMessage(input, mode, docId, jurisdiction);
    setInput('');
  };

  const contextItems: DropdownItem[] = [
      { id: 'general', label: 'General (Case)', icon: <Briefcase size={14} className="text-amber-400" /> },
      ...(documents || []).map(doc => ({
          id: doc.id,
          label: doc.file_name,
          icon: <FileText size={14} className="text-blue-400" />
      }))
  ];

  const jurisdictionItems: DropdownItem[] = [
      { id: 'ks', label: 'Kosovë', icon: <MapPin size={14} /> },
      { id: 'al', label: 'Shqipëri', icon: <MapPin size={14} /> }
  ];
  
  const selectedContextItem = contextItems.find(item => item.id === selectedContextId) || contextItems[0];
  const selectedJurisdictionItem = jurisdictionItems.find(item => item.id === jurisdiction) || jurisdictionItems[0];

  return (
    <div className={`flex flex-col bg-background-dark border-l border-glass-edge h-full ${className}`}>
      {/* Unified Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-glass-edge bg-background-light/50 backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-500' : 'bg-red-500'}`} />
            <h3 className="text-sm font-bold text-gray-100">{t('chatPanel.title')}</h3>
        </div>
        <div className="flex items-center gap-1.5">
            <Dropdown 
                items={contextItems}
                onSelect={setSelectedContextId}
                trigger={
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 text-xs font-medium text-gray-300 transition-all max-w-[150px]">
                        {selectedContextItem.icon}
                        <span className="truncate">{selectedContextItem.label}</span>
                        <ChevronDown className="h-3 w-3 opacity-50 flex-shrink-0" />
                    </div>
                }
            />
            <Dropdown 
                items={jurisdictionItems}
                onSelect={(id) => setJurisdiction(id as Jurisdiction)}
                trigger={
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 text-xs font-medium text-gray-300 transition-all">
                        {selectedJurisdictionItem.icon}
                        <span className="hidden sm:inline">{selectedJurisdictionItem.label}</span>
                        <ChevronDown className="h-3 w-3 opacity-50" />
                    </div>
                }
            />
            <button onClick={onClearChat} className="p-2 text-gray-500 hover:text-red-400 transition-colors" title={t('chatPanel.confirmClear')}><Trash2 size={16} /></button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.length === 0 && !isSendingMessage ? (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-50"><Bot size={48} className="mb-4 text-primary-start" /><p className="text-sm text-gray-400">{t('chatPanel.welcomeMessage')}</p></div>
        ) : (
            messages.map((msg, idx) => (
                <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${msg.sender === 'user' ? 'bg-primary-start text-white rounded-br-none' : 'bg-white/10 text-gray-200 rounded-bl-none border border-white/5'}`}>{msg.content}</div>
                </motion.div>
            ))
        )}
        {isSendingMessage && (
            <div className="flex justify-start"><div className="bg-white/5 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex items-center gap-2"><RefreshCw className="h-3 w-3 animate-spin" />{t('chatPanel.thinking')}</div></div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-glass-edge bg-background-light/30 flex-shrink-0">
        <form onSubmit={handleSubmit} className="relative">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder={t('chatPanel.inputPlaceholder')} className="w-full bg-black/40 border border-glass-edge text-white rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-primary-start/50 focus:ring-1 focus:ring-primary-start/50 transition-all placeholder:text-gray-600"/>
            <button type="submit" disabled={!input.trim() || isSendingMessage} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary-start hover:bg-primary-end text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"><Send size={16} /></button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;