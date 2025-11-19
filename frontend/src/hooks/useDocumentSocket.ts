// FILE: frontend/src/hooks/useDocumentSocket.ts
import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService } from '../services/api';

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
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
        eventSourceRef.current.close();
        eventSourceRef.current = null;
        setConnectionStatus('DISCONNECTED');
      }
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) { setConnectionStatus('DISCONNECTED'); return; }

    const connectSSE = async () => {
        setConnectionStatus('CONNECTING');
        try {
            const token = apiService.getToken();
            if (!token) { setConnectionStatus('DISCONNECTED'); return; }
            const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const sseUrl = `${baseUrl}/api/v1/stream/updates?token=${token}`;

            const es = new EventSource(sseUrl);
            eventSourceRef.current = es;

            es.onopen = () => setConnectionStatus('CONNECTED');

            es.addEventListener('update', (event: MessageEvent) => {
                try {
                    const payload = JSON.parse(event.data);
                    
                    if (payload.type === 'DOCUMENT_STATUS') {
                        setDocuments(prevDocs => {
                            const index = prevDocs.findIndex(d => d.id === payload.document_id);
                            if (index === -1) return prevDocs;
                            const newDocs = [...prevDocs];
                            const doc = newDocs[index];
                            if (payload.status === 'READY' || payload.status === 'COMPLETED') doc.status = 'COMPLETED';
                            else if (payload.status === 'FAILED') { doc.status = 'FAILED'; doc.error_message = payload.error; }
                            return newDocs;
                        });
                    }

                    if (payload.type === 'CHAT_MESSAGE' && payload.case_id === caseId) {
                         setMessages(prev => [...prev, { sender: 'ai', content: payload.content, timestamp: new Date().toISOString() }]);
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
  
  const sendChatMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    setIsSendingMessage(true);
    setMessages(prev => [...prev, { sender: 'user', content, timestamp: new Date().toISOString() }]);
    try {
        await apiService.post(`/chat/case/${caseId}`, { message: content });
    } catch (error) { console.error("Chat Error", error); } 
    finally { setIsSendingMessage(false); }
  }, [caseId]);

  return { documents, setDocuments, messages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};