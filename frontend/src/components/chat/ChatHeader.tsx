// FILE: frontend/src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V30.0 (PURE MINIMALIST ACTIONS • NO DROPDOWN CLUTTER)
// ZERO TS WARNINGS • RESPONSIVE PINNED ACTIONS • 100% COMPLETE CODE

import React from 'react';
import { Download, Trash2, Loader2, RefreshCw, FileText, Sparkles } from 'lucide-react';
import { TFunction } from 'i18next';

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
  documents?: any[];
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
}) => {
  return (
    <div className="flex flex-row items-center justify-between px-3 sm:px-5 py-2.5 border-b border-main bg-surface z-30 shrink-0 h-13 min-h-[52px] w-full gap-2 select-none">
      {/* 1. MAJTAS: Vetëm Drita LED e Statusit (Pastërti Absolute) */}
      <div className="flex items-center gap-2 shrink-0">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
            connectionStatus === 'CONNECTED'
              ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
          title={connectionStatus === 'CONNECTED' ? 'Lidhja aktive' : 'Lidhja e shkëputur'}
        />
        {selectedDocName && (
          <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-main text-[11px] font-medium text-text-secondary max-w-[220px] truncate" title={`Shkresa aktive: ${selectedDocName}`}>
            <FileText size={12} className="text-primary-start shrink-0" />
            <span className="truncate">{selectedDocName}</span>
          </span>
        )}
      </div>

      {/* 2. DJATHAS: Butonat e Pastër dhe të Kyçur */}
      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 ml-auto">
        {/* Butoni 1: Analizo Rastin */}
        {onAnalyzeCase && (
          <button
            type="button"
            onClick={onAnalyzeCase}
            disabled={isAnalyzingCase}
            className={`h-8 px-2.5 sm:px-3.5 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none cursor-pointer border ${
              isAnalyzingCase
                ? 'bg-surface text-primary-start border-primary-start/30 opacity-80'
                : isAnalysisDirty
                ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 border-amber-500/30'
                : 'bg-surface hover:bg-hover text-primary-start hover:text-primary-end border-main hover:border-primary-start/40'
            }`}
            title="Kryej pasqyrën e shpejtë të të gjithë fashikullit të lëndës"
          >
            {isAnalyzingCase ? (
              <>
                <Loader2 size={12} className="animate-spin shrink-0 text-primary-start" />
                <span className="hidden sm:inline">Duke analizuar...</span>
              </>
            ) : isAnalysisDirty ? (
              <>
                <RefreshCw size={12} className="shrink-0 text-amber-500" />
                <span>Përditëso Rastin</span>
              </>
            ) : (
              <>
                <Sparkles size={12} className="shrink-0 text-primary-start" />
                <span>Analizo Rastin</span>
              </>
            )}
          </button>
        )}

        {/* Butoni 2: Analizo Dokumentin */}
        {onAnalyzeDocument && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            className="h-8 px-2.5 sm:px-3.5 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none bg-surface hover:bg-hover text-primary-start hover:text-primary-end border border-main hover:border-primary-start/40 cursor-pointer"
            title={selectedDocName ? `Kryej pasqyrën e shkresës: ${selectedDocName}` : 'Klikoni mbi një shkresë në listën majtas për ta analizuar'}
          >
            <FileText size={12} className="shrink-0 text-primary-start" />
            <span className="hidden sm:inline">Analizo Dokumentin</span>
            <span className="sm:hidden">Dokumenti</span>
          </button>
        )}

        {/* Butoni: Shkarko Bisedën */}
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

        {/* Butoni: Pastro Bisedën (Koshi) */}
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