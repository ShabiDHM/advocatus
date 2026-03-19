// FILE: src/pages/ChatPage.tsx
// PHOENIX PROTOCOL - CHAT PAGE V1.1 (FIXED UNUSED PARAMETER WARNING)
// 1. FIXED: Renamed 'mode' to '_mode' in handleSendMessage to indicate intentional non-use.
// 2. RETAINED: All functionality.

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

  // Load chat history from the case (optional – you can fetch from API)
  useEffect(() => {
    if (caseId) {
      // You might want to fetch existing chat history from the backend
      // For now, we'll start with an empty array or a welcome message
      setMessages([]);
    }
  }, [caseId]);

  const handleSendMessage = async (
    text: string,
    _mode: ChatMode,  // renamed to silence warning – not needed in logic
    reasoning: ReasoningMode,
    domain: LegalDomain,
    documentId?: string,
    jurisdiction?: Jurisdiction
  ) => {
    if (!caseId) return;

    // Add user message to UI
    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsSending(true);

    // Placeholder AI message for streaming
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
        documentId,
        jurisdiction,
        reasoning,
        domain
      );
      for await (const chunk of stream) {
        fullResponse += chunk;
        // Update the last AI message (streaming)
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
      // Append error message (will trigger retry button)
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
      } catch (error) {
        console.error('Failed to clear chat history:', error);
      }
    }
  };

  const reconnect = () => {
    // Optional: implement reconnection logic if WebSocket is used
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
      />
    </div>
  );
};

export default ChatPage;