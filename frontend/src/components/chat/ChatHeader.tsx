// FILE: frontend/src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V23.0 (DYNAMIC "PËRDITËSO ANALIZËN" STATUS ENGINE)
// ZERO TS WARNINGS • DYNAMIC BUTTON STATES (DIRTY / CACHED / INITIAL)

import React from 'react';
import { Download, Trash2, FileSearch, Loader2, RefreshCw } from 'lucide-react';
import { TFunction } from 'i18next';

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId: string;
  onClearChat: () => void;
  onExportChat?: () => void;
  t: TFunction;
  isPro?: boolean;
  onAnalyzeCase?: () => void;
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
  t,
  onAnalyzeCase,
  isAnalyzingCase = false,
  isAnalysisDirty = false,
  hasExistingAnalysis = false,
}) => {
  return (
    <div className="flex flex-row items-center justify-between px-3.5 sm:px-5 py-2.5 border-b border-main bg-surface z-50 shrink-0 h-13 min-h-[52px] select-none">
      {/* Left: Titulli i Agjentit dhe LED Drita e Statusit */}
      <div className="flex items-center gap-2 min-w-0">
        <h2 className="text-xs sm:text-sm font-bold text-text-primary uppercase tracking-wide leading-none truncate">
          {t('chatPanel.title', 'Asistenti Shabi')}
        </h2>
        <div className="flex items-center justify-center ml-0.5 shrink-0">
          <span
            className={`w-2 h-2 rounded-full ${
              connectionStatus === 'CONNECTED'
                ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse'
                : 'bg-danger-start animate-pulse'
            }`}
          />
        </div>
      </div>

      {/* Right: Butoni Inteligjent me 4 Gjendje Dinamike */}
      <div className="flex items-center justify-end gap-2 shrink-0">
        {onAnalyzeCase && (
          <button
            type="button"
            onClick={onAnalyzeCase}
            disabled={isAnalyzingCase}
            className={`h-8 px-3.5 rounded-xl font-bold text-[11px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-sm transition-all whitespace-nowrap focus:outline-none hover-lift active:scale-95 disabled:opacity-80 cursor-pointer border ${
              isAnalyzingCase
                ? 'bg-primary-start text-white border-primary-start/30'
                : isAnalysisDirty
                ? 'bg-amber-600 hover:bg-amber-700 text-white border-amber-500/40 shadow-amber-600/20 animate-pulse'
                : hasExistingAnalysis
                ? 'bg-surface hover:bg-hover text-text-primary border-main'
                : 'bg-primary-start hover:bg-primary-start/90 text-white border-primary-start/30'
            }`}
            title={
              isAnalysisDirty
                ? 'Janë shtuar dokumente të reja. Klikoni për të përditësuar raportin master!'
                : hasExistingAnalysis
                ? 'Hap raportin e ruajtur (0ms)'
                : 'Krijo Raportin e Plotë Doktrinar'
            }
          >
            {isAnalyzingCase ? (
              <>
                <Loader2 size={14} className="text-white animate-spin shrink-0" />
                <span className="text-white font-bold whitespace-nowrap animate-pulse">Rasti duke u analizuar...</span>
              </>
            ) : isAnalysisDirty ? (
              <>
                <RefreshCw size={14} className="text-white shrink-0 animate-spin" />
                <span className="text-white font-bold whitespace-nowrap">Përditëso Analizën</span>
              </>
            ) : hasExistingAnalysis ? (
              <>
                <FileSearch size={14} className="text-primary-start shrink-0" />
                <span className="font-bold whitespace-nowrap">Shiko Analizën</span>
              </>
            ) : (
              <>
                <FileSearch size={14} className="text-white shrink-0" />
                <span className="font-bold whitespace-nowrap">Analizo Rastin</span>
              </>
            )}
          </button>
        )}

        {onExportChat && (
          <button
            type="button"
            onClick={onExportChat}
            className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-primary-start hover:bg-hover rounded-lg transition-all focus:outline-none cursor-pointer"
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