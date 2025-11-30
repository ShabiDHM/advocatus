// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - SYNC FIX
// 1. EXPORT: Properly exports 'ChatMode' type.
// 2. INTERFACE: Strict 'ChatPanelProps' definition.

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ConnectionStatus, Document } from '../data/types';
import { TFunction } from 'i18next';
import moment from 'moment';
import { Brain, Send, Trash2, User as UserIcon, Sparkles, StopCircle, RefreshCw, ChevronDown, FileText, Briefcase } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export type ChatMode = 'document' | 'case';

export interface ChatPanelProps {
  caseId: string;
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  documents?: Document[]; 
  onSendMessage: (text: string, mode: ChatMode, documentId?: string) => void; 
  isSendingMessage: boolean;
  reconnect: () => void;
  onClearChat: () => void;
  t: TFunction;
  className?: string;
}

const TypingIndicator: React.FC<{ t: TFunction }> = ({ t }) => (
    <div className="flex items-center space-x-3 px-3 py-2 bg-background-light/50 rounded-2xl rounded-bl-none border border-glass-edge backdrop-blur-md w-fit shadow-lg">
        <div className="flex space-x-1.5">
            <motion.div className="w-2.5 h-2.5 bg-primary-start rounded-full" animate={{ y: [0, -8, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0 }} />
            <motion.div className="w-2.5 h-2.5 bg-primary-start rounded-full" animate={{ y: [0, -8, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0.2 }} />
            <motion.div className="w-2.5 h-2.5 bg-primary-start rounded-full" animate={{ y: [0, -8, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0.4 }} />
        </div>
        <span className="text-xs text-text-primary font-semibold animate-pulse">{t('chatPanel.thinking', 'Sokrati duke analizuar...')}</span>
    </div>
);

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, reconnect, onClearChat, t, className, documents = []
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedContextId, setSelectedContextId] = useState<string>('case');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null); 
  const [showThinking, setShowThinking] = useState(false);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, showThinking]);

  useEffect(() => {
      if (isSendingMessage) { setShowThinking(true); } 
      else { const timer = setTimeout(() => setShowThinking(false), 1500); return () => clearTimeout(timer); }
  }, [isSendingMessage]);

  useEffect(() => {
      if (textareaRef.current) {
          textareaRef.current.style.height = 'auto'; 
          textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`; 
      }
  }, [inputText]);

  const handleSubmit = (e: React.FormEvent) => { 
      e.preventDefault(); 
      if (inputText.trim() && !isSendingMessage) { 
          const mode: ChatMode = selectedContextId === 'case' ? 'case' : 'document';
          const docId = selectedContextId === 'case' ? undefined : selectedContextId;
          onSendMessage(inputText.trim(), mode, docId); 
          setInputText(''); 
          if (textareaRef.current) textareaRef.current.style.height = 'auto';
      } 
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { 
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); } 
  };

  const statusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'CONNECTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default: return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
  };

  return (
    <div className={`chat-panel bg-background-dark p-4 sm:p-6 rounded-2xl shadow-xl flex flex-col ${className || 'h-[500px] sm:h-[600px]'}`}>
      <div className="flex flex-col gap-3 border-b border-background-light/50 pb-3 mb-4 flex-shrink-0">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-text-primary">Asistenti Sokratik</h2>
                <div className={`text-[10px] px-2 py-0.5 rounded-full border flex items-center gap-1 transition-all ${statusColor(connectionStatus)}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                    {connectionStatus !== 'CONNECTED' && <button onClick={reconnect} className="ml-1 hover:text-white"><RefreshCw size={10} /></button>}
                </div>
            </div>
            <button onClick={onClearChat} title={t('chatPanel.clearChat')} className="p-2 text-gray-400 hover:text-red-400 transition-colors rounded-lg hover:bg-white/5"><Trash2 className="h-4 w-4" /></button>
          </div>

          <div className="relative group w-full sm:w-auto">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                  {selectedContextId === 'case' ? <Briefcase size={14} className="text-amber-500" /> : <FileText size={14} className="text-primary-start" />}
              </div>
              <select
                value={selectedContextId}
                onChange={(e) => setSelectedContextId(e.target.value)}
                className={`w-full appearance-none pl-9 pr-8 py-2 text-sm rounded-lg border focus:ring-2 focus:outline-none transition-all cursor-pointer font-medium
                    ${selectedContextId === 'case' 
                        ? 'bg-amber-900/10 border-amber-500/30 text-amber-100 focus:border-amber-500 focus:ring-amber-500/20' 
                        : 'bg-background-light/30 border-glass-edge text-white focus:border-primary-start focus:ring-primary-start/20'
                    }`}
              >
                  <option value="case" className="bg-slate-900 text-amber-400 font-bold">🗂️ E gjithë Dosja</option>
                  {documents.length > 0 && (
                      <optgroup label="Zgjidh Dokument Specifik" className="bg-slate-900 text-gray-400">
                          {documents.map(doc => <option key={doc.id} value={doc.id} className="bg-slate-900 text-white">📄 {doc.file_name}</option>)}
                      </optgroup>
                  )}
              </select>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500"><ChevronDown size={14} /></div>
          </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-6 custom-scrollbar pr-2 mb-4">
        {messages.length === 0 && !showThinking && ( 
            <div className="flex flex-col items-center justify-center h-full text-center text-text-secondary opacity-60 space-y-4">
                <Sparkles className={`w-12 h-12 ${selectedContextId === 'case' ? 'text-amber-500/40' : 'text-primary-start/30'}`} />
                <p className="text-sm">{t('chatPanel.welcomeMessage')}</p>
                <span className={`text-xs px-3 py-1 rounded-full border ${selectedContextId === 'case' ? 'text-amber-500/80 bg-amber-500/10 border-amber-500/20' : 'text-primary-start/80 bg-primary-start/10 border-primary-start/20'}`}>
                    {selectedContextId === 'case' ? 'Modi: Kërkim në Çështje' : 'Modi: Kërkim në Dokument'}
                </span>
            </div>
        )}
        
        {messages.map((msg, index) => (
          <motion.div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} items-end gap-3`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {msg.sender === 'ai' && <div className="w-8 h-8 rounded-full bg-background-light border border-glass-edge flex items-center justify-center flex-shrink-0"><Brain className="w-4 h-4 text-primary-start" /></div>}
            <div className={`max-w-[85%] p-3 rounded-2xl shadow-sm text-sm leading-relaxed ${msg.sender === 'user' ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' : 'bg-background-light/20 border border-glass-edge/30 text-text-primary rounded-bl-none'}`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              <span className="text-[10px] block mt-1 opacity-60 text-right">{moment(msg.timestamp).format('HH:mm')}</span>
            </div>
            {msg.sender === 'user' && <div className="w-8 h-8 rounded-full bg-secondary-start flex items-center justify-center flex-shrink-0"><UserIcon className="w-4 h-4 text-white" /></div>}
          </motion.div>
        ))}
        
        <AnimatePresence>
            {showThinking && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex justify-start items-end gap-3">
                    <div className="w-8 h-8 rounded-full bg-background-light border border-glass-edge flex items-center justify-center flex-shrink-0"><Brain className="w-4 h-4 text-primary-start animate-pulse" /></div>
                    <TypingIndicator t={t} />
                </motion.div>
            )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <div className={`flex-none pt-3 border-t ${selectedContextId === 'case' ? 'border-amber-500/20' : 'border-glass-edge/30'}`}>
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <textarea 
            ref={textareaRef}
            value={inputText} 
            onChange={(e) => setInputText(e.target.value)} 
            onKeyDown={handleKeyDown} 
            rows={1} 
            placeholder={selectedContextId === 'case' ? "Pyetni për të gjithë çështjen..." : "Pyetni për këtë dokument..."} 
            className={`flex-1 resize-none py-3 px-4 border rounded-xl bg-background-light/10 text-text-primary focus:ring-1 min-h-[48px] max-h-[200px] custom-scrollbar text-sm transition-all duration-200 
                ${selectedContextId === 'case' ? 'border-amber-500/30 focus:border-amber-500 focus:ring-amber-500 placeholder-amber-500/30' : 'border-glass-edge/50 focus:border-primary-start focus:ring-primary-start'}`}
            disabled={connectionStatus !== 'CONNECTED' || isSendingMessage} 
          />
          <motion.button type="submit" className={`h-[48px] w-[48px] flex-shrink-0 flex items-center justify-center rounded-xl shadow-lg transition-all ${isSendingMessage || !inputText.trim() ? 'bg-gray-800 text-gray-600 cursor-not-allowed' : selectedContextId === 'case' ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:scale-105 shadow-amber-900/20' : 'bg-gradient-to-r from-primary-start to-primary-end text-white glow-primary hover:scale-105'}`} disabled={connectionStatus !== 'CONNECTED' || isSendingMessage || !inputText.trim()}>
            {isSendingMessage ? <StopCircle size={20} className="animate-pulse" /> : <Send size={20} />}
          </motion.button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;