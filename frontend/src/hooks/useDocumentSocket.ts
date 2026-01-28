// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - SOCKET HOOK V8.1 (STREAM RESILIENCE)
// 1. FIX: Added check to prevent 'empty message' bug that keeps spinner active.
// 2. FIX: Improved placeholder logic to ensure text appears as soon as the first byte arrives.

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import { Jurisdiction, ReasoningMode } from '../components/ChatPanel';

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  sendChatMessage: (content: string, mode: ReasoningMode, documentId?: string, jurisdiction?: Jurisdiction) => void;
  isSendingMessage: boolean;
}

export const useDocumentSocket = (caseId: string | undefined): UseDocumentSocketReturn => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [reconnectCounter, setReconnectCounter] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => { if (eventSourceRef.current) { eventSourceRef.current.close(); eventSourceRef.current = null; } };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) { setConnectionStatus('DISCONNECTED'); return; }
    const connectSSE = async () => {
        if (eventSourceRef.current?.readyState === EventSource.OPEN) return;
        setConnectionStatus('CONNECTING');
        try {
            const token = apiService.getToken() || await (async () => { await apiService.refreshToken(); return apiService.getToken(); })();
            if (!token) { setConnectionStatus('DISCONNECTED'); return; }
            const sseUrl = `${API_V1_URL}/stream/updates?token=${token}`;
            const es = new EventSource(sseUrl);
            eventSourceRef.current = es;
            es.onopen = () => setConnectionStatus('CONNECTED');
            es.addEventListener('update', (event: MessageEvent) => {
                try {
                    const payload = JSON.parse(event.data);
                    if (payload.type === 'DOCUMENT_PROGRESS' || payload.type === 'DOCUMENT_STATUS') {
                        setDocuments(prevDocs => prevDocs.map(doc => {
                            if (String(doc.id) === String(payload.document_id)) {
                                if (payload.type === 'DOCUMENT_PROGRESS') return { ...doc, progress_message: payload.message, progress_percent: payload.percent } as Document;
                                const newStatus = payload.status.toUpperCase();
                                return { ...doc, status: (newStatus === 'READY' || newStatus === 'COMPLETED') ? 'COMPLETED' : (newStatus === 'FAILED' ? 'FAILED' : doc.status), error_message: newStatus === 'FAILED' ? payload.error : doc.error_message, progress_percent: 100 } as Document;
                            }
                            return doc;
                        }));
                    }
                } catch (e) { console.error("SSE Parse Error", e); }
            });
            es.onerror = () => { if (es.readyState === EventSource.CLOSED) setConnectionStatus('DISCONNECTED'); else setConnectionStatus('CONNECTING'); };
        } catch (error) { setConnectionStatus('DISCONNECTED'); }
    };
    connectSSE();
  }, [caseId, reconnectCounter]);

  const reconnect = useCallback(() => { if (eventSourceRef.current) eventSourceRef.current.close(); setReconnectCounter(prev => prev + 1); }, []);
  
  const sendChatMessage = useCallback(async (content: string, mode: ReasoningMode, documentId?: string, jurisdiction?: Jurisdiction) => {
    if (!content.trim() || !caseId || isSendingMessage) return;
    
    setIsSendingMessage(true);
    
    // 1. Add User Message
    const userMsg: ChatMessage = { role: 'user', content, timestamp: new Date().toISOString() };
    // 2. Add empty AI placeholder
    const aiPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    
    setMessages(prev => [...prev, userMsg, aiPlaceholder]);
    
    let streamContent = "";

    try {
        const stream = apiService.sendChatMessageStream(caseId, content, documentId, jurisdiction, mode);
        
        for await (const chunk of stream) {
            streamContent += chunk;
            
            // 3. Update AI message in real-time
            setMessages(prev => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                // Only update if the last message is the AI placeholder
                if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                    updated[lastIdx] = { ...updated[lastIdx], content: streamContent };
                }
                return updated;
            });
            
            // PHOENIX FIX: As soon as we get the first real text, remove the "Thinking" state
            if (streamContent.trim().length > 0 && isSendingMessage) {
                setIsSendingMessage(false);
            }
        }
    } catch (error) {
        console.error("Stream failed:", error);
        setMessages(prev => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                updated[lastIdx].content = "Dështoi dërgimi i mesazhit. Ju lutem provoni përsëri.";
            }
            return updated;
        });
    } finally {
        // PHOENIX FIX: Always ensure the global loader is off once stream loop finishes
        setIsSendingMessage(false);
    }
  }, [caseId, isSendingMessage]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};