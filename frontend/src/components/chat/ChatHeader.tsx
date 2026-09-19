// FILE: src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V43.0 (SINGLE CIRCULAR PROGRESS)
// V43.0: Hequr progress bar-in majtas. Butoni djathtas është i vetmi tregues progresi.
//        Shtuar faza (phase label) si tooltip.
// V42.0: Circular progress + përqindje.

import React, { useEffect, useState } from 'react';
import { Download, Trash2, FileText, Maximize2, Minimize2, Sparkles } from 'lucide-react';
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
  isAuditGenerating?: boolean;
  auditProgressText?: string;
  auditProgressPercent?: number;
  auditPhaseLabel?: string;
  auditStartTime?: number | null;
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
  auditProgressPercent = 0,
  auditPhaseLabel = '',
  auditStartTime = null,
}) => {
  const hasSelectedDoc = !!selectedDocName && selectedDocName.trim().length > 0;
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isAuditGenerating || !auditStartTime) {
      setElapsed(0);
      return;
    }
    setElapsed(Math.floor((Date.now() - auditStartTime) / 1000));
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - auditStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isAuditGenerating, auditStartTime]);

  const formatElapsed = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const safePercent = Math.min(100, Math.max(0, Math.round(auditProgressPercent)));

  // Circular progress parameters
  const ringRadius = 7;
  const ringCircumference = 2 * Math.PI * ringRadius;
  const ringOffset = ringCircumference * (1 - safePercent / 100);

  return (
    <div className="flex flex-row items-center justify-between px-3 sm:px-5 py-2.5 border-b border-main bg-surface z-30 shrink-0 h-13 min-h-[52px] w-full gap-2 select-none shadow-xs">
      {/* 1. MAJTAS: LED + Emri i dokumentit / Statusi */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
            connectionStatus === 'CONNECTED'
              ? 'bg-success-start shadow-md shadow-success-start/50 animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
          title={connectionStatus === 'CONNECTED' ? 'Lidhja aktive' : 'Lidhja e shkëputur'}
        />

        {isAuditGenerating ? (
          // V43.0: Vetëm teksti i fazës — pa progress bar
          <span
            className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-primary-start/10 border border-primary-start/30 text-[11px] font-bold text-primary-start max-w-[180px] sm:max-w-[400px] truncate"
            title={auditPhaseLabel || 'Duke analizuar...'}
          >
            <span className="truncate">{auditPhaseLabel || 'Duke analizuar...'}</span>
            <span className="text-[10px] font-mono text-primary-start/70 shrink-0">
              {formatElapsed(elapsed)}
            </span>
          </span>
        ) : selectedDocName ? (
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-main text-[11px] font-medium text-text-secondary max-w-[180px] sm:max-w-[300px] truncate"
            title={`Shkresa aktive: ${selectedDocName}`}
          >
            <FileText size={12} className="text-primary-start shrink-0" />
            <span className="truncate">{selectedDocName}</span>
          </span>
        ) : (
          <span className="text-xs font-bold text-text-muted hidden sm:inline">
            Biseda e Lëndës
          </span>
        )}
      </div>

      {/* 2. DJATHTAS: Butoni dinamik me circular progress, Fullscreen, Eksporti, Koshi */}
      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0 ml-auto">

        {/* V43.0: Butoni Dinamik me circular progress */}
        {onAnalyzeDocument && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            disabled={isAuditGenerating}
            className={`h-8 px-2 sm:px-3 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all whitespace-nowrap focus:outline-none border cursor-pointer mr-1 ${
              isAuditGenerating
                ? 'bg-primary-start/15 border-primary-start/30 text-primary-start cursor-wait'
                : 'bg-surface hover:bg-hover text-primary-start hover:text-primary-end border-main hover:border-primary-start/40'
            }`}
            title={
              isAuditGenerating
                ? `Duke analizuar... ${safePercent}% — ${auditPhaseLabel || ''}`
                : hasSelectedDoc
                  ? `Kryej pasqyrën e shkresës: ${selectedDocName}`
                  : `Kryej doktrinën e rastit të plotë (të gjitha shkresat)`
            }
          >
            {isAuditGenerating ? (
              // V43.0: Circular progress + përqindje
              <>
                <svg
                  className="w-4 h-4 shrink-0 -rotate-90"
                  viewBox="0 0 20 20"
                  fill="none"
                >
                  <circle
                    cx="10"
                    cy="10"
                    r={ringRadius}
                    stroke="currentColor"
                    strokeWidth="2"
                    className="opacity-20"
                  />
                  <circle
                    cx="10"
                    cy="10"
                    r={ringRadius}
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeDasharray={ringCircumference}
                    strokeDashoffset={ringOffset}
                    className="transition-all duration-300 ease-out"
                  />
                </svg>
                <span className="tabular-nums font-black text-[11px] min-w-[28px] text-right">
                  {safePercent}%
                </span>
              </>
            ) : hasSelectedDoc ? (
              <>
                <FileText size={12} className="shrink-0 text-primary-start" />
                <span className="hidden sm:inline">Analizo Dokumentin</span>
                <span className="sm:hidden">Analizo</span>
              </>
            ) : (
              <>
                <Sparkles size={12} className="shrink-0 text-primary-start" />
                <span className="hidden sm:inline">Analizo Rastin</span>
                <span className="sm:hidden">Rast</span>
              </>
            )}
          </button>
        )}

        {/* Fullscreen toggle */}
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
            {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        )}

        {/* Export */}
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

        {/* Clear */}
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