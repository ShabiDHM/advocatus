// FILE: frontend/src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V14.0 (TYPE SAFE & CLEAN INTERFACE)

import React from 'react';
import { Download, Trash2, FileSearch } from 'lucide-react';
import { TFunction } from 'i18next';

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId: string;
  onClearChat: () => void;
  onExportChat?: () => void;
  t: TFunction;
  isPro?: boolean;
  onAnalyzeCase?: () => void;
  // Opsionale për përputhshmëri të plotë
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
}) => {
  return (
    <div className="flex flex-row items-center justify-between px-3.5 sm:px-5 py-2.5 border-b border-main bg-surface z-50 shrink-0 h-13 min-h-[52px]">
      {/* Left: Chat Agent Title & LED status light */}
      <div className="flex items-center gap-2 min-w-0">
        <h2 className="text-xs sm:text-sm font-bold text-text-primary uppercase tracking-wide leading-none truncate">
          {t('chatPanel.title', 'Asistenti Sokratik')}
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

      {/* Right: ANALIZO RASTIN + Action Buttons */}
      <div className="flex items-center justify-end gap-2 shrink-0">
        <button
          type="button"
          onClick={onAnalyzeCase}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-primary-start text-white font-bold text-[10px] sm:text-xs uppercase tracking-wider shadow-md shadow-amber-500/20 hover:brightness-110 active:scale-95 transition-all focus:outline-none cursor-pointer"
        >
          <FileSearch size={15} />
          <span>⚖️ Analizo Rastin</span>
        </button>

        {onExportChat && (
          <button
            type="button"
            onClick={onExportChat}
            className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-primary-start hover:bg-hover rounded-xl transition-all focus:outline-none cursor-pointer"
            title="Shkarko Bisedën"
          >
            <Download size={15} />
          </button>
        )}

        <button
          type="button"
          onClick={onClearChat}
          className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-xl transition-all focus:outline-none cursor-pointer"
          title="Pastro Bisedën"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;