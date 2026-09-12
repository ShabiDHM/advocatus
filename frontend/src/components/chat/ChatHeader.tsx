// FILE: src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V34.0 (ICON-ONLY CLEAN EXPAND/MINIMIZE)
// ZERO TS WARNINGS • RESPONSIVE PINNED ACTIONS • 100% COMPLETE CODE

import React from 'react';
import { Download, Trash2, FileText, Maximize2, Minimize2 } from 'lucide-react';
import { TFunction } from 'i18next';

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId?: string;
  onClearChat: () => void;
  onExportChat?: () => void;
  t?: TFunction;
  isPro?: boolean;
  onAnalyzeDocument?: () => void;
  selectedDocName?: string;
  documents?: any[];
  selectedDocumentIds?: string[];
  onDocumentSelectionChange?: (ids: string[]) => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  connectionStatus,
  onClearChat,
  onExportChat,
  onAnalyzeDocument,
  selectedDocName,
  isFullscreen = false,
  onToggleFullscreen,
}) => {
  return (
    <div className="flex flex-row items-center justify-between px-3 sm:px-5 py-2.5 border-b border-main bg-surface z-30 shrink-0 h-13 min-h-[52px] w-full gap-2 select-none shadow-xs">
      {/* 1. MAJTAS: Drita LED e Statusit dhe Emri i Dokumentit Aktiv */}
      <div className="flex items-center gap-2 shrink-0">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
            connectionStatus === 'CONNECTED'
              ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
          title={connectionStatus === 'CONNECTED' ? 'Lidhja aktive me DeepSeek' : 'Lidhja e shkëputur'}
        />
        {selectedDocName ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-main text-[11px] font-medium text-text-secondary max-w-[180px] sm:max-w-[300px] truncate" title={`Shkresa aktive: ${selectedDocName}`}>
            <FileText size={12} className="text-primary-start shrink-0" />
            <span className="truncate">{selectedDocName}</span>
          </span>
        ) : (
          <span className="text-xs font-bold text-text-muted hidden sm:inline">
            Biseda e Lëndës
          </span>
        )}
      </div>

      {/* 2. DJATHTAS: Butoni 'Analizo Dokumentin', Ikona Zgjero/Zvogëlo, Eksporti dhe Koshi */}
      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0 ml-auto">
        
        {/* Butoni: Analizo Dokumentin */}
        {onAnalyzeDocument && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            className="h-8 px-2.5 sm:px-3.5 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none bg-surface hover:bg-hover text-primary-start hover:text-primary-end border border-main hover:border-primary-start/40 cursor-pointer mr-1"
            title={selectedDocName ? `Kryej pasqyrën e shkresës: ${selectedDocName}` : 'Klikoni mbi një shkresë në listën majtas për ta analizuar'}
          >
            <FileText size={12} className="shrink-0 text-primary-start" />
            <span className="hidden sm:inline">Analizo Dokumentin</span>
            <span className="sm:hidden">Analizo</span>
          </button>
        )}

        {/* BUTONI VETËM ME IKONË: ZGJERO / ZVOGËLO (PA TEKST) */}
        {onToggleFullscreen && (
          <button
            type="button"
            onClick={onToggleFullscreen}
            className={`flex items-center justify-center w-8 h-8 shrink-0 rounded-lg transition-all focus:outline-none cursor-pointer ${
              isFullscreen
                ? 'bg-primary-start text-white hover:bg-primary-start/90 shadow-xs'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
            title={isFullscreen ? "Zvogëlo dritaren (ESC)" : "Zgjero dritaren"}
            aria-label={isFullscreen ? "Zvogëlo dritaren" : "Zgjero dritaren"}
          >
            {isFullscreen ? (
              <Minimize2 size={15} />
            ) : (
              <Maximize2 size={15} />
            )}
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