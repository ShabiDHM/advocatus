// FILE: src/hooks/useDocumentSocket.ts
// PHOENIX PROTOCOL - SOCKET HOOK V9.1 (CASE-SCOPED SSE + AUTO-REFETCH)
// V9.1: CASE-SCOPED — SSE abonohet në user + case channel. Kur merr event për
//       dokument të panjohur (ngarkuar nga user tjetër), bën refetch automatik.
// V9.0: Dual-listener + auto-healing watchdog.

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction } from 'react';
import { Document, ChatMessage, ConnectionStatus } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import { Jurisdiction, ReasoningMode } from '../components/ChatPanel';
import { sanitizeDocument } from '../utils/documentUtils';

interface UseDocumentSocketReturn {
  documents: Document[];
  setDocuments: Dispatch<SetStateAction<Document[]>>;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  sendChatMessage: (content: string, mode: ReasoningMode, documentIds?: string[], jurisdiction?: Jurisdiction) => void;
  isSendingMessage: boolean;
}

export const useDocumentSocket = (caseId: string | undefined): UseDocumentSocketReturn => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [reconnectCounter, setReconnectCounter] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const refetchInFlightRef = useRef<boolean>(false);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [caseId]);

  // SELF-HEALING WATCHDOG
  useEffect(() => {
    if (!caseId) return;

    const hasPendingDocs = documents.some(
      (d) => d.status === 'PENDING' || d.status === 'PROCESSING' || (d as any).status === 'UPLOADING'
    );

    if (!hasPendingDocs) return;

    const interval = setInterval(async () => {
      try {
        const freshDocs = await apiService.getDocuments(caseId);
        if (Array.isArray(freshDocs)) {
          setDocuments(freshDocs.map(sanitizeDocument));
        }
      } catch (err) {
        console.warn('Watchdog sync failed:', err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [caseId, documents]);

  // SSE: Real-Time Document Status & Progress Listener
  useEffect(() => {
    if (!caseId) {
      setConnectionStatus('DISCONNECTED');
      return;
    }

    const connectSSE = async () => {
        if (eventSourceRef.current?.readyState === EventSource.OPEN) return;
        setConnectionStatus('CONNECTING');
        try {
            const token = apiService.getToken() || await (async () => { await apiService.refreshToken(); return apiService.getToken(); })();
            if (!token) {
              setConnectionStatus('DISCONNECTED');
              return;
            }

            // V9.1: Përfshij case_id për case-scoped channel
            const caseParam = caseId ? `&case_id=${encodeURIComponent(caseId)}` : '';
            const sseUrl = `${API_V1_URL}/stream/updates?token=${token}${caseParam}`;
            const es = new EventSource(sseUrl);
            eventSourceRef.current = es;

            es.onopen = () => setConnectionStatus('CONNECTED');

            const triggerRefetch = () => {
              if (!caseId || refetchInFlightRef.current) return;
              refetchInFlightRef.current = true;
              apiService.getDocuments(caseId)
                .then((fresh) => {
                  if (Array.isArray(fresh)) {
                    setDocuments(fresh.map(sanitizeDocument));
                  }
                })
                .catch((err) => console.warn('SSE refetch failed:', err))
                .finally(() => { refetchInFlightRef.current = false; });
            };

            const handlePayloadData = (rawData: string) => {
              try {
                const payload = JSON.parse(rawData);
                const targetDocId = String(payload.document_id || payload.documentId || payload.doc_id || '');

                if (payload.type === 'DOCUMENT_PROGRESS' || payload.type === 'DOCUMENT_STATUS') {
                    setDocuments((prevDocs) => {
                      // V9.1: Nëse dokumenti nuk njihet (ngarkuar nga user tjetër),
                      // bëj refetch automatik.
                      const isKnown = prevDocs.some(
                        (d) => String(d.id || (d as any)._id || '') === targetDocId
                      );
                      if (!isKnown && targetDocId) {
                        triggerRefetch();
                        return prevDocs;
                      }

                      return prevDocs.map((doc) => {
                        const currentId = String(doc.id || (doc as any)._id || '');
                        if (currentId === targetDocId) {
                          if (payload.type === 'DOCUMENT_PROGRESS') {
                            return {
                              ...doc,
                              progress_message: payload.message,
                              progress_percent: payload.percent
                            } as Document;
                          }

                          const newStatus = (payload.status || 'READY').toUpperCase();
                          return {
                            ...doc,
                            status: (newStatus === 'READY' || newStatus === 'COMPLETED' || newStatus === 'PROCESSED') ? 'READY' : (newStatus === 'FAILED' ? 'FAILED' : doc.status),
                            error_message: newStatus === 'FAILED' ? payload.error : doc.error_message,
                            progress_percent: 100
                          } as Document;
                        }
                        return doc;
                      });
                    });
                }

                if (payload.type === 'DOCUMENT_DELETED') {
                  setDocuments((prevDocs) =>
                    prevDocs.filter((doc) => {
                      const currentId = String(doc.id || (doc as any)._id || '');
                      return currentId !== targetDocId;
                    })
                  );
                }

                // V9.1: Event i panjohur nga case channel → refetch
                if (payload.type === 'DOCUMENT_CREATED' || payload.type === 'CASE_DOCUMENTS_CHANGED') {
                  triggerRefetch();
                }
              } catch (e) {
                console.error("SSE Parse Error", e);
              }
            };

            es.addEventListener('update', (event: MessageEvent) => {
              handlePayloadData(event.data);
            });

            es.onmessage = (event: MessageEvent) => {
              handlePayloadData(event.data);
            };

            es.onerror = () => {
                if (es.readyState === EventSource.CLOSED) {
                  setConnectionStatus('DISCONNECTED');
                } else {
                  setConnectionStatus('CONNECTING');
                }
            };
        } catch (error) {
          setConnectionStatus('DISCONNECTED');
        }
    };
    connectSSE();
  }, [caseId, reconnectCounter]);

  const reconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setReconnectCounter((prev) => prev + 1);
  }, []);

  // Legal Chat HTTP Streaming
  const sendChatMessage = useCallback(async (content: string, mode: ReasoningMode, documentIds?: string[], jurisdiction?: Jurisdiction) => {
    if (!content.trim() || !caseId) return;

    setIsSendingMessage(true);

    const userMsg: ChatMessage = { role: 'user', content, timestamp: new Date().toISOString() };
    const aiPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg, aiPlaceholder]);

    let streamContent = "";

    try {
        const stream = apiService.sendChatMessageStream(caseId, content, documentIds, jurisdiction, mode);

        for await (const chunk of stream) {
            streamContent += chunk;

            setMessages((prev) => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                    updated[lastIdx] = { ...updated[lastIdx], content: streamContent };
                }
                return updated;
            });
        }
    } catch (error) {
        console.error("Legal Chat Stream failed:", error);
        setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx] && updated[lastIdx].role === 'ai') {
                updated[lastIdx].content = "Ndodhi një gabim teknik. Shërbimi i bisedës dështoi.";
            }
            return updated;
        });
    } finally {
        setIsSendingMessage(false);
    }
  }, [caseId]);

  return { documents, setDocuments, messages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage };
};

export default useDocumentSocket;