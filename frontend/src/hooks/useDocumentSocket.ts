// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (SAFE TOKEN VALIDATION)
// CORRECTION: The connectWebSocket function now explicitly awaits apiService.ensureValidToken()
// before attempting to connect. This is the definitive fix for the authentication race
// condition, ensuring the WebSocket only ever attempts to connect with a guaranteed-fresh token.

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
    if (connectionAttemptsRef.current >= maxConnectionAttempts) {
      console.error('[WebSocket Hook] Max connection attempts reached, giving up');
      onConnectionStatusChange('ERROR', 'Failed to connect after multiple attempts. Please refresh the page.');
      return;
    }

    connectionAttemptsRef.current++;
    console.log(`[WebSocket Hook] Connection attempt ${connectionAttemptsRef.current}/${maxConnectionAttempts} for case:`, caseId);
    onConnectionStatusChange('CONNECTING', null);

    try {
      // This await is the definitive fix for the race condition.
      await apiService.ensureValidToken();
      
      const { url, token } = apiService.getWebSocketInfo(caseId);
      const ws = new WebSocket(url, token);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket Hook] ✅ WebSocket connection established successfully');
        onConnectionStatusChange('CONNECTED', null);
        connectionAttemptsRef.current = 0;
        clearTimeout(reconnectTimeoutRef.current);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          // Removed verbose logging for production
          switch (message.type) {
            case 'chat_response_chunk':
            case 'chat_message_out':
              onIsSendingChange(false);
              onChatMessage({
                sender: 'AI',
                text: message.text || "",
                timestamp: new Date().toISOString(),
                isPartial: message.type === 'chat_response_chunk'
              });
              break;
            case 'document_update':
              if (message.payload) onDocumentUpdate(message.payload);
              break;
            case 'findings_update':
              if (message.payload) onFindingsUpdate(message.payload);
              break;
            case 'connection_established':
              console.log(`[WebSocket Hook] Server confirmed connection: ${message.message}`);
              break;
            default:
              console.warn('[WebSocket Hook] Received unhandled message type:', message.type);
          }
        } catch (e) {
          console.error('[WebSocket Hook] Error processing WebSocket message:', e, event.data);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket Hook] WebSocket connection closed:', event.code, event.reason);
        onIsSendingChange(false);
        let errorMessage = 'Connection closed';
        if (event.code === 1006) {
          errorMessage = 'Unable to connect to server. Please check your internet connection or try again later.';
        }
        
        if (connectionAttemptsRef.current < maxConnectionAttempts) {
          onConnectionStatusChange('DISCONNECTED', errorMessage);
          const backoffTime = Math.min(3000 * Math.pow(2, connectionAttemptsRef.current - 1), 30000);
          console.log(`[WebSocket Hook] Scheduling auto-reconnect in ${backoffTime}ms`);
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, backoffTime);
        } else {
          onConnectionStatusChange('ERROR', 'Failed to establish connection after multiple attempts. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket Hook] WebSocket connection error:', error);
        onConnectionStatusChange('ERROR', 'Connection error occurred. Please try again.');
      };

    } catch (error) {
      console.error('[WebSocket Hook] Failed to establish WebSocket connection:', error);
      if (connectionAttemptsRef.current < maxConnectionAttempts) {
        onConnectionStatusChange('DISCONNECTED', 'Failed to establish connection. Please check your network and try again.');
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      } else {
        onConnectionStatusChange('ERROR', 'Failed to establish connection. Please check your network and try again.');
      }
    }
  }, [caseId, onConnectionStatusChange, onChatMessage, onDocumentUpdate, onFindingsUpdate, onIsSendingChange]);

  useEffect(() => {
    if (!caseId || !isReady) {
      return;
    }
    connectWebSocket();
    return () => {
      console.log('[WebSocket Hook] Cleaning up WebSocket connection');
      connectionAttemptsRef.current = maxConnectionAttempts; // Prevent reconnect on unmount
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
    console.log('[WebSocket Hook] 🔄 Manual reconnect triggered');
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    connectionAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    connectWebSocket();
  }, [connectWebSocket]);

  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      onIsSendingChange(true);
      onChatMessage({
        sender: 'user',
        text: text,
        timestamp: new Date().toISOString()
      });
      const messageToSend = JSON.stringify({ type: 'chat_message', payload: { text } });
      wsRef.current.send(messageToSend);
    } else {
      onConnectionStatusChange('ERROR', 'Cannot send message - connection not available');
    }
  }, [onIsSendingChange, onChatMessage, onConnectionStatusChange]);

  return { reconnect, sendChatMessage };
};