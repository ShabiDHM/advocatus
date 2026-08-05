// FILE: src/components/chat/ChatHeader.tsx
import React from 'react';
import { Download, Trash2 } from 'lucide-react';
import { TFunction } from 'i18next';

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId: string;
  selectedDocumentCount: number;
  onClearChat: () => void;
  onExportChat?: () => void;
  t: TFunction;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  connectionStatus,
  activeContextId,
  selectedDocumentCount,
  onClearChat,
  onExportChat,
  t,
}) => {
  return (
    <div className="flex flex-row items-center justify-between px-4 sm:px-5 py-3 border-b border-main bg-surface z-50 shrink-0 h-12">
      <div className="flex items-center gap-2">
        <h2 className="text-xs sm:text-sm font-bold text-text-primary uppercase tracking-wide leading-none">
          {t('chatPanel.title', 'Asistenti Sokratik')}
        </h2>
        <div className="flex items-center justify-center ml-0.5">
          <span
            className={`w-2 h-2 rounded-full ${
              connectionStatus === 'CONNECTED'
                ? 'bg-[#22c55e] shadow-[0_0_8px_rgba(34,197,94,0.8),0_0_3px_rgba(34,197,94,1)] animate-pulse'
                : 'bg-danger-start animate-pulse'
            }`}
          />
        </div>

        {activeContextId !== 'general' && selectedDocumentCount > 0 && (
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-primary-start/10 border border-primary-start/20 rounded-full shadow-sm">
            <span className="text-[10px] font-semibold text-primary-start uppercase tracking-wide">
              {selectedDocumentCount} Lëndë
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-1.5 h-8">
        {onExportChat && (
          <button
            type="button"
            onClick={onExportChat}
            className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-primary-start hover:bg-hover rounded-xl transition-all focus:outline-none"
            title="Download"
          >
            <Download size={15} />
          </button>
        )}
        <button
          type="button"
          onClick={onClearChat}
          className="flex items-center justify-center w-8 h-8 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-xl transition-all focus:outline-none"
          title="Clear"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};