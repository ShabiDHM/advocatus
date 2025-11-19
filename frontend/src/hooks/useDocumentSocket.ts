// FILE: src/hooks/useDocumentSocket.ts
import { useState, useEffect, useRef, useCallback } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService, API_BASE_URL } from '../services/api'; // Import shared base URL

interface SocketCallbacks {
  onConnectionStatusChange: (status: ConnectionStatus) => void;
  onChatMessage: (message: ChatMessage) => void;
  onDocumentUpdate: (document: Document) => void;
  onFindingsUpdate: () => void;
  onIsSendingChange: (isSending: boolean) => void;
}

interface UseDocumentSocketReturn {
  reconnect: () => void;
  sendChatMessage: (content: string) => void;
  connectionStatus: ConnectionStatus;
}

export const useDocumentSocket = (
  caseId: string,
  isReady: boolean,
  callbacks: SocketCallbacks
): UseDocumentSocketReturn => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [reconnectCounter, setReconnectCounter] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    callbacks.onConnectionStatusChange(connectionStatus);
  }, [connectionStatus]); 

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
    if (!isReady || !caseId) {
      if (connectionStatus !== 'DISCONNECTED') setConnectionStatus('DISCONNECTED');
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

        // Ensure HTTPS is used for socket too
        const socketBase = API_BASE_URL.startsWith('http:') && window.location.protocol === 'https:' 
            ? API_BASE_URL.replace('http:', 'https:') 
            : API_BASE_URL;
            
        const sseUrl = `${socketBase}/api/v1/stream/updates?token=${token}`;
        
        const es = new EventSource(sseUrl);
        eventSourceRef.current = es;

        es.onopen = () => setConnectionStatus('CONNECTED');

        es.addEventListener('update', async (event: MessageEvent) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === 'DOCUMENT_STATUS') {
              try {
                const fullDoc = await apiService.getDocument(caseId, payload.document_id);
                callbacks.onDocumentUpdate(fullDoc);
                if (fullDoc.status === 'READY') callbacks.onFindingsUpdate();
              } catch (e) { console.error(e); }
            } else if (payload.type === 'CHAT_MESSAGE' && payload.case_id === caseId) {
              callbacks.onChatMessage({
                sender: 'ai', content: payload.content, text: payload.content, timestamp: new Date().toISOString(), isPartial: payload.is_partial 
              });
            } else if (payload.type === 'FINDINGS_UPDATE') {
                callbacks.onFindingsUpdate();
            }
          } catch (e) { console.error(e); }
        });

        es.onerror = () => {
          if (es.readyState === EventSource.CLOSED) setConnectionStatus('DISCONNECTED');
          else setConnectionStatus('CONNECTING');
        };
      } catch { setConnectionStatus('DISCONNECTED'); }
    };

    connectSSE();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, isReady, reconnectCounter]);

  const reconnect = useCallback(() => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    setReconnectCounter(prev => prev + 1); 
  }, []);

  const sendChatMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    callbacks.onIsSendingChange(true);
    callbacks.onChatMessage({ sender: 'user', content, text: content, timestamp: new Date().toISOString() });
    try {
      await apiService.post(`/chat/case/${caseId}`, { message: content });
    } catch (error) { console.error(error); } 
    finally { callbacks.onIsSendingChange(false); }
  }, [caseId, callbacks]);

  return { reconnect, sendChatMessage, connectionStatus };
};