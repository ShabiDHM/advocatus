// FILE: src/components/case/EvidenceVaultPanel.tsx
// PHOENIX PROTOCOL - EVIDENCE VAULT PANEL V18.0 (DESKTOP-ONLY SUBTABS • ZERO MOBILE DUPLICATION)
// ZERO TS WARNINGS • FULL HEIGHT FILL • 100% COMPLETE CODE

import React, { useState } from 'react';
import { Document, DeletedDocumentResponse } from '../../data/types';
import DocumentsPanel from '../DocumentsPanel';
import MediaEvidencePanel from '../MediaEvidencePanel';
import { FileText, Film } from 'lucide-react';
import { TFunction } from 'i18next';

export type EvidenceSubTab = 'documents' | 'audio';

interface EvidenceVaultPanelProps {
  caseId: string;
  documents: Document[];
  connectionStatus: any;
  reconnect: () => void;
  onDocumentUploaded: (doc: Document) => void;
  onDocumentDeleted: (res: DeletedDocumentResponse) => void;
  onViewOriginal: (doc: Document) => void;
  onRenameDocument: (doc: Document) => void;
  onVerifyDocumentLaws?: (doc: Document) => void;
  selectedDocumentId?: string;
  onSelectDocument?: (document: Document) => void;
  activeSubTab?: EvidenceSubTab;
  onSubTabChange?: (tab: EvidenceSubTab) => void;
  t: TFunction;
}

export const EvidenceVaultPanel: React.FC<EvidenceVaultPanelProps> = ({
  caseId,
  documents,
  connectionStatus,
  reconnect,
  onDocumentUploaded,
  onDocumentDeleted,
  onViewOriginal,
  onRenameDocument,
  onVerifyDocumentLaws,
  selectedDocumentId,
  onSelectDocument,
  activeSubTab,
  onSubTabChange,
  t,
}) => {
  const [internalTab, setInternalTab] = useState<EvidenceSubTab>('documents');

  // Sinkronizim i kontrollit nga prindi nëse jepet activeSubTab
  const currentTab = activeSubTab || internalTab;

  const handleTabClick = (tab: EvidenceSubTab) => {
    setInternalTab(tab);
    if (onSubTabChange) {
      onSubTabChange(tab);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-surface border border-main rounded-2xl overflow-hidden shadow-sm flex-1">
      {/* SHIRITI I BRENDSHËM - SHFAQET VETËM NË DESKTOP (hidden lg:flex) PËR TË SHMANGUR DYFISHIMIN NË CELULAR */}
      <div className="hidden lg:flex p-2 sm:p-2.5 bg-canvas border-b border-main items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-main w-full">
          <button
            type="button"
            onClick={() => handleTabClick('documents')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 focus:outline-none cursor-pointer ${
              currentTab === 'documents'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <FileText size={13} />
            <span>Dokumentet ({documents.length})</span>
          </button>

          <button
            type="button"
            onClick={() => handleTabClick('audio')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 focus:outline-none cursor-pointer ${
              currentTab === 'audio'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Film size={13} />
            <span>Audio & Video</span>
          </button>
        </div>
      </div>

      {/* ZONA KRYESORE E PËRMBAJTJES */}
      <div className="flex-1 overflow-hidden relative flex flex-col h-full">
        {currentTab === 'documents' ? (
          <DocumentsPanel
            caseId={caseId}
            documents={documents}
            t={t}
            connectionStatus={connectionStatus}
            reconnect={reconnect}
            onDocumentUploaded={onDocumentUploaded}
            onDocumentDeleted={onDocumentDeleted}
            onViewOriginal={onViewOriginal}
            onRename={onRenameDocument}
            onVerifyDocumentLaws={onVerifyDocumentLaws}
            selectedDocId={selectedDocumentId}
            onSelectDocument={onSelectDocument}
            className="h-full w-full flex-1 bg-transparent border-0 rounded-none"
          />
        ) : (
          <div className="h-full w-full flex-1 overflow-y-auto p-3 sm:p-4 custom-finance-scroll">
            <MediaEvidencePanel caseId={caseId} t={t} />
          </div>
        )}
      </div>
    </div>
  );
};

export default EvidenceVaultPanel;