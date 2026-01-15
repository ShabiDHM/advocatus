// FILE: frontend/src/components/CaseGraphVisualization.tsx
import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { 
    FileText, ShieldAlert, Scale, X 
} from 'lucide-react';

// --- Configuration ---
const CARD_WIDTH = 160;
const CARD_HEIGHT = 60;
const BORDER_RADIUS = 4;

interface CaseGraphProps {
    caseId: string;
}

// --- NATIVE RESIZE HOOK ---
function useResizeObserver(ref: React.RefObject<HTMLElement>) {
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    useEffect(() => {
        if (!ref.current) return;
        const resizeObserver = new ResizeObserver((entries) => {
            if (entries[0]) {
                const { width, height } = entries[0].contentRect;
                setDimensions({ width, height });
            }
        });
        resizeObserver.observe(ref.current);
        return () => resizeObserver.disconnect();
    }, [ref]);
    return dimensions;
}

// --- LEGAL THEME ---
const THEME = {
  node: {
    judge:   { bg: '#450a0a', border: '#ef4444', text: '#fecaca' },
    court:   { bg: '#1c1917', border: '#a8a29e', text: '#e7e5e4' },
    claim:   { bg: '#172554', border: '#3b82f6', text: '#dbeafe' },
    person:  { bg: '#064e3b', border: '#10b981', text: '#d1fae5' },
    document:{ bg: '#374151', border: '#9ca3af', text: '#f3f4f6' },
    evidence:{ bg: '#7c2d12', border: '#f97316', text: '#ffedd5' },
    default: { bg: '#111827', border: '#4b5563', text: '#e5e7eb' },
  }
};

const CaseGraphVisualization: React.FC<CaseGraphProps> = ({ caseId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { width, height } = useResizeObserver(containerRef);
  
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  
  const fgRef = useRef<ForceGraphMethods>();

  // 1. Fetch Data
  useEffect(() => {
    if (!caseId) return;
    
    let isMounted = true;
    const loadGraph = async () => {
        setIsLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            
            if (isMounted) {
                setData({
                    nodes: graphData.nodes.map((n: any) => ({ ...n })),
                    links: graphData.links.map((l: any) => ({ ...l }))
                });
            }
        } catch (e) {
            console.error("Failed to load case graph:", e);
        } finally {
            if (isMounted) setIsLoading(false);
        }
    };
    loadGraph();
    return () => { isMounted = false; };
  }, [caseId]);

  // 2. Physics Engine
  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        graph.d3Force('charge')?.strength(-1000);
        graph.d3Force('link')?.distance(150);
        graph.d3Force('center')?.strength(0.3);
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(600, 50), 500);
        }
    }
  }, [data]);

  // 3. Canvas Renderer
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const group = (node.group || 'Default').toLowerCase();
    const styleKey = Object.keys(THEME.node).find(k => group.includes(k)) || 'default';
    const style = (THEME.node as any)[styleKey];
    
    const x = node.x!;
    const y = node.y!;
    const isSelected = node.id === selectedNode?.id;

    ctx.shadowBlur = isSelected ? 20 : 0;
    ctx.shadowColor = style.border;

    ctx.fillStyle = style.bg;
    ctx.strokeStyle = isSelected ? '#ffffff' : style.border;
    ctx.lineWidth = isSelected ? 2 : 1;
    
    ctx.beginPath();
    ctx.roundRect(x - CARD_WIDTH / 2, y - CARD_HEIGHT / 2, CARD_WIDTH, CARD_HEIGHT, BORDER_RADIUS);
    ctx.fill();
    ctx.stroke();
    
    ctx.shadowBlur = 0; 

    ctx.fillStyle = style.border;
    ctx.globalAlpha = 0.2;
    ctx.beginPath();
    ctx.roundRect(x - CARD_WIDTH / 2, y - CARD_HEIGHT / 2, CARD_WIDTH, 20, [BORDER_RADIUS, BORDER_RADIUS, 0, 0]);
    ctx.fill();
    ctx.globalAlpha = 1.0;

    ctx.font = `600 9px "Inter", sans-serif`;
    ctx.fillStyle = style.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(node.group.toUpperCase(), x, y - CARD_HEIGHT / 2 + 10);

    ctx.font = `bold 12px "Inter", sans-serif`;
    ctx.fillStyle = '#ffffff';
    let label = node.name || node.id;
    if (label.length > 20) label = label.substring(0, 18) + '...';
    ctx.fillText(label, x, y + 5);

  }, [selectedNode]);

  // 4. Hit Detection
  const nodePointerAreaPaint = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    ctx.fillStyle = color;
    const x = node.x!;
    const y = node.y!;
    ctx.beginPath();
    ctx.roundRect(x - CARD_WIDTH / 2, y - CARD_HEIGHT / 2, CARD_WIDTH, CARD_HEIGHT, BORDER_RADIUS);
    ctx.fill();
  }, []);

  return (
    <div ref={containerRef} className="relative w-full h-[600px] bg-slate-950 rounded-lg overflow-hidden border border-slate-800 shadow-xl flex flex-col">
        <div className="absolute top-4 left-4 z-10 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded border border-slate-700 flex items-center gap-2">
            <ShieldAlert size={14} className="text-red-500" />
            <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">Case Intelligence Map</span>
        </div>

        {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-950/80 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-3">
                    <Scale className="w-8 h-8 text-slate-500 animate-pulse" />
                    <span className="text-xs font-mono text-slate-400">ANALYZING EVIDENCE...</span>
                </div>
            </div>
        )}

        {!isLoading && data.nodes.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none">
                <FileText className="w-12 h-12 text-slate-700 mb-4" />
                <h3 className="text-lg font-bold text-slate-500">No Graph Data</h3>
                <p className="text-xs text-slate-600">Upload documents or add parties to generate the map.</p>
            </div>
        )}

        <ForceGraph2D
            ref={fgRef}
            width={width}
            height={height}
            graphData={data}
            nodeCanvasObject={nodeCanvasObject}
            nodePointerAreaPaint={nodePointerAreaPaint}
            backgroundColor="rgba(0,0,0,0)" 
            
            linkColor={() => '#334155'}
            linkWidth={1.5}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            
            onNodeClick={(node) => {
                setSelectedNode(node as GraphNode);
                fgRef.current?.centerAt(node.x, node.y, 600);
                fgRef.current?.zoom(1.2, 600);
            }}
            onBackgroundClick={() => setSelectedNode(null)}
            
            minZoom={0.5}
            maxZoom={3.0}
        />

        {selectedNode && (
            <div className="absolute bottom-4 left-4 right-4 bg-slate-900/95 backdrop-blur border border-slate-700 p-4 rounded-lg shadow-2xl animate-in slide-in-from-bottom-4 duration-300 flex items-center justify-between">
                <div>
                    <h4 className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">{selectedNode.group}</h4>
                    <h3 className="text-lg text-white font-bold">{selectedNode.name}</h3>
                </div>
                <button onClick={() => setSelectedNode(null)} className="p-2 hover:bg-slate-800 rounded-full text-slate-400">
                    <X size={18} />
                </button>
            </div>
        )}
    </div>
  );
};

export default CaseGraphVisualization;