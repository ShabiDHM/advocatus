// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - SOCKET HOOK V8.2 (UI TRANSITION FIX)
// 1. FIX: Disables 'isSendingMessage' (spinner) as soon as the first token arrives.
// 2. STATUS: Resolves the "double indicator" bug where thinking shows during typing.

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
    if (!content.trim() || !caseId) return;
    
    setIsSendingMessage(true);
    
    const userMsg: ChatMessage = { role: 'user', content, timestamp: new Date().toISOString() };
    const aiPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    
    setMessages(prev => [...prev, userMsg, aiPlaceholder]);
    
    let streamContent = "";
    let hasStartedTyping = false;

    try {
        const stream = apiService.sendChatMessageStream(caseId, content, documentId, jurisdiction, mode);
        
        for await (const chunk of stream) {
            streamContent += chunk;
            
            // PHOENIX FIX: Transition from "Thinking" to "Typing"
            // We turn off the loader as soon as the first non-empty chunk arrives
            if (!hasStartedTyping && streamContent.trim().length > 0) {
                hasStartedTyping = true;
                setIsSendingMessage(false);
            }

            setMessages(prev => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                    updated[lastIdx] = { ...updated[lastIdx], content: streamContent };
                }
                return updated;
            });
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
        // Absolute safety reset
        setIsSendingMessage(false);
    }
  }, [caseId]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};