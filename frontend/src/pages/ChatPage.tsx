// FILE: src/pages/ChatPage.tsx
// PHOENIX PROTOCOL - CHAT PAGE V1.5
// V1.5: PERFORMANCE & SAFETY —
//       - localStorage debounced (300ms) — parandalon 100+ write gjatë streaming.
//       - AbortController — anulohet stream-i kur user largohet nga komponenti.
//       - useRef për isSending — eliminon recreation të handleSendMessage.
//       - Reset messages kur ndryshon caseId (shmang "hallucination" mes lëndëve).
// V1.4: FIXES —
//       - localStorage key unifikuar: `chat_${caseId}` (konsistencë me CaseViewPage V110.8).
//       - Error handling: placeholder-i AI ZËVENDËSOHET me mesazh error (jo append).
//       - Guard `isSending` — parandalon dërgimin e dy mesazheve njëkohësisht.
//       - Migrim i dhënave nga key i vjetër → i re (backward compat).

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { apiService } from '../services/api';
import ChatPanel, { ChatMode, ReasoningMode, Jurisdiction } from '../components/ChatPanel';
import { ChatMessage } from '../data/types';
import { useAuth } from '../context/AuthContext';

const _chatHistoryKey = (caseId: string): string => `chat_${caseId}`;
const _legacyChatHistoryKey = (caseId: string): string => `chat_history_${caseId}`;
const SAVE_DEBOUNCE_MS = 300;

const ChatPage: React.FC = () => {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);

  // V1.5: Ref për guard (pa recreim të useCallback)
  const isSendingRef = useRef(false);

  // V1.5: AbortController për cleanup
  const abortRef = useRef<AbortController | null>(null);

  // V1.5: Debounce timer për localStorage
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // V1.5: Reset messages kur ndryshon caseId
  useEffect(() => {
    setMessages([]);
    setIsSending(false);
    isSendingRef.current = false;
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, [caseId]);

  // V1.4/V1.5: Lexo historikun (me migrim nga key i vjetër)
  useEffect(() => {
    if (!caseId) return;

    const currentKey = _chatHistoryKey(caseId);
    const legacyKey = _legacyChatHistoryKey(caseId);

    let raw = localStorage.getItem(currentKey);
    if (!raw) {
      const legacy = localStorage.getItem(legacyKey);
      if (legacy) {
        localStorage.setItem(currentKey, legacy);
        localStorage.removeItem(legacyKey);
        raw = legacy;
      }
    }

    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      } catch {
        // historiku i korruptuar → fillojmë nga e para
      }
    }
  }, [caseId]);

  // V1.5: Ruaj historikun — DEBOUNCED (300ms) për të shmangur write gjatë streaming
  useEffect(() => {
    if (!caseId) return;
    if (messages.length === 0) return;

    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }

    saveTimerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(_chatHistoryKey(caseId), JSON.stringify(messages));
      } catch (e) {
        console.warn('Chat history save failed (quota?):', e);
      }
    }, SAVE_DEBOUNCE_MS);

    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, [messages, caseId]);

  // V1.5: Cleanup në unmount
  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  const handleSendMessage = useCallback(async (
    text: string,
    _mode: ChatMode,
    reasoning: ReasoningMode,
    domain: string,
    documentIds?: string[],
    jurisdiction?: Jurisdiction
  ) => {
    if (!caseId) return;
    if (isSendingRef.current) return;  // V1.5: ref guard (race-safe)

    isSendingRef.current = true;
    setIsSending(true);

    // V1.5: AbortController per këtë stream
    const controller = new AbortController();
    abortRef.current = controller;

    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    const aiMessage: ChatMessage = {
      role: 'ai',
      content: '',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage, aiMessage]);

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
        if (controller.signal.aborted) break;

        fullResponse += chunk;
        setMessages(prev => {
          const newMessages = [...prev];
          const last = newMessages.length - 1;
          if (last >= 0) {
            newMessages[last] = { ...newMessages[last], content: fullResponse };
          }
          return newMessages;
        });
      }
    } catch (error) {
      // V1.5: Nëse ishte abort (user largim), mos shfaq error
      if (controller.signal.aborted) return;

      console.error('Chat stream error:', error);
      setMessages(prev => {
        const updated = [...prev];
        const last = updated.length - 1;
        if (last >= 0) {
          updated[last] = {
            ...updated[last],
            content: '[Gabim Teknik: Lidhja me shërbimin dështoi.]',
          };
        }
        return updated;
      });
    } finally {
      isSendingRef.current = false;
      setIsSending(false);
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
    }
  }, [caseId]);

  const clearChat = useCallback(async () => {
    setMessages([]);
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
    } catch (error) {
      console.error('Failed to clear chat history:', error);
    }
    localStorage.removeItem(_chatHistoryKey(caseId));
    localStorage.removeItem(_legacyChatHistoryKey(caseId));
  }, [caseId]);

  return (
    <div className="h-full w-full">
      <ChatPanel
        messages={messages}
        connectionStatus="CONNECTED"
        reconnect={() => {}}
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