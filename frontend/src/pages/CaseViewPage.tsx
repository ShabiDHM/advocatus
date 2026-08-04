// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V44.0 (ADMIN-ONLY FEATURE GATE FOR ANALIZA, FINANCAT & ONTOLOGJIA)

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, CaseAnalysisResult, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel, { ChatMode, Jurisdiction, ReasoningMode } from '../components/ChatPanel';
import MediaEvidencePanel from '../components/MediaEvidencePanel';
import PDFViewerModal from '../components/FileViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import OntologyModal from '../components/OntologyModal';
import FinancialAnalystModal from '../components/FinancialAnalystModal';
import { DocumentSelector } from '../components/DocumentSelector';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertCircle,
  ShieldCheck,
  Loader2,
  X,
  Save,
  Calendar,
  Activity,
  Lock,
  RefreshCw,
  Trash2,
  AlertTriangle,
  FileText,
  Shield,
  Swords,
  Gavel,
  Network,
  Mic,
  Briefcase,
  Scale
} from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';
import DockedPDFViewer from '../components/DockedPDFViewer';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

type CaseData = { details: Case | null };
type ActiveModal = 'none' | 'analysis' | 'ontology' | 'analyst';
type EvidenceSubTab = 'documents' | 'audio';

// BULLETPROOF CHAT HISTORY NORMALIZER
const extractAndNormalizeHistory = (data: any): ChatMessage[] => {
  if (!data) return [];
  const rawArray = data.chat_history || data.chatHistory || data.history || data.messages || [];
  if (!Array.isArray(rawArray)) return [];

  return rawArray
    .map((item: any) => {
      if (!item) return null;

      const rawRole = (item.role || item.sender || item.author || 'user').toString().toLowerCase();
      const role: 'user' | 'ai' =
        rawRole.includes('ai') || rawRole.includes('assistant') || rawRole.includes('system') ? 'ai' : 'user';

      let contentStr = '';
      if (typeof item.content === 'string') {
        contentStr = item.content;
      } else if (typeof item.message === 'string') {
        contentStr = item.message;
      } else if (typeof item.text === 'string') {
        contentStr = item.text;
      } else if (item.content && typeof item.content === 'object') {
        contentStr = item.content.text || item.content.message || JSON.stringify(item.content);
      } else {
        contentStr = safeString(item.content || item.message || item.text);
      }

      const timestamp = item.timestamp || item.created_at || new Date().toISOString();
      return { role, content: contentStr, timestamp };
    })
    .filter((msg): msg is ChatMessage => Boolean(msg && typeof msg.content === 'string' && msg.content.trim() !== ''));
};

const safeString = (val: any): string => {
  if (!val) return '';
  if (typeof val === 'string') return val;
  try {
    return JSON.stringify(val);
  } catch {
    return String(val);
  }
};

const getUserSalutation = (user: any): string => {
  if (!user) return 'Avokat';
  const rawName = (user.last_name || user.lastName || user.full_name || user.name || user.first_name || '').trim();
  const cleanName = rawName.replace(/[\(\)]/g, '').replace(/admin/gi, '').trim();
  
  if (!cleanName) return 'Avokat';
  const parts = cleanName.split(' ');
  const lastName = parts.length > 1 ? parts[parts.length - 1] : parts[0];
  
  return lastName ? `z. ${lastName}` : 'Avokat';
};

const RenameDocumentModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onRename: (newName: string) => Promise<void>;
  currentName: string;
  t: TFunction;
}> = ({ isOpen, onClose, onRename, currentName, t }) => {
  const [name, setName] = useState(currentName);
  const [isSaving, setIsSaving] = useState(false);

  useLockBodyScroll(isOpen);

  useEffect(() => {
    setName(currentName);
  }, [currentName]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSaving(true);
    try {
      await onRename(name);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200] p-4">
      <div className="bg-canvas w-full max-w-md p-6 sm:p-8 rounded-2xl shadow-2xl border border-main animate-in zoom-in-95">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-text-primary uppercase tracking-wider">{t('documentsPanel.renameTitle')}</h3>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-11 h-11 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-11 px-4 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all"
          />
          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="w-full sm:w-auto px-5 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-colors focus:outline-none"
            >
              {t('general.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-bold bg-primary-start hover:bg-opacity-90 text-white flex items-center justify-center gap-2 focus:outline-none shadow-lg shadow-primary-start/15"
            >
              {isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />} {t('general.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// TRI-PARTY ROLE SELECTION POPUP MODAL COMPONENT (DEFENDANT | PLAINTIFF | NEUTRAL)
const RoleSelectionModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSelectRole: (role: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL') => void;
}> = ({ isOpen, onClose, onSelectRole }) => {
  useLockBodyScroll(isOpen);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[300] p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        className="glass-panel w-full max-w-lg p-6 sm:p-8 rounded-3xl shadow-2xl border border-main bg-canvas"
      >
        <div className="flex justify-between items-center mb-6 border-b border-main pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
              <Gavel size={20} />
            </div>
            <div>
              <h3 className="text-lg font-black text-text-primary uppercase tracking-tight">Cilin Pozicion po Përfaqësoni?</h3>
              <p className="text-xs text-text-muted font-medium">Zgjidhni rolin e klientit për të përshtatur strategjinë AI</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-text-muted hover:text-text-primary transition-colors focus:outline-none">
            <X size={20} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 mb-6">
          <button
            type="button"
            onClick={() => onSelectRole('DEFENDANT')}
            className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-2xl text-left transition-all hover-lift focus:outline-none flex items-start gap-3.5 shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 group-hover:scale-110 transition-transform">
              <Shield size={22} />
            </div>
            <div>
              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide group-hover:text-primary-start transition-colors">
                🛡️ I Paditur / I Akuzuar (Mbrojtje)
              </h4>
              <p className="text-[11px] text-text-secondary leading-relaxed mt-0.5">
                Mbrojtja e palës që paditet. Strategjia fokusohet në prapësime, gabime procedurale dhe rrëzimin e pretendimeve.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectRole('PLAINTIFF')}
            className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-2xl text-left transition-all hover-lift focus:outline-none flex items-start gap-3.5 shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 group-hover:scale-110 transition-transform">
              <Swords size={22} />
            </div>
            <div>
              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide group-hover:text-primary-start transition-colors">
                ⚔️ Paditësi / I Dëmtuari (Sulm)
              </h4>
              <p className="text-[11px] text-text-secondary leading-relaxed mt-0.5">
                Përfaqësimi i palës që ngre padinë. Strategjia fokusohet në provimin e përgjegjësisë dhe forcat e padisë.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectRole('NEUTRAL')}
            className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-2xl text-left transition-all hover-lift focus:outline-none flex items-start gap-3.5 shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 group-hover:scale-110 transition-transform">
              <Scale size={22} />
            </div>
            <div>
              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide group-hover:text-primary-start transition-colors">
                ⚖️ Neutral / Analizë Objektive
              </h4>
              <p className="text-[11px] text-text-secondary leading-relaxed mt-0.5">
                Vlerësim i paanshëm ligjor (për Gjyqtarë, Arbitra ose Simuluar të Seancës). Peshon të dyja anët në mënyrë objektive.
              </p>
            </div>
          </button>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="w-full py-3 rounded-xl text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary bg-surface border border-main transition-colors focus:outline-none"
        >
          Anulo
        </button>
      </motion.div>
    </div>
  );
};

// EXECUTIVE CASE HERO HEADER COMPONENT
const CaseHeader: React.FC<{
  caseDetails: Case;
  documents: Document[];
  onOpenRoleModal: () => void;
  onRunAnalysis: (forceReanalyze?: boolean) => void;
  onViewExistingAnalysis: () => void;
  onOpenOntologyModal: () => void;
  onOpenAnalystModal: () => void;
  onClearAnalysis: () => void;
  isAnalyzing: boolean;
  isPro: boolean;
  isAdmin: boolean; // FEATURE GATE FLAG
  selectedDocumentIds: string[];
  onDocumentSelectionChange: (ids: string[]) => void;
}> = ({
  caseDetails,
  documents,
  onOpenRoleModal,
  onRunAnalysis,
  onViewExistingAnalysis,
  onOpenOntologyModal,
  onOpenAnalystModal,
  onClearAnalysis,
  isAnalyzing,
  isPro,
  isAdmin,
  selectedDocumentIds,
  onDocumentSelectionChange,
}) => {
  const hasExistingAnalysis = !!(caseDetails as any).latest_analysis && selectedDocumentIds.length === 0;
  const clientPosition = (caseDetails as any).client_position || 'DEFENDANT';

  const analyzeButtonText = isAnalyzing ? (
    <span className="flex items-center justify-center gap-1 sm:gap-2 min-w-0">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary-start shrink-0" />
      <span className="text-primary-start truncate text-[10px] sm:text-xs">ANALIZO...</span>
    </span>
  ) : selectedDocumentIds.length === 0 ? (
    <span className="flex items-center justify-center gap-1 sm:gap-2 min-w-0">
      <ShieldCheck size={14} className="text-primary-start shrink-0" />
      <span className="text-primary-start truncate text-[10px] sm:text-xs">ANALIZO RASTIN</span>
    </span>
  ) : (
    <span className="flex items-center justify-center gap-1 sm:gap-2 min-w-0">
      <ShieldCheck size={14} className="text-primary-start shrink-0" />
      <span className="text-primary-start truncate text-[10px] sm:text-xs">KRYQËZO</span>
    </span>
  );

  const buttonBase =
    'h-10 sm:h-11 flex items-center justify-center gap-1.5 sm:gap-2 px-2 sm:px-4 rounded-xl glass-panel bg-surface border border-main shadow-sm transition-all duration-200 hover:bg-hover text-[10px] sm:text-xs font-bold uppercase tracking-wider text-text-primary focus:outline-none';

  return (
    <motion.div
      className="relative mb-4 sm:mb-6 z-[30]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* TOP HERO BRANDING BAR */}
      <div className="bg-surface border border-main rounded-2xl p-3.5 sm:p-5 shadow-sm mb-3 sm:mb-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
        
        {/* Left: Case Info & Role Badge Switcher */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2.5 sm:p-3 bg-primary-start/10 text-primary-start border border-primary-start/20 rounded-2xl shrink-0">
            <Briefcase size={20} className="sm:w-5 sm:h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">
                {caseDetails.title || (caseDetails as any).name || 'Rast pa Titull'}
              </h1>
              
              <button
                type="button"
                onClick={onOpenRoleModal}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] sm:text-[10px] font-black uppercase tracking-wider border transition-all shadow-sm cursor-pointer ${
                  clientPosition === 'DEFENDANT'
                    ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 hover:bg-blue-500/20'
                    : clientPosition === 'PLAINTIFF'
                    ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30 hover:bg-purple-500/20'
                    : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                }`}
                title="Kliko për të ndryshuar pozicionin e klientit"
              >
                {clientPosition === 'DEFENDANT' ? <Shield size={11} /> : clientPosition === 'PLAINTIFF' ? <Swords size={11} /> : <Scale size={11} />}
                <span>{clientPosition === 'DEFENDANT' ? '🛡️ I PADITUR' : clientPosition === 'PLAINTIFF' ? '⚔️ PADITËSI' : '⚖️ NEUTRAL'}</span>
              </button>
            </div>

            <div className="flex items-center gap-2 sm:gap-3 text-[11px] sm:text-xs text-text-muted mt-0.5 sm:mt-1 font-medium">
              <span className="flex items-center gap-1">
                <Calendar size={12} className="text-primary-start/70" />
                {new Date(caseDetails.created_at).toLocaleDateString()}
              </span>
              <span>•</span>
              <span className="font-mono text-text-secondary">{documents.length} Dok</span>
            </div>
          </div>
        </div>

        {/* Right: Document Selector Dropdown */}
        <div className="w-full sm:w-64 z-[60]">
          <DocumentSelector
            documents={documents.map((d) => ({ id: d.id, file_name: d.file_name }))}
            selectedIds={selectedDocumentIds}
            onChange={onDocumentSelectionChange}
            disabled={!isPro}
          />
        </div>
      </div>

      {/* ADMIN-ONLY ACTION BUTTONS ROW (HIDDEN FOR NON-ADMIN USERS) */}
      {isAdmin && (
        <div className="grid grid-cols-3 gap-1.5 sm:gap-3 animate-in fade-in duration-200">
          
          {/* 1. ANALISTI FINANCIAR MODAL TRIGGER */}
          <button
            type="button"
            onClick={onOpenAnalystModal}
            disabled={!isPro}
            className={`${buttonBase} w-full ${!isPro && 'opacity-40 cursor-not-allowed'}`}
          >
            {!isPro ? (
              <Lock size={13} className="shrink-0 text-text-muted" />
            ) : (
              <Activity size={14} className="text-primary-start shrink-0" />
            )}
            <span className="truncate">FINANCAT</span>
          </button>

          {/* 2. ONTOLOGJIA MODAL TRIGGER */}
          <button
            type="button"
            onClick={onOpenOntologyModal}
            className={`${buttonBase} w-full hover:border-primary-start/80`}
          >
            <Network size={14} className="text-primary-start shrink-0" />
            <span className="truncate">ONTOLOGJIA</span>
          </button>

          {/* 3. DIRECT ANALYSIS TRIGGER */}
          <div className="w-full">
            {hasExistingAnalysis ? (
              <div className="h-10 sm:h-11 flex items-center justify-between rounded-xl glass-panel bg-surface border border-main shadow-sm text-[10px] sm:text-xs font-bold uppercase tracking-wider text-text-primary overflow-hidden w-full">
                <button
                  type="button"
                  onClick={onViewExistingAnalysis}
                  disabled={isAnalyzing}
                  className="flex-1 h-full flex items-center justify-center px-1.5 sm:px-3 hover:bg-hover hover:text-primary-start transition-all duration-200 focus:outline-none min-w-0"
                  title="Shiko Analizën ekzistuese"
                >
                  <span className="truncate text-primary-start font-bold">ANALIZA</span>
                </button>

                <div className="border-r border-main h-5 sm:h-6 shrink-0" />

                <button
                  type="button"
                  onClick={() => onRunAnalysis(true)}
                  disabled={isAnalyzing}
                  className="px-1.5 sm:px-2.5 h-full flex items-center justify-center hover:bg-hover hover:text-primary-start transition-all duration-200 focus:outline-none shrink-0"
                  title="Rianalizo sërish me AI"
                >
                  <RefreshCw size={13} className={`text-text-muted shrink-0 ${isAnalyzing ? 'animate-spin text-primary-start' : ''}`} />
                </button>

                <div className="border-r border-main h-5 sm:h-6 shrink-0" />

                <button
                  type="button"
                  onClick={onClearAnalysis}
                  disabled={isAnalyzing}
                  className="px-1.5 sm:px-2.5 h-full flex items-center justify-center hover:bg-hover hover:text-danger-start transition-all duration-200 focus:outline-none shrink-0"
                  title="Fshi analizën e ruajtur"
                >
                  <Trash2 size={13} className="text-text-muted hover:text-danger-start shrink-0" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onRunAnalysis(false)}
                disabled={!isPro || isAnalyzing}
                className={`${buttonBase} w-full disabled:opacity-40`}
              >
                {analyzeButtonText}
              </button>
            )}
          </div>

        </div>
      )}
    </motion.div>
  );
};

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
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [activeModal, setActiveModal] = useState<ActiveModal>('none');
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  // Evidence Vault Subtab State
  const [evidenceTab, setEvidenceTab] = useState<EvidenceSubTab>('documents');

  // Role Popup & Gatekeeper Notice state
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [gatekeeperNotice, setGatekeeperNotice] = useState<string | null>(null);

  const isPro = true;

  // ADMIN ROLE CHECK
  const isAdmin = useMemo(() => {
    if (!user) return false;
    const roleStr = (user.role || (user as any).user_type || '').toString().toUpperCase();
    const emailStr = (user.email || '').toString().toLowerCase();
    return roleStr === 'ADMIN' || (user as any).is_admin === true || emailStr.includes('admin') || emailStr.includes('shabanbala');
  }, [user]);

  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const userSalutation = useMemo(() => getUserSalutation(user), [user]);
  const clientPosition = useMemo(() => (caseData.details as any)?.client_position || 'DEFENDANT', [caseData.details]);

  const saveToLocalStorage = useCallback(
    (messages: ChatMessage[]) => {
      if (!caseId) return;
      localStorage.setItem(`chat_${caseId}`, JSON.stringify(messages));
    },
    [caseId]
  );

  const loadFromLocalStorage = useCallback((): ChatMessage[] | null => {
    if (!caseId) return null;
    const stored = localStorage.getItem(`chat_${caseId}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          return parsed.filter((m) => m && typeof m.content === 'string' && m.content.trim() !== '');
        }
      } catch {
        return null;
      }
    }
    return null;
  }, [caseId]);

  const persistChatHistory = useCallback(
    async (messages: ChatMessage[]) => {
      saveToLocalStorage(messages);
      if (!caseId) return;
      try {
        await apiService.updateChatHistory(caseId, messages);
      } catch (err) {
        console.error('Failed to persist chat history to backend:', err);
      }
    },
    [caseId, saveToLocalStorage]
  );

  const fetchCaseData = useCallback(
    async (isInitialLoad = false) => {
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

        if (details && (details as any).latest_analysis) {
          setAnalysisResult((details as any).latest_analysis);
        }

        const backendMessages = extractAndNormalizeHistory(details);
        if (backendMessages.length > 0) {
          setChatMessages(backendMessages);
          saveToLocalStorage(backendMessages);
        } else {
          const localMessages = loadFromLocalStorage();
          if (localMessages && localMessages.length > 0) {
            setChatMessages(localMessages);
            persistChatHistory(localMessages);
          } else {
            setChatMessages([]);
          }
        }
      } catch {
        setError(t('error.failedToLoadCase'));
      } finally {
        if (isInitialLoad) setIsLoading(false);
      }
    },
    [caseId, t, setLiveDocuments, loadFromLocalStorage, saveToLocalStorage, persistChatHistory]
  );

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);

  const handleDocumentUploaded = (newDoc: Document) => {
    setLiveDocuments((p) => [sanitizeDocument(newDoc), ...p]);
  };
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    setLiveDocuments((p) => p.filter((d) => String(d.id) !== String(response.documentId)));
  };

  const handleClearChat = async () => {
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
      setChatMessages([]);
      await persistChatHistory([]);
      localStorage.removeItem(`chat_${caseId}`);
    } catch {
      alert(t('error.generic'));
    }
  };

  const handleClearAnalysis = async () => {
    if (!caseId) return;
    try {
      await apiService.clearCaseAnalysis(caseId);
      setAnalysisResult(null);
      setCaseData((prev) => (prev.details ? { details: { ...prev.details, latest_analysis: null } } : prev));
    } catch {
      alert(t('error.generic'));
    }
  };

  const handleRunAnalysis = async (force = false) => {
    if (!caseId) return;

    const existingAnalysis =
      caseData.details && (caseData.details as any).latest_analysis
        ? (caseData.details as any).latest_analysis
        : analysisResult;

    if (force && existingAnalysis) {
      const lastDocIds: string[] = (existingAnalysis as any).analyzed_doc_ids || [];
      const currentDocIds: string[] = liveDocuments.map((d) => String(d.id)).sort();

      const isIdentical =
        lastDocIds.length > 0 &&
        lastDocIds.length === currentDocIds.length &&
        lastDocIds.slice().sort().every((id, idx) => id === currentDocIds[idx]);

      if (isIdentical) {
        setGatekeeperNotice(
          'Nuk ka ndryshime në dokumentet e rastit. Për të ekzekutuar një ri-analizë të re, kërkohet të shtohet një dokument i ri ose të fshihet një dokument ekzistues.'
        );
        return;
      }
    }

    setIsAnalyzing(true);
    setActiveModal('none');

    try {
      const activeRole = clientPosition || 'DEFENDANT';
      let result =
        selectedDocumentIds.length === 0
          ? await apiService.analyzeCase(caseId, activeRole)
          : await apiService.crossExamineDocument(caseId, selectedDocumentIds[0]);

      if (result.error) {
        alert(result.error);
      } else {
        const resultWithMeta = {
          ...result,
          analyzed_doc_ids: liveDocuments.map((d) => String(d.id)).sort(),
          client_position: activeRole,
        };

        setAnalysisResult(resultWithMeta);
        setActiveModal('analysis');
        setCaseData((prev) =>
          prev.details
            ? { details: { ...prev.details, client_position: activeRole, latest_analysis: resultWithMeta } }
            : prev
        );
      }
    } catch {
      alert(t('error.generic'));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRoleChosen = async (selectedRole: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL') => {
    if (!caseId) return;
    setShowRoleModal(false);

    setCaseData((prev) =>
      prev.details ? { details: { ...prev.details, client_position: selectedRole } } : prev
    );

    try {
      await apiService.updateCasePosition(caseId, selectedRole);
    } catch (e) {
      console.warn('Failed to persist position update:', e);
    }
  };

  const handleViewExistingAnalysis = () => {
    if (analysisResult || (caseData.details && (caseData.details as any).latest_analysis)) {
      setActiveModal('analysis');
    }
  };

  const handleChatSubmit = async (
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

      const enrichedText = `${text}\n\n(Ju lutem, në fund të përgjigjes suaj, shtoni një seksion të titulluar 'Sugjerime:' dhe rreshtoni saktësisht 3 pyetje të shkurtra vijuese që unë mund t'i bëj më pas in lidhje me këtë përgjigje. Formatizo si: \nSugjerime:\n1. Pyetja e parë?\n2. Pyetja e dytë?\n3. Pyetja e tretë?)`;

      const stream = apiService.sendChatMessageStream(
        caseId,
        enrichedText,
        documentIds,
        jurisdiction,
        reasoning,
        mode === 'document' ? domain : undefined
      );

      for await (const chunk of stream) {
        acc += chunk;
        setChatMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: acc };
          return updated;
        });
      }
      setChatMessages((prev) => {
        const finalMessages = [...prev];
        persistChatHistory(finalMessages);
        return finalMessages;
      });
    } catch {
      const errorMsg = '[Gabim Teknik]';
      setChatMessages((prev) => {
        const withError = [...prev];
        withError[withError.length - 1] = { ...withError[withError.length - 1], content: errorMsg };
        persistChatHistory(withError);
        return withError;
      });
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleViewOriginal = (doc: Document) => {
    setViewingUrl(`${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`);
    setViewingDocument(doc);
    setMinimizedDocument(null);
  };
  const handleRenameAction = async (newName: string) => {
    if (!caseId || !documentToRename) return;
    try {
      await apiService.renameDocument(caseId, documentToRename.id, newName);
      setLiveDocuments((p) => p.map((d) => (d.id === documentToRename.id ? { ...d, file_name: newName } : d)));
    } catch {
      alert(t('error.generic'));
    }
  };

  if (isAuthLoading || isLoading)
    return (
      <div className="flex items-center justify-center h-screen bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  if (error || !caseData.details)
    return (
      <div className="p-8 text-center text-danger border border-danger/30 rounded-2xl bg-danger/5 mt-20 max-w-lg mx-auto animate-pulse">
        <AlertCircle className="mx-auto h-12 w-12 mb-4" />
        <p className="font-bold uppercase tracking-wide">{error}</p>
      </div>
    );

  return (
    <motion.div className="w-full min-h-screen pb-12 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-8">
        
        {/* HERO EXECUTIVE HEADER WITH ADMIN FEATURE GATE */}
        <CaseHeader
          caseDetails={caseData.details}
          documents={liveDocuments}
          onOpenRoleModal={() => setShowRoleModal(true)}
          onRunAnalysis={handleRunAnalysis}
          onViewExistingAnalysis={handleViewExistingAnalysis}
          onOpenOntologyModal={() => setActiveModal('ontology')}
          onOpenAnalystModal={() => setActiveModal('analyst')}
          onClearAnalysis={handleClearAnalysis}
          isAnalyzing={isAnalyzing}
          isPro={isPro}
          isAdmin={isAdmin}
          selectedDocumentIds={selectedDocumentIds}
          onDocumentSelectionChange={setSelectedDocumentIds}
        />

        {/* WORKSPACE VIEW */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 z-0">
          
          {/* LEFT COLUMN: UNIFIED EVIDENCE VAULT PANEL */}
          <div className="lg:col-span-5 flex flex-col h-[520px] sm:h-[700px] bg-surface border border-main rounded-2xl overflow-hidden shadow-sm">
            
            {/* EVIDENCE VAULT SUB-HEADER SWITCHER */}
            <div className="p-2.5 sm:p-3 bg-canvas border-b border-main flex items-center justify-between gap-2">
              <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-main w-full">
                <button
                  type="button"
                  onClick={() => setEvidenceTab('documents')}
                  className={`flex-1 py-1.5 px-2.5 rounded-lg text-[11px] sm:text-xs font-extrabold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                    evidenceTab === 'documents'
                      ? 'bg-primary-start text-white shadow-sm'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  <FileText size={13} />
                  <span>Dokumentet ({liveDocuments.length})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setEvidenceTab('audio')}
                  className={`flex-1 py-1.5 px-2.5 rounded-lg text-[11px] sm:text-xs font-extrabold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                    evidenceTab === 'audio'
                      ? 'bg-primary-start text-white shadow-sm'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  <Mic size={13} />
                  <span>Inqizimet Audio</span>
                </button>
              </div>
            </div>

            {/* SUBTAB CONTENT BODY */}
            <div className="flex-1 overflow-hidden relative">
              {evidenceTab === 'documents' ? (
                <DocumentsPanel
                  caseId={caseData.details.id}
                  documents={liveDocuments}
                  t={t}
                  connectionStatus={connectionStatus}
                  reconnect={reconnect}
                  onDocumentUploaded={handleDocumentUploaded}
                  onDocumentDeleted={handleDocumentDeleted}
                  onViewOriginal={handleViewOriginal}
                  onRename={setDocumentToRename}
                  className="h-full w-full bg-transparent border-0 rounded-none"
                />
              ) : (
                <div className="h-full overflow-y-auto p-3 sm:p-4">
                  <MediaEvidencePanel caseId={caseData.details.id} t={t} />
                </div>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: AGJENTI I RASTIT */}
          <div className="lg:col-span-7 flex flex-col h-[540px] sm:h-[700px] bg-surface border border-main rounded-2xl overflow-hidden shadow-sm relative">
            <ChatPanel
              messages={chatMessages}
              connectionStatus={connectionStatus}
              reconnect={reconnect}
              onSendMessage={handleChatSubmit}
              isSendingMessage={isSendingMessage}
              onClearChat={handleClearChat}
              t={t}
              className="h-full w-full bg-transparent border-0 rounded-none"
              activeContextId={currentCaseId}
              isPro={isPro}
              selectedDocumentCount={selectedDocumentIds.length}
              userSalutation={userSalutation}
              clientPosition={clientPosition}
            />
          </div>

        </div>
      </div>

      {/* DOCUMENT PREVIEW MODAL */}
      {viewingDocument && (
        <PDFViewerModal
          documentData={viewingDocument}
          caseId={caseData.details.id}
          onClose={() => {
            setViewingDocument(null);
            setViewingUrl(null);
          }}
          onMinimize={() => {
            if (viewingDocument) {
              setMinimizedDocument(viewingDocument);
              setViewingDocument(null);
            }
          }}
          t={t}
          directUrl={viewingUrl}
          isAuth={true}
        />
      )}
      {minimizedDocument && (
        <DockedPDFViewer
          document={minimizedDocument}
          onExpand={() => handleViewOriginal(minimizedDocument)}
          onClose={() => setMinimizedDocument(null)}
        />
      )}

      {/* 1. CASE ANALYSIS MODAL (ADMIN ONLY) */}
      {isAdmin && analysisResult && (
        <AnalysisModal
          isOpen={activeModal === 'analysis'}
          onClose={() => setActiveModal('none')}
          result={analysisResult}
          caseId={currentCaseId}
          isLoading={isAnalyzing}
        />
      )}

      {/* 2. ONTOLOGY GRAPH MODAL (ADMIN ONLY) */}
      {isAdmin && (
        <OntologyModal
          isOpen={activeModal === 'ontology'}
          onClose={() => setActiveModal('none')}
          caseId={currentCaseId}
          caseTitle={caseData.details?.title || (caseData.details as any)?.name}
          clientPosition={clientPosition}
        />
      )}

      {/* 3. FINANCIAL ANALYST MODAL (ADMIN ONLY) */}
      {isAdmin && (
        <FinancialAnalystModal
          isOpen={activeModal === 'analyst'}
          onClose={() => setActiveModal('none')}
          caseId={currentCaseId}
          caseTitle={caseData.details?.title || (caseData.details as any)?.name}
        />
      )}

      <RenameDocumentModal
        isOpen={!!documentToRename}
        onClose={() => setDocumentToRename(null)}
        onRename={handleRenameAction}
        currentName={documentToRename?.file_name || ''}
        t={t}
      />

      {/* ROLE SELECTION POPUP MODAL */}
      <RoleSelectionModal
        isOpen={showRoleModal}
        onClose={() => setShowRoleModal(false)}
        onSelectRole={handleRoleChosen}
      />

      {/* RE-ANALYSIS GATEKEEPER NOTIFICATION MODAL */}
      <AnimatePresence>
        {gatekeeperNotice && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[300] p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="glass-panel w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl border border-warning-start/30 bg-canvas text-center text-text-primary"
            >
              <div className="w-14 h-14 bg-warning-start/15 border border-warning-start/30 rounded-2xl flex items-center justify-center mx-auto mb-5 text-warning-start">
                <AlertTriangle size={28} />
              </div>

              <h3 className="text-lg sm:text-xl font-bold uppercase tracking-tight mb-3">
                S'ka Ndryshime në Lëndë
              </h3>

              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium mb-6">
                {gatekeeperNotice}
              </p>

              <div className="p-3.5 bg-surface border border-main rounded-xl text-[11px] text-text-muted flex items-center gap-2 font-mono mb-6 justify-center">
                <FileText size={14} className="text-primary-start shrink-0" />
                <span>Dokumente Aktive: {liveDocuments.length}</span>
              </div>

              <button
                type="button"
                onClick={() => setGatekeeperNotice(null)}
                className="btn-primary w-full h-11 rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-primary-start/15 focus:outline-none"
              >
                E Kuptova
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default CaseViewPage;