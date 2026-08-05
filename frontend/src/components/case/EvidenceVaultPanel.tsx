// FILE: src/components/case/EvidenceVaultPanel.tsx
import React, { useState } from 'react';
import { Document, DeletedDocumentResponse } from '../../data/types';
import DocumentsPanel from '../DocumentsPanel';
import MediaEvidencePanel from '../MediaEvidencePanel';
import { FileText, Mic } from 'lucide-react';
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
  t,
}) => {
  const [evidenceTab, setEvidenceTab] = useState<EvidenceSubTab>('documents');

  return (
    <div className="lg:col-span-5 flex flex-col h-[520px] sm:h-[700px] bg-surface border border-main rounded-2xl overflow-hidden shadow-sm">
      <div className="p-2.5 sm:p-3 bg-canvas border-b border-main flex items-center justify-between gap-2">
        <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-main w-full">
          <button
            type="button"
            onClick={() => setEvidenceTab('documents')}
            className={`flex-1 py-1.5 px-2.5 rounded-lg text-[11px] sm:text-xs font-extrabold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
              evidenceTab === 'documents'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <FileText size={13} />
            <span>Dokumentet ({documents.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setEvidenceTab('audio')}
            className={`flex-1 py-1.5 px-2.5 rounded-lg text-[11px] sm:text-xs font-extrabold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
              evidenceTab === 'audio'
                ? 'bg-primary-start text-white shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Mic size={13} />
            <span>Inqizimet Audio</span>
          </button>
        </div>
      </div>

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
            className="h-full w-full bg-transparent border-0 rounded-none"
          />
        ) : (
          <div className="h-full overflow-y-auto p-3 sm:p-4">
            <MediaEvidencePanel caseId={caseId} t={t} />
          </div>
        )}
      </div>
    </div>
  );
};