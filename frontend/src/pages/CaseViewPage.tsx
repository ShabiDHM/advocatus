// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V109.5
// V109.5: FIX KRITIK — rikthyer handler-i section_chunk (humbur gjatë refaktorimit).
//         Shtuar handler për report_ready edhe në fresh run.
//         Shtuar logging diagnostikues për accumulated bosh.
// V109.4: Hequr auditSubLabel + auditIsDocumentMode.
// V109.3: Progress bar inline në ChatHeader.
// V109.0: Background audit generation.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import ChatPanel, { ChatMode, Jurisdiction, ReasoningMode } from '../components/ChatPanel';
import PDFViewerModal from '../components/FileViewerModal';
import DockedPDFViewer from '../components/DockedPDFViewer';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { AlertCircle, FileText, Film, BrainCircuit } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { extractAndNormalizeHistory, getUserSalutation } from '../utils/caseHelpers';
import { CaseHeaderBar } from '../components/case/CaseHeaderBar';
import { EvidenceVaultPanel, EvidenceSubTab } from '../components/case/EvidenceVaultPanel';
import { RenameDocumentModal } from '../components/case/RenameDocumentModal';
import { CaseDossierAuditModal } from '../components/case/CaseDossierAuditModal';

type CaseData = { details: Case | null };

type MobileMainTab = 'DOCS' | 'MEDIA' | 'CHAT';

const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated, user } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();

  const [caseData, setCaseData] = useState<CaseData>({ details: null });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [minimizedDocument, setMinimizedDocument] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);
  const [viewingInitialPage, setViewingInitialPage] = useState<number>(1);
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  const [mobileTab, setMobileTab] = useState<MobileMainTab>('DOCS');
  const [vaultSubTab, setVaultSubTab] = useState<EvidenceSubTab>('documents');

  // V109.0: Background audit generation state
  const [isAuditGenerating, setIsAuditGenerating] = useState<boolean>(false);
  const [auditProgressText, setAuditProgressText] = useState<string>('');
  const [pendingAuditReport, setPendingAuditReport] = useState<string | null>(null);
  const [pendingAuditSource, setPendingAuditSource] = useState<'fresh' | 'cache' | 'saved'>('fresh');
  const [pendingAuditDocIds, setPendingAuditDocIds] = useState<string[] | null>(null);

  // V109.3: Progress state — kalohet në ChatHeader
  const [auditPhaseLabel, setAuditPhaseLabel] = useState<string>('');
  const [auditProgressPercent, setAuditProgressPercent] = useState<number>(0);
  const [auditStartTime, setAuditStartTime] = useState<number | null>(null);

  const [isDossierAuditModalOpen, setIsDossierAuditModalOpen] = useState<boolean>(false);

  const isPro = true;
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const userSalutation = useMemo(() => getUserSalutation(user), [user]);
  const clientName = useMemo(() => (caseData.details as any)?.client_name || (caseData.details as any)?.client?.name || 'Klienti', [caseData.details]);
  const clientPosition = useMemo(() => (caseData.details as any)?.client_position || 'DEFENDANT', [caseData.details]);

  const selectedDocObj = useMemo(() => {
    if (selectedDocumentIds.length > 0) {
      return liveDocuments.find(d => selectedDocumentIds.includes(String(d.id))) || null;
    }
    return null;
  }, [selectedDocumentIds, liveDocuments]);

  const handleSelectDocument = useCallback((doc: Document) => {
    const docIdStr = String(doc.id);
    setSelectedDocumentIds((prev) => {
      if (prev.includes(docIdStr)) {
        return [];
      } else {
        return [docIdStr];
      }
    });
    setMobileTab('CHAT');
  }, []);

  const saveToLocalStorage = useCallback((messages: ChatMessage[]) => {
    if (!caseId) return;
    localStorage.setItem(`chat_${caseId}`, JSON.stringify(messages));
  }, [caseId]);

  const persistChatHistory = useCallback(async (messages: ChatMessage[]) => {
    if (!caseId) return;
    saveToLocalStorage(messages);
    try {
      await apiService.updateChatHistory(caseId, messages);
    } catch (err) {
      console.error('Failed to persist chat history:', err);
    }
  }, [caseId, saveToLocalStorage]);

  const fetchCaseData = useCallback(async (isInitialLoad = false) => {
    if (!caseId) return;
    if (isInitialLoad) setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs] = await Promise.all([
        apiService.getCaseDetails(caseId),
        apiService.getDocuments(caseId),
      ]);
      setCaseData({ details });
      setLiveDocuments((initialDocs || []).map(sanitizeDocument));

      const backendMessages = extractAndNormalizeHistory(details);
      if (backendMessages.length > 0) {
        setChatMessages(backendMessages);
        saveToLocalStorage(backendMessages);
      } else {
        setChatMessages([]);
        localStorage.removeItem(`chat_${caseId}`);
      }
    } catch {
      setError(t('error.failedToLoadCase', 'Dështoi ngarkimi i lëndës.'));
    } finally {
      if (isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, saveToLocalStorage]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);

  useEffect(() => {
    const hasProcessingDocs = liveDocuments.some(
      (doc) => doc.status === 'PROCESSING' || doc.status === 'PENDING'
    );

    if (!hasProcessingDocs || !caseId) return;

    const interval = setInterval(async () => {
      try {
        const latestDocs = await apiService.getDocuments(caseId);
        if (Array.isArray(latestDocs)) {
          setLiveDocuments(latestDocs.map(sanitizeDocument));
        }
      } catch (err) {
        console.warn('Auto-sync documents polling error:', err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [liveDocuments, caseId, setLiveDocuments]);

  const handleDocumentUploaded = (newDoc: Document) => setLiveDocuments((p) => [sanitizeDocument(newDoc), ...p]);
  const handleDocumentDeleted = (res: DeletedDocumentResponse) => setLiveDocuments((p) => p.filter((d) => String(d.id) !== String(res.documentId)));

  const handleViewOriginal = useCallback((doc: Document) => {
    setViewingInitialPage(1);
    setViewingUrl(`${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`);
    setViewingDocument(doc);
    setMinimizedDocument(null);
  }, [caseId]);

  useEffect(() => {
    const handleOpenDocPreview = (e: any) => {
      const { fileName, href } = e.detail || {};
      if (!fileName && !href) return;

      const cleanSearch = (fileName || '').toString().toLowerCase().trim().replace(/^[\(\[\s"']+|[\)\]\s"']+$|\.pdf$/gi, '');
      const docIdFromHref = (href || '').match(/\/documents\/([a-f0-9]{24})/i)?.[1]?.toLowerCase();

      const matchedDoc = liveDocuments.find((doc) => {
        const docId = String(doc.id || (doc as any)._id || '').toLowerCase();
        if (docIdFromHref && docId === docIdFromHref) return true;
        if (href && href.toLowerCase().includes(docId)) return true;

        const docName = (doc.file_name || (doc as any).title || '').toLowerCase();
        if (cleanSearch && (docName.includes(cleanSearch) || cleanSearch.includes(docName.replace(/\.pdf$/i, '')))) {
          return true;
        }
        return false;
      });

      if (matchedDoc) {
        handleViewOriginal(matchedDoc);
      } else if (liveDocuments.length > 0 && cleanSearch) {
        const fuzzyMatch = liveDocuments.find((d) => {
          const words = cleanSearch.split(/\s+/).filter((w: string) => w.length > 3);
          const name = (d.file_name || (d as any).title || '').toLowerCase();
          return words.some((w: string) => name.includes(w));
        });
        if (fuzzyMatch) {
          handleViewOriginal(fuzzyMatch);
        }
      }
    };

    window.addEventListener('open_document_preview', handleOpenDocPreview);
    return () => window.removeEventListener('open_document_preview', handleOpenDocPreview);
  }, [liveDocuments, handleViewOriginal]);

  const handleClearChat = async () => {
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
      try {
        await apiService.updateChatHistory(caseId, []);
      } catch {}

      localStorage.removeItem(`chat_${caseId}`);
      setChatMessages([]);

      setCaseData((prev) => ({
        ...prev,
        details: prev.details ? ({
          ...prev.details,
          chat_history: [],
        } as any) : null,
      }));
    } catch (err) {
      console.error("Dështoi pastrimi i bisedës në server:", err);
      alert(t('error.generic', 'Ndodhi një gabim gjatë pastrimit të bisedës.'));
    }
  };

  const handleChatSubmit = useCallback(async (
    text: string,
    mode: ChatMode,
    reasoning: ReasoningMode,
    domain: string,
    documentIds?: string[],
    jurisdiction?: Jurisdiction
  ) => {
    if (!caseId) return;
    const userMessage: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    const assistantPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };

    setChatMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsSendingMessage(true);

    try {
      let acc = '';
      const stream = apiService.sendChatMessageStream(
        caseId,
        text,
        documentIds,
        jurisdiction,
        reasoning,
        mode === 'document' ? domain : 'automatic',
        true
      );

      for await (const chunk of stream) {
        acc += chunk;
        const currentAcc = acc;

        setChatMessages((prev) => {
          const updated = [...prev];
          if (updated.length > 0) {
            updated[updated.length - 1] = { ...updated[updated.length - 1], content: currentAcc };
          }
          return updated;
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
      }

      setChatMessages((prev) => {
        const finalMessages = [...prev];
        persistChatHistory(finalMessages);
        return finalMessages;
      });
    } catch (err: any) {
      console.error("[Chat Stream Error]:", err);
      const errorDetail = err?.message || 'Nuk u arrit komunikimi me shërbimin AI.';
      setChatMessages((prev) => {
        const withError = [...prev];
        if (withError.length > 0) {
          withError[withError.length - 1] = {
            ...withError[withError.length - 1],
            content: `[Gabim Teknik] ${errorDetail}`
          };
        }
        persistChatHistory(withError);
        return withError;
      });
    } finally {
      setIsSendingMessage(false);
    }
  }, [caseId, persistChatHistory]);

  // ═══════════════════════════════════════════════════════════════════════
  // V109.5: Background generation + Progress tracking
  // ═══════════════════════════════════════════════════════════════════════

  const _runBackgroundAudit = useCallback(async (docIds: string[] | null) => {
    if (!currentCaseId) return;

    const isDocMode = !!docIds;
    const startedAt = Date.now();

    // Reset progress state
    setIsAuditGenerating(true);
    setAuditProgressText(isDocMode ? 'Duke verifikuar dokumentin...' : 'Duke analizuar fashikullin...');
    setAuditStartTime(startedAt);
    setAuditPhaseLabel(isDocMode ? 'Fillimi i verifikimit' : 'Fillimi i analizës');
    setAuditProgressPercent(2);

    let accumulated = '';
    let detectedSource: 'fresh' | 'cache' = 'fresh';
    let currentPhase = '';
    let docsTotal = 0;
    let sectionsCompleted = 0;
    let sectionsStarted = 0;
    let chunksReceived = 0;

    const SECTIONS_TOTAL = 6;

    try {
      const stream = apiService.streamCaseAnalysis(currentCaseId, false, docIds || undefined);

      for await (const evt of stream) {
        const evtType = evt.event;

        if (evtType === 'start') {
          setAuditProgressText(isDocMode ? 'Duke verifikuar dokumentin...' : 'Duke analizuar fashikullin...');
          continue;
        }

        if (evtType === 'phase_started') {
          currentPhase = evt.phase || '';
          const phaseLabels: Record<string, string> = {
            extraction: isDocMode ? 'Ekstraktimi i dokumentit' : 'Ekstraktimi i shkresave',
            cross_reference: 'Gjetja e lidhjeve',
            synthesis: 'Hartimi i doktrinës',
            document_review: 'Verifikimi ligjor',
          };
          setAuditPhaseLabel(phaseLabels[currentPhase] || currentPhase);

          if (currentPhase === 'extraction') {
            setAuditProgressPercent(5);
          } else if (currentPhase === 'cross_reference') {
            setAuditProgressPercent(60);
          } else if (currentPhase === 'synthesis') {
            setAuditProgressPercent(70);
          } else if (currentPhase === 'document_review') {
            setAuditProgressPercent(35);
          }
          continue;
        }

        if (evtType === 'phase_skipped') {
          if (evt.phase === 'synthesis' || evt.phase === 'document_review') {
            detectedSource = 'cache';
          }
          continue;
        }

        if (evtType === 'document_started') {
          const idx = (evt.index || 0) + 1;
          docsTotal = evt.total_documents || 0;
          setAuditProgressText(`Ekstraktimi ${idx}/${docsTotal}: ${evt.file_name || ''}`);

          if (docsTotal > 0) {
            if (isDocMode) {
              const pct = 5 + (idx / docsTotal) * 25;
              setAuditProgressPercent(Math.round(pct));
            } else {
              const pct = 5 + (idx / docsTotal) * 50;
              setAuditProgressPercent(Math.round(pct));
            }
          }
          continue;
        }

        if (evtType === 'section_started') {
          const title = evt.section_title || evt.section_key || '';
          sectionsStarted++;
          setAuditProgressText(`Seksioni: ${title}`);
          // V109.5: Shto titullin në accumulated për strukturë
          if (title) {
            accumulated += `\n\n## ${title}\n\n`;
          }
          continue;
        }

        // ═══════════════════════════════════════════════════════════════
        // V109.5: FIX — handler-i section_chunk u rikthye
        // ═══════════════════════════════════════════════════════════════
        if (evtType === 'section_chunk') {
          const chunk = evt.chunk || evt.content || evt.text || '';
          if (chunk) {
            chunksReceived++;
            accumulated += chunk;
          }
          continue;
        }

        if (evtType === 'section_completed') {
          sectionsCompleted++;
          if (currentPhase === 'synthesis') {
            const pct = 70 + (sectionsCompleted / SECTIONS_TOTAL) * 25;
            setAuditProgressPercent(Math.round(pct));
          } else if (currentPhase === 'document_review') {
            const pct = 35 + (sectionsCompleted / SECTIONS_TOTAL) * 60;
            setAuditProgressPercent(Math.round(pct));
          }
          continue;
        }

        if (evtType === 'report_ready') {
          const content = evt.content || '';
          const fromCache = evt.from_cache === true;
          // V109.5: Prano report_ready edhe për fresh nëse accumulated është bosh
          if (content.trim() && !accumulated) {
            detectedSource = fromCache ? 'cache' : 'fresh';
            accumulated = content;
          }
          continue;
        }

        if (evtType === 'error') {
          throw new Error(evt.message || 'Gabim në server gjatë analizës.');
        }

        if (evtType === 'complete') {
          break;
        }
      }

      const finalReport = accumulated.trim();
      if (!finalReport) {
        console.error('[Background Audit] Accumulated content is empty!', {
          isDocMode,
          docsTotal,
          sectionsStarted,
          sectionsCompleted,
          chunksReceived,
          currentPhase,
          detectedSource
        });
        throw new Error('Raporti nuk u gjenerua. Provoni përsëri.');
      }

      // Save në server
      try {
        await apiService.saveCaseDossierAudit(currentCaseId, finalReport);
      } catch (saveErr) {
        console.error('Save audit error:', saveErr);
      }

      // Set progress 100% + hap modal
      setAuditProgressPercent(100);
      setAuditPhaseLabel('Përfundoi');
      setAuditProgressText('Raporti u gjenerua me sukses');

      setPendingAuditReport(finalReport);
      setPendingAuditSource(detectedSource);
      setPendingAuditDocIds(docIds);
      setIsDossierAuditModalOpen(true);

    } catch (err: any) {
      console.error('[Background Audit Error]', err);
      alert(err?.message || 'Ndodhi një gabim gjatë gjenerimit të raportit.');
    } finally {
      setTimeout(() => {
        setIsAuditGenerating(false);
        setAuditProgressText('');
        setAuditStartTime(null);
        setAuditPhaseLabel('');
        setAuditProgressPercent(0);
      }, 800);
    }
  }, [currentCaseId]);

  const handleTriggerSelectedDocAudit = useCallback(() => {
    if (isAuditGenerating) return;

    let docIds: string[] | null = null;

    if (selectedDocObj) {
      docIds = [String(selectedDocObj.id)];
    } else if (liveDocuments.length === 0) {
      alert("Nuk ka shkresa të administruara në këtë lëndë. Ngarkoni shkresat së pari.");
      return;
    }

    _runBackgroundAudit(docIds);
  }, [selectedDocObj, liveDocuments.length, isAuditGenerating, _runBackgroundAudit]);

  const handleCloseDossierModal = useCallback(() => {
    setIsDossierAuditModalOpen(false);
    setPendingAuditReport(null);
    setPendingAuditDocIds(null);
  }, []);

  const handleRegenerateAudit = useCallback(() => {
    const docIds = pendingAuditDocIds;
    setIsDossierAuditModalOpen(false);
    setPendingAuditReport(null);
    setTimeout(() => _runBackgroundAudit(docIds), 150);
  }, [pendingAuditDocIds, _runBackgroundAudit]);

  const handleRenameAction = async (newName: string) => {
    if (!caseId || !documentToRename) return;
    try {
      await apiService.renameDocument(caseId, documentToRename.id, newName);
      setLiveDocuments((p) => p.map((d) => (d.id === documentToRename.id ? { ...d, file_name: newName } : d)));
    } catch {
      alert(t('error.generic', 'Ndodhi një gabim.'));
    }
  };

  if (isAuthLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-canvas">
        <div className="w-14 h-14 border-4 border-primary-start border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !caseData.details) {
    return (
      <div className="p-8 text-center text-danger border border-danger/30 rounded-2xl bg-danger/5 mt-20 max-w-lg mx-auto animate-pulse">
        <AlertCircle className="mx-auto h-12 w-12 mb-4" />
        <p className="font-bold uppercase tracking-wide">{error}</p>
      </div>
    );
  }

  const dossierDocumentNames = pendingAuditDocIds
    ? pendingAuditDocIds
        .map((id) => liveDocuments.find((d) => String(d.id) === id)?.file_name)
        .filter((n): n is string => Boolean(n))
    : undefined;

  return (
    <motion.div className="w-full min-h-screen pb-6 bg-canvas text-text-primary flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-16 sm:pt-20 pb-2 space-y-2.5 sm:space-y-3.5 flex-1 flex flex-col">

        <CaseHeaderBar
          caseDetails={caseData.details}
          documents={liveDocuments}
        />

        <div className="flex lg:hidden items-center bg-surface border border-main rounded-xl p-1 shadow-xs shrink-0">
          <button
            type="button"
            onClick={() => {
              setMobileTab('DOCS');
              setVaultSubTab('documents');
            }}
            className={`flex-1 py-2 px-1.5 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-all cursor-pointer min-h-[38px] ${
              mobileTab === 'DOCS'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <FileText size={13} className="shrink-0" />
            <span className="truncate">Dokumentet ({liveDocuments.length})</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setMobileTab('MEDIA');
              setVaultSubTab('audio');
            }}
            className={`flex-1 py-2 px-1.5 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-all cursor-pointer min-h-[38px] ${
              mobileTab === 'MEDIA'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Film size={13} className="shrink-0" />
            <span className="truncate">Audio & Video</span>
          </button>

          <button
            type="button"
            onClick={() => setMobileTab('CHAT')}
            className={`flex-1 py-2 px-1.5 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-all cursor-pointer min-h-[38px] ${
              mobileTab === 'CHAT'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <BrainCircuit size={13} className="shrink-0" />
            <span className="truncate">Biseda</span>
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 lg:gap-6 z-0 h-[calc(100dvh-185px)] sm:h-[calc(100dvh-200px)] lg:h-[720px] max-h-[850px] items-stretch flex-1 min-h-[480px]">

          <div className={`lg:col-span-5 h-full overflow-y-auto flex-col ${
            mobileTab === 'DOCS' || mobileTab === 'MEDIA' ? 'flex' : 'hidden lg:flex'
          }`}>
            <EvidenceVaultPanel
              caseId={caseData.details.id}
              documents={liveDocuments}
              connectionStatus={connectionStatus}
              reconnect={reconnect}
              onDocumentUploaded={handleDocumentUploaded}
              onDocumentDeleted={handleDocumentDeleted}
              onViewOriginal={handleViewOriginal}
              onRenameDocument={setDocumentToRename}
              onVerifyDocumentLaws={(doc) => {
                setSelectedDocumentIds([String(doc.id)]);
                handleTriggerSelectedDocAudit();
              }}
              selectedDocumentId={selectedDocObj ? String(selectedDocObj.id) : ''}
              onSelectDocument={handleSelectDocument}
              activeSubTab={vaultSubTab}
              onSubTabChange={setVaultSubTab}
              t={t}
            />
          </div>

          <div className={`lg:col-span-7 flex-col bg-surface border border-main rounded-2xl overflow-hidden shadow-sm relative h-full ${
            mobileTab === 'CHAT' ? 'flex' : 'hidden lg:flex'
          }`}>
            <ChatPanel
              messages={chatMessages}
              connectionStatus={connectionStatus}
              reconnect={reconnect}
              onSendMessage={handleChatSubmit}
              isSendingMessage={isSendingMessage}
              onClearChat={handleClearChat}
              t={t}
              className="h-full w-full bg-transparent border-0 rounded-none flex-1"
              activeContextId={currentCaseId}
              isPro={isPro}
              documents={liveDocuments}
              selectedDocumentIds={selectedDocumentIds}
              onDocumentSelectionChange={setSelectedDocumentIds}
              userSalutation={userSalutation}
              clientPosition={clientPosition}
              onAnalyzeDocument={handleTriggerSelectedDocAudit}
              selectedDocName={selectedDocObj?.file_name}
              isAuditGenerating={isAuditGenerating}
              auditProgressText={auditProgressText}
              auditProgressPercent={auditProgressPercent}
              auditPhaseLabel={auditPhaseLabel}
              auditStartTime={auditStartTime}
            />
          </div>
        </div>
      </div>

      {viewingDocument && (
        <PDFViewerModal
          documentData={viewingDocument}
          caseId={caseData.details.id}
          onClose={() => { setViewingDocument(null); setViewingUrl(null); }}
          onMinimize={() => { if (viewingDocument) { setMinimizedDocument(viewingDocument); setViewingDocument(null); } }}
          t={t}
          directUrl={viewingUrl}
          isAuth={true}
          initialPage={viewingInitialPage}
        />
      )}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={() => handleViewOriginal(minimizedDocument)} onClose={() => setMinimizedDocument(null)} />}

      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />

      <CaseDossierAuditModal
        isOpen={isDossierAuditModalOpen}
        onClose={handleCloseDossierModal}
        caseId={currentCaseId}
        caseName={(caseData.details as any)?.title || 'Fashikulli i Lëndës'}
        clientName={clientName}
        documentCount={liveDocuments.length}
        documentIds={pendingAuditDocIds || undefined}
        documentNames={dossierDocumentNames}
        preGeneratedReport={pendingAuditReport}
        preGeneratedSource={pendingAuditSource}
        onRegenerate={handleRegenerateAudit}
      />
    </motion.div>
  );
};

export default CaseViewPage;