// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - PATH ALIGNMENT (CLEAN)

import { useEffect, useRef, useCallback } from 'react';
import { ChatMessage, ConnectionStatus } from '../data/types';

// ALIGNED with Caddyfile and backend router.
const WEBSOCKET_URL = 'wss://advocatus-prod-api.duckdns.org/api/v1/comms';

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
  _caseId: string, // Prefixed with underscore to denote it is intentionally unused for this test.
  isReady: boolean,
  handlers: SocketEventHandlers
): UseDocumentSocketReturn => {
  const { onConnectionStatusChange, onChatMessage, onIsSendingChange } = handlers;
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current) return;

    onConnectionStatusChange('CONNECTING', null);
    console.log(`[WebSocket Test] Attempting to connect to: ${WEBSOCKET_URL}`);

    const ws = new WebSocket(WEBSOCKET_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      onConnectionStatusChange('CONNECTED', null);
      console.log('[WebSocket Test] Connection successful.');
      onChatMessage({ sender: 'AI', text: 'System: Connected to WebSocket echo server.', timestamp: new Date().toISOString() });
    };

    ws.onmessage = (event) => {
      console.log(`[WebSocket Test] Echo received: ${event.data}`);
      onChatMessage({ sender: 'AI', text: `Echo Server: ${event.data}`, timestamp: new Date().toISOString() });
      onIsSendingChange(false);
    };

    ws.onclose = () => {
      wsRef.current = null;
      onConnectionStatusChange('DISCONNECTED', 'Connection closed');
      console.log('[WebSocket Test] Connection closed.');
    };

    ws.onerror = () => {
      wsRef.current = null;
      onConnectionStatusChange('ERROR', 'A connection error occurred.');
      console.error('[WebSocket Test] A connection error occurred.');
    };
  }, [onConnectionStatusChange, onChatMessage, onIsSendingChange]);

  useEffect(() => {
    if (isReady) {
      connect();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isReady, connect]);

  const reconnect = useCallback(() => {
    if (!wsRef.current) {
      connect();
    }
  }, [connect]);

  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      onIsSendingChange(true);
      onChatMessage({ sender: 'user', text: text, timestamp: new Date().toISOString() });
      console.log(`[WebSocket Test] Sending message: ${text}`);
      wsRef.current.send(text);
    } else {
      onConnectionStatusChange('ERROR', 'Cannot send message. Connection is not open.');
    }
  }, [onIsSendingChange, onChatMessage, onConnectionStatusChange]);

  return { reconnect, sendChatMessage };
};