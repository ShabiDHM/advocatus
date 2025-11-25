// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - PROGRESS TRACKING SUPPORT
// 1. HANDLER: Added listener for 'DOCUMENT_PROGRESS' events.
// 2. STATE: Updates document state with real-time progress percent/message.

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  sendChatMessage: (content: string) => void;
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
        console.log("SSE: Closing connection on unmount");
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
                console.error("SSE: No authentication token found.");
                setConnectionStatus('DISCONNECTED');
                return;
            }

            const sseUrl = `${API_V1_URL}/stream/updates?token=${token}`;
            console.log(`SSE: Connecting to ${sseUrl}`);

            const es = new EventSource(sseUrl);
            eventSourceRef.current = es;

            es.onopen = () => {
                console.log("%cSSE: Connected to Stream", "color: green; font-weight: bold;");
                setConnectionStatus('CONNECTED');
            };

            es.addEventListener('update', (event: MessageEvent) => {
                try {
                    const payload = JSON.parse(event.data);

                    // --- SCENARIO A: Document Progress Update (New) ---
                    if (payload.type === 'DOCUMENT_PROGRESS') {
                        setDocuments(prevDocs => {
                            const targetId = String(payload.document_id);
                            return prevDocs.map(doc => {
                                if (String(doc.id) === targetId) {
                                    // We inject dynamic properties for the UI
                                    return {
                                        ...doc,
                                        progress_message: payload.message,
                                        progress_percent: payload.percent
                                    } as Document;
                                }
                                return doc;
                            });
                        });
                    }

                    // --- SCENARIO B: Document Status Update ---
                    if (payload.type === 'DOCUMENT_STATUS') {
                        setDocuments(prevDocs => {
                            const targetId = String(payload.document_id);
                            return prevDocs.map(doc => {
                                if (String(doc.id) === targetId) {
                                    const newStatus = payload.status.toUpperCase();
                                    return {
                                        ...doc,
                                        status: (newStatus === 'READY' || newStatus === 'COMPLETED') ? 'COMPLETED' : 
                                                (newStatus === 'FAILED') ? 'FAILED' : doc.status,
                                        error_message: newStatus === 'FAILED' ? payload.error : doc.error_message,
                                        // Clear progress on completion
                                        progress_percent: newStatus === 'FAILED' ? 0 : 100
                                    } as Document;
                                }
                                return doc;
                            });
                        });
                    }

                    // --- SCENARIO C: Chat Message ---
                    if (payload.type === 'CHAT_MESSAGE' && payload.case_id === caseId) {
                         setMessages(prev => [...prev, {
                             sender: 'ai',
                             content: payload.content,
                             timestamp: new Date().toISOString()
                         }]);
                    }

                } catch (e) {
                    console.error("SSE: Failed to parse message", e);
                }
            });

            es.onerror = (err) => {
                console.error("SSE: Connection Error", err);
                if (es.readyState === EventSource.CLOSED) {
                    setConnectionStatus('DISCONNECTED');
                } else {
                    setConnectionStatus('CONNECTING');
                }
            };

        } catch (error) {
            console.error("SSE: Setup failed", error);
            setConnectionStatus('DISCONNECTED');
        }
    };

    connectSSE();

  }, [caseId, reconnectCounter]);

  const reconnect = useCallback(() => { 
    if (eventSourceRef.current) eventSourceRef.current.close();
    setReconnectCounter(prev => prev + 1); 
  }, []);
  
  const sendChatMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    setIsSendingMessage(true);
    setMessages(prev => [...prev, { sender: 'user', content, timestamp: new Date().toISOString() }]);
    try {
        await apiService.post(`/chat/case/${caseId}`, { message: content });
    } catch (error) {
        console.error("Failed to send message", error);
    } finally {
        setIsSendingMessage(false);
    }
  }, [caseId]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};