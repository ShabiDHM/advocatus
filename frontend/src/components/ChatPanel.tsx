// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - MOBILE & I18N UPDATE
// 1. I18N: Added translation keys for Dropdown options (General, Kosovo, Albania).
// 2. MOBILE: Increased max-width for context dropdown to prevent "Gene..." truncation.
// 3. MOBILE: Added visible text (KS/AL) to Jurisdiction dropdown on small screens.

import React, { useState, useRef, useEffect, ReactNode, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, Brain, RefreshCw, Trash2, MapPin, ChevronDown, FileText, Briefcase 
} from 'lucide-react';
import { ChatMessage, Document } from '../data/types';
import { TFunction } from 'i18next';

export type ChatMode = 'general' | 'document';
export type Jurisdiction = 'ks' | 'al';

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
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>('ks');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSendingMessage) return;
    const mode: ChatMode = selectedContextId === 'general' ? 'general' : 'document';
    const docId = mode === 'document' ? selectedContextId : undefined;
    onSendMessage(input, mode, docId, jurisdiction);
    setInput('');
  };

  // PHOENIX: Memoize items to react to language changes
  const contextItems: DropdownItem[] = useMemo(() => [
      { id: 'general', label: t('chatPanel.contextGeneral', 'E gjithë Dosja'), icon: <Briefcase size={14} className="text-amber-400" /> },
      ...(documents || []).map(doc => ({ id: doc.id, label: doc.file_name, icon: <FileText size={14} className="text-blue-400" /> }))
  ], [documents, t]);

  const jurisdictionItems: DropdownItem[] = useMemo(() => [
      { id: 'ks', label: t('jurisdiction.kosovo', 'Kosovë'), shortLabel: 'KS', icon: <MapPin size={14} /> },
      { id: 'al', label: t('jurisdiction.albania', 'Shqipëri'), shortLabel: 'AL', icon: <MapPin size={14} /> }
  ], [t]);
  
  const selectedContextItem = contextItems.find(item => item.id === selectedContextId) || contextItems[0];
  const selectedJurisdictionItem = jurisdictionItems.find(item => item.id === jurisdiction) || jurisdictionItems[0];

  const statusDotColor = (status: string) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]';
      case 'CONNECTING': return 'bg-yellow-500 animate-pulse';
      default: return 'bg-red-500';
    }
  };

  return (
    <div className={`flex flex-col relative bg-background-dark/40 backdrop-blur-md border border-white/10 rounded-2xl shadow-xl overflow-visible ${className}`}>
      
      {/* HEADER */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-3 border-b border-white/10 bg-white/5 rounded-t-2xl z-50">
        <div className="flex items-center gap-2 sm:gap-3">
            <div className={`w-2.5 h-2.5 rounded-full transition-colors duration-500 ${statusDotColor(connectionStatus)}`} />
            <h3 className="text-sm font-bold text-gray-100 hidden sm:block">{t('chatPanel.title')}</h3>
        </div>
        
        <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Context Dropdown - WIDENED for Mobile */}
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
            
            {/* Jurisdiction Dropdown - ADDED 'shortLabel' for Mobile */}
            <Dropdown 
                items={jurisdictionItems} 
                onSelect={(id) => setJurisdiction(id as Jurisdiction)} 
                trigger={
                    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 hover:border-white/20 text-xs font-medium text-gray-300 transition-all">
                        {selectedJurisdictionItem.icon}
                        {/* Mobile: KS/AL | Desktop: Full Name */}
                        <span className="inline md:hidden">{selectedJurisdictionItem.shortLabel}</span>
                        <span className="hidden md:inline">{selectedJurisdictionItem.label}</span>
                        <ChevronDown className="h-3 w-3 opacity-50" />
                    </div>
                } 
            />

            <button onClick={onClearChat} className="p-1.5 text-gray-500 hover:text-red-400 transition-colors" title={t('chatPanel.confirmClear')}>
                <Trash2 size={16} />
            </button>
        </div>
      </div>

      {/* MESSAGES */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar z-0 relative">
        {messages.length === 0 && !isSendingMessage ? (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-40">
                <Brain size={48} className="mb-4 text-primary-start" />
                <p className="text-sm text-gray-400 max-w-xs">{t('chatPanel.welcomeMessage')}</p>
            </div>
        ) : (
            messages.map((msg, idx) => (
                <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex items-end gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.sender === 'ai' && <div className="w-8 h-8 rounded-full bg-black/40 border border-white/10 flex items-center justify-center flex-shrink-0"><Brain className="w-4 h-4 text-primary-start" /></div>}
                    <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.sender === 'user' ? 'bg-primary-start text-white rounded-br-none' : 'bg-white/10 text-gray-200 rounded-bl-none border border-white/5'}`}>
                        {msg.content}
                    </div>
                </motion.div>
            ))
        )}
        {isSendingMessage && (
            <div className="flex items-start gap-2">
                <div className="w-8 h-8 rounded-full bg-black/40 border border-white/10 flex items-center justify-center flex-shrink-0"><Brain className="w-4 h-4 text-primary-start animate-pulse" /></div>
                <div className="bg-white/5 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex items-center gap-2">
                    <RefreshCw className="h-3 w-3 animate-spin" /> {t('chatPanel.thinking')}
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* INPUT */}
      <div className="p-4 border-t border-white/10 bg-white/5 rounded-b-2xl z-10">
        <form onSubmit={handleSubmit} className="relative">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder={t('chatPanel.inputPlaceholder')} className="w-full bg-black/40 border border-white/10 text-white rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-primary-start/50 focus:ring-1 focus:ring-primary-start/50 transition-all placeholder:text-gray-600 text-sm"/>
            <button type="submit" disabled={!input.trim() || isSendingMessage} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary-start hover:bg-primary-end text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                <Send size={16} />
            </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;