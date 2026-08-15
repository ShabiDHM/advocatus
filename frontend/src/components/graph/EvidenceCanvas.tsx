// FILE: src/components/graph/EvidenceCanvas.tsx
// PHOENIX PROTOCOL - EVIDENCE CANVAS V110.0 (TRUE CONTRADICTION STYLING ONLY)

import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';
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

  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 1200,
    height: 800,
  });

  useEffect(() => {
    if (!containerRef.current) return;

    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        if (clientWidth > 50 && clientHeight > 50) {
          setDimensions({ width: clientWidth, height: clientHeight });
        }
      }
    };

    updateSize();
    const resizeObserver = new ResizeObserver(() => updateSize());
    resizeObserver.observe(containerRef.current);

    return () => resizeObserver.disconnect();
  }, []);

  const nodeDegreeMap = useMemo(() => {
    const map = new Map<string, number>();
    filteredEdges.forEach((e) => {
      map.set(e.source, (map.get(e.source) || 0) + 1);
      map.set(e.target, (map.get(e.target) || 0) + 1);
    });
    return map;
  }, [filteredEdges]);

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
        degree: nodeDegreeMap.get(n.id) || 0,
      };
    });

    const pairMap = new Map<string, number>();
    filteredEdges.forEach((e) => {
      const key = [e.source, e.target].sort().join('___');
      pairMap.set(key, (pairMap.get(key) || 0) + 1);
    });

    const pairCurrentIndex = new Map<string, number>();

    const edges = filteredEdges.map((e) => {
      const key = [e.source, e.target].sort().join('___');
      const total = pairMap.get(key) || 1;
      const currentIndex = pairCurrentIndex.get(key) || 0;
      pairCurrentIndex.set(key, currentIndex + 1);

      let curvature = 0;
      if (total > 1) {
        curvature = (currentIndex - (total - 1) / 2) * 0.22;
        if (e.source > e.target) curvature *= -1;
      }

      // VIJA E KUQE VETËM PËR KONTRADIKTA DHE SHKELJE TË VËRTETUARA TË KUNDËRSHTARIT
      const isContradiction =
        e.relation.includes('CONTRADICT') ||
        e.relation.includes('KUNDËRTHËNIE') ||
        e.relation.includes('MOSPËRPUTHJE') ||
        e.relation.includes('FALSIFIKIM') ||
        e.relation.includes('E_RREME');

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
        curvature: curvature,
      };
    });

    return { nodes, links: edges };
  }, [filteredNodes, filteredEdges, nodeDegreeMap]);

  useEffect(() => {
    if (!fgRef.current) return;

    fgRef.current.d3Force('charge')?.strength(-950);
    fgRef.current.d3Force('link')?.distance(210);

    const d3 = (window as any).d3;
    if (d3) {
      if (d3.forceCenter) {
        fgRef.current.d3Force('center', d3.forceCenter(0, 0));
      }
      if (d3.forceCollide) {
        fgRef.current.d3Force('collide', d3.forceCollide(72).iterations(2));
      }
      if (d3.forceX && d3.forceY) {
        fgRef.current.d3Force('x', d3.forceX(0).strength(0.06));
        fgRef.current.d3Force('y', d3.forceY(0).strength(0.06));
      }
    }

    fgRef.current.d3ReheatSimulation();

    const timer = setTimeout(() => {
      if (fgRef.current) {
        fgRef.current.zoomToFit(500, 50);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [graphData, dimensions]);

  const handleResetView = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(500, 50);
    }
  }, []);

  const handleZoomIn = () => {
    if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() * 1.3, 300);
  };

  const handleZoomOut = () => {
    if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() / 1.3, 300);
  };

  const handleResetSimulationAndUnpin = useCallback(() => {
    if (graphData && graphData.nodes) {
      graphData.nodes.forEach((n: any) => {
        n.fx = undefined;
        n.fy = undefined;
      });
    }
    if (fgRef.current) {
      fgRef.current.d3ReheatSimulation();
      fgRef.current.zoomToFit(500, 50);
    }
  }, [graphData]);

  const drawNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      void globalScale;
      const isSelected = selectedNode?.id === node.id;
      const isDimmed = isFocusMode && !isSelected;
      const isPinned = node.fx !== undefined && node.fy !== undefined;

      const r = 24;
      const x = node.x;
      const y = node.y;

      ctx.save();
      ctx.globalAlpha = isDimmed ? 0.15 : 1.0;

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, r + 9, 0, 2 * Math.PI, false);
        ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x, y, r + 4, 0, 2 * Math.PI, false);
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI, false);
      ctx.fillStyle = node.color || '#2563eb';
      ctx.fill();

      ctx.strokeStyle = isSelected ? '#ffffff' : isPinned ? '#fbbf24' : node.borderColor || '#60a5fa';
      ctx.lineWidth = isSelected ? 3 : isPinned ? 2.5 : 2;
      ctx.stroke();

      ctx.font = 'bold 12px system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(node.initials || '', x, y);

      const labelText = node.label || '';
      ctx.font = 'bold 10.5px system-ui, sans-serif';
      const textWidth = ctx.measureText(labelText).width;
      const badgeW = textWidth + 14;
      const badgeH = 20;
      const badgeX = x - badgeW / 2;
      const badgeY = y + r + 7;

      ctx.fillStyle = '#090d16';
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 5);
      } else {
        ctx.rect(badgeX, badgeY, badgeW, badgeH);
      }
      ctx.fill();

      ctx.strokeStyle = isSelected ? '#38bdf8' : isPinned ? '#fbbf24' : '#334155';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.fillStyle = isSelected ? '#38bdf8' : isPinned ? '#fef08a' : '#f8fafc';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, x, badgeY + badgeH / 2);

      ctx.restore();
    },
    [selectedNode, isFocusMode]
  );

  const drawLink = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      void globalScale;
      const isSelected = selectedEdge?.id === link.id || hoveredEdge?.id === link.id;
      const isDimmed = isFocusMode && !isSelected;

      const start = link.source;
      const end = link.target;
      if (!start || !end || typeof start.x !== 'number' || typeof end.x !== 'number') return;

      const midX = (start.x + end.x) / 2 + (link.curvature || 0) * (end.y - start.y) * 0.4;
      const midY = (start.y + end.y) / 2 - (link.curvature || 0) * (end.x - start.x) * 0.4;

      ctx.save();
      ctx.globalAlpha = isDimmed ? 0.08 : 1.0;

      let angle = Math.atan2(end.y - start.y, end.x - start.x);
      if (angle > Math.PI / 2) angle -= Math.PI;
      if (angle < -Math.PI / 2) angle += Math.PI;

      ctx.save();
      ctx.translate(midX, midY);
      ctx.rotate(angle);

      const labelText = link.label || '';
      ctx.font = 'bold 8.5px system-ui, sans-serif';
      const textWidth = ctx.measureText(labelText).width;
      const padW = textWidth + 10;
      const padH = 16;

      ctx.fillStyle = link.isContradiction ? '#450a0a' : isSelected ? '#0369a1' : '#090d16';
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(-padW / 2, -padH / 2, padW, padH, 4);
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
        <p className="text-xs font-semibold text-text-primary">Po ngarkohet Ontologjia e Provave...</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 h-full w-full relative bg-canvas overflow-hidden flex items-center justify-center">
      <ForceGraph2D
        ref={fgRef as any}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        backgroundColor="rgba(0,0,0,0)"
        nodeRelSize={24}
        nodeCanvasObject={drawNode}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 28, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
        linkCanvasObjectMode={() => 'after'}
        linkCanvasObject={drawLink}
        linkCurvature="curvature"
        linkColor={(link: any) =>
          link.isContradiction
            ? '#ef4444'
            : selectedEdge?.id === link.id
            ? '#38bdf8'
            : '#475569'
        }
        linkWidth={(link: any) =>
          link.isContradiction || selectedEdge?.id === link.id ? 2.5 : 1.8
        }
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={0.85}
        linkDirectionalArrowColor={(link: any) =>
          link.isContradiction
            ? '#ef4444'
            : selectedEdge?.id === link.id
            ? '#38bdf8'
            : '#64748b'
        }
        linkLineDash={(link: any) => (link.isContradiction ? [5, 3] : null)}
        onNodeClick={(node: any) => onSelectNode(node.rawNode)}
        onLinkClick={(link: any) => onSelectEdge(link.rawEdge)}
        onLinkHover={(link: any) => onHoverEdge(link ? link.rawEdge : null)}
        onNodeDragEnd={(node: any) => {
          node.fx = node.x;
          node.fy = node.y;
        }}
        onNodeRightClick={(node: any) => {
          node.fx = undefined;
          node.fy = undefined;
          if (fgRef.current) {
            fgRef.current.d3ReheatSimulation();
          }
        }}
        onBackgroundClick={() => {
          onSelectNode(null);
          onSelectEdge(null);
          onHoverEdge(null);
        }}
        cooldownTicks={120}
      />

      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 bg-surface border border-main p-2 rounded-2xl shadow-2xl z-20 text-text-primary">
        <button
          type="button"
          onClick={handleZoomIn}
          className="p-2 text-text-secondary hover:text-text-primary hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Zmadho"
        >
          <ZoomIn size={16} />
        </button>
        <button
          type="button"
          onClick={handleResetView}
          className="p-2 text-text-secondary hover:text-text-primary hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Qendërzo Rrjetin"
        >
          <Maximize2 size={15} />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="p-2 text-text-secondary hover:text-text-primary hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Zvogëlo"
        >
          <ZoomOut size={16} />
        </button>
        <div className="h-4 w-px bg-main mx-1" />
        <button
          type="button"
          onClick={handleResetSimulationAndUnpin}
          className="p-2 text-primary-start hover:bg-canvas rounded-xl transition-all focus:outline-none"
          title="Liro të gjitha nyjet dhe Ri-kalkulo Fizikën"
        >
          <RotateCcw size={15} />
        </button>
      </div>
    </div>
  );
};

export default EvidenceCanvas;