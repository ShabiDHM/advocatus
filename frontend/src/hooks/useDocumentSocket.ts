// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (CONNECTION TIMING FIX)
// CORRECTION: The primary useEffect hook now strictly respects the 'isReady' prop.
// The connectWebSocket function will not be called until the parent component
// has explicitly signaled that all prerequisites (like authentication) are complete.
// This is the definitive fix for the WebSocket connection race condition.

import { useEffect, useRef, useCallback } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';
import { apiService } from '../services/api';

interface SocketEventHandlers {
  onConnectionStatusChange: (status: ConnectionStatus, error: string | null) => void;
  onChatMessage: (message: ChatMessage) => void;
  onDocumentUpdate: (documentData: any) => void; 
  onFindingsUpdate: () => void;
  onIsSendingChange: (isSending: boolean) => void;
}

interface UseDocumentSocketReturn {
  reconnect: () => void;
  sendChatMessage: (text: string) => void;
}

export const useDocumentSocket = (
  caseId: string,
  isReady: boolean,
  handlers: SocketEventHandlers
): UseDocumentSocketReturn => {
  const { onConnectionStatusChange, onChatMessage, onDocumentUpdate, onFindingsUpdate, onIsSendingChange } = handlers;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const connectionAttemptsRef = useRef(0);
  const maxConnectionAttempts = 5;

  const connectWebSocket = useCallback(async () => {
    if (wsRef.current || connectionAttemptsRef.current >= maxConnectionAttempts) {
      if(connectionAttemptsRef.current >= maxConnectionAttempts){
        onConnectionStatusChange('ERROR', 'Failed to connect after multiple attempts.');
      }
      return;
    }

    connectionAttemptsRef.current++;
    onConnectionStatusChange('CONNECTING', null);

    try {
      await apiService.ensureValidToken();
      const { url, token } = apiService.getWebSocketInfo(caseId);
      const ws = new WebSocket(url, token);
      wsRef.current = ws;

      ws.onopen = () => {
        onConnectionStatusChange('CONNECTED', null);
        connectionAttemptsRef.current = 0;
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          switch (message.type) {
            case 'chat_response_chunk':
            case 'chat_message_out':
              onIsSendingChange(false);
              onChatMessage({ sender: 'AI', text: message.text || "", timestamp: new Date().toISOString(), isPartial: message.type === 'chat_response_chunk' });
              break;
            case 'document_update':
              if (message.payload) onDocumentUpdate(message.payload);
              break;
            case 'findings_update':
              onFindingsUpdate();
              break;
            case 'connection_established':
              break;
            default:
              break;
          }
        } catch (e) { console.error('Error processing WebSocket message:', e, event.data); }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (connectionAttemptsRef.current >= maxConnectionAttempts) {
          onConnectionStatusChange('ERROR', 'Failed to connect after multiple attempts.');
          return;
        }
        onConnectionStatusChange('DISCONNECTED', 'Connection closed');
        const backoffTime = Math.min(3000 * Math.pow(2, connectionAttemptsRef.current), 30000);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, backoffTime);
      };

      ws.onerror = () => {
        onConnectionStatusChange('ERROR', 'A connection error occurred.');
      };

    } catch (error) {
        if (connectionAttemptsRef.current < maxConnectionAttempts) {
            onConnectionStatusChange('DISCONNECTED', 'Failed to establish connection.');
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        } else {
            onConnectionStatusChange('ERROR', 'Failed to establish connection.');
        }
    }
  }, [caseId, onConnectionStatusChange, onChatMessage, onDocumentUpdate, onFindingsUpdate, onIsSendingChange]);

  useEffect(() => {
    if (isReady && caseId) {
      connectionAttemptsRef.current = 0;
      connectWebSocket();
    }
    return () => {
      connectionAttemptsRef.current = maxConnectionAttempts;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; 
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [caseId, isReady, connectWebSocket]);

  const reconnect = useCallback(() => {
    if (wsRef.current) return;
    connectionAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    connectWebSocket();
  }, [connectWebSocket]);

  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      onIsSendingChange(true);
      onChatMessage({ sender: 'user', text: text, timestamp: new Date().toISOString() });
      const messageToSend = JSON.stringify({ type: 'chat_message', payload: { text } });
      wsRef.current.send(messageToSend);
    } else {
      onConnectionStatusChange('ERROR', 'Cannot send message.');
    }
  }, [onIsSendingChange, onChatMessage, onConnectionStatusChange]);

  return { reconnect, sendChatMessage };
};