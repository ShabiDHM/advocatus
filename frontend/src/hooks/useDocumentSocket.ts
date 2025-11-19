// FILE: src/hooks/useDocumentSocket.ts
import { useState, useEffect, useRef, useCallback } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService } from '../services/api';

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

  // Sync internal status with callback
  useEffect(() => {
    callbacks.onConnectionStatusChange(connectionStatus);
  }, [connectionStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        console.log('[Socket] Cleaning up connection');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
        setConnectionStatus('DISCONNECTED');
      }
    };
  }, [caseId]);

  useEffect(() => {
    if (!isReady || !caseId) {
      if (connectionStatus !== 'DISCONNECTED') {
        setConnectionStatus('DISCONNECTED');
      }
      return;
    }

    const connectSSE = async () => {
      console.log(`[Socket] Connecting to case ${caseId}...`);
      setConnectionStatus('CONNECTING');
      
      try {
        const token = apiService.getToken();
        if (!token) {
          console.error('[Socket] No auth token available');
          setConnectionStatus('DISCONNECTED');
          return;
        }

        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const sseUrl = `${baseUrl}/api/v1/stream/updates?token=${token}`;
        
        const es = new EventSource(sseUrl);
        eventSourceRef.current = es;

        es.onopen = () => {
          console.log('[Socket] Connected');
          setConnectionStatus('CONNECTED');
        };

        es.addEventListener('update', async (event: MessageEvent) => {
          try {
            const payload = JSON.parse(event.data);
            
            if (payload.type === 'DOCUMENT_STATUS') {
              // Fetch the full document to ensure we have complete data for the UI
              try {
                const fullDoc = await apiService.getDocument(caseId, payload.document_id);
                callbacks.onDocumentUpdate(fullDoc);
                
                // If the document is ready, findings might be ready too
                if (fullDoc.status === 'READY') {
                    callbacks.onFindingsUpdate();
                }
              } catch (fetchErr) {
                console.error('[Socket] Failed to fetch updated document details', fetchErr);
              }
            } else if (payload.type === 'CHAT_MESSAGE' && payload.case_id === caseId) {
              const chatMsg: ChatMessage = {
                sender: 'ai', // Standardize on lowercase 'ai' for internal logic, though UI might handle both
                content: payload.content,
                text: payload.content, // Support legacy field
                timestamp: new Date().toISOString(),
                isPartial: payload.is_partial // Pass through partial flag if backend sends it
              };
              callbacks.onChatMessage(chatMsg);
            } else if (payload.type === 'FINDINGS_UPDATE') {
                callbacks.onFindingsUpdate();
            }
          } catch (e) {
            console.error("[Socket] Error processing message", e);
          }
        });

        es.onerror = (err) => {
          console.error('[Socket] Connection error', err);
          if (es.readyState === EventSource.CLOSED) {
            setConnectionStatus('DISCONNECTED');
          } else {
            setConnectionStatus('CONNECTING');
          }
        };

      } catch (error) {
        console.error('[Socket] Setup error', error);
        setConnectionStatus('DISCONNECTED');
      }
    };

    connectSSE();
    
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, isReady, reconnectCounter]);

  const reconnect = useCallback(() => {
    console.log('[Socket] Manually reconnecting...');
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setReconnectCounter(prev => prev + 1);
  }, []);

  const sendChatMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    
    callbacks.onIsSendingChange(true);
    
    // Optimistic update
    const userMsg: ChatMessage = {
      sender: 'user',
      content: content,
      text: content,
      timestamp: new Date().toISOString()
    };
    callbacks.onChatMessage(userMsg);

    try {
      await apiService.post(`/chat/case/${caseId}`, { message: content });
    } catch (error) {
      console.error("[Socket] Failed to send message", error);
      // Optional: Add error handling/toast here
    } finally {
      callbacks.onIsSendingChange(false);
    }
  }, [caseId, callbacks]);

  return { reconnect, sendChatMessage, connectionStatus };
};