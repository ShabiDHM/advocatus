// FILE: frontend/src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V27.0 (PURE MINIMALIST LED STATUS & SYMMETRICAL AUTOPSY PAIR)
// ZERO TS WARNINGS • NO TEXT ON LEFT • SUBTLE OUTLINED BUTTONS • 100% COMPLETE CODE

import React from 'react';
import { Download, Trash2, Loader2, RefreshCw } from 'lucide-react';
import { TFunction } from 'i18next';

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId: string;
  onClearChat: () => void;
  onExportChat?: () => void;
  t: TFunction;
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
    <div className="flex flex-row items-center justify-between px-3.5 sm:px-5 py-2.5 border-b border-main bg-surface z-50 shrink-0 h-13 min-h-[52px] select-none">
      {/* Left: Vetëm Drita LED e Statusit në të Majtë (Pa Tekst) */}
      <div className="flex items-center justify-center shrink-0">
        <span
          className={`w-2.5 h-2.5 rounded-full ${
            connectionStatus === 'CONNECTED'
              ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
          title={connectionStatus === 'CONNECTED' ? 'I lidhur' : 'Shkëputur'}
        />
      </div>

      {/* Right: Dy Butonat Minimalë e Elegantë */}
      <div className="flex items-center justify-end gap-2 shrink-0">
        {/* BUTONI 1: AUTOPSIA E RASTIT */}
        {onAnalyzeCase && (
          <button
            type="button"
            onClick={onAnalyzeCase}
            disabled={isAnalyzingCase}
            className={`h-8 px-3.5 rounded-xl font-bold text-[11px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none hover-lift active:scale-95 cursor-pointer border ${
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
                <Loader2 size={13} className="animate-spin shrink-0 text-primary-start" />
                <span className="font-bold whitespace-nowrap">Duke analizuar...</span>
              </>
            ) : isAnalysisDirty ? (
              <>
                <RefreshCw size={13} className="animate-spin shrink-0 text-amber-500" />
                <span className="font-bold whitespace-nowrap">Përditëso Rastin</span>
              </>
            ) : (
              <span>Autopsia e Rastit</span>
            )}
          </button>
        )}

        {/* BUTONI 2: AUTOPSIA E DOKUMENTIT */}
        {onAnalyzeDocument && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            className="h-8 px-3.5 rounded-xl font-bold text-[11px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none hover-lift active:scale-95 bg-surface hover:bg-hover text-primary-start hover:text-primary-end border border-main hover:border-primary-start/40 cursor-pointer"
            title={selectedDocName ? `Kryej autopsinë e shkresës: ${selectedDocName}` : "Përzgjidhni një shkresë majtas për autopsi"}
          >
            <span>Autopsia e Dokumentit</span>
          </button>
        )}

        {onExportChat && (
          <button
            type="button"
            onClick={onExportChat}
            className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-primary-start hover:bg-hover rounded-lg transition-all focus:outline-none cursor-pointer ml-1"
            title="Shkarko Bisedën"
          >
            <Download size={15} />
          </button>
        )}

        <button
          type="button"
          onClick={onClearChat}
          className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-lg transition-all focus:outline-none cursor-pointer"
          title="Pastro Bisedën"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;