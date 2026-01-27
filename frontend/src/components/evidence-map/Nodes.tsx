// FILE: src/components/evidence-map/Nodes.tsx (FINAL CLEANUP)
// PHOENIX PROTOCOL - FIX V5.5.1
// 1. FIX: Added 'import React from 'react';' back in to resolve UMD global error (TS2686), as JSX usage requires it in helper components.

import React, { memo } from 'react'; // PHOENIX FIX: Re-added React import
import { Handle, Position, NodeProps, Node, useReactFlow } from '@xyflow/react';
import { Gavel, FileText, CheckCircle, XCircle, ShieldCheck, Lock, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export type MapNodeData = {
  label: string;
  content?: string;
  status?: string;
  
  // Phase 5 Data (synced)
  exhibitNumber?: string;
  isAuthenticated?: boolean;
  isAdmitted?: string;
  isProven?: boolean;
  
  // Phase 3 Data (transient/derived)
  stats?: { supports: number; contradicts: number };
  isHighlighted?: boolean;
  
  // PHOENIX ADDITION: Transient UI state for editing modal (NOT synced to backend)
  editing?: boolean; 
};

// Helper component for metadata badges (Unchanged)
const MetadataBadge: React.FC<{ icon: JSX.Element; text: string; color: string }> = ({ icon, text, color }) => (
    <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
        {React.cloneElement(icon, { size: 12 })}
        {text}
    </span>
);

export const ClaimNode = memo(({ id, data, selected }: NodeProps<Node<MapNodeData>>) => {
  const { t } = useTranslation();
  const hasStats = data.stats && (data.stats.supports > 0 || data.stats.contradicts > 0);
  const { setNodes } = useReactFlow();

  const baseBorder = selected ? 'border-green-500 scale-105' : 'border-green-900/50';
  const highlightBorder = data.isHighlighted ? '!border-yellow-400 ring-2 ring-yellow-400 ring-offset-2 ring-offset-background-dark' : '';
  
  const handleDoubleClick = () => {
    setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, editing: true } } : n));
  };
  
  const isProvenClass = data.isProven ? 'border-l-4 border-green-400' : 'border-l-4 border-yellow-400';

  return (
    <div onDoubleClick={handleDoubleClick} className={`px-4 py-2 shadow-xl rounded-md bg-background-light border-2 transition-all ${baseBorder} ${highlightBorder} ${isProvenClass} cursor-pointer`}>
      <div className="flex items-center pb-2 border-b border-green-900/30 mb-2">
        <Gavel className="w-4 h-4 text-green-500 mr-2" />
        <div className="text-xs font-bold text-green-500 uppercase tracking-wider">{t('evidenceMap.node.claimType')}</div>
      </div>
      <div className="text-sm font-semibold text-text-main break-words">{data.label}</div>
      {data.content && <div className="text-xs text-text-muted mt-1 italic line-clamp-2 break-words">{data.content}</div>}
      
      {/* PHASE 5: Claim Metadata */}
      <div className="mt-2 pt-2 border-t border-green-900/30 flex items-center gap-2">
        {data.isProven ? (
            <MetadataBadge icon={<Check />} text={t('nodeEdit.proven', 'Vërtetuar')} color="bg-green-600/20 text-green-400" />
        ) : (
            <MetadataBadge icon={<XCircle />} text={t('nodeEdit.disputed', 'I Diskutueshëm')} color="bg-yellow-600/20 text-yellow-400" />
        )}
      </div>
      
      {/* Phase 3: Stats Display */}
      {hasStats && (
        <div className="mt-2 pt-2 border-t border-green-900/30 flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1 text-green-400">
            <CheckCircle size={14} />
            <span>{data.stats?.supports || 0}</span>
          </div>
          <div className="flex items-center gap-1 text-red-400">
            <XCircle size={14} />
            <span>{data.stats?.contradicts || 0}</span>
          </div>
        </div>
      )}
      
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-green-500" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-green-500" />
    </div>
  );
});

export const EvidenceNode = memo(({ id, data, selected }: NodeProps<Node<MapNodeData>>) => {
  const { t } = useTranslation();
  const { setNodes } = useReactFlow();

  const baseBorder = selected ? 'border-blue-500 scale-105' : 'border-blue-900/50';
  const highlightBorder = data.isHighlighted ? '!border-yellow-400 ring-2 ring-yellow-400 ring-offset-2 ring-offset-background-dark' : '';
  
  const handleDoubleClick = () => {
    setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, editing: true } } : n));
  };
  
  const isAdmitted = data.isAdmitted === 'Admitted';
  const admittedClass = isAdmitted ? 'border-l-4 border-green-400' : data.isAdmitted === 'Stricken' ? 'border-l-4 border-red-400' : 'border-l-4 border-blue-400';

  return (
    <div onDoubleClick={handleDoubleClick} className={`px-4 py-2 shadow-xl rounded-md bg-background-light border-2 transition-all ${baseBorder} ${highlightBorder} ${admittedClass} cursor-pointer`}>
      <div className="flex items-center pb-2 border-b border-blue-900/30 mb-2">
        <FileText className="w-4 h-4 text-blue-500 mr-2" />
        <div className="text-xs font-bold text-blue-500 uppercase tracking-wider">{t('evidenceMap.node.evidenceType')}</div>
      </div>
      <div className="text-sm font-semibold text-text-main break-words">{data.label}</div>
      {data.content && <div className="text-xs text-text-muted mt-1 italic line-clamp-2 break-words">{data.content}</div>}
      
      {/* PHASE 5: Evidence Metadata */}
      <div className="mt-2 pt-2 border-t border-blue-900/30 flex flex-wrap items-center gap-2">
        {data.exhibitNumber && (
            <MetadataBadge icon={<FileText />} text={data.exhibitNumber} color="bg-blue-600/20 text-blue-400" />
        )}
        {data.isAuthenticated ? (
            <MetadataBadge icon={<ShieldCheck />} text={t('nodeEdit.authenticated', 'Autentikuar')} color="bg-green-600/20 text-green-400" />
        ) : (
            <MetadataBadge icon={<Lock />} text={t('nodeEdit.unauthenticated', 'Pa Autentikim')} color="bg-gray-600/20 text-gray-400" />
        )}
        {data.isAdmitted === 'Admitted' && (
            <MetadataBadge icon={<Check />} text={t('nodeEdit.admitted', 'Pranuar')} color="bg-green-600/20 text-green-400" />
        )}
        {data.isAdmitted === 'Stricken' && (
            <MetadataBadge icon={<XCircle />} text={t('nodeEdit.stricken', 'Hequr')} color="bg-red-600/20 text-red-400" />
        )}
      </div>

      <Handle type="source" position={Position.Top} className="w-3 h-3 bg-blue-500" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-blue-500" />
    </div>
  );
});