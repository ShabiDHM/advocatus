// FILE: /home/user/advocatus-frontend/src/components/ChatPanel.tsx

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types'; // CURE: Import ConnectionStatus
import { TFunction } from 'i18next';
import moment from 'moment';
import { Brain } from 'lucide-react';
import { motion } from 'framer-motion';

interface ChatPanelProps {
  caseId: string;
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus; // CURE: Use authoritative type
  onSendMessage: (text: string) => void;
  isSendingMessage: boolean;
  reconnect: () => void;
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

const ChatPanel: React.FC<ChatPanelProps> = ({ messages, connectionStatus, onSendMessage, isSendingMessage, reconnect, t }) => {
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
      case 'ERROR': return 'bg-red-500 text-white'; // CURE: Handle ERROR state
      default: return 'bg-background-light text-text-secondary';
    }
  };

  const statusText = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return t('chatPanel.statusConnected');
      case 'CONNECTING': return t('chatPanel.statusConnecting');
      case 'DISCONNECTED': return t('chatPanel.statusDisconnected');
      case 'ERROR': return t('chatPanel.statusError'); // CURE: Handle ERROR state
    }
  };

  return (
    <motion.div className="flex flex-col h-[600px] bg-background-light/50 backdrop-blur-sm border border-glass-edge rounded-2xl shadow-xl" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }}>
      <div className="flex-none p-4 border-b border-glass-edge flex justify-between items-center">
        <div className="flex items-center space-x-2">
            <Brain className="h-6 w-6 text-text-primary" />
            <h2 className="text-xl font-bold text-text-primary">{t('chatPanel.title')}</h2>
        </div>
        <div className={`text-xs font-semibold px-3 py-1 rounded-full flex items-center transition-all ${statusColor(connectionStatus)}`}>
          {statusText(connectionStatus)}
          {connectionStatus !== 'CONNECTED' && ( <motion.button onClick={reconnect} className="ml-2 underline text-white/80 hover:text-white" whileHover={{ scale: 1.05 }}> {t('chatPanel.reconnect')} </motion.button> )}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.length === 0 && !isSendingMessage && ( <div className="text-center text-text-secondary pt-10"> {t('chatPanel.welcomeMessage')} </div> )}
        
        {messages.map((msg: ChatMessage, index: number) => (
          <motion.div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: index * 0.05 }}>
            <div className={`max-w-xs md:max-w-md lg:max-w-lg p-3 rounded-xl shadow-lg transition-all ${ msg.sender === 'user' ? 'bg-gradient-to-r from-primary-start to-primary-end text-white rounded-br-none glow-primary/50' : 'bg-background-dark/80 text-text-primary rounded-tl-none border border-glass-edge' }`}>
              <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
              <span className={`text-xs block mt-1 ${msg.sender === 'user' ? 'text-white/70' : 'text-text-secondary'}`}> {moment(msg.timestamp).format('HH:mm')} </span>
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

      <div className="flex-none p-4 border-t border-glass-edge">
        <form onSubmit={handleSubmit} className="flex items-center space-x-3">
          <textarea value={inputText} onChange={(e) => setInputText(e.target.value)} onKeyDown={handleKeyDown} rows={2} placeholder={t('chatPanel.inputPlaceholder')} className="flex-1 resize-none p-3 border border-glass-edge rounded-xl bg-background-dark text-text-primary focus:ring-primary-start focus:border-primary-start" disabled={connectionStatus !== 'CONNECTED' || isSendingMessage} />
          <motion.button type="submit" className={`h-10 w-10 flex items-center justify-center rounded-full transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end ${isSendingMessage || inputText.trim().length === 0 ? 'opacity-50' : ''}`} disabled={connectionStatus !== 'CONNECTED' || isSendingMessage || inputText.trim().length === 0} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-send text-white"><line x1="22" x2="11" y1="2" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </motion.button>
        </form>
      </div>
    </motion.div>
  );
};

export default ChatPanel;