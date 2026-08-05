// FILE: src/components/graph/EvidenceCanvas.tsx
import React from 'react';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';
import { OntologyNode, OntologyEdge, ENTITY_CONFIG } from './graphTypes';
import { translateToAlbanian, formatRelationText } from '../../utils/albanianLegalTranslator';

interface EvidenceCanvasProps {
  loading: boolean;
  svgRef: React.Ref<SVGSVGElement>;
  viewBox: { x: number; y: number; width: number; height: number };
  positions: Record<string, { x: number; y: number }>;
  filteredNodes: OntologyNode[];
  filteredEdges: OntologyEdge[];
  selectedNode: OntologyNode | null;
  selectedEdge: OntologyEdge | null;
  hoveredEdge: OntologyEdge | null;
  connectedNodeIds: Set<string>;
  connectedEdgeIds: Set<string>;
  isFocusMode: boolean;
  onSelectNode: (n: OntologyNode) => void;
  onSelectEdge: (e: OntologyEdge) => void;
  onHoverEdge: (e: OntologyEdge | null) => void;
  onMouseDown: (e: React.MouseEvent) => void;
  onMouseMove: (e: React.MouseEvent) => void;
  onMouseUp: () => void;
  onTouchStart: (e: React.TouchEvent) => void;
  onTouchMove: (e: React.TouchEvent) => void;
  onTouchEnd: () => void;
  onNodeDragStart: (id: string) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

export const EvidenceCanvas: React.FC<EvidenceCanvasProps> = ({
  loading,
  svgRef,
  viewBox,
  positions,
  filteredNodes,
  filteredEdges,
  selectedNode,
  selectedEdge,
  hoveredEdge,
  connectedNodeIds,
  connectedEdgeIds,
  isFocusMode,
  onSelectNode,
  onSelectEdge,
  onHoverEdge,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
  onNodeDragStart,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}) => {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted w-full">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-start" />
        <p className="text-xs font-semibold">Po ngarkohet Ontologjia e Provave...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full w-full relative">
      <svg
        ref={svgRef}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:28px_28px]"
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <g pointerEvents="none">
          {['👤 PERSONA', '🏢 INSTITUCIONE', '💳 LLOGARI & LOKACIONE', '📄 PROVAT & DOKUMENTET', '⚖️ ORGANET & SEANCAT'].map((title, i) => (
            <g key={i} transform={`translate(${-1100 + i * 550}, -780)`}>
              <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#2563eb" strokeWidth="2" />
              <text x="0" y="6" textAnchor="middle" fill="#60a5fa" fontSize="16" fontWeight="900">
                {title}
              </text>
            </g>
          ))}
        </g>

        <g className="edges">
          {filteredEdges.map((edge) => {
            const s = positions[edge.source];
            const t = positions[edge.target];
            if (!s || !t) return null;

            const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');
            const isSelected = selectedEdge?.id === edge.id;
            const isHovered = hoveredEdge?.id === edge.id;

            const isEdgeConnected = connectedEdgeIds.has(edge.id);
            const edgeOpacity = isFocusMode ? (isEdgeConnected ? 1.0 : 0.05) : isHovered || isSelected || isContradiction ? 1.0 : 0.6;

            const pathD = `M ${s.x},${s.y} C ${s.x + (t.x - s.x) * 0.4},${s.y + 70} ${s.x + (t.x - s.x) * 0.6},${t.y - 70} ${t.x},${t.y}`;
            const midX = (s.x + t.x) / 2;
            const midY = (s.y + t.y) / 2 + 20;

            return (
              <g key={edge.id} style={{ opacity: edgeOpacity }} className="transition-opacity duration-200">
                <path
                  d={pathD}
                  fill="none"
                  stroke="transparent"
                  strokeWidth="28"
                  className="cursor-pointer"
                  onClick={() => onSelectEdge(edge)}
                  onMouseEnter={() => onHoverEdge(edge)}
                  onMouseLeave={() => onHoverEdge(null)}
                />

                <path
                  d={pathD}
                  fill="none"
                  stroke={isContradiction ? '#ef4444' : isSelected || isHovered ? '#3b82f6' : '#475569'}
                  strokeWidth={isContradiction || isSelected || isHovered ? 4.5 : 2}
                  strokeDasharray={isContradiction ? '8,8' : 'none'}
                  className="pointer-events-none"
                />

                <g transform={`translate(${midX}, ${midY})`} className="pointer-events-none">
                  <rect
                    x="-65"
                    y="-14"
                    width="130"
                    height="28"
                    fill="#090d16"
                    stroke={isSelected || isHovered ? '#60a5fa' : '#334155'}
                    strokeWidth={isSelected || isHovered ? 2 : 1}
                    rx="14"
                  />
                  <text
                    x="0"
                    y="4"
                    textAnchor="middle"
                    fill={isSelected || isHovered ? '#ffffff' : '#cbd5e1'}
                    fontSize="12"
                    fontWeight="800"
                  >
                    {formatRelationText(edge.relation)}
                  </text>
                </g>
              </g>
            );
          })}
        </g>

        <g className="nodes">
          {filteredNodes.map((node) => {
            const pos = positions[node.id] || { x: 0, y: 0 };
            const conf = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
            const IconComponent = conf.icon;

            const isNodeConnected = connectedNodeIds.has(node.id);
            const nodeOpacity = isFocusMode ? (isNodeConnected ? 1.0 : 0.05) : 1.0;

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                className="cursor-grab active:cursor-grabbing transition-opacity duration-200"
                style={{ opacity: nodeOpacity }}
                onClick={() => onSelectNode(node)}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  onNodeDragStart(node.id);
                }}
              >
                <rect
                  x="-140"
                  y="-42"
                  width="280"
                  height="84"
                  rx="18"
                  fill="#0b0f19"
                  stroke={selectedNode?.id === node.id ? '#ffffff' : '#1e293b'}
                  strokeWidth={selectedNode?.id === node.id ? '3' : '2'}
                />
                <rect x="-140" y="-42" width="10" height="84" rx="5" fill={conf.bg} />
                <g transform="translate(-104, 0)">
                  <circle r="20" fill={conf.bg} />
                  <foreignObject x="-10" y="-10" width="20" height="20" className="pointer-events-none">
                    <div className="w-full h-full flex items-center justify-center text-white">
                      <IconComponent size={16} />
                    </div>
                  </foreignObject>
                </g>
                <text x="-72" y="-8" fill="#ffffff" fontSize="16" fontWeight="800">
                  {translateToAlbanian(node.label)}
                </text>
                <text x="-72" y="18" fill={conf.border} fontSize="11" fontWeight="800" className="uppercase">
                  {conf.albanianLabel}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="absolute bottom-4 right-4 flex items-center gap-1 bg-surface/90 p-1.5 rounded-2xl border border-main shadow-2xl z-20">
        <button type="button" onClick={onZoomIn} className="p-2 text-text-muted hover:text-text-primary rounded-xl" title="Zmadho">
          <ZoomIn size={16} />
        </button>
        <button type="button" onClick={onResetZoom} className="p-2 text-text-muted hover:text-text-primary rounded-xl" title="Reset View">
          <Maximize2 size={15} />
        </button>
        <button type="button" onClick={onZoomOut} className="p-2 text-text-muted hover:text-text-primary rounded-xl" title="Zvogëlo">
          <ZoomOut size={16} />
        </button>
      </div>
    </div>
  );
};