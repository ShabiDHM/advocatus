// FILE: /home/user/advocatus-frontend/src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - PHASE 2 (IMPORT PATH CORRECTED)

import { useEffect, useRef, useCallback } from 'react';
import { apiService } from '../services/api'; // CORRECTED IMPORT PATH
import { ChatMessage, ConnectionStatus } from '../data/types';

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
  caseId: string, // Now actively used to establish a scoped connection.
  isReady: boolean,
  handlers: SocketEventHandlers
): UseDocumentSocketReturn => {
  const { onConnectionStatusChange, onChatMessage, onIsSendingChange } = handlers;
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current || !caseId) return;

    onConnectionStatusChange('CONNECTING', null);
    
    try {
      const { url, token } = apiService.getWebSocketInfo(caseId);
      console.log(`[WebSocket] Attempting secure connection to: ${url}`);
      
      // The backend dependency `get_current_user_ws` expects the token as a subprotocol.
      const ws = new WebSocket(url, token);
      wsRef.current = ws;

      ws.onopen = () => {
        onConnectionStatusChange('CONNECTED', null);
        console.log('[WebSocket] Secure connection successful.');
        onChatMessage({ sender: 'AI', text: `System: Securely connected to case channel.`, timestamp: new Date().toISOString() });
      };

      ws.onmessage = (event) => {
        console.log(`[WebSocket] Broadcast received: ${event.data}`);
        onChatMessage({ sender: 'AI', text: `Broadcast: ${event.data}`, timestamp: new Date().toISOString() });
        onIsSendingChange(false);
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        // 1000 is a normal closure. Don't show an error for that.
        if (event.code !== 1000) {
            onConnectionStatusChange('DISCONNECTED', `Connection closed unexpectedly. Code: ${event.code}`);
            console.warn(`[WebSocket] Connection closed unexpectedly. Code: ${event.code}`);
        } else {
            onConnectionStatusChange('DISCONNECTED', null);
            console.log('[WebSocket] Connection closed normally.');
        }
      };

      ws.onerror = (event) => {
        wsRef.current = null;
        onConnectionStatusChange('ERROR', 'A WebSocket error occurred.');
        console.error('[WebSocket] A connection error occurred.', event);
      };

    } catch (error) {
        onConnectionStatusChange('ERROR', 'Failed to get WebSocket connection info. User may be unauthenticated.');
        console.error('[WebSocket] Failed to prepare connection:', error);
    }
  }, [caseId, onConnectionStatusChange, onChatMessage, onIsSendingChange]);

  useEffect(() => {
    if (isReady && caseId) {
      connect();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent onclose handler from firing on component unmount
        wsRef.current.close(1000, "Component unmounting");
        wsRef.current = null;
      }
    };
  }, [isReady, caseId, connect]);

  const reconnect = useCallback(() => {
    if (!wsRef.current) {
      connect();
    }
  }, [connect]);

  const sendChatMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      onIsSendingChange(true);
      onChatMessage({ sender: 'user', text: text, timestamp: new Date().toISOString() });
      console.log(`[WebSocket] Sending message: ${text}`);
      wsRef.current.send(text);
    } else {
      onConnectionStatusChange('ERROR', 'Cannot send message. Connection is not open.');
    }
  }, [onIsSendingChange, onChatMessage, onConnectionStatusChange]);

  return { reconnect, sendChatMessage };
};