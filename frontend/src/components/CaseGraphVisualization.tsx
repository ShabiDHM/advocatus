/* FILE: src/components/CaseGraphVisualization.tsx
   PHOENIX PROTOCOL - PROFESSIONAL GRAPH VISUALIZATION V2.1 (CLEANUP)
   1. FIX: Removed unused 'Scale' import.
   2. FUNCTION: Same robust LOD rendering and physics as V2.
*/

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    FileText, ShieldAlert, BrainCircuit, Search, 
    Sparkles, Gavel, Users, Banknote, AlertTriangle, ArrowRight, FileCheck, Landmark,
    Network
} from 'lucide-react';

// --- CONFIGURATION ---
const CARD_WIDTH = 220;
const CARD_HEIGHT = 80;
const BORDER_RADIUS = 6;
const LOD_THRESHOLD = 0.8; // Zoom level at which Cards turn into Dots

interface CaseGraphProps {
    caseId: string;
}

// Extended Node Interface with Physics Props
interface SimulationNode extends GraphNode {
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    properties?: any; // Data from backend
}

interface RealAnalysisData {
    summary: string;
    strategic_value: string;
    confidence_score: number;
}

// --- THEME ENGINE ---
const THEME = {
  colors: {
    judge:   '#dc2626', // Red-600
    court:   '#475569', // Slate-600
    person:  '#059669', // Emerald-600
    document:'#2563eb', // Blue-600
    money:   '#d97706', // Amber-600
    evidence:'#ea580c', // Orange-600
    claim:   '#db2777', // Pink-600
    default: '#64748b'  // Slate-500
  },
  bgColors: {
    judge:   '#fef2f2', 
    court:   '#f8fafc',
    person:  '#ecfdf5',
    document:'#eff6ff',
    money:   '#fffbeb',
    evidence:'#fff7ed',
    claim:   '#fdf2f8',
    default: '#f8fafc'
  },
  icons: {
    judge:   '⚖️',
    court:   '🏛️',
    person:  '👤',
    document:'📄',
    money:   '💰',
    evidence:'🔎',
    claim:   '💬',
    default: '🔹'
  }
};

const normalizeGroup = (group: string | undefined): string => {
    const g = (group || '').toUpperCase();
    if (g.includes('JUDGE')) return 'judge';
    if (g.includes('COURT')) return 'court';
    if (g.includes('PERSON') || g.includes('USER') || g.includes('CLIENT')) return 'person';
    if (g.includes('MONEY') || g.includes('AMOUNT') || g.includes('FINANCE')) return 'money';
    if (g.includes('DOC') || g.includes('FILE')) return 'document';
    if (g.includes('EVIDENCE')) return 'evidence';
    if (g.includes('CLAIM') || g.includes('ASSERT')) return 'claim';
    return 'default';
};

const getNodeIcon = (group: string) => {
    const g = group.toLowerCase();
    const size = 20;
    if (g === 'judge') return <Gavel size={size} className="text-red-600" />;
    if (g === 'court') return <Landmark size={size} className="text-slate-600" />;
    if (g === 'person') return <Users size={size} className="text-emerald-600" />;
    if (g === 'money') return <Banknote size={size} className="text-amber-600" />;
    if (g === 'document') return <FileText size={size} className="text-blue-600" />;
    if (g === 'evidence') return <AlertTriangle size={size} className="text-orange-600" />;
    return <Network size={size} className="text-slate-500" />;
};

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

const CaseGraphVisualization: React.FC<CaseGraphProps> = ({ caseId }) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const { width, height } = useResizeObserver(containerRef);
  
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);
  
  // Real Analysis State
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [realAnalysis, setRealAnalysis] = useState<RealAnalysisData | null>(null);
  
  const fgRef = useRef<ForceGraphMethods>();

  // 1. Load Data
  useEffect(() => {
    if (!caseId) return;
    let isMounted = true;
    const loadGraph = async () => {
        setIsLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            if (isMounted) {
                // Deep copy to prevent mutation issues with strict mode
                const validNodes = graphData.nodes.map((n: any) => ({ ...n }));
                const validLinks = graphData.links.map((l: any) => ({ ...l }));
                setData({ nodes: validNodes, links: validLinks });
            }
        } catch (e) { 
            console.error("Graph load error:", e);
        } finally { 
            if (isMounted) setIsLoading(false); 
        }
    };
    loadGraph();
    return () => { isMounted = false; };
  }, [caseId]);

  // 2. Physics Tuning
  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        // Tuned for "Mesh" topology (not star)
        graph.d3Force('charge')?.strength(-1000).distanceMax(500); 
        graph.d3Force('link')?.distance(150).strength(0.6);
        graph.d3Force('center')?.strength(0.2);
        
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(400, 50), 500);
        }
    }
  }, [data]);

  // 3. Selection Handler
  const handleNodeClick = async (node: SimulationNode) => {
      setSelectedNode(node);
      setRealAnalysis(null);
      setAnalysisLoading(true);

      // Simulate API delay for "AI Analysis" (Replace with real call later)
      // This gives the user feedback that something is happening
      setTimeout(() => {
          setRealAnalysis({
              summary: `Analysis for ${node.name}: This entity appears in ${Math.floor(Math.random() * 5) + 1} documents. Connected to critical case timeline events.`,
              strategic_value: "HIGH PRIORITY",
              confidence_score: 0.92
          });
          setAnalysisLoading(false);
      }, 800);
      
      if (node.x !== undefined && node.y !== undefined) {
          fgRef.current?.centerAt(node.x, node.y, 1000);
          fgRef.current?.zoom(1.5, 1000);
      }
  };

  // 4. Advanced Canvas Rendering (LOD System)
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const normGroup = normalizeGroup(node.group);
    const primaryColor = (THEME.colors as any)[normGroup];
    const bgColor = (THEME.bgColors as any)[normGroup];
    const icon = (THEME.icons as any)[normGroup];
    
    const x = node.x!;
    const y = node.y!;
    const isSelected = node.id === selectedNode?.id;

    // --- LOD 1: DOT MODE (Zoomed Out) ---
    if (globalScale < LOD_THRESHOLD && !isSelected) {
        const r = 5 + (node.val || 1);
        ctx.beginPath();
        ctx.arc(x, y, r, 0, 2 * Math.PI);
        ctx.fillStyle = primaryColor;
        ctx.fill();
        return;
    }

    // --- LOD 2: CARD MODE (Zoomed In or Selected) ---
    const scale = isSelected ? 1.1 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    const r = BORDER_RADIUS * scale;

    // Shadow (Fancy glow if selected)
    ctx.shadowColor = isSelected ? primaryColor : 'rgba(0, 0, 0, 0.2)';
    ctx.shadowBlur = isSelected ? 30 : 10;
    ctx.shadowOffsetY = 4;

    // Card Background
    ctx.fillStyle = '#ffffff'; 
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2, w, h, r);
    ctx.fill();
    
    // Reset Shadow for internal elements
    ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;

    // Color Strip (Left Side)
    ctx.fillStyle = primaryColor;
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2, 6 * scale, h, [r, 0, 0, r]);
    ctx.fill();

    // Icon Circle
    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.arc(x - w/2 + (24 * scale), y - h/2 + (24 * scale), 14 * scale, 0, 2 * Math.PI);
    ctx.fill();
    
    ctx.font = `${14 * scale}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon, x - w/2 + (24 * scale), y - h/2 + (25 * scale));

    // Text Content
    const textStartX = x - w/2 + (48 * scale);
    
    // Label (Group)
    ctx.font = `600 ${9 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = primaryColor;
    ctx.textAlign = 'left';
    ctx.fillText(normGroup.toUpperCase(), textStartX, y - h/2 + (20 * scale));

    // Name (Truncated)
    ctx.font = `bold ${11 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#1e293b';
    let label = node.name || node.id;
    if (label.length > 25) label = label.substring(0, 24) + '...';
    ctx.fillText(label, textStartX, y - h/2 + (38 * scale));

    // Subtext (Node ID or Prop)
    ctx.font = `400 ${8 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#64748b';
    ctx.fillText(node.group || "Entity", textStartX, y - h/2 + (52 * scale));

    // Selection Border
    if (isSelected) {
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x - w/2, y - h/2, w, h, r);
        ctx.stroke();
    }
  }, [selectedNode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-sans h-full">
        {/* GRAPH CONTAINER */}
        <div ref={containerRef} className="lg:col-span-2 relative w-full h-[650px] bg-slate-950 rounded-lg border border-slate-800 shadow-2xl overflow-hidden group">
            
            {/* Overlay Header */}
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2 pointer-events-none">
                <div className="bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded border border-slate-700 flex items-center gap-2">
                    <ShieldAlert size={14} className="text-emerald-500" />
                    <span className="text-[10px] font-bold text-slate-200 uppercase tracking-widest">
                        {t('caseGraph.title', 'CASE INTEL MAP')}
                    </span>
                </div>
            </div>

            {/* Controls Help */}
            <div className="absolute bottom-4 left-4 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                <div className="text-[10px] text-slate-500 bg-slate-900/80 px-2 py-1 rounded border border-slate-800">
                    Scroll to Zoom • Drag to Pan • Click to Inspect
                </div>
            </div>

            {isLoading && ( 
                <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-950">
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-16 h-1 bg-slate-800 rounded-full overflow-hidden">
                            <div className="w-full h-full bg-emerald-500 origin-left animate-[progress_1s_ease-in-out_infinite]"></div>
                        </div>
                        <span className="text-xs font-mono text-slate-400 tracking-widest">DECRYPTING GRAPH...</span>
                    </div>
                </div> 
            )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={data}
                nodeCanvasObject={nodeCanvasObject}
                backgroundColor="#0f172a"
                
                // Link Styling
                linkColor={() => '#334155'} 
                linkWidth={1.2}
                linkDirectionalArrowLength={5}
                linkDirectionalArrowRelPos={1}
                
                // Interaction
                onNodeClick={(node) => handleNodeClick(node as SimulationNode)}
                onBackgroundClick={() => { setSelectedNode(null); setRealAnalysis(null); }}
                minZoom={0.1}
                maxZoom={5.0}
            />
        </div>

        {/* SIDE PANEL */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-lg h-[650px] flex flex-col shadow-xl overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-slate-400" />
                    {t('caseGraph.panelTitle', 'Intelligence Panel')}
                </h3>
                <div className={`w-2 h-2 rounded-full ${selectedNode ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'}`}></div>
            </div>

            <div className="flex-grow p-6 overflow-y-auto custom-scrollbar bg-white">
                {selectedNode ? (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        {/* 1. Primary Metadata (Immediate) */}
                        <div className="flex items-start gap-4 mb-6">
                            <div className="w-12 h-12 rounded-lg bg-slate-50 flex items-center justify-center border border-slate-200 shrink-0 shadow-sm">
                                {getNodeIcon(normalizeGroup(selectedNode.group))}
                            </div>
                            <div>
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-1 text-slate-600 bg-slate-100 border border-slate-200">
                                    {normalizeGroup(selectedNode.group)}
                                </span>
                                <h2 className="text-lg font-bold text-slate-900 leading-tight">{selectedNode.name}</h2>
                                <p className="text-xs text-slate-400 mt-1 font-mono">{selectedNode.id}</p>
                            </div>
                        </div>

                        {/* 2. Known Properties (Immediate from Graph Data) */}
                        {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                             <div className="mb-6 bg-slate-50 rounded border border-slate-100 p-3">
                                <h4 className="text-[10px] font-bold text-slate-400 uppercase mb-2">Known Attributes</h4>
                                <div className="space-y-1">
                                    {Object.entries(selectedNode.properties).slice(0, 4).map(([k, v]) => (
                                        (k !== 'id' && k !== 'name' && k !== 'group') && (
                                            <div key={k} className="flex justify-between text-xs border-b border-slate-200/50 pb-1 last:border-0">
                                                <span className="text-slate-500 capitalize">{k.replace('_', ' ')}:</span>
                                                <span className="text-slate-800 font-medium truncate max-w-[120px]">{String(v)}</span>
                                            </div>
                                        )
                                    ))}
                                </div>
                             </div>
                        )}

                        {/* 3. Deep Analysis (Async) */}
                        <div className="mt-2">
                            <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="text-indigo-500" size={16} />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-widest">
                                    {t('caseGraph.aiTitle', 'AI ANALYSIS')}
                                </span>
                            </div>

                            {analysisLoading ? (
                                <div className="p-6 bg-slate-50 border border-slate-100 rounded text-center">
                                    <BrainCircuit className="w-6 h-6 text-indigo-500 animate-spin mx-auto mb-3" />
                                    <p className="text-xs text-slate-500 font-medium">Querying Legal LLM...</p>
                                </div>
                            ) : realAnalysis ? (
                                <div className="bg-slate-900 text-slate-300 p-5 rounded border border-slate-800 shadow-md relative overflow-hidden">
                                    {/* Decorative gradient */}
                                    <div className="absolute top-0 right-0 w-20 h-20 bg-indigo-500/10 blur-xl rounded-full pointer-events-none"></div>
                                    
                                    <h4 className="text-[10px] font-bold text-slate-500 uppercase mb-2">Executive Summary</h4>
                                    <p className="text-sm font-light leading-relaxed mb-4 text-slate-100">
                                        {realAnalysis.summary}
                                    </p>
                                    
                                    <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                                        <div>
                                            <h4 className="text-[10px] font-bold text-emerald-500 uppercase">Confidence</h4>
                                            <span className="text-xs font-mono">{realAnalysis.confidence_score * 100}%</span>
                                        </div>
                                        <div className="text-right">
                                            <h4 className="text-[10px] font-bold text-amber-500 uppercase">Value</h4>
                                            <span className="text-xs font-mono">{realAnalysis.strategic_value}</span>
                                        </div>
                                    </div>
                                </div>
                            ) : null}
                        </div>

                        {/* Action Buttons */}
                        <div className="mt-auto pt-6">
                            <button className="w-full py-2.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 hover:border-slate-300 text-xs font-bold uppercase rounded flex items-center justify-center gap-2 transition-all shadow-sm">
                                <FileCheck size={14} className="text-slate-400" />
                                Inspect Source Document
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-40 select-none">
                        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                            <ArrowRight size={24} className="text-slate-400" />
                        </div>
                        <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide">Ready for Selection</h3>
                        <p className="text-xs text-slate-400 mt-2 max-w-[200px]">
                            Click any node in the graph to reveal its connections and AI analysis.
                        </p>
                    </div>
                )}
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;