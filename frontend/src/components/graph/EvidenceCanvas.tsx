// FILE: src/components/graph/EvidenceCanvas.tsx
// PHOENIX PROTOCOL - EVIDENCE CANVAS V77.0 (STRICT ZERO-WARNING D3 ENGINE)

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw, RotateCcw } from 'lucide-react';
import { OntologyNode, OntologyEdge, ENTITY_CONFIG } from './graphTypes';
import { translateToAlbanian, formatRelationText } from '../../utils/albanianLegalTranslator';

export interface EvidenceCanvasProps {
  loading: boolean;
  filteredNodes: OntologyNode[];
  filteredEdges: OntologyEdge[];
  selectedNode: OntologyNode | null;
  selectedEdge: OntologyEdge | null;
  hoveredEdge: OntologyEdge | null;
  connectedNodeIds?: Set<string>;
  connectedEdgeIds?: Set<string>;
  isFocusMode: boolean;
  onSelectNode: (n: OntologyNode | null) => void;
  onSelectEdge: (e: OntologyEdge | null) => void;
  onHoverEdge: (e: OntologyEdge | null) => void;
}

export const EvidenceCanvas: React.FC<EvidenceCanvasProps> = ({
  loading,
  filteredNodes,
  filteredEdges,
  selectedNode,
  selectedEdge,
  hoveredEdge,
  isFocusMode,
  onSelectNode,
  onSelectEdge,
  onHoverEdge,
}) => {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Struktura e të dhënave për D3 Force Graph
  const graphData = useMemo(() => {
    const nodes = filteredNodes.map((n) => {
      const conf = ENTITY_CONFIG[n.type] || ENTITY_CONFIG.PERSON;
      const displayLabel = translateToAlbanian(n.label);
      const initials =
        displayLabel
          .split(' ')
          .filter(Boolean)
          .map((w) => w[0])
          .slice(0, 2)
          .join('')
          .toUpperCase() || n.label.substring(0, 2).toUpperCase();

      return {
        id: n.id,
        rawNode: n,
        label: displayLabel,
        initials: initials,
        type: n.type,
        color: conf.bg,
        borderColor: conf.border,
        albanianType: conf.albanianLabel,
      };
    });

    const edges = filteredEdges.map((e) => {
      const isContradiction = e.relation.includes('CONTRADICT') || e.relation.includes('KUNDËR');
      let edgeLabel = formatRelationText(e.relation).toUpperCase();
      if (e.amount_eur) {
        edgeLabel += ` • €${e.amount_eur.toLocaleString()}`;
      }

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        rawEdge: e,
        label: edgeLabel,
        isContradiction,
      };
    });

    return { nodes, links: edges };
  }, [filteredNodes, filteredEdges]);

  // Konfigurimi i Forcave D3 (Hard Collision Constraint)
  useEffect(() => {
    if (!fgRef.current) return;

    fgRef.current.d3Force('charge')?.strength(-2000);
    fgRef.current.d3Force('link')?.distance(240);

    const d3 = (window as any).d3;
    if (d3 && d3.forceCollide) {
      fgRef.current.d3Force('collide', d3.forceCollide(90).iterations(3));
    }

    fgRef.current.d3ReheatSimulation();
  }, [graphData]);

  const handleResetView = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(700, 100);
    }
  }, []);

  const handleZoomIn = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() * 1.3, 400);
    }
  };

  const handleZoomOut = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() / 1.3, 400);
    }
  };

  // Vizatimi i Nyjes në Canvas
  const drawNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      void globalScale; // Parandalon paralajmërimin TS6133
      const isSelected = selectedNode?.id === node.id;
      const isDimmed = isFocusMode && !isSelected;

      const r = 26;
      const x = node.x;
      const y = node.y;

      ctx.save();
      ctx.globalAlpha = isDimmed ? 0.15 : 1.0;

      // 1. Halo kur Zgjidhet Nyja
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, r + 10, 0, 2 * Math.PI, false);
        ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x, y, r + 5, 0, 2 * Math.PI, false);
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3.5;
        ctx.stroke();
      }

      // 2. Rrethi Kryesor
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI, false);
      ctx.fillStyle = node.color || '#2563eb';
      ctx.fill();

      ctx.strokeStyle = isSelected ? '#ffffff' : node.borderColor || '#60a5fa';
      ctx.lineWidth = isSelected ? 3.5 : 2.5;
      ctx.stroke();

      // 3. Inicialet në Qendër
      ctx.font = 'bold 13px system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(node.initials || '', x, y);

      // 4. Badge me Emrin e Plotë poshtë Nyjes
      const labelText = node.label || '';
      ctx.font = 'bold 11px system-ui, sans-serif';
      const textWidth = ctx.measureText(labelText).width;
      const badgeW = textWidth + 16;
      const badgeH = 22;
      const badgeX = x - badgeW / 2;
      const badgeY = y + r + 8;

      ctx.fillStyle = '#090d16';
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 6);
      } else {
        ctx.rect(badgeX, badgeY, badgeW, badgeH);
      }
      ctx.fill();

      ctx.strokeStyle = isSelected ? '#38bdf8' : '#334155';
      ctx.lineWidth = isSelected ? 1.5 : 1;
      ctx.stroke();

      ctx.fillStyle = isSelected ? '#38bdf8' : '#f8fafc';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, x, badgeY + badgeH / 2);

      ctx.restore();
    },
    [selectedNode, isFocusMode]
  );

  // Vizatimi i Lidhjes me Etiketë në Canvas
  const drawLink = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      void globalScale; // Parandalon paralajmërimin TS6133
      const isSelected = selectedEdge?.id === link.id || hoveredEdge?.id === link.id;
      const isDimmed = isFocusMode && !isSelected;

      const start = link.source;
      const end = link.target;
      if (!start || !end || typeof start.x !== 'number' || typeof end.x !== 'number') return;

      const midX = (start.x + end.x) / 2;
      const midY = (start.y + end.y) / 2;

      ctx.save();
      ctx.globalAlpha = isDimmed ? 0.1 : 1.0;

      let angle = Math.atan2(end.y - start.y, end.x - start.x);
      if (angle > Math.PI / 2) angle -= Math.PI;
      if (angle < -Math.PI / 2) angle += Math.PI;

      ctx.save();
      ctx.translate(midX, midY);
      ctx.rotate(angle);

      const labelText = link.label || '';
      ctx.font = 'bold 9px system-ui, sans-serif';
      const textWidth = ctx.measureText(labelText).width;
      const padW = textWidth + 12;
      const padH = 18;

      ctx.fillStyle = link.isContradiction ? '#450a0a' : isSelected ? '#0369a1' : '#090d16';
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(-padW / 2, -padH / 2, padW, padH, 5);
      } else {
        ctx.rect(-padW / 2, -padH / 2, padW, padH);
      }
      ctx.fill();

      ctx.strokeStyle = link.isContradiction ? '#ef4444' : isSelected ? '#38bdf8' : '#334155';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = link.isContradiction ? '#fca5a5' : isSelected ? '#ffffff' : '#94a3b8';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, 0, 0);

      ctx.restore();
      ctx.restore();
    },
    [selectedEdge, hoveredEdge, isFocusMode]
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted w-full bg-canvas">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-start" />
        <p className="text-xs font-semibold">Po ngarkohet Ontologjia e Provave...</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 h-full w-full relative bg-canvas overflow-hidden">
      <ForceGraph2D
        ref={fgRef as any}
        graphData={graphData}
        backgroundColor="rgba(0,0,0,0)"
        nodeRelSize={26}
        nodeCanvasObject={drawNode}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 30, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
        linkCanvasObjectMode={() => 'after'}
        linkCanvasObject={drawLink}
        linkColor={(link: any) =>
          link.isContradiction
            ? '#ef4444'
            : selectedEdge?.id === link.id
            ? '#38bdf8'
            : '#475569'
        }
        linkWidth={(link: any) =>
          link.isContradiction || selectedEdge?.id === link.id ? 3 : 2
        }
        linkDirectionalArrowLength={7}
        linkDirectionalArrowRelPos={0.85}
        linkDirectionalArrowColor={(link: any) =>
          link.isContradiction
            ? '#ef4444'
            : selectedEdge?.id === link.id
            ? '#38bdf8'
            : '#64748b'
        }
        linkLineDash={(link: any) => (link.isContradiction ? [5, 4] : null)}
        linkCurvature={0.12}
        onNodeClick={(node: any) => onSelectNode(node.rawNode)}
        onLinkClick={(link: any) => onSelectEdge(link.rawEdge)}
        onLinkHover={(link: any) => onHoverEdge(link ? link.rawEdge : null)}
        onBackgroundClick={() => {
          onSelectNode(null);
          onSelectEdge(null);
          onHoverEdge(null);
        }}
        cooldownTicks={120}
        onEngineStop={handleResetView}
      />

      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 bg-surface border border-main p-2 rounded-2xl shadow-2xl z-20 text-text-primary">
        <button
          type="button"
          onClick={handleZoomIn}
          className="p-2 text-text-primary hover:text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Zmadho"
        >
          <ZoomIn size={16} />
        </button>
        <button
          type="button"
          onClick={handleResetView}
          className="p-2 text-text-primary hover:text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Qendërzo Rrjetin"
        >
          <Maximize2 size={15} />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="p-2 text-text-primary hover:text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Zvogëlo"
        >
          <ZoomOut size={16} />
        </button>
        <div className="h-4 w-px bg-main mx-1" />
        <button
          type="button"
          onClick={() => {
            if (fgRef.current) {
              fgRef.current.d3ReheatSimulation();
            }
          }}
          className="p-2 text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Ri-kalkulo Fizikën D3"
        >
          <RotateCcw size={15} />
        </button>
      </div>
    </div>
  );
};

export default EvidenceCanvas;