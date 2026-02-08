// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - SOCKET HOOK V8.4 (UNIFIED LOGIC INTEGRITY)
// 1. RESTORED: Full SSE (EventSource) logic for real-time document status and progress tracking.
// 2. RESTORED: Reconnection counter and manual 'reconnect' function.
// 3. INTEGRATED: True HTTP Streaming consumer (for await) for high-IQ legal chat.
// 4. FIX: Synchronized 'isSendingMessage' to prevent state race conditions during streaming.
// 5. STATUS: 100% Logic Preserved. Zero Degradation.

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

  // Cleanup on unmount
  useEffect(() => {
    return () => { if (eventSourceRef.current) { eventSourceRef.current.close(); eventSourceRef.current = null; } };
  }, [caseId]);

  // SSE: Document Status & Progress Listener (Legacy Logic)
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
                    // Legacy Progress Tracking
                    if (payload.type === 'DOCUMENT_PROGRESS' || payload.type === 'DOCUMENT_STATUS') {
                        setDocuments(prevDocs => prevDocs.map(doc => {
                            if (String(doc.id) === String(payload.document_id)) {
                                if (payload.type === 'DOCUMENT_PROGRESS') {
                                    return { ...doc, progress_message: payload.message, progress_percent: payload.percent } as Document;
                                }
                                const newStatus = payload.status.toUpperCase();
                                return { 
                                    ...doc, 
                                    status: (newStatus === 'READY' || newStatus === 'COMPLETED') ? 'COMPLETED' : (newStatus === 'FAILED' ? 'FAILED' : doc.status), 
                                    error_message: newStatus === 'FAILED' ? payload.error : doc.error_message, 
                                    progress_percent: 100 
                                } as Document;
                            }
                            return doc;
                        }));
                    }
                } catch (e) { console.error("SSE Parse Error", e); }
            });
            
            es.onerror = () => { 
                if (es.readyState === EventSource.CLOSED) setConnectionStatus('DISCONNECTED'); 
                else setConnectionStatus('CONNECTING'); 
            };
        } catch (error) { setConnectionStatus('DISCONNECTED'); }
    };
    connectSSE();
  }, [caseId, reconnectCounter]);

  const reconnect = useCallback(() => { 
    if (eventSourceRef.current) eventSourceRef.current.close(); 
    setReconnectCounter(prev => prev + 1); 
  }, []);
  
  // CHAT: High-IQ HTTP Streaming Implementation
  const sendChatMessage = useCallback(async (content: string, mode: ReasoningMode, documentId?: string, jurisdiction?: Jurisdiction) => {
    if (!content.trim() || !caseId) return;
    
    setIsSendingMessage(true);
    
    // Optimistic UI Update
    const userMsg: ChatMessage = { role: 'user', content, timestamp: new Date().toISOString() };
    const aiPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg, aiPlaceholder]);
    
    let streamContent = "";

    try {
        const stream = apiService.sendChatMessageStream(caseId, content, documentId, jurisdiction, mode);
        
        for await (const chunk of stream) {
            streamContent += chunk;
            
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
        console.error("Legal Chat Stream failed:", error);
        setMessages(prev => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                updated[lastIdx].content = "Ndodhi një gabim teknik. Shërbimi i bisedës dështoi.";
            }
            return updated;
        });
    } finally {
        setIsSendingMessage(false);
    }
  }, [caseId]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};