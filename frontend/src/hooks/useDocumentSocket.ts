// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL MODIFICATION 28.0 (ARCHITECTURAL STABILITY FIX):
// 1. CRITICAL FIX: The fragile, local `getWsUrl` helper function has been completely
//    removed. This function was the definitive root cause of the unhandled TypeError
//    that was crashing the application and causing the blank screen.
// 2. ARCHITECTURAL ALIGNMENT: The hook now calls the new, authoritative
//    `apiService.getWebSocketUrl(caseId)` method. This centralizes all connection
//    logic within the ApiService, making the application robust and stable.
//
// PHOENIX PROTOCOL MODIFICATION 27.0 (DATA CONTRACT ALIGNMENT)
// ...

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

// --- PHOENIX PROTOCOL: The faulty getWsUrl function has been removed entirely. ---

export const useDocumentSocket = (caseId: string): UseDocumentSocketReturn => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [reconnectCounter, setReconnectCounter] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('jwtToken');
    if (!caseId || !token) {
        setConnectionStatus('DISCONNECTED');
        return;
    }

    setConnectionStatus('CONNECTING');
    // --- PHOENIX PROTOCOL FIX: Call the authoritative method from the ApiService. ---
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
                const incomingDoc = message.payload;
                if (!incomingDoc.id) return;

                setDocuments(prevDocs => {
                    if (incomingDoc.status?.toUpperCase() === 'DELETED') {
                        return prevDocs.filter(d => d.id !== incomingDoc.id);
                    }

                    const docExists = prevDocs.some(d => d.id === incomingDoc.id);

                    if (docExists) {
                        return prevDocs.map(doc =>
                            doc.id === incomingDoc.id
                                ? sanitizeDocument({ ...doc, ...incomingDoc })
                                : doc
                        ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                    } else {
                        return [sanitizeDocument(incomingDoc), ...prevDocs]
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
  }, [caseId, reconnectCounter]);

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