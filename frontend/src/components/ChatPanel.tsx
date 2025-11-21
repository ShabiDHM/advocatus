// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - UI STANDARDIZATION
// 1. VISUALS: Switched to 'bg-background-dark' to match Documents Panel.
// 2. HEADER: Aligned Title and Badge in a single row (no subtitle look).
// 3. LAYOUT: Set to 'h-full' to stretch with the sibling panel.

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';
import { TFunction } from 'i18next';
import moment from 'moment';
import { Brain, Send, Trash2, User as UserIcon, Sparkles, StopCircle, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatPanelProps {
  caseId: string;
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  onSendMessage: (text: string) => void;
  isSendingMessage: boolean;
  reconnect: () => void;
  onClearChat: () => void;
  t: TFunction;
}

const TypingIndicator: React.FC<{ t: TFunction }> = ({ t }) => (
    <div className="flex items-center space-x-2 px-3 py-2 bg-background-light/20 rounded-2xl rounded-bl-none border border-glass-edge w-fit">
        <div className="flex space-x-1">
            <motion.div className="w-1.5 h-1.5 bg-primary-start rounded-full" animate={{ y: [0, -5, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0 }} />
            <motion.div className="w-1.5 h-1.5 bg-primary-start rounded-full" animate={{ y: [0, -5, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }} />
            <motion.div className="w-1.5 h-1.5 bg-primary-start rounded-full" animate={{ y: [0, -5, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }} />
        </div>
        <span className="text-xs text-text-secondary font-medium animate-pulse">{t('chatPanel.thinking', 'Duke analizuar...')}</span>
    </div>
);

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, connectionStatus, onSendMessage, isSendingMessage, reconnect, onClearChat, t 
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
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

  const handleSubmit = (e: React.FormEvent) => { 
      e.preventDefault(); 
      if (inputText.trim() && !isSendingMessage) { 
          onSendMessage(inputText.trim()); 
          setInputText(''); 
      } 
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { 
      if (e.key === 'Enter' && !e.shiftKey) { 
          e.preventDefault(); 
          handleSubmit(e as unknown as React.FormEvent); 
      } 
  };

  // Same badge style as DocumentsPanel
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
    // MATCHED CONTAINER STYLE: bg-background-dark, same padding structure
    <div className="chat-panel bg-background-dark p-4 sm:p-6 rounded-2xl shadow-xl flex flex-col h-full">
      
      {/* HEADER: Matches DocumentsPanel Layout (Title | Badge ... Actions) */}
      <div className="flex flex-row justify-between items-center border-b border-background-light/50 pb-3 mb-4 flex-shrink-0 gap-2">
        <div className="flex items-center gap-2 sm:gap-4 min-w-0 overflow-hidden">
            <h2 className="text-lg sm:text-xl font-bold text-text-primary truncate">{t('chatPanel.title')}</h2>
            
            {/* Inline Badge */}
            <div className={`text-[10px] sm:text-xs px-2 sm:px-3 py-1 rounded-full border flex items-center gap-1.5 transition-all whitespace-nowrap ${statusColor(connectionStatus)}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                {statusText(connectionStatus)}
                
                {connectionStatus !== 'CONNECTED' && (
                    <button onClick={reconnect} className="ml-1 underline hover:text-white" title={t('chatPanel.reconnect')}>
                        <RefreshCw size={10} />
                    </button>
                )}
            </div>
        </div>

        <button 
            onClick={onClearChat} 
            title={t('chatPanel.clearChat')}
            className="p-2 text-text-secondary hover:text-red-400 transition-colors rounded-full hover:bg-white/5"
        >
            <Trash2 className="h-5 w-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-6 custom-scrollbar pr-2 mb-4">
        {messages.length === 0 && !showThinking && ( 
            <div className="flex flex-col items-center justify-center h-full text-center text-text-secondary opacity-60 space-y-4">
                <Sparkles className="w-12 h-12 text-primary-start/30" />
                <p className="text-sm">{t('chatPanel.welcomeMessage')}</p>
            </div>
        )}
        
        {messages.map((msg: ChatMessage, index: number) => (
          <motion.div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} items-end gap-3`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {msg.sender === 'ai' && <div className="w-8 h-8 rounded-full bg-background-light border border-glass-edge flex items-center justify-center flex-shrink-0"><Brain className="w-4 h-4 text-primary-start" /></div>}
            <div className={`max-w-[85%] p-3 rounded-2xl shadow-sm text-sm leading-relaxed ${msg.sender === 'user' ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' : 'bg-background-light/20 border border-glass-edge/30 text-text-primary rounded-bl-none'}`}>
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
      <div className="flex-none pt-3 border-t border-glass-edge/30">
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <textarea value={inputText} onChange={(e) => setInputText(e.target.value)} onKeyDown={handleKeyDown} rows={1} placeholder={t('chatPanel.inputPlaceholder')} className="flex-1 resize-none py-3 px-4 border border-glass-edge/50 rounded-xl bg-background-light/10 text-text-primary focus:ring-1 focus:ring-primary-start focus:border-primary-start min-h-[46px] max-h-[100px] custom-scrollbar text-sm" disabled={connectionStatus !== 'CONNECTED' || isSendingMessage} />
          <motion.button type="submit" className={`h-[46px] w-[46px] flex-shrink-0 flex items-center justify-center rounded-xl shadow-lg transition-all ${isSendingMessage || !inputText.trim() ? 'bg-gray-800 text-gray-600 cursor-not-allowed' : 'bg-gradient-to-r from-primary-start to-primary-end text-white glow-primary hover:scale-105'}`} disabled={connectionStatus !== 'CONNECTED' || isSendingMessage || !inputText.trim()}>
            {isSendingMessage ? <StopCircle size={20} className="animate-pulse" /> : <Send size={20} />}
          </motion.button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;