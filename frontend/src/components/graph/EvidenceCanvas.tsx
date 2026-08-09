// FILE: src/components/graph/EvidenceCanvas.tsx
// PHOENIX PROTOCOL - EVIDENCE CANVAS V66.0 (THEME AWARE & HIGH-CONTRAST ZOOM TOOLBAR)

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

  // Derive distinct active X columns and their minimum Y positions to place headers cleanly above top nodes
  const activeColHeaderMap = new Map<number, { title: string; minY: number }>();
  filteredNodes.forEach((node) => {
    const pos = positions[node.id];
    if (pos) {
      const conf = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
      const current = activeColHeaderMap.get(pos.x);
      const title = conf.albanianLabel.toUpperCase();
      
      if (!current) {
        activeColHeaderMap.set(pos.x, { title, minY: pos.y });
      } else {
        if (pos.y < current.minY) {
          current.minY = pos.y;
        }
      }
    }
  });

  // Calculate connection counts for each node
  const nodeConnectionCounts = new Map<string, number>();
  filteredEdges.forEach((e) => {
    nodeConnectionCounts.set(e.source, (nodeConnectionCounts.get(e.source) || 0) + 1);
    nodeConnectionCounts.set(e.target, (nodeConnectionCounts.get(e.target) || 0) + 1);
  });

  return (
    <div className="flex-1 h-full w-full relative">
      <svg
        ref={svgRef}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none bg-[radial-gradient(#334155_1.5px,transparent_1.5px)] [background-size:32px_32px]"
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <defs>
          {/* Arrowheads */}
          <marker id="arrowhead-blue" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto">
            <polygon points="0 0, 10 4, 0 8" fill="#3b82f6" />
          </marker>
          <marker id="arrowhead-contradiction" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto">
            <polygon points="0 0, 10 4, 0 8" fill="#ef4444" />
          </marker>

          {/* Fiber-Optic Line Gradients */}
          <linearGradient id="lineGradientBlue" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#60a5fa" stopOpacity="1" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.8" />
          </linearGradient>

          {/* Palantir Glassmorphism Card Gradient */}
          <linearGradient id="nodeGlassBg" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#111827" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#0b0f19" stopOpacity="0.98" />
          </linearGradient>
        </defs>

        {/* DYNAMIC ACTIVE COLUMN HEADERS ELEVATED SAFELY ABOVE TOP NODES */}
        <g className="swimlane-grid" pointerEvents="none">
          {Array.from(activeColHeaderMap.entries()).map(([xPos, data], i) => {
            const headerY = data.minY - 90; // Floats 90px above the highest node card in that column
            return (
              <g key={i}>
                <line
                  x1={xPos + 280}
                  y1={-1200}
                  x2={xPos + 280}
                  y2={1200}
                  stroke="#334155"
                  strokeWidth="1.5"
                  strokeDasharray="6,6"
                />

                <g transform={`translate(${xPos}, ${headerY})`}>
                  <rect
                    x="-110"
                    y="-20"
                    width="220"
                    height="40"
                    rx="20"
                    fill="#0f172a"
                    stroke="#2563eb"
                    strokeWidth="2"
                    className="shadow-2xl"
                  />
                  <text x="0" y="5" textAnchor="middle" fill="#60a5fa" fontSize="12" fontWeight="900" letterSpacing="1px">
                    {data.title}
                  </text>
                </g>
              </g>
            );
          })}
        </g>

        {/* FIBER-OPTIC EDGES WITH CLEAN HOVER BADGES */}
        <g className="edges">
          {filteredEdges.map((edge) => {
            const s = positions[edge.source];
            const t = positions[edge.target];
            if (!s || !t) return null;

            const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');
            const isSelected = selectedEdge?.id === edge.id;
            const isHovered = hoveredEdge?.id === edge.id;

            const isEdgeConnected = connectedEdgeIds.has(edge.id);
            const edgeOpacity = isFocusMode ? (isEdgeConnected ? 1.0 : 0.05) : isHovered || isSelected || isContradiction ? 1.0 : 0.65;

            const pathD = `M ${s.x},${s.y} C ${s.x + (t.x - s.x) * 0.4},${s.y + 40} ${s.x + (t.x - s.x) * 0.6},${t.y - 40} ${t.x},${t.y}`;
            const midX = (s.x + t.x) / 2;
            const midY = (s.y + t.y) / 2 + 10;

            const showBadge = isHovered || isSelected;

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
                  stroke={isContradiction ? '#ef4444' : isSelected || isHovered ? '#60a5fa' : 'url(#lineGradientBlue)'}
                  strokeWidth={isContradiction ? 3.5 : isSelected || isHovered ? 3.5 : 2}
                  strokeDasharray={isContradiction ? '6,6' : 'none'}
                  markerEnd={isContradiction ? 'url(#arrowhead-contradiction)' : isSelected || isHovered ? 'url(#arrowhead-blue)' : undefined}
                  className="pointer-events-none transition-all duration-200"
                />

                {showBadge && (
                  <g transform={`translate(${midX}, ${midY})`} className="pointer-events-none">
                    <rect
                      x="-75"
                      y="-15"
                      width="150"
                      height="30"
                      fill={isContradiction ? '#450a0a' : '#0a0f1d'}
                      stroke={isContradiction ? '#ef4444' : '#60a5fa'}
                      strokeWidth="2"
                      rx="15"
                      className="shadow-2xl"
                    />
                    <text
                      x="0"
                      y="4"
                      textAnchor="middle"
                      fill={isContradiction ? '#fca5a5' : '#ffffff'}
                      fontSize="11"
                      fontWeight="900"
                      className="uppercase tracking-wider font-sans"
                    >
                      {formatRelationText(edge.relation)}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>

        {/* PALANTIR GLASSMORPHISM NODE CARDS */}
        <g className="nodes">
          {filteredNodes.map((node) => {
            const pos = positions[node.id] || { x: 0, y: 0 };
            const conf = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
            const IconComponent = conf.icon;

            const isNodeConnected = connectedNodeIds.has(node.id);
            const nodeOpacity = isFocusMode ? (isNodeConnected ? 1.0 : 0.05) : 1.0;
            const isSelected = selectedNode?.id === node.id;

            const cardW = 240;
            const cardH = 62;
            const connCount = nodeConnectionCounts.get(node.id) || 0;

            const displayLabel = translateToAlbanian(node.label);

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                className="cursor-grab active:cursor-grabbing transition-opacity duration-200 group"
                style={{ opacity: nodeOpacity }}
                onClick={() => onSelectNode(node)}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  onNodeDragStart(node.id);
                }}
              >
                {isSelected && (
                  <rect
                    x={-cardW / 2 - 8}
                    y={-cardH / 2 - 8}
                    width={cardW + 16}
                    height={cardH + 16}
                    rx="20"
                    fill="none"
                    stroke={conf.border}
                    strokeWidth="3.5"
                    className="animate-pulse"
                  />
                )}

                <rect
                  x={-cardW / 2}
                  y={-cardH / 2}
                  width={cardW}
                  height={cardH}
                  rx="16"
                  fill="url(#nodeGlassBg)"
                  stroke={isSelected ? '#ffffff' : '#334155'}
                  strokeWidth={isSelected ? '2.5' : '1.5'}
                  className="shadow-2xl transition-transform duration-150 group-hover:scale-105"
                />

                <rect
                  x={-cardW / 2}
                  y={-cardH / 2}
                  width="8"
                  height={cardH}
                  rx="4"
                  fill={conf.bg}
                />

                <g transform={`translate(${-cardW / 2 + 30}, 0)`}>
                  <circle r="16" fill={conf.bg} className="shadow-md" />
                  <foreignObject x="-8" y="-8" width="16" height="16" className="pointer-events-none">
                    <div className="w-full h-full flex items-center justify-center text-white">
                      <IconComponent size={13} />
                    </div>
                  </foreignObject>
                </g>

                <text
                  x={-cardW / 2 + 56}
                  y="-5"
                  fill="#ffffff"
                  fontSize="14"
                  fontWeight="900"
                  className="select-none tracking-tight pointer-events-none font-sans"
                >
                  {displayLabel.length > 18 ? `${displayLabel.substring(0, 16)}..` : displayLabel}
                </text>

                <text
                  x={-cardW / 2 + 56}
                  y="15"
                  fill={conf.border}
                  fontSize="10"
                  fontWeight="800"
                  className="select-none uppercase tracking-wider pointer-events-none font-sans"
                >
                  {conf.albanianLabel}
                </text>

                {connCount > 0 && (
                  <g transform={`translate(${cardW / 2 - 28}, ${-cardH / 2 + 16})`}>
                    <rect
                      x="-14"
                      y="-9"
                      width="28"
                      height="18"
                      rx="9"
                      fill="#0d1322"
                      stroke="#334155"
                      strokeWidth="1"
                    />
                    <text
                      x="0"
                      y="4"
                      textAnchor="middle"
                      fill="#60a5fa"
                      fontSize="9"
                      fontWeight="900"
                      className="font-mono select-none"
                    >
                      {connCount}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* THEME AWARE & HIGH-CONTRAST FLOATING ZOOM CONTROLS TOOLBAR */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 bg-surface border border-main p-2 rounded-2xl shadow-2xl z-20 text-text-primary">
        <button
          type="button"
          onClick={onZoomIn}
          className="p-2 text-text-primary hover:text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Zmadho"
        >
          <ZoomIn size={16} />
        </button>
        <button
          type="button"
          onClick={onResetZoom}
          className="p-2 text-text-primary hover:text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Rivendos Pamjen"
        >
          <Maximize2 size={15} />
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          className="p-2 text-text-primary hover:text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Zvogëlo"
        >
          <ZoomOut size={16} />
        </button>
      </div>
    </div>
  );
};