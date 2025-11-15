// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (CODE CLEANUP)
// CORRECTION: Removed the unused 'event' parameter from the ws.onclose handler
// to resolve the "'event' is declared but its value is never read" compiler warning.

import { useEffect, useRef, useCallback } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';
import { apiService } from '../services/api';

interface SocketEventHandlers {
  onConnectionStatusChange: (status: ConnectionStatus, error: string | null) => void;
  onChatMessage: (message: ChatMessage) => void;
  onDocumentUpdate: (documentData: any) => void; 
  onFindingsUpdate: (findingsData: any) => void;
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
  const {
    onConnectionStatusChange,
    onChatMessage,
    onDocumentUpdate,
    onFindingsUpdate,
    onIsSendingChange,
  } = handlers;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const connectionAttemptsRef = useRef(0);
  const maxConnectionAttempts = 5;

  const connectWebSocket = useCallback(async () => {
    if (wsRef.current) return;
    if (connectionAttemptsRef.current >= maxConnectionAttempts) {
      onConnectionStatusChange('ERROR', 'Failed to connect after multiple attempts. Please refresh the page.');
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
        clearTimeout(reconnectTimeoutRef.current);
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
              if (message.payload) onFindingsUpdate(message.payload);
              break;
            case 'connection_established':
              break;
            default:
              console.warn('[WebSocket Hook] Received unhandled message type:', message.type);
          }
        } catch (e) {
          console.error('[WebSocket Hook] Error processing WebSocket message:', e, event.data);
        }
      };

      ws.onclose = () => { // Removed 'event' parameter
        wsRef.current = null;
        onIsSendingChange(false);
        if (connectionAttemptsRef.current >= maxConnectionAttempts) {
          onConnectionStatusChange('ERROR', 'Failed to establish connection after multiple attempts. Please refresh the page.');
          return;
        }
        onConnectionStatusChange('DISCONNECTED', 'Connection closed');
        const backoffTime = Math.min(3000 * Math.pow(2, connectionAttemptsRef.current - 1), 30000);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, backoffTime);
      };

      ws.onerror = () => {
        onConnectionStatusChange('ERROR', 'Connection error occurred.');
      };

    } catch (error) {
        if (connectionAttemptsRef.current < maxConnectionAttempts) {
            onConnectionStatusChange('DISCONNECTED', 'Failed to establish connection.');
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
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
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
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
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    connectWebSocket();
  }, [connectWebSocket]);

  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      onIsSendingChange(true);
      onChatMessage({ sender: 'user', text: text, timestamp: new Date().toISOString() });
      const messageToSend = JSON.stringify({ type: 'chat_message', payload: { text } });
      wsRef.current.send(messageToSend);
    } else {
      onConnectionStatusChange('ERROR', 'Cannot send message - connection not available');
    }
  }, [onIsSendingChange, onChatMessage, onConnectionStatusChange]);

  return { reconnect, sendChatMessage };
};