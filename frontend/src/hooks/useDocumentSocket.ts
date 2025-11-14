// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts

import { useEffect, useRef, useCallback } from 'react';
// The 'Document' import is now removed as it's no longer used within this hook.
import { ChatMessage, ConnectionStatus } from '../data/types';
import { apiService } from '../services/api';

interface SocketEventHandlers {
  onConnectionStatusChange: (status: ConnectionStatus, error: string | null) => void;
  onChatMessage: (message: ChatMessage) => void;
  onDocumentUpdate: (documentData: any) => void; // eslint-disable-line @typescript-eslint/no-explicit-any
  onFindingsUpdate: (findingsData: any) => void; // eslint-disable-line @typescript-eslint/no-explicit-any
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
  const reconnectCounterRef = useRef(0);

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
      const { url, token } = await apiService.getWebSocketInfo(caseId);
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
          console.log('[WebSocket Hook] Received message type:', message.type);

          switch (message.type) {
            case 'chat_response_chunk':
            case 'chat_message_out':
              onIsSendingChange(false);
              onChatMessage({
                sender: 'AI',
                text: message.text || (message.type === 'chat_response_chunk' ? "" : "No AI response text received."),
                timestamp: new Date().toISOString(),
                isPartial: message.type === 'chat_response_chunk'
              });
              break;

            case 'document_update':
              if (message.payload) {
                onDocumentUpdate(message.payload);
              } else {
                console.warn('[WebSocket Hook] Received document_update without payload');
              }
              break;

            case 'findings_update':
              if (message.payload) {
                onFindingsUpdate(message.payload);
              } else {
                console.warn('[WebSocket Hook] Received findings_update without payload');
              }
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
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCounterRef.current += 1;
            connectWebSocket();
          }, backoffTime);
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
        reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCounterRef.current += 1;
            connectWebSocket();
        }, 3000);
      } else {
        onConnectionStatusChange('ERROR', 'Failed to establish connection. Please check your network and try again.');
      }
    }
  }, [caseId, onConnectionStatusChange, onChatMessage, onDocumentUpdate, onFindingsUpdate, onIsSendingChange]);

  useEffect(() => {
    if (!caseId || !isReady) {
      console.log('[WebSocket Hook] Connection skipped - missing caseId or not ready');
      return;
    }

    connectWebSocket();

    return () => {
      console.log('[WebSocket Hook] Cleaning up WebSocket connection');
      connectionAttemptsRef.current = maxConnectionAttempts;
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
      console.log('[WebSocket Hook] Already connected.');
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

      const messageToSend = JSON.stringify({
        type: 'chat_message',
        payload: { text }
      });

      console.log('[WebSocket Hook] Sending chat message:', text.substring(0, 50) + '...');
      wsRef.current.send(messageToSend);
    } else {
      console.error('[WebSocket Hook] Cannot send message - WebSocket not ready or message empty. ReadyState:', wsRef.current?.readyState);
      onConnectionStatusChange('ERROR', 'Cannot send message - connection not available');
    }
  }, [onIsSendingChange, onChatMessage, onConnectionStatusChange]);

  return {
    reconnect,
    sendChatMessage,
  };
};