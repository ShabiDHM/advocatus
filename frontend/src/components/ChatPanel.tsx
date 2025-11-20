// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - MOBILE OPTIMIZATION
// 1. RESPONSIVE HEIGHT: 'h-[450px] sm:h-[600px]' to fit mobile viewports.
// 2. HEADER LAYOUT: Improved flex wrapping for small screens.
// 3. INPUT AREA: Optimized padding for touch targets.

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';
import { TFunction } from 'i18next';
import moment from 'moment';
import { Brain, Send, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

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
    <div className="flex items-center space-x-1">
        <span className="text-sm text-text-secondary">{t('chatPanel.thinking')}</span>
        <motion.div className="h-2 w-2 bg-text-secondary rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0 }} />
        <motion.div className="h-2 w-2 bg-text-secondary rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0.5 }} />
        <motion.div className="h-2 w-2 bg-text-secondary rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.5, repeat: Infinity, delay: 1 }} />
    </div>
);

const ChatPanel: React.FC<ChatPanelProps> = ({ messages, connectionStatus, onSendMessage, isSendingMessage, reconnect, onClearChat, t }) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isSendingMessage]);

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); if (inputText.trim() && !isSendingMessage) { onSendMessage(inputText.trim()); setInputText(''); } };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); } };

  const statusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-success-start text-white glow-accent';
      case 'CONNECTING': return 'bg-accent-start text-white';
      case 'DISCONNECTED': return 'bg-red-500 text-white';
      case 'ERROR': return 'bg-red-500 text-white';
      default: return 'bg-background-light text-text-secondary';
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
    <motion.div 
        className="flex flex-col h-[450px] sm:h-[600px] bg-background-light/50 backdrop-blur-sm border border-glass-edge rounded-2xl shadow-xl" 
        initial={{ opacity: 0, scale: 0.98 }} 
        animate={{ opacity: 1, scale: 1 }} 
        transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="flex-none p-4 border-b border-glass-edge flex flex-row justify-between items-center gap-2">
        <div className="flex items-center space-x-2 min-w-0">
            <Brain className="h-5 w-5 sm:h-6 sm:w-6 text-text-primary flex-shrink-0" />
            <h2 className="text-lg sm:text-xl font-bold text-text-primary truncate">{t('chatPanel.title')}</h2>
        </div>
        <div className="flex items-center space-x-2 sm:space-x-3 flex-shrink-0">
            <div className={`text-[10px] sm:text-xs font-semibold px-2 sm:px-3 py-1 rounded-full flex items-center transition-all whitespace-nowrap ${statusColor(connectionStatus)}`}>
                {statusText(connectionStatus)}
                {connectionStatus !== 'CONNECTED' && ( 
                    <motion.button onClick={reconnect} className="ml-2 underline text-white/80 hover:text-white" whileHover={{ scale: 1.05 }}> 
                        {t('chatPanel.reconnect')} 
                    </motion.button> 
                )}
            </div>
            
            <motion.button 
                onClick={onClearChat} 
                title={t('chatPanel.clearChat')}
                className="p-1.5 sm:p-2 text-text-secondary hover:text-red-400 transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
            >
                <Trash2 className="h-4 w-4 sm:h-5 sm:w-5" />
            </motion.button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4 custom-scrollbar">
        {messages.length === 0 && !isSendingMessage && ( <div className="text-center text-text-secondary pt-10 text-sm sm:text-base"> {t('chatPanel.welcomeMessage')} </div> )}
        
        {messages.map((msg: ChatMessage, index: number) => (
          <motion.div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: index * 0.05 }}>
            <div className={`max-w-[85%] sm:max-w-md lg:max-w-lg p-3 rounded-xl shadow-lg transition-all ${ msg.sender === 'user' ? 'bg-gradient-to-r from-primary-start to-primary-end text-white rounded-br-none glow-primary/50' : 'bg-background-dark/80 text-text-primary rounded-tl-none border border-glass-edge' }`}>
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content || msg.text || ""}</p>
              <span className={`text-[10px] sm:text-xs block mt-1 ${msg.sender === 'user' ? 'text-white/70' : 'text-text-secondary'}`}> {moment(msg.timestamp).format('HH:mm')} </span>
            </div>
          </motion.div>
        ))}
        
        {isSendingMessage && (
          <motion.div className="flex justify-start">
            <div className="p-3 rounded-xl bg-background-dark/80 text-text-secondary border border-glass-edge flex items-center space-x-2">
              <TypingIndicator t={t} />
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex-none p-3 sm:p-4 border-t border-glass-edge">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2 sm:space-x-3">
          <textarea 
            value={inputText} 
            onChange={(e) => setInputText(e.target.value)} 
            onKeyDown={handleKeyDown} 
            rows={1} 
            placeholder={t('chatPanel.inputPlaceholder')} 
            className="flex-1 resize-none p-3 border border-glass-edge rounded-xl bg-background-dark text-text-primary text-sm sm:text-base focus:ring-primary-start focus:border-primary-start min-h-[44px] max-h-[100px]" 
            disabled={connectionStatus !== 'CONNECTED' || isSendingMessage} 
          />
          <motion.button 
            type="submit" 
            className={`h-10 w-10 sm:h-11 sm:w-11 flex-shrink-0 flex items-center justify-center rounded-full transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end ${isSendingMessage || inputText.trim().length === 0 ? 'opacity-50' : ''}`} 
            disabled={connectionStatus !== 'CONNECTED' || isSendingMessage || inputText.trim().length === 0} 
            whileHover={{ scale: 1.05 }} 
            whileTap={{ scale: 0.95 }}
          >
            <Send size={20} className="text-white" />
          </motion.button>
        </form>
      </div>
    </motion.div>
  );
};

export default ChatPanel;