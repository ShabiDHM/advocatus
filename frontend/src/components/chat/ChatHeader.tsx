// FILE: src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V40.0 (BACKGROUND AUDIT BUTTON)
// V40.0: Butoni "Analizo" shfaq spinner + status gjatë gjenerimit background.
// V39.0: Fix — tab character brenda var(--status-success).

import React from 'react';
import { Download, Trash2, FileText, Maximize2, Minimize2, Sparkles, Loader2 } from 'lucide-react';
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
  // V40.0: Background generation state
  isAuditGenerating?: boolean;
  auditProgressText?: string;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  connectionStatus,
  onClearChat,
  onExportChat,
  onAnalyzeDocument,
  selectedDocName,
  isFullscreen = false,
  onToggleFullscreen,
  isAuditGenerating = false,
  auditProgressText = '',
}) => {
  const hasSelectedDoc = !!selectedDocName && selectedDocName.trim().length > 0;

  return (
    <div className="flex flex-row items-center justify-between px-3 sm:px-5 py-2.5 border-b border-main bg-surface z-30 shrink-0 h-13 min-h-[52px] w-full gap-2 select-none shadow-xs">
      {/* 1. MAJTAS: Drita LED + Emri i Dokumentit / Statusi i gjenerimit */}
      <div className="flex items-center gap-2 shrink-0 min-w-0">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
            connectionStatus === 'CONNECTED'
              ? 'bg-success-start shadow-md shadow-success-start/50 animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
          title={connectionStatus === 'CONNECTED' ? 'Lidhja aktive' : 'Lidhja e shkëputur'}
        />

        {isAuditGenerating ? (
          <span className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-primary-start/10 border border-primary-start/30 text-[11px] font-bold text-primary-start max-w-[260px] sm:max-w-[400px] truncate animate-pulse">
            <Loader2 size={12} className="animate-spin shrink-0" />
            <span className="truncate">{auditProgressText || 'Duke analizuar...'}</span>
          </span>
        ) : selectedDocName ? (
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

      {/* 2. DJATHTAS: Butoni dinamik, Fullscreen, Eksporti, Koshi */}
      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0 ml-auto">

        {/* Butoni Dinamik: Analizo Rastin / Analizo Dokumentin */}
        {onAnalyzeDocument && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            disabled={isAuditGenerating}
            className={`h-8 px-2.5 sm:px-3.5 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none border cursor-pointer mr-1 ${
              isAuditGenerating
                ? 'bg-primary-start/15 border-primary-start/30 text-primary-start cursor-wait'
                : 'bg-surface hover:bg-hover text-primary-start hover:text-primary-end border-main hover:border-primary-start/40'
            }`}
            title={
              isAuditGenerating
                ? 'Analiza është në progres...'
                : hasSelectedDoc
                  ? `Kryej pasqyrën e shkresës: ${selectedDocName}`
                  : `Kryej doktrinën e rastit të plotë (të gjitha shkresat)`
            }
          >
            {isAuditGenerating ? (
              <Loader2 size={12} className="shrink-0 animate-spin" />
            ) : hasSelectedDoc ? (
              <FileText size={12} className="shrink-0 text-primary-start" />
            ) : (
              <Sparkles size={12} className="shrink-0 text-primary-start" />
            )}
            <span className="hidden sm:inline">
              {isAuditGenerating
                ? 'Duke analizuar...'
                : hasSelectedDoc
                  ? 'Analizo Dokumentin'
                  : 'Analizo Rastin'}
            </span>
            <span className="sm:hidden">
              {isAuditGenerating ? '...' : hasSelectedDoc ? 'Analizo' : 'Rast'}
            </span>
          </button>
        )}

        {/* BUTONI VETËM ME IKONË: ZGJERO / ZVOGËLO */}
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
          className="flex items-center justify-center w-8 h-8 shrink-0 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-lg transition-all focus:outline-none cursor-pointer"
          title="Pastro Bisedën"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;