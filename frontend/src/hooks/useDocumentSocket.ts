// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - CRITICAL FIX VERSION 32.0
// CRITICAL DISCOVERY: getWebSocketUrl() returns Promise<string> (async), not string!
// FIXES APPLIED:
// 1. ✅ Added await for getWebSocketUrl() - it's async and returns Promise<string>
// 2. ✅ Fixed URL string operations that were failing on Promise
// 3. ✅ Restored async/await pattern for the connection function

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage } from '../data/types';
import { apiService } from '../services/api';
import { sanitizeDocument } from '../utils/documentUtils';

type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED';

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  sendChatMessage: (text: string) => void;
  isSendingMessage: boolean;
}

export const useDocumentSocket = (caseId: string, isReady: boolean): UseDocumentSocketReturn => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [reconnectCounter, setReconnectCounter] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!caseId || !isReady) {
      console.log('[WebSocket Hook] Connection skipped - missing caseId or not ready');
      setConnectionStatus('DISCONNECTED');
      return;
    }

    const connectWebSocket = async () => { // ✅ FIX: Made this async
      console.log('[WebSocket Hook] Starting WebSocket connection for case:', caseId);
      setConnectionStatus('CONNECTING');
      
      try {
        // ✅ CRITICAL FIX: getWebSocketUrl returns Promise<string> - MUST AWAIT
        const url = await apiService.getWebSocketUrl(caseId);
        
        console.log('[WebSocket Hook] WebSocket URL constructed:', 
          url.replace(/(token=)[^&]+/, '$1REDACTED') // ✅ FIX: Now url is string, not Promise
        );
        
        const ws = new WebSocket(url); // ✅ FIX: Now url is string, not Promise
        wsRef.current = ws;

        ws.onopen = () => { 
          console.log('[WebSocket Hook] ✅ WebSocket connection established successfully');
          setConnectionStatus('CONNECTED');
          clearTimeout(reconnectTimeoutRef.current);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('[WebSocket Hook] Received message type:', message.type);

            // Handle chat responses
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

            // Handle document updates
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
                // Handle document deletion
                if (correctedDoc.status?.toUpperCase() === 'DELETED') {
                  console.log('[WebSocket Hook] Document deleted:', correctedDoc.id);
                  return prevDocs.filter(d => d.id !== correctedDoc.id);
                }

                const docExists = prevDocs.some(d => d.id === correctedDoc.id);
                
                if (docExists) {
                  // Update existing document
                  console.log('[WebSocket Hook] Document updated:', correctedDoc.id);
                  return prevDocs.map(doc =>
                    doc.id === correctedDoc.id
                      ? sanitizeDocument({ ...doc, ...correctedDoc })
                      : doc
                  ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                } else {
                  // Add new document
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
          
          // Auto-reconnect after 3 seconds if not a normal closure
          if (event.code !== 1000) {
            console.log('[WebSocket Hook] Scheduling auto-reconnect in 3000ms');
            reconnectTimeoutRef.current = setTimeout(() => {
              setReconnectCounter(prev => prev + 1);
            }, 3000);
          }
        };

        ws.onerror = (error) => { 
          console.error('[WebSocket Hook] WebSocket connection error:', error);
          setConnectionStatus('DISCONNECTED');
        };
      
      } catch (error) {
        console.error('[WebSocket Hook] Failed to establish WebSocket connection:', error);
        setConnectionStatus('DISCONNECTED');
      }
    };

    connectWebSocket();
    
    // Cleanup function
    return () => {
      console.log('[WebSocket Hook] Cleaning up WebSocket connection');
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
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
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
    }
  }, []);

  return { 
    documents, 
    setDocuments, 
    messages, 
    connectionStatus, 
    reconnect, 
    sendChatMessage, 
    isSendingMessage 
  };
};