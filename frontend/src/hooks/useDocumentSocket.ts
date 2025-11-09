// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL MODIFICATION 26.0 (RACE CONDITION FIX):
// 1. ROOT CAUSE FIX: The hook now accepts a new boolean parameter, 'isReady'.
// 2. DELAYED CONNECTION: The useEffect hook will now wait until both 'caseId' is present
//    and 'isReady' is true before attempting to establish a WebSocket connection.
// 3. This definitively resolves the race condition where the hook would try to connect with a
//    stale token before the main application had finished its authentication refresh cycle.
//    This cures the handshake failure.

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

  useEffect(() => {
    // --- RACE CONDITION FIX: Do not connect until the app is ready ---
    if (!caseId || !isReady) {
        setConnectionStatus('DISCONNECTED');
        return;
    }

    setConnectionStatus('CONNECTING');
    const url = apiService.getWebSocketUrl(caseId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => { setConnectionStatus('CONNECTED'); };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);

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
                        newMessages.push({ sender: 'AI', text: message.text || "", timestamp: new Date().toISOString() });
                    }
                    return newMessages;
                });
                return;
            }

            if (message.type === 'document_update' && message.payload) {
                const incomingDocData = message.payload;
                if (!incomingDocData.id) return;

                const correctedDoc: Document = {
                    ...incomingDocData,
                    created_at: incomingDocData.uploadedAt || new Date().toISOString(),
                };
                
                setDocuments(prevDocs => {
                    if (correctedDoc.status?.toUpperCase() === 'DELETED') {
                        return prevDocs.filter(d => d.id !== correctedDoc.id);
                    }
                    const docExists = prevDocs.some(d => d.id === correctedDoc.id);
                    if (docExists) {
                        return prevDocs.map(doc =>
                            doc.id === correctedDoc.id
                                ? sanitizeDocument({ ...doc, ...correctedDoc })
                                : doc
                        ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                    } else {
                        return [sanitizeDocument(correctedDoc), ...prevDocs]
                            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                    }
                });
            }
        } catch (e) {
            console.error("Error processing WebSocket message:", e, event.data);
        }
    };

    ws.onclose = () => { setConnectionStatus('DISCONNECTED'); setIsSendingMessage(false); };
    ws.onerror = (error) => { console.error('WebSocket Error:', error); ws.close(); };
    
    return () => {
        ws.onclose = null;
        ws.close();
        wsRef.current = null;
    };
  }, [caseId, isReady, reconnectCounter]); // Add isReady to dependency array

  const reconnect = useCallback(() => { setReconnectCounter(prev => prev + 1); }, []);
  
  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      setIsSendingMessage(true);
      setMessages(prev => [...prev, { sender: 'user', text: text, timestamp: new Date().toISOString() }]);
      const messageToSend = JSON.stringify({ type: 'chat_message', payload: { text } });
      wsRef.current.send(messageToSend);
    } else {
      console.error("WebSocket not open or message is empty.");
    }
  }, []);

  return { documents, setDocuments, messages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};