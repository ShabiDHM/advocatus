// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - UI POLISH V4
// 1. ICON: Replaced generic 'Bot' icon with 'BrainCircuit' for consistent AI identity.
// 2. FORMATTING: Fixed ReactMarkdown styling to correctly render lists, bolding, etc.
// 3. STATUS: Restored "beautiful output".

import React, { useState, useEffect, useRef } from 'react';
import { ChatMessage, ConnectionStatus, Document } from '../data/types';
import { Send, Eraser, Loader2, User, Scale, BrainCircuit } from 'lucide-react'; // PHOENIX: Changed Bot to BrainCircuit
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';

export type ChatMode = 'general' | 'document' | 'analysis';
export type Jurisdiction = 'ks' | 'al';

interface ChatPanelProps {
    messages: ChatMessage[];
    connectionStatus: ConnectionStatus;
    reconnect: () => void;
    onSendMessage: (text: string, mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => void;
    isSendingMessage: boolean;
    caseId: string;
    onClearChat: () => void;
    t: TFunction;
    documents: Document[];
    className?: string;
}

// Simulates streaming text character by character
const TypingMessage: React.FC<{ text: string }> = ({ text }) => {
    const [displayedText, setDisplayedText] = useState("");
    
    useEffect(() => {
        setDisplayedText(""); // Reset on new text
        let index = 0;
        const speed = 10; // ms per char

        const intervalId = setInterval(() => {
            setDisplayedText((prev) => {
                if (index >= text.length) {
                    clearInterval(intervalId);
                    return text;
                }
                const nextChar = text.charAt(index);
                index++;
                return prev + nextChar;
            });
        }, speed);

        return () => clearInterval(intervalId);
    }, [text]);

    // PHOENIX FIX: Apply prose styling directly here
    return (
        <div className="prose prose-invert prose-sm max-w-none text-sm break-words leading-relaxed">
            <ReactMarkdown>{displayedText}</ReactMarkdown>
        </div>
    );
};

const ChatPanel: React.FC<ChatPanelProps> = ({ 
    messages, 
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
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isSendingMessage]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isSendingMessage) return;
        onSendMessage(input, mode, selectedDocId || undefined, jurisdiction);
        setInput('');
    };

    return (
        <div className={`flex flex-col bg-background-dark/40 border border-white/10 rounded-2xl shadow-xl overflow-hidden backdrop-blur-md ${className || 'h-[600px]'}`}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/20">
                <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-xl ${jurisdiction === 'ks' ? 'bg-blue-600/20 text-blue-400' : 'bg-red-600/20 text-red-400'}`}>
                        <Scale size={18} />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold text-white flex items-center gap-2">
                            {t('chatPanel.title')}
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/10 text-gray-400 border border-white/5 uppercase">
                                {jurisdiction === 'ks' ? 'Kosovë' : 'Shqipëri'}
                            </span>
                        </h2>
                        <p className="text-[10px] text-gray-500">Socratic Legal Assistant</p>
                    </div>
                </div>
                <button onClick={onClearChat} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title={t('chatPanel.clearHistory')}>
                    <Eraser size={16} />
                </button>
            </div>

            {/* Config Bar */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-white/5 bg-white/5 overflow-x-auto no-scrollbar">
                <select 
                    value={jurisdiction} 
                    onChange={(e) => setJurisdiction(e.target.value as Jurisdiction)}
                    className="bg-black/20 border border-white/10 rounded-lg px-2 py-1 text-xs text-gray-300 focus:ring-1 focus:ring-primary-start outline-none"
                >
                    <option value="ks">⚖️ Kosovë</option>
                    <option value="al">🦅 Shqipëri</option>
                </select>

                <select 
                    value={mode} 
                    onChange={(e) => setMode(e.target.value as ChatMode)}
                    className="bg-black/20 border border-white/10 rounded-lg px-2 py-1 text-xs text-gray-300 focus:ring-1 focus:ring-primary-start outline-none"
                >
                    <option value="general">🌐 Pyetje e Përgjithshme</option>
                    <option value="document">📄 Pyet Dokumentin</option>
                </select>

                {mode === 'document' && (
                    <select 
                        value={selectedDocId} 
                        onChange={(e) => setSelectedDocId(e.target.value)}
                        className="max-w-[150px] bg-black/20 border border-white/10 rounded-lg px-2 py-1 text-xs text-gray-300 focus:ring-1 focus:ring-primary-start outline-none truncate"
                    >
                        <option value="">Zgjidh Dokumentin...</option>
                        {documents.map(d => (
                            <option key={d.id} value={d.id}>{d.file_name}</option>
                        ))}
                    </select>
                )}
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-gradient-to-b from-transparent to-black/20">
                {messages.length === 0 && !isSendingMessage && (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-50">
                        <BrainCircuit size={48} className="mb-4" /> {/* PHOENIX: Changed to Brain icon */}
                        <p className="text-sm">Përshëndetje! Unë jam asistenti juaj ligjor.</p>
                        <p className="text-xs mt-2">Mund të pyesni për dokumentet ose ligjet.</p>
                    </div>
                )}
                
                {messages.map((msg, index) => {
                    const isAi = msg.role === 'ai';
                    const isLatest = index === messages.length - 1;
                    const useTyping = isAi && isLatest && !isSendingMessage;

                    return (
                        <motion.div 
                            key={index} 
                            initial={{ opacity: 0, y: 10 }} 
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex gap-3 ${isAi ? 'justify-start' : 'justify-end'}`}
                        >
                            {isAi && (
                                <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30 flex-shrink-0 mt-1">
                                    <BrainCircuit size={16} className="text-indigo-400" /> {/* PHOENIX: Changed to Brain icon */}
                                </div>
                            )}
                            
                            <div className={`max-w-[85%] rounded-2xl p-3.5 text-sm shadow-md ${
                                isAi 
                                ? 'bg-gray-800/80 border border-white/5 text-gray-200 rounded-tl-none' 
                                : 'bg-primary-start text-white rounded-tr-none'
                            }`}>
                                {isAi ? (
                                    useTyping ? (
                                        <TypingMessage text={msg.content} />
                                    ) : (
                                        // PHOENIX FIX: Added prose classes to the container to fix markdown rendering
                                        <div className="prose prose-invert prose-sm max-w-none text-sm break-words leading-relaxed">
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        </div>
                                    )
                                ) : (
                                    <p className="break-words leading-relaxed">{msg.content}</p>
                                )}
                            </div>

                            {!isAi && (
                                <div className="w-8 h-8 rounded-full bg-primary-start/20 flex items-center justify-center border border-primary-start/30 flex-shrink-0 mt-1">
                                    <User size={16} className="text-primary-start" />
                                </div>
                            )}
                        </motion.div>
                    );
                })}

                {/* Loading Indicator */}
                {isSendingMessage && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3 justify-start">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30 flex-shrink-0 mt-1">
                            <Loader2 size={16} className="text-indigo-400 animate-spin" />
                        </div>
                        <div className="bg-gray-800/50 border border-white/5 rounded-2xl rounded-tl-none p-3 flex items-center gap-2">
                            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></span>
                        </div>
                    </motion.div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-black/20 border-t border-white/10">
                <form onSubmit={handleSubmit} className="relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={t('chatPanel.placeholder')}
                        disabled={isSendingMessage}
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-start/50 focus:border-primary-start transition-all"
                    />
                    <button 
                        type="submit" 
                        disabled={!input.trim() || isSendingMessage}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary-start hover:bg-primary-end text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary-start/20"
                    >
                        {isSendingMessage ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ChatPanel;