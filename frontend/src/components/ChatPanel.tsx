// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V6.0
// 1. LAYOUT: Moved Context Selector (Case vs Document) to Header.
// 2. LAYOUT: Kept Jurisdiction Selector (Kosovo vs Albania) in Header.
// 3. UX: Cleaned up footer input area.

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, Bot, RefreshCw, Trash2, MapPin, ChevronDown, FileText, Briefcase 
} from 'lucide-react';
import { ChatMessage, Document } from '../data/types';
import { TFunction } from 'i18next';

export type ChatMode = 'general' | 'document';
export type Jurisdiction = 'ks' | 'al';

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
    messages, 
    connectionStatus, 
    reconnect: _reconnect,
    onSendMessage, 
    isSendingMessage, 
    onClearChat, 
    t, 
    documents, 
    className 
}) => {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<ChatMode>('general');
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>('ks');
  const [showJurisdictionMenu, setShowJurisdictionMenu] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSendingMessage) return;
    onSendMessage(input, mode, mode === 'document' ? selectedDocId : undefined, jurisdiction);
    setInput('');
  };

  return (
    <div className={`flex flex-col bg-background-dark border-l border-glass-edge h-full ${className}`}>
      {/* Header */}
      <div className="flex flex-col gap-3 px-4 py-3 border-b border-glass-edge bg-background-light/50 backdrop-blur-md">
        
        {/* Row 1: Title & Jurisdiction */}
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
                <div className={`p-1.5 rounded-lg ${connectionStatus === 'CONNECTED' ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                    <div className={`w-2 h-2 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                </div>
                <h3 className="text-sm font-bold text-gray-100">{t('chatPanel.title')}</h3>
            </div>

            <div className="flex items-center gap-2">
                {/* Jurisdiction Dropdown */}
                <div className="relative">
                    <button 
                        onClick={() => setShowJurisdictionMenu(!showJurisdictionMenu)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 text-xs font-medium text-gray-300 transition-all"
                    >
                        <MapPin className={`h-3 w-3 ${jurisdiction === 'ks' ? 'text-blue-400' : 'text-red-500'}`} />
                        <span>{jurisdiction === 'ks' ? 'Kosovë' : 'Shqipëri'}</span>
                        <ChevronDown className="h-3 w-3 opacity-50" />
                    </button>

                    <AnimatePresence>
                        {showJurisdictionMenu && (
                            <motion.div 
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: 10 }}
                                className="absolute right-0 top-full mt-2 w-32 bg-[#1a1a1a] border border-glass-edge rounded-xl shadow-xl z-50 overflow-hidden"
                            >
                                <button 
                                    onClick={() => { setJurisdiction('ks'); setShowJurisdictionMenu(false); }}
                                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/5 ${jurisdiction === 'ks' ? 'text-blue-400 bg-blue-500/10' : 'text-gray-400'}`}
                                >
                                    <span>🇽🇰</span> Kosovë
                                </button>
                                <button 
                                    onClick={() => { setJurisdiction('al'); setShowJurisdictionMenu(false); }}
                                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/5 ${jurisdiction === 'al' ? 'text-red-400 bg-red-500/10' : 'text-gray-400'}`}
                                >
                                    <span>🇦🇱</span> Shqipëri
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <button onClick={onClearChat} className="p-1.5 text-gray-500 hover:text-red-400 transition-colors" title={t('chatPanel.confirmClear')}>
                    <Trash2 size={16} />
                </button>
            </div>
        </div>

        {/* Row 2: Context Scope Selector (Case vs Docs) */}
        <div className="flex items-center gap-2 bg-black/20 p-1 rounded-lg border border-white/5">
            <button 
                onClick={() => { setMode('general'); setSelectedDocId(''); }}
                className={`flex-1 flex items-center justify-center gap-2 py-1.5 rounded-md text-[10px] uppercase tracking-wide font-bold transition-all ${mode === 'general' ? 'bg-primary-start/20 text-primary-start border border-primary-start/30' : 'text-gray-500 hover:text-gray-300'}`}
            >
                <Briefcase size={12} />
                General (Case)
            </button>
            <div className="relative flex-1">
                <select 
                    value={selectedDocId}
                    onChange={(e) => { 
                        const val = e.target.value;
                        setSelectedDocId(val); 
                        setMode(val ? 'document' : 'general'); 
                    }}
                    className={`w-full appearance-none bg-transparent py-1.5 pl-8 pr-4 rounded-md text-[10px] font-bold uppercase tracking-wide outline-none cursor-pointer transition-colors ${mode === 'document' ? 'text-yellow-400 bg-yellow-400/10 border border-yellow-400/30' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    <option value="" className="bg-gray-900 text-gray-400">Select Document</option>
                    {documents.map(d => (
                        <option key={d.id} value={d.id} className="bg-gray-900 text-white truncate">
                            {d.file_name.substring(0, 20)}...
                        </option>
                    ))}
                </select>
                <FileText size={12} className={`absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none ${mode === 'document' ? 'text-yellow-400' : 'text-gray-500'}`} />
                <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none opacity-50" />
            </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-50">
                <Bot size={48} className="mb-4 text-primary-start" />
                <p className="text-sm text-gray-400">{t('chatPanel.welcomeMessage')}</p>
                <div className="mt-4 flex gap-2 text-xs text-gray-600">
                    <span className={`px-2 py-1 rounded border border-white/5 ${jurisdiction === 'ks' ? 'bg-blue-500/10 text-blue-300' : 'bg-white/5'}`}>Ligjet e Kosovës</span>
                    <span className={`px-2 py-1 rounded border border-white/5 ${jurisdiction === 'al' ? 'bg-red-500/10 text-red-300' : 'bg-white/5'}`}>Ligjet e Shqipërisë</span>
                </div>
            </div>
        ) : (
            messages.map((msg, idx) => (
                <motion.div 
                    key={idx} 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        msg.sender === 'user' 
                        ? 'bg-primary-start text-white rounded-br-none' 
                        : 'bg-white/10 text-gray-200 rounded-bl-none border border-white/5'
                    }`}>
                        {msg.content}
                    </div>
                </motion.div>
            ))
        )}
        {isSendingMessage && (
            <div className="flex justify-start">
                <div className="bg-white/5 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex items-center gap-2">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    {t('chatPanel.thinking')}
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-glass-edge bg-background-light/30">
        <form onSubmit={handleSubmit} className="relative">
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('chatPanel.inputPlaceholder')}
                className="w-full bg-black/40 border border-glass-edge text-white rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-primary-start/50 focus:ring-1 focus:ring-primary-start/50 transition-all placeholder:text-gray-600"
            />
            <button 
                type="submit" 
                disabled={!input.trim() || isSendingMessage}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary-start hover:bg-primary-end text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Send size={16} />
            </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;