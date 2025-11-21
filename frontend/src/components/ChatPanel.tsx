// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - LINT & UX FIX
// 1. LINT: Utilized the 'reconnect' prop to fix the "unused variable" warning.
// 2. UX: Restored the "Reconnect" button in the header (visible only when disconnected).
// 3. UI: Maintained the bouncing dots and polished bubble design.

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';
import { TFunction } from 'i18next';
import moment from 'moment';
import { 
    Brain, Send, Trash2, User as UserIcon, Sparkles, StopCircle, RefreshCw
} from 'lucide-react';
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
    <div className="flex items-center space-x-3 px-2 py-1">
        <div className="flex space-x-1">
            <motion.div 
                className="w-2 h-2 bg-primary-start rounded-full"
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut", delay: 0 }}
            />
            <motion.div 
                className="w-2 h-2 bg-primary-start rounded-full"
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
            />
            <motion.div 
                className="w-2 h-2 bg-primary-start rounded-full"
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
            />
        </div>
        <span className="text-xs text-primary-start font-medium animate-pulse">
            {t('chatPanel.thinking', 'Asistenti po analizon...')}
        </span>
    </div>
);

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, 
    connectionStatus, 
    onSendMessage, 
    isSendingMessage, 
    reconnect, 
    onClearChat, 
    t 
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => { 
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); 
  }, [messages, isSendingMessage]);

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

  const statusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'CONNECTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'DISCONNECTED': 
      case 'ERROR': return 'bg-red-500/10 text-red-400 border-red-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
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
        className="flex flex-col h-[500px] sm:h-[650px] bg-background-light/30 backdrop-blur-md border border-glass-edge rounded-2xl shadow-2xl overflow-hidden relative" 
        initial={{ opacity: 0, scale: 0.98 }} 
        animate={{ opacity: 1, scale: 1 }} 
        transition={{ duration: 0.4 }}
    >
      {/* --- Header --- */}
      <div className="flex-none p-4 border-b border-glass-edge bg-background-dark/80 flex flex-row justify-between items-center gap-2 z-10">
        <div className="flex items-center space-x-3 min-w-0">
            <div className="p-2 bg-primary-start/20 rounded-lg">
                <Brain className="h-5 w-5 sm:h-6 sm:w-6 text-primary-start" />
            </div>
            <div>
                <h2 className="text-base sm:text-lg font-bold text-text-primary truncate leading-tight">{t('chatPanel.title')}</h2>
                <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border flex items-center gap-1 ${statusColor(connectionStatus)}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                        {statusText(connectionStatus)}
                    </span>
                    
                    {/* PHOENIX FIX: Reconnect Button Restored */}
                    {connectionStatus !== 'CONNECTED' && (
                        <button 
                            onClick={reconnect} 
                            className="text-[10px] text-primary-start hover:underline flex items-center gap-1"
                            title={t('chatPanel.reconnect')}
                        >
                            <RefreshCw size={10} />
                            {t('chatPanel.reconnect')}
                        </button>
                    )}
                </div>
            </div>
        </div>
        
        <button 
            onClick={onClearChat} 
            title={t('chatPanel.clearChat')}
            className="p-2 text-text-secondary hover:text-red-400 hover:bg-white/5 rounded-full transition-colors"
        >
            <Trash2 className="h-4 w-4 sm:h-5 sm:w-5" />
        </button>
      </div>

      {/* --- Messages Area --- */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-6 custom-scrollbar bg-gradient-to-b from-background-dark/50 to-background-dark/90">
        
        {messages.length === 0 && !isSendingMessage && ( 
            <div className="flex flex-col items-center justify-center h-full text-center text-text-secondary space-y-4 opacity-60">
                <Sparkles className="w-12 h-12 text-primary-start/50" />
                <p className="text-sm sm:text-base max-w-xs">{t('chatPanel.welcomeMessage')}</p>
            </div>
        )}
        
        {messages.map((msg: ChatMessage, index: number) => (
          <motion.div 
            key={index} 
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`} 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.3 }}
          >
            {/* Avatar for AI */}
            {msg.sender === 'ai' && (
                <div className="w-8 h-8 rounded-full bg-background-light border border-glass-edge flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Brain className="w-4 h-4 text-primary-start" />
                </div>
            )}

            {/* Message Bubble */}
            <div className={`
                max-w-[85%] sm:max-w-[75%] p-3 sm:p-4 rounded-2xl shadow-md text-sm sm:text-base leading-relaxed relative
                ${msg.sender === 'user' 
                    ? 'bg-gradient-to-br from-primary-start to-primary-end text-white rounded-br-none' 
                    : 'bg-background-light/60 backdrop-blur-md border border-glass-edge text-text-primary rounded-bl-none'
                }
            `}>
              <p className="whitespace-pre-wrap">{msg.content || msg.text || ""}</p>
              <span className={`text-[10px] absolute bottom-1 right-3 opacity-60 ${msg.sender === 'user' ? 'text-white' : 'text-text-secondary'}`}>
                 {moment(msg.timestamp).format('HH:mm')}
              </span>
            </div>

            {/* Avatar for User */}
            {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-full bg-secondary-start border border-transparent flex items-center justify-center flex-shrink-0 shadow-sm">
                    <UserIcon className="w-4 h-4 text-white" />
                </div>
            )}
          </motion.div>
        ))}
        
        {/* Typing Indicator Area */}
        <AnimatePresence>
            {isSendingMessage && (
            <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex justify-start items-end gap-2"
            >
                <div className="w-8 h-8 rounded-full bg-background-light border border-glass-edge flex items-center justify-center flex-shrink-0">
                    <Brain className="w-4 h-4 text-primary-start animate-pulse" />
                </div>
                <div className="p-3 rounded-2xl rounded-bl-none bg-background-light/40 border border-glass-edge backdrop-blur-sm">
                    <TypingIndicator t={t} />
                </div>
            </motion.div>
            )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* --- Input Area --- */}
      <div className="flex-none p-3 sm:p-4 border-t border-glass-edge bg-background-dark/90 backdrop-blur-xl">
        <form onSubmit={handleSubmit} className="flex items-end space-x-2 relative">
          <div className="flex-1 relative">
              <textarea 
                value={inputText} 
                onChange={(e) => setInputText(e.target.value)} 
                onKeyDown={handleKeyDown} 
                rows={1} 
                placeholder={t('chatPanel.inputPlaceholder')} 
                className="w-full resize-none py-3 pl-4 pr-12 border border-glass-edge rounded-2xl bg-background-light/50 text-text-primary text-sm sm:text-base focus:ring-2 focus:ring-primary-start focus:border-transparent transition-all shadow-inner custom-scrollbar max-h-[100px] placeholder:text-text-secondary/50"
                disabled={connectionStatus !== 'CONNECTED' || isSendingMessage} 
                style={{ minHeight: '48px' }}
              />
          </div>
          
          <motion.button 
            type="submit" 
            className={`h-12 w-12 flex-shrink-0 flex items-center justify-center rounded-2xl transition-all duration-300 shadow-lg 
                        ${isSendingMessage || inputText.trim().length === 0 
                            ? 'bg-gray-700 cursor-not-allowed text-gray-400' 
                            : 'bg-gradient-to-r from-primary-start to-primary-end text-white glow-primary hover:scale-105 active:scale-95'}`
            } 
            disabled={connectionStatus !== 'CONNECTED' || isSendingMessage || inputText.trim().length === 0}
          >
            {isSendingMessage ? <StopCircle size={20} className="animate-pulse" /> : <Send size={20} className="ml-0.5" />}
          </motion.button>
        </form>
      </div>
    </motion.div>
  );
};

export default ChatPanel;