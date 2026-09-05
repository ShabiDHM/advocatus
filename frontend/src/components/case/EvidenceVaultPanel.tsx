// FILE: src/components/case/EvidenceVaultPanel.tsx
// PHOENIX PROTOCOL - EVIDENCE VAULT PANEL V14.0 (PIXEL-PERFECT SYMMETRY & MOBILE RESPONSIVENESS)

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
  t,
}) => {
  const [evidenceTab, setEvidenceTab] = useState<EvidenceSubTab>('documents');

  return (
    <div className="lg:col-span-5 flex flex-col h-[520px] sm:h-[620px] lg:h-[calc(100vh-255px)] min-h-[580px] bg-surface border border-main rounded-2xl overflow-hidden shadow-sm">
      {/* Top Segmented Sub-Tab Switcher */}
      <div className="p-2 sm:p-2.5 bg-canvas border-b border-main flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-main w-full">
          <button
            type="button"
            onClick={() => setEvidenceTab('documents')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 focus:outline-none cursor-pointer ${
              evidenceTab === 'documents'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <FileText size={13} />
            <span>Dokumentet ({documents.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setEvidenceTab('audio')}
            className={`flex-1 py-1.5 px-2 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 focus:outline-none cursor-pointer ${
              evidenceTab === 'audio'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Film size={13} />
            <span>Audio & Video</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        {evidenceTab === 'documents' ? (
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
            className="h-full w-full bg-transparent border-0 rounded-none"
          />
        ) : (
          <div className="h-full overflow-y-auto p-3 sm:p-4 custom-finance-scroll">
            <MediaEvidencePanel caseId={caseId} t={t} />
          </div>
        )}
      </div>
    </div>
  );
};

export default EvidenceVaultPanel;