// FILE: frontend/src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V28.0 (RESPONSIVE ACTION PINNING & UNIVERSAL PAGE/DOC SELECTOR)
// ZERO TS WARNINGS • VISIBLE TRASH & ACTIONS • 100% COMPLETE CODE

import React from 'react';
import { Download, Trash2, Loader2, RefreshCw, FileText, Sparkles } from 'lucide-react';
import { TFunction } from 'i18next';

interface DocumentItem {
  id: string;
  name?: string;
  title?: string;
  page_count?: number;
  [key: string]: any;
}

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId?: string;
  onClearChat: () => void;
  onExportChat?: () => void;
  t?: TFunction;
  isPro?: boolean;
  onAnalyzeCase?: () => void;
  onAnalyzeDocument?: () => void;
  selectedDocName?: string;
  isAnalyzingCase?: boolean;
  isAnalysisDirty?: boolean;
  hasExistingAnalysis?: boolean;
  documents?: DocumentItem[];
  selectedDocumentIds?: string[];
  onDocumentSelectionChange?: (ids: string[]) => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  connectionStatus,
  onClearChat,
  onExportChat,
  onAnalyzeCase,
  onAnalyzeDocument,
  selectedDocName,
  isAnalyzingCase = false,
  isAnalysisDirty = false,
  documents = [],
  selectedDocumentIds = [],
  onDocumentSelectionChange,
}) => {
  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!onDocumentSelectionChange) return;
    const val = e.target.value;
    if (!val) {
      onDocumentSelectionChange([]);
    } else {
      onDocumentSelectionChange([val]);
    }
  };

  return (
    <div className="flex flex-row items-center justify-between px-3 sm:px-4 py-2 border-b border-main bg-surface z-30 shrink-0 h-13 min-h-[52px] w-full gap-2 select-none overflow-x-hidden">
      {/* 1. MAJTAS: Drita LED dhe Selektori Dinamik i Dokumentit/Faqes (nëse ekzistojnë dokumente) */}
      <div className="flex items-center gap-2 min-w-0 shrink">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
            connectionStatus === 'CONNECTED'
              ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
          title={connectionStatus === 'CONNECTED' ? 'Lidhja aktive' : 'Lidhja e shkëputur'}
        />

        {documents && documents.length > 0 && onDocumentSelectionChange && (
          <div className="relative flex items-center min-w-0 max-w-[140px] sm:max-w-[180px]">
            <FileText size={12} className="absolute left-2 text-text-muted pointer-events-none shrink-0" />
            <select
              value={selectedDocumentIds[0] || ''}
              onChange={handleSelectChange}
              className="w-full pl-6 pr-2 py-1 text-[11px] font-medium rounded-lg border border-main bg-hover text-text truncate focus:outline-none focus:border-primary-start cursor-pointer"
              title="Përzgjidh dokumentin/faqen për analizë"
            >
              <option value="">I gjithë fashikulli</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.name || doc.title || `Dokumenti ${doc.id.slice(-4)}`}
                  {doc.page_count ? ` (${doc.page_count} fq)` : ''}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 2. DJATHAS: Butonat e Autopsisë (elastikë) dhe Veprimet Kryesore (Koshi & Shkarkimi të palëvizshëm) */}
      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 ml-auto">
        {/* Butoni 1: Autopsia e Rastit */}
        {onAnalyzeCase && (
          <button
            type="button"
            onClick={onAnalyzeCase}
            disabled={isAnalyzingCase}
            className={`h-8 px-2 sm:px-3 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1 transition-all whitespace-nowrap focus:outline-none cursor-pointer border ${
              isAnalyzingCase
                ? 'bg-surface text-primary-start border-primary-start/30 opacity-80'
                : isAnalysisDirty
                ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 border-amber-500/30 animate-pulse'
                : 'bg-surface hover:bg-hover text-primary-start hover:text-primary-end border-main hover:border-primary-start/40'
            }`}
            title="Kryej autopsinë e thellë forenzike për të gjithë fashikullin e lëndës"
          >
            {isAnalyzingCase ? (
              <>
                <Loader2 size={12} className="animate-spin shrink-0 text-primary-start" />
                <span className="hidden sm:inline">Duke analizuar...</span>
              </>
            ) : isAnalysisDirty ? (
              <>
                <RefreshCw size={12} className="animate-spin shrink-0 text-amber-500" />
                <span>Përditëso</span>
              </>
            ) : (
              <>
                <Sparkles size={12} className="shrink-0 hidden xs:inline" />
                <span>Autopsia e Rastit</span>
              </>
            )}
          </button>
        )}

        {/* Butoni 2: Autopsia e Dokumentit */}
        {onAnalyzeDocument && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            className="h-8 px-2 sm:px-3 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1 transition-all whitespace-nowrap focus:outline-none bg-surface hover:bg-hover text-primary-start hover:text-primary-end border border-main hover:border-primary-start/40 cursor-pointer"
            title={selectedDocName ? `Kryej autopsinë e shkresës: ${selectedDocName}` : 'Përzgjidhni një shkresë majtas për autopsi'}
          >
            <FileText size={12} className="shrink-0 hidden xs:inline" />
            <span className="hidden sm:inline">Autopsia e Dokumentit</span>
            <span className="sm:hidden">Dokumenti</span>
          </button>
        )}

        {/* Butoni: Shkarko Bisedën (Pin-uar, nuk shtyhet kurrë jashtë) */}
        {onExportChat && (
          <button
            type="button"
            onClick={onExportChat}
            className="flex items-center justify-center w-8 h-8 shrink-0 text-text-muted hover:text-primary-start hover:bg-hover rounded-lg transition-all focus:outline-none cursor-pointer"
            title="Shkarko Bisedën"
          >
            <Download size={15} />
          </button>
        )}

        {/* Butoni: Pastro Bisedën / Koshi (Pin-uar me prioritet të lartë) */}
        <button
          type="button"
          onClick={onClearChat}
          className="flex items-center justify-center w-8 h-8 shrink-0 text-text-muted hover:text-rose-500 hover:bg-rose-500/10 rounded-lg transition-all focus:outline-none cursor-pointer"
          title="Pastro Bisedën"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;