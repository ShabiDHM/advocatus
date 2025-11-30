// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - DUAL MODE CHAT
// 1. FEATURE: Added Toggle for 'Dokumenti' vs 'E gjithë Çështja'.
// 2. LOGIC: Passes active mode to parent handler (requires parent update, backward compatible).
// 3. UI: distinct visual cues for Case Mode (Gold/Indigo accents).

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';
import { TFunction } from 'i18next';
import moment from 'moment';
import { Brain, Send, Trash2, User as UserIcon, Sparkles, StopCircle, RefreshCw, FileText, Briefcase } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export type ChatMode = 'document' | 'case';

interface ChatPanelProps {
  caseId: string;
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  // UPDATED: Now accepts optional mode, defaults to 'document' if not handled
  onSendMessage: (text: string, mode?: ChatMode) => void; 
  isSendingMessage: boolean;
  reconnect: () => void;
  onClearChat: () => void;
  t: TFunction;
  className?: string;
}

const TypingIndicator: React.FC<{ t: TFunction }> = ({ t }) => (
    <div className="flex items-center space-x-3 px-3 py-2 bg-background-light/50 rounded-2xl rounded-bl-none border border-glass-edge backdrop-blur-md w-fit shadow-lg">
        <div className="flex space-x-1.5">
            <motion.div 
                className="w-2.5 h-2.5 bg-primary-start rounded-full"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0 }}
            />
            <motion.div 
                className="w-2.5 h-2.5 bg-primary-start rounded-full"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
            />
            <motion.div 
                className="w-2.5 h-2.5 bg-primary-start rounded-full"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
            />
        </div>
        <span className="text-xs text-text-primary font-semibold animate-pulse">
            {t('chatPanel.thinking', 'Sokrati duke analizuar...')}
        </span>
    </div>
);

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, reconnect, onClearChat, t, className 
}) => {
  const [inputText, setInputText] = useState('');
  const [activeMode, setActiveMode] = useState<ChatMode>('document');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null); 
  const [showThinking, setShowThinking] = useState(false);

  useEffect(() => { 
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); 
  }, [messages, showThinking]);

  useEffect(() => {
      if (isSendingMessage) {
          setShowThinking(true);
      } else {
          const timer = setTimeout(() => setShowThinking(false), 1500);
          return () => clearTimeout(timer);
      }
  }, [isSendingMessage]);

  useEffect(() => {
      const textarea = textareaRef.current;
      if (textarea) {
          textarea.style.height = 'auto'; 
          textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`; 
      }
  }, [inputText]);

  const handleSubmit = (e: React.FormEvent) => { 
      e.preventDefault(); 
      if (inputText.trim() && !isSendingMessage) { 
          onSendMessage(inputText.trim(), activeMode); 
          setInputText(''); 
          if (textareaRef.current) {
              textareaRef.current.style.height = 'auto';
          }
      } 
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { 
      if (e.key === 'Enter' && !e.shiftKey) { 
          e.preventDefault(); 
          handleSubmit(e as unknown as React.FormEvent); 
      } 
  };

  const statusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'CONNECTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default: return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
  };

  const statusText = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return t('chatPanel.statusConnected');
      case 'CONNECTING': return t('chatPanel.statusConnecting');
      case 'DISCONNECTED': return t('chatPanel.statusDisconnected');
      case 'ERROR': return t('chatPanel.statusError');
    }
  };

  return (
    <div className={`chat-panel bg-background-dark p-4 sm:p-6 rounded-2xl shadow-xl flex flex-col ${className || 'h-[500px] sm:h-[600px]'}`}>
      
      {/* Header & Controls */}
      <div className="flex flex-col gap-3 border-b border-background-light/50 pb-3 mb-4 flex-shrink-0">
          {/* Top Row: Title + Connection + Delete */}
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-text-primary">Asistenti Sokratik</h2>
                <div className={`text-[10px] px-2 py-0.5 rounded-full border flex items-center gap-1 transition-all ${statusColor(connectionStatus)}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                    <span className="hidden sm:inline">{statusText(connectionStatus)}</span>
                    {connectionStatus !== 'CONNECTED' && (
                        <button onClick={reconnect} className="ml-1 hover:text-white"><RefreshCw size={10} /></button>
                    )}
                </div>
            </div>
            <button 
                onClick={onClearChat} 
                title={t('chatPanel.clearChat')}
                className="p-2 text-gray-400 hover:text-red-400 transition-colors rounded-lg hover:bg-white/5"
            >
                <Trash2 className="h-4 w-4" />
            </button>
          </div>

          {/* Mode Switcher */}
          <div className="flex bg-background-light/20 p-1 rounded-lg border border-glass-edge self-start">
              <button
                onClick={() => setActiveMode('document')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    activeMode === 'document' 
                    ? 'bg-primary-start text-white shadow-md' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                  <FileText size={12} />
                  Dokumenti
              </button>
              <button
                onClick={() => setActiveMode('case')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    activeMode === 'case' 
                    ? 'bg-amber-600 text-white shadow-md' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                  <Briefcase size={12} />
                  E gjithë Çështja
              </button>
          </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-6 custom-scrollbar pr-2 mb-4">
        {messages.length === 0 && !showThinking && ( 
            <div className="flex flex-col items-center justify-center h-full text-center text-text-secondary opacity-60 space-y-4">
                <Sparkles className={`w-12 h-12 ${activeMode === 'case' ? 'text-amber-500/40' : 'text-primary-start/30'}`} />
                <p className="text-sm">{t('chatPanel.welcomeMessage')}</p>
                {activeMode === 'case' && (
                    <span className="text-xs text-amber-500/80 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20">
                        Mode: Kërkim i Avancuar në të gjithë Dosjen
                    </span>
                )}
            </div>
        )}
        
        {messages.map((msg: ChatMessage, index: number) => (
          <motion.div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} items-end gap-3`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {msg.sender === 'ai' && (
                <div className={`w-8 h-8 rounded-full border border-glass-edge flex items-center justify-center flex-shrink-0 ${activeMode === 'case' && index === messages.length - 1 ? 'bg-amber-900/30 border-amber-500/30' : 'bg-background-light'}`}>
                    <Brain className={`w-4 h-4 ${activeMode === 'case' && index === messages.length - 1 ? 'text-amber-400' : 'text-primary-start'}`} />
                </div>
            )}
            
            <div className={`max-w-[85%] p-3 rounded-2xl shadow-sm text-sm leading-relaxed ${
                msg.sender === 'user' 
                ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' 
                : 'bg-background-light/20 border border-glass-edge/30 text-text-primary rounded-bl-none'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content || msg.text || ""}</p>
              <span className={`text-[10px] block mt-1 opacity-60 text-right`}>{moment(msg.timestamp).format('HH:mm')}</span>
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

      {/* Input */}
      <div className={`flex-none pt-3 border-t ${activeMode === 'case' ? 'border-amber-500/20' : 'border-glass-edge/30'}`}>
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <textarea 
            ref={textareaRef}
            value={inputText} 
            onChange={(e) => setInputText(e.target.value)} 
            onKeyDown={handleKeyDown} 
            rows={1} 
            placeholder={activeMode === 'case' ? "Pyetni për të gjithë çështjen..." : t('chatPanel.inputPlaceholder')} 
            className={`flex-1 resize-none py-3 px-4 border rounded-xl bg-background-light/10 text-text-primary focus:ring-1 min-h-[48px] max-h-[200px] custom-scrollbar text-sm transition-all duration-200 
                ${activeMode === 'case' 
                    ? 'border-amber-500/30 focus:border-amber-500 focus:ring-amber-500 placeholder-amber-500/30' 
                    : 'border-glass-edge/50 focus:border-primary-start focus:ring-primary-start'}`}
            disabled={connectionStatus !== 'CONNECTED' || isSendingMessage} 
          />
          <motion.button 
            type="submit" 
            className={`h-[48px] w-[48px] flex-shrink-0 flex items-center justify-center rounded-xl shadow-lg transition-all ${
                isSendingMessage || !inputText.trim() 
                ? 'bg-gray-800 text-gray-600 cursor-not-allowed' 
                : activeMode === 'case'
                    ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:scale-105 shadow-amber-900/20'
                    : 'bg-gradient-to-r from-primary-start to-primary-end text-white glow-primary hover:scale-105'
            }`} 
            disabled={connectionStatus !== 'CONNECTED' || isSendingMessage || !inputText.trim()}
          >
            {isSendingMessage ? <StopCircle size={20} className="animate-pulse" /> : <Send size={20} />}
          </motion.button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;