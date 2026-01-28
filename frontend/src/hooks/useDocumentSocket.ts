// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - SOCKET HOOK V8.0 (HYDRA STREAMING INTEGRATION)
// 1. FIX: Implemented 'sendChatMessageStream' consumption to enable real-time token rendering.
// 2. FIX: Added placeholder state management for the incoming AI stream to prevent UI flickering.
// 3. STATUS: Document progress SSE and Chat Streaming now operate in parallel.

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
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
        setConnectionStatus('DISCONNECTED');
        return;
    }

    const connectSSE = async () => {
        setConnectionStatus('CONNECTING');

        try {
            const token = apiService.getToken();
            if (!token) {
                setConnectionStatus('DISCONNECTED');
                return;
            }

            // Using your specific route structure
            const sseUrl = `${API_V1_URL}/stream/updates?token=${token}`;
            const es = new EventSource(sseUrl);
            eventSourceRef.current = es;

            es.onopen = () => setConnectionStatus('CONNECTED');

            es.addEventListener('update', (event: MessageEvent) => {
                try {
                    const payload = JSON.parse(event.data);

                    if (payload.type === 'DOCUMENT_PROGRESS') {
                        setDocuments(prevDocs => prevDocs.map(doc => {
                            if (String(doc.id) === String(payload.document_id)) {
                                return { ...doc, progress_message: payload.message, progress_percent: payload.percent } as Document;
                            }
                            return doc;
                        }));
                    }

                    if (payload.type === 'DOCUMENT_STATUS') {
                        setDocuments(prevDocs => prevDocs.map(doc => {
                            if (String(doc.id) === String(payload.document_id)) {
                                const newStatus = payload.status.toUpperCase();
                                return {
                                    ...doc,
                                    status: (newStatus === 'READY' || newStatus === 'COMPLETED') ? 'COMPLETED' : 
                                            (newStatus === 'FAILED') ? 'FAILED' : doc.status,
                                    error_message: newStatus === 'FAILED' ? payload.error : doc.error_message,
                                    progress_percent: 100
                                } as Document;
                            }
                            return doc;
                        }));
                    }

                    // PHOENIX: Background history sync
                    // We only add if the message isn't currently being streamed or already exists
                    if (payload.type === 'CHAT_MESSAGE' && payload.case_id === caseId) {
                         setMessages(prev => {
                             const exists = prev.some(m => m.content === payload.content);
                             if (exists) return prev;
                             return [...prev, {
                                 role: 'ai',
                                 content: payload.content,
                                 timestamp: new Date().toISOString()
                             }];
                         });
                    }

                } catch (e) {
                    console.error("SSE Parse Error", e);
                }
            });

            es.onerror = () => {
                if (es.readyState === EventSource.CLOSED) setConnectionStatus('DISCONNECTED');
                else setConnectionStatus('CONNECTING');
            };

        } catch (error) {
            setConnectionStatus('DISCONNECTED');
        }
    };

    connectSSE();

  }, [caseId, reconnectCounter]);

  const reconnect = useCallback(() => { 
    if (eventSourceRef.current) eventSourceRef.current.close();
    setReconnectCounter(prev => prev + 1); 
  }, []);
  
  // PHOENIX: Refactored for real-time Token Streaming
  const sendChatMessage = useCallback(async (content: string, mode: ReasoningMode, documentId?: string, jurisdiction?: Jurisdiction) => {
    if (!content.trim() || !caseId) return;
    
    setIsSendingMessage(true);
    
    // 1. Add User Message
    const userMsg: ChatMessage = { role: 'user', content, timestamp: new Date().toISOString() };
    
    // 2. Add empty AI placeholder for the stream
    const aiPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    
    setMessages(prev => [...prev, userMsg, aiPlaceholder]);
    
    let streamContent = "";

    try {
        // 3. Consume the stream from the API
        const stream = apiService.sendChatMessageStream(caseId, content, documentId, jurisdiction, mode);
        
        for await (const chunk of stream) {
            streamContent += chunk;
            
            // 4. Update the placeholder message in real-time
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
        console.error("Hydra Stream failed:", error);
        setMessages(prev => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                updated[lastIdx].content = "Dështoi dërgimi i mesazhit. Ju lutem provoni përsëri.";
            }
            return updated;
        });
    } finally {
        setIsSendingMessage(false);
    }
  }, [caseId]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};