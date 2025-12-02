// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V8.1 (STATE & EVENT FIX)
// 1. FIX: Created explicit handler functions (handleJurisdictionChange, etc.).
// 2. FIX: Ensured state updates are correctly triggered and UI re-renders.
// 3. STATUS: Dropdowns are now fully functional and interactive.

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
  const [showContextMenu, setShowContextMenu] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const jurisdictionMenuRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Click outside handler to close dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (jurisdictionMenuRef.current && !jurisdictionMenuRef.current.contains(event.target as Node)) {
        setShowJurisdictionMenu(false);
      }
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        setShowContextMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSendingMessage) return;
    onSendMessage(input, mode, mode === 'document' ? selectedDocId : undefined, jurisdiction);
    setInput('');
  };

  const getContextButtonLabel = () => {
    if (mode === 'document' && selectedDocId) {
        const doc = documents.find(d => d.id === selectedDocId);
        return doc ? doc.file_name : 'Select Document';
    }
    return 'General (Case)';
  };

  // PHOENIX FIX: Explicit handlers for state changes
  const handleJurisdictionChange = (e: React.MouseEvent, newJurisdiction: Jurisdiction) => {
      e.stopPropagation();
      setJurisdiction(newJurisdiction);
      setShowJurisdictionMenu(false);
  };

  const handleContextChange = (e: React.MouseEvent, newMode: ChatMode, docId: string = '') => {
      e.stopPropagation();
      setMode(newMode);
      setSelectedDocId(docId);
      setShowContextMenu(false);
  };

  return (
    <div className={`flex flex-col bg-background-dark border-l border-glass-edge h-full ${className}`}>
      {/* Unified Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-glass-edge bg-background-light/50 backdrop-blur-md">
        
        <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-500' : 'bg-red-500'}`} />
            <h3 className="text-sm font-bold text-gray-100">{t('chatPanel.title')}</h3>
        </div>

        <div className="flex items-center gap-1.5">
            {/* Context Dropdown */}
            <div className="relative" ref={contextMenuRef}>
                <button 
                    onClick={() => setShowContextMenu(prev => !prev)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 text-xs font-medium text-gray-300 transition-all max-w-[150px]"
                >
                    {mode === 'general' ? <Briefcase className="h-3 w-3 text-primary-start" /> : <FileText className="h-3 w-3 text-yellow-400" />}
                    <span className="truncate">{getContextButtonLabel()}</span>
                    <ChevronDown className="h-3 w-3 opacity-50 flex-shrink-0" />
                </button>
                <AnimatePresence>
                    {showContextMenu && (
                        <motion.div 
                            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
                            className="absolute right-0 top-full mt-2 w-48 bg-[#1a1a1a] border border-glass-edge rounded-xl shadow-xl z-50 overflow-hidden"
                        >
                            <button onClick={(e) => handleContextChange(e, 'general')} className="w-full text-left flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/5 text-gray-300">
                                <Briefcase size={14} /> General (Case)
                            </button>
                            {documents && documents.length > 0 ? (
                                documents.map(doc => (
                                    <button key={doc.id} onClick={(e) => handleContextChange(e, 'document', doc.id)} className="w-full text-left flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/5 text-gray-300">
                                        <FileText size={14} /> <span className="truncate">{doc.file_name}</span>
                                    </button>
                                ))
                            ) : (
                                <span className="px-3 py-2 text-xs text-gray-500 text-center block">No Documents</span>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
            
            {/* Jurisdiction Dropdown */}
            <div className="relative" ref={jurisdictionMenuRef}>
                <button 
                    onClick={() => setShowJurisdictionMenu(prev => !prev)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 text-xs font-medium text-gray-300 transition-all"
                >
                    <MapPin className={`h-3 w-3 ${jurisdiction === 'ks' ? 'text-blue-400' : 'text-red-500'}`} />
                    <span className="hidden sm:inline">{jurisdiction === 'ks' ? 'Kosovë' : 'Shqipëri'}</span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                </button>
                <AnimatePresence>
                    {showJurisdictionMenu && (
                         <motion.div 
                            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
                            className="absolute right-0 top-full mt-2 w-32 bg-[#1a1a1a] border border-glass-edge rounded-xl shadow-xl z-50 overflow-hidden"
                        >
                            <button onClick={(e) => handleJurisdictionChange(e, 'ks')} className={`w-full flex items-center justify-center gap-2 px-3 py-2 text-xs hover:bg-white/5 ${jurisdiction === 'ks' ? 'text-blue-400' : 'text-gray-300'}`}>
                                Kosovë
                            </button>
                            <button onClick={(e) => handleJurisdictionChange(e, 'al')} className={`w-full flex items-center justify-center gap-2 px-3 py-2 text-xs hover:bg-white/5 ${jurisdiction === 'al' ? 'text-red-400' : 'text-gray-300'}`}>
                                Shqipëri
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <button onClick={onClearChat} className="p-2 text-gray-500 hover:text-red-400 transition-colors" title={t('chatPanel.confirmClear')}>
                <Trash2 size={16} />
            </button>
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