// FILE: src/components/evidence-map/Nodes.tsx
import React, { memo } from 'react';
import { Handle, Position, NodeProps, Node } from '@xyflow/react';
import { Gavel, FileText } from 'lucide-react';

export type MapNodeData = {
  label: string;
  content?: string;
  status?: string;
};

export const ClaimNode = memo(({ data, selected }: NodeProps<Node<MapNodeData>>) => {
  return (
    <div className={`px-4 py-2 shadow-xl rounded-md bg-background-light border-2 transition-all ${selected ? 'border-green-500 scale-105' : 'border-green-900/50'}`}>
      <div className="flex items-center pb-2 border-b border-green-900/30 mb-2">
        <Gavel className="w-4 h-4 text-green-500 mr-2" />
        <div className="text-xs font-bold text-green-500 uppercase tracking-wider">Legal Claim</div>
      </div>
      <div className="text-sm font-semibold text-text-main">{data.label}</div>
      {data.content && <div className="text-xs text-text-muted mt-1 italic line-clamp-2">{data.content}</div>}
      
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-green-500" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-green-500" />
    </div>
  );
});

export const EvidenceNode = memo(({ data, selected }: NodeProps<Node<MapNodeData>>) => {
  return (
    <div className={`px-4 py-2 shadow-xl rounded-md bg-background-light border-2 transition-all ${selected ? 'border-blue-500 scale-105' : 'border-blue-900/50'}`}>
      <div className="flex items-center pb-2 border-b border-blue-900/30 mb-2">
        <FileText className="w-4 h-4 text-blue-500 mr-2" />
        <div className="text-xs font-bold text-blue-500 uppercase tracking-wider">Evidence Piece</div>
      </div>
      <div className="text-sm font-semibold text-text-main">{data.label}</div>
      
      <Handle type="source" position={Position.Top} className="w-3 h-3 bg-blue-500" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-blue-500" />
    </div>
  );
});