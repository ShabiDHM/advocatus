// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - RESILIENT VERSION 33.1 (TYPE INTEGRITY CURE)
// 1. TYPE INTEGRITY CURE: Removed the local ConnectionStatus type definition.
// 2. GLOBAL TYPE ADOPTION: Now imports the authoritative 'ConnectionStatus' type
//    from the global types.ts file, ensuring consistency across the application.

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types'; // CURE: Import global type
import { apiService } from '../services/api';
import { sanitizeDocument } from '../utils/documentUtils';

// CURE: Local type definition removed. The hook now uses the global type.

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  sendChatMessage: (text: string) => void;
  isSendingMessage: boolean;
  connectionError: string | null;
}

export const useDocumentSocket = (caseId: string, isReady: boolean): UseDocumentSocketReturn => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [reconnectCounter, setReconnectCounter] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const connectionAttemptsRef = useRef(0);
  const maxConnectionAttempts = 5;

  useEffect(() => {
    if (!caseId || !isReady) {
      console.log('[WebSocket Hook] Connection skipped - missing caseId or not ready');
      setConnectionStatus('DISCONNECTED');
      setConnectionError(null);
      return;
    }

    const connectWebSocket = async () => {
      if (connectionAttemptsRef.current >= maxConnectionAttempts) {
        console.error('[WebSocket Hook] Max connection attempts reached, giving up');
        setConnectionStatus('ERROR');
        setConnectionError('Failed to connect after multiple attempts. Please refresh the page.');
        return;
      }

      connectionAttemptsRef.current++;
      console.log(`[WebSocket Hook] Connection attempt ${connectionAttemptsRef.current}/${maxConnectionAttempts} for case:`, caseId);
      
      setConnectionStatus('CONNECTING');
      setConnectionError(null);
      
      try {
        const url = await apiService.getWebSocketUrl(caseId);
        
        console.log('[WebSocket Hook] WebSocket URL constructed (token redacted):', 
          url.replace(/(token=)[^&]+/, '$1REDACTED')
        );
        
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => { 
          console.log('[WebSocket Hook] ✅ WebSocket connection established successfully');
          setConnectionStatus('CONNECTED');
          setConnectionError(null);
          connectionAttemptsRef.current = 0;
          clearTimeout(reconnectTimeoutRef.current);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('[WebSocket Hook] Received message type:', message.type);

            if (message.type === 'chat_response_chunk' || message.type === 'chat_message_out') {
              setIsSendingMessage(false);
              setMessages(prevMessages => {
                const newMessages = [...prevMessages];
                const lastMessage = newMessages[newMessages.length - 1];
                
                if (lastMessage && lastMessage.sender === 'AI') {
                  if (message.type === 'chat_response_chunk') {
                    lastMessage.text += message.text || "";
                  } else {
                    lastMessage.text = message.text || "No AI response text received.";
                    lastMessage.timestamp = new Date().toISOString();
                  }
                } else {
                  newMessages.push({ 
                    sender: 'AI', 
                    text: message.text || "", 
                    timestamp: new Date().toISOString() 
                  });
                }
                return newMessages;
              });
              return;
            }

            if (message.type === 'document_update' && message.payload) {
              const incomingDocData = message.payload;
              if (!incomingDocData.id) {
                console.warn('[WebSocket Hook] Received document update without ID');
                return;
              }

              const correctedDoc: Document = { 
                ...incomingDocData, 
                created_at: incomingDocData.uploadedAt || new Date().toISOString(),
              };
              
              setDocuments(prevDocs => {
                if (correctedDoc.status?.toUpperCase() === 'DELETED') {
                  console.log('[WebSocket Hook] Document deleted:', correctedDoc.id);
                  return prevDocs.filter(d => d.id !== correctedDoc.id);
                }

                const docExists = prevDocs.some(d => d.id === correctedDoc.id);
                
                if (docExists) {
                  console.log('[WebSocket Hook] Document updated:', correctedDoc.id);
                  return prevDocs.map(doc =>
                    doc.id === correctedDoc.id
                      ? sanitizeDocument({ ...doc, ...correctedDoc })
                      : doc
                  ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                } else {
                  console.log('[WebSocket Hook] New document added:', correctedDoc.id);
                  return [sanitizeDocument(correctedDoc), ...prevDocs]
                    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                }
              });
            }
          } catch (e) {
            console.error('[WebSocket Hook] Error processing WebSocket message:', e, event.data);
          }
        };

        ws.onclose = (event) => { 
          console.log('[WebSocket Hook] WebSocket connection closed:', event.code, event.reason);
          setConnectionStatus('DISCONNECTED');
          setIsSendingMessage(false);
          
          let errorMessage = 'Connection closed';
          if (event.code === 1006) {
            errorMessage = 'Unable to connect to server. Please check your internet connection or try again later.';
          }
          setConnectionError(errorMessage);

          if (connectionAttemptsRef.current < maxConnectionAttempts) {
            const backoffTime = Math.min(3000 * Math.pow(2, connectionAttemptsRef.current - 1), 30000);
            console.log(`[WebSocket Hook] Scheduling auto-reconnect in ${backoffTime}ms`);
            reconnectTimeoutRef.current = setTimeout(() => {
              setReconnectCounter(prev => prev + 1);
            }, backoffTime);
          } else {
            setConnectionStatus('ERROR');
            setConnectionError('Failed to establish connection after multiple attempts. Please refresh the page.');
          }
        };

        ws.onerror = (error) => { 
          console.error('[WebSocket Hook] WebSocket connection error:', error);
          setConnectionStatus('ERROR');
          setConnectionError('Connection error occurred. Please try again.');
        };
      
      } catch (error) {
        console.error('[WebSocket Hook] Failed to establish WebSocket connection:', error);
        setConnectionStatus('ERROR');
        setConnectionError('Failed to establish connection. Please check your network and try again.');
        
        if (connectionAttemptsRef.current < maxConnectionAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectCounter(prev => prev + 1);
          }, 3000);
        }
      }
    };

    connectWebSocket();
    
    return () => {
      console.log('[WebSocket Hook] Cleaning up WebSocket connection');
      connectionAttemptsRef.current = 0;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [caseId, isReady, reconnectCounter]);

  const reconnect = useCallback(() => { 
    console.log('[WebSocket Hook] 🔄 Manual reconnect triggered');
    connectionAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    setConnectionError(null);
    setReconnectCounter(prev => prev + 1); 
  }, []);
  
  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      setIsSendingMessage(true);
      setMessages(prev => [...prev, { 
        sender: 'user', 
        text: text, 
        timestamp: new Date().toISOString() 
      }]);
      
      const messageToSend = JSON.stringify({ 
        type: 'chat_message', 
        payload: { text } 
      });
      
      console.log('[WebSocket Hook] Sending chat message:', text.substring(0, 50) + '...');
      wsRef.current.send(messageToSend);
    } else {
      console.error('[WebSocket Hook] Cannot send message - WebSocket not ready or message empty. ReadyState:', wsRef.current?.readyState);
      setConnectionError('Cannot send message - connection not available');
    }
  }, []);

  return { 
    documents, 
    setDocuments, 
    messages, 
    connectionStatus, 
    reconnect, 
    sendChatMessage, 
    isSendingMessage,
    connectionError
  };
};