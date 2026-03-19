// FILE: src/pages/ChatPage.tsx
// PHOENIX PROTOCOL - CHAT PAGE V1.2 (HTTP STREAMING, MULTI‑DOCUMENT SUPPORT)
// 1. UPDATED: Now uses apiService.sendChatMessageStream instead of WebSocket for chat.
// 2. FIXED: Signature matches ChatPanelProps (documentIds array).
// 3. RETAINED: All other functionality.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { apiService } from '../services/api';
import ChatPanel, { ChatMode, ReasoningMode, LegalDomain, Jurisdiction } from '../components/ChatPanel';
import { ChatMessage } from '../data/types';
import { useAuth } from '../context/AuthContext';

const ChatPage: React.FC = () => {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('CONNECTED');

  // Load chat history from localStorage if available
  useEffect(() => {
    if (!caseId) return;
    const cached = localStorage.getItem(`chat_history_${caseId}`);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      } catch (e) {}
    }
  }, [caseId]);

  // Save chat history to localStorage
  useEffect(() => {
    if (!caseId) return;
    if (messages.length > 0) {
      localStorage.setItem(`chat_history_${caseId}`, JSON.stringify(messages));
    }
  }, [messages, caseId]);

  const handleSendMessage = async (
    text: string,
    _mode: ChatMode,
    reasoning: ReasoningMode,
    domain: LegalDomain,
    documentIds?: string[],
    jurisdiction?: Jurisdiction
  ) => {
    if (!caseId) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsSending(true);

    const aiMessage: ChatMessage = {
      role: 'ai',
      content: '',
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, aiMessage]);

    try {
      let fullResponse = '';
      const stream = apiService.sendChatMessageStream(
        caseId,
        text,
        documentIds,
        jurisdiction,
        reasoning,
        domain
      );
      for await (const chunk of stream) {
        fullResponse += chunk;
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            content: fullResponse,
          };
          return newMessages;
        });
      }
    } catch (error) {
      console.error('Chat stream error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'ai',
          content: '[Gabim Teknik: Lidhja me shërbimin dështoi.]',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const clearChat = async () => {
    setMessages([]);
    if (caseId) {
      try {
        await apiService.clearChatHistory(caseId);
        localStorage.removeItem(`chat_history_${caseId}`);
      } catch (error) {
        console.error('Failed to clear chat history:', error);
      }
    }
  };

  const reconnect = () => {
    setConnectionStatus('CONNECTED');
  };

  return (
    <div className="h-full w-full">
      <ChatPanel
        messages={messages}
        connectionStatus={connectionStatus}
        reconnect={reconnect}
        onSendMessage={handleSendMessage}
        isSendingMessage={isSending}
        onClearChat={clearChat}
        t={t}
        activeContextId={caseId || 'general'}
        isPro={user?.subscription_tier === 'PRO' || user?.role === 'ADMIN'}
        // documents not needed for general chat, but could be added later
      />
    </div>
  );
};

export default ChatPage;