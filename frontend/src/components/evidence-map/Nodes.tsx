// FILE: src/components/evidence-map/Nodes.tsx
// PHOENIX PROTOCOL - NODES V3.0 (HIERARCHY & DATA VISIBILITY)
// 1. FIX: Standardized Handles (Target=Top, Source=Bottom) for a clean TB Tree.
// 2. FIX: Added 'content' rendering to all node types so AI analysis is visible.
// 3. UI: Improved spacing and added 'italic' styling for descriptions.

import React, { memo } from 'react';
import { Handle, Position, NodeProps, Node, useReactFlow } from '@xyflow/react';
import { Gavel, FileText, Shield, Scale, Lock, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export type MapNodeData = {
  label: string;
  content?: string;
  exhibitNumber?: string;
  isAuthenticated?: boolean;
  isAdmitted?: string;
  isProven?: boolean;
  stats?: { supports: number; contradicts: number };
  isHighlighted?: boolean;
  editing?: boolean; 
};

const MetadataBadge: React.FC<{ icon: JSX.Element; text: string; color: string }> = ({ icon, text, color }) => (
    <span className={`flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${color}`}>
        {React.cloneElement(icon, { size: 10 })}
        {text}
    </span>
);

// NYJA: PRETENDIMI (The Goal)
export const ClaimNode = memo(({ id, data, selected }: NodeProps<Node<MapNodeData>>) => {
  const { t } = useTranslation();
  const { setNodes } = useReactFlow();
  const baseBorder = selected ? 'border-green-500 scale-105' : 'border-green-900/50';
  
  return (
    <div onDoubleClick={() => setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, editing: true } } : n))} 
         className={`px-4 py-3 shadow-2xl rounded-xl bg-[#1a1b1e] border-2 transition-all ${baseBorder} border-l-4 ${data.isProven ? 'border-l-green-400' : 'border-l-yellow-400'} w-64`}>
      <Handle type="target" position={Position.Top} className="!bg-green-500 w-3 h-3" />
      <div className="flex items-center pb-2 border-b border-white/10 mb-2 gap-2">
        <Gavel className="w-4 h-4 text-green-500" />
        <div className="text-[10px] font-black text-green-500 uppercase tracking-tighter">{t('evidenceMap.node.claimType', 'Pretendim')}</div>
      </div>
      <div className="text-sm font-bold text-white mb-1 leading-tight">{data.label}</div>
      <div className="text-[11px] text-gray-400 italic line-clamp-3 leading-relaxed">{data.content}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-green-500 w-3 h-3" />
    </div>
  );
});

// NYJA: FAKTI (The Bridge)
export const FactNode = memo(({ id, data, selected }: NodeProps<Node<MapNodeData>>) => {
  const { setNodes } = useReactFlow();
  return (
    <div onDoubleClick={() => setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, editing: true } } : n))}
         className={`px-4 py-3 shadow-2xl rounded-xl bg-[#1a1b1e] border-2 transition-all ${selected ? 'border-yellow-500 scale-105' : 'border-yellow-900/50'} border-l-4 border-l-yellow-500 w-64`}>
      <Handle type="target" position={Position.Top} className="!bg-yellow-500 w-3 h-3" />
      <div className="flex items-center pb-2 border-b border-white/10 mb-2 gap-2">
        <Shield className="w-4 h-4 text-yellow-500" />
        <div className="text-[10px] font-black text-yellow-500 uppercase tracking-tighter">FAKT I KONSTATUAR</div>
      </div>
      <div className="text-sm font-bold text-white mb-1 leading-tight">{data.label}</div>
      <div className="text-[11px] text-gray-400 italic line-clamp-3 leading-relaxed">{data.content}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-yellow-500 w-3 h-3" />
    </div>
  );
});

// NYJA: PROVA (The Foundation)
export const EvidenceNode = memo(({ id, data, selected }: NodeProps<Node<MapNodeData>>) => {
  const { t } = useTranslation();
  const { setNodes } = useReactFlow();
  
  return (
    <div onDoubleClick={() => setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, editing: true } } : n))}
         className={`px-4 py-3 shadow-2xl rounded-xl bg-[#1a1b1e] border-2 transition-all ${selected ? 'border-blue-500 scale-105' : 'border-blue-900/50'} border-l-4 border-l-blue-500 w-64`}>
      <div className="flex items-center pb-2 border-b border-white/10 mb-2 gap-2">
        <FileText className="w-4 h-4 text-blue-500" />
        <div className="text-[10px] font-black text-blue-500 uppercase tracking-tighter">{t('evidenceMap.node.evidenceType', 'Provë')}</div>
      </div>
      <div className="text-sm font-bold text-white mb-1 leading-tight">{data.label}</div>
      <div className="text-[11px] text-gray-400 italic line-clamp-2 leading-relaxed mb-2">{data.content}</div>
      
      <div className="flex flex-wrap gap-1">
        {data.exhibitNumber && <MetadataBadge icon={<FileText />} text={data.exhibitNumber} color="bg-blue-600/20 text-blue-400" />}
        {data.isAuthenticated ? <MetadataBadge icon={<ShieldCheck />} text="OK" color="bg-green-600/20 text-green-400" /> : <MetadataBadge icon={<Lock />} text="?!" color="bg-gray-600/20 text-gray-400" />}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-blue-500 w-3 h-3" />
    </div>
  );
});

// NYJA: LIGJI (The Rule)
export const LawNode = memo(({ id, data, selected }: NodeProps<Node<MapNodeData>>) => {
  const { setNodes } = useReactFlow();
  return (
    <div onDoubleClick={() => setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, editing: true } } : n))}
         className={`px-4 py-3 shadow-2xl rounded-xl bg-[#1a1b1e] border-2 transition-all ${selected ? 'border-purple-500 scale-105' : 'border-purple-900/50'} border-l-4 border-l-purple-500 w-64`}>
      <div className="flex items-center pb-2 border-b border-white/10 mb-2 gap-2">
        <Scale className="w-4 h-4 text-purple-500" />
        <div className="text-[10px] font-black text-purple-500 uppercase tracking-tighter">BAZA LIGJORE</div>
      </div>
      <div className="text-sm font-bold text-white mb-1 leading-tight">{data.label}</div>
      <div className="text-[11px] text-gray-400 italic leading-relaxed">{data.content}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-purple-500 w-3 h-3" />
    </div>
  );
});