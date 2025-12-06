// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - JURISDICTION INTEGRATION (HOOK LAYER)
// 1. SCOPE: sendChatMessage now accepts and forwards 'jurisdiction'.
// 2. API: Passes the jurisdiction to the 'apiService' call.

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import { Jurisdiction } from '../components/ChatPanel'; // Import type from UI

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  // PHOENIX UPDATE: Added jurisdiction parameter
  sendChatMessage: (content: string, documentId?: string, jurisdiction?: Jurisdiction) => void;
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

                    if (payload.type === 'CHAT_MESSAGE' && payload.case_id === caseId) {
                         setMessages(prev => [...prev, {
                             sender: 'ai',
                             content: payload.content,
                             timestamp: new Date().toISOString()
                         }]);
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
  
  // PHOENIX UPDATE: Handle specialized chat with jurisdiction
  const sendChatMessage = useCallback(async (content: string, documentId?: string, jurisdiction?: Jurisdiction) => {
    if (!content.trim() || !caseId) return;
    
    setIsSendingMessage(true);
    // Optimistic UI update
    setMessages(prev => [...prev, { sender: 'user', content, timestamp: new Date().toISOString() }]);
    
    try {
        // Use the centralized API method with all parameters
        await apiService.sendChatMessage(caseId, content, documentId, jurisdiction);
    } catch (error) {
        console.error("Message send failed:", error);
        // Optionally add a failure message to the chat
        setMessages(prev => [...prev, { sender: 'ai', content: "Dështoi dërgimi i mesazhit.", timestamp: new Date().toISOString() }]);
    } finally {
        setIsSendingMessage(false);
    }
  }, [caseId]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};