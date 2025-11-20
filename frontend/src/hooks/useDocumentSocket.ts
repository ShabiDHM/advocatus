// FILE: frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - STATE EXPOSURE FIX
// 1. Exposed 'setMessages' to allow hydration of chat history from DB.

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService } from '../services/api';

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>; // <--- EXPOSED
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

            const baseUrl = import.meta.env.VITE_API_URL || 'https://advocatus-prod-api.duckdns.org';
            const sseUrl = `${baseUrl}/api/v1/stream/updates?token=${token}`;
            
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

                    // --- SCENARIO A: Document Status Update ---
                    if (payload.type === 'DOCUMENT_STATUS') {
                        setDocuments(prevDocs => {
                            const targetId = String(payload.document_id);
                            const index = prevDocs.findIndex(d => String(d.id) === targetId);
                            
                            if (index === -1) return prevDocs; 

                            const newDocs = [...prevDocs];
                            const doc = newDocs[index];
                            const newStatus = payload.status.toUpperCase();

                            if (newStatus === 'READY' || newStatus === 'COMPLETED') {
                                doc.status = 'COMPLETED';
                            } else if (newStatus === 'FAILED') {
                                doc.status = 'FAILED';
                                doc.error_message = payload.error;
                            }
                            
                            return newDocs;
                        });
                    }

                    // --- SCENARIO B: Chat Message ---
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