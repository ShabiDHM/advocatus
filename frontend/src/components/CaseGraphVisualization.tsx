import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    FileText, ShieldAlert, Scale, BrainCircuit, Search, 
    Sparkles, Gavel, Users, Banknote, AlertTriangle, ArrowRight, FileCheck, Landmark
} from 'lucide-react';

// --- CONFIGURATION ---
const CARD_WIDTH = 240;
const CARD_HEIGHT = 90;
const BORDER_RADIUS = 4;

interface CaseGraphProps {
    caseId: string;
}

// --- TYPE EXTENSION ---
// We extend the base GraphNode to include the physics coordinates 
// that the library injects at runtime.
interface SimulationNode extends GraphNode {
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
}

// --- REAL DATA INTERFACE ---
interface RealAnalysisData {
    summary: string;
    strategic_value: string;
    confidence_score: number;
    financial_impact?: string;
}

// --- REAL API CALL ---
// We prefix arguments with "_" to tell TypeScript: "We know these are unused right now, 
// but keep them in the signature because we will connect them to the backend soon."
const fetchRealNodeAnalysis = async (_caseId: string, _nodeId: string): Promise<RealAnalysisData | null> => {
    try {
        // ACTUAL BACKEND CONNECTION WILL GO HERE:
        // const response = await apiService.getNodeAnalysis(_caseId, _nodeId);
        // return response;
        
        // For now, return null to show the "No Intelligence Found" state correctly
        return null; 
    } catch (error) {
        console.error("Failed to fetch node analysis", error);
        return null;
    }
};

const THEME = {
  colors: {
    judge:   '#dc2626', // Red
    court:   '#334155', // Slate Dark
    person:  '#059669', // Emerald
    document:'#2563eb', // Blue
    money:   '#d97706', // Amber
    evidence:'#ea580c', // Orange
    default: '#64748b'  // Slate Light
  },
  bgColors: {
    judge:   '#fef2f2', 
    court:   '#f1f5f9',
    person:  '#ecfdf5',
    document:'#eff6ff',
    money:   '#fffbeb',
    evidence:'#fff7ed',
    default: '#f8fafc'
  },
  icons: {
    judge:   '⚖️',
    court:   '🏛️',
    person:  '👤',
    document:'📄',
    money:   '💰',
    evidence:'cj',
    default: '🔹'
  }
};

const normalizeGroup = (group: string | undefined): string => {
    const g = (group || '').toUpperCase();
    if (g.includes('JUDGE')) return 'judge';
    if (g.includes('COURT')) return 'court';
    if (g.includes('PERSON') || g.includes('USER') || g.includes('CLIENT')) return 'person';
    if (g.includes('MONEY') || g.includes('AMOUNT') || g.includes('FINANCE')) return 'money';
    if (g.includes('DOC') || g.includes('FILE') || g.includes('PDF') || g.includes('PADI') || g.includes('AKTGJYKIM')) return 'document';
    if (g.includes('EVIDENCE')) return 'evidence';
    return 'default';
};

const getNodeIcon = (group: string) => {
    const g = group.toLowerCase();
    if (g === 'judge') return <Gavel size={24} className="text-red-600" />;
    if (g === 'court') return <Landmark size={24} className="text-slate-600" />;
    if (g === 'person') return <Users size={24} className="text-emerald-600" />;
    if (g === 'money') return <Banknote size={24} className="text-amber-600" />;
    if (g === 'document') return <FileText size={24} className="text-blue-600" />;
    if (g === 'evidence') return <AlertTriangle size={24} className="text-orange-600" />;
    return <Scale size={24} className="text-slate-500" />;
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

// --- COMPONENT START ---
const CaseGraphVisualization: React.FC<CaseGraphProps> = ({ caseId }) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const { width, height } = useResizeObserver(containerRef);
  
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  
  // Use SimulationNode type here to fix the x/y errors
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);
  
  // Real Analysis State
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [realAnalysis, setRealAnalysis] = useState<RealAnalysisData | null>(null);
  
  const fgRef = useRef<ForceGraphMethods>();

  useEffect(() => {
    if (!caseId) return;
    let isMounted = true;
    const loadGraph = async () => {
        setIsLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            if (isMounted) {
                const validNodes = graphData.nodes.map((n: any) => ({ ...n }));
                const validLinks = graphData.links.map((l: any) => ({ ...l }));
                setData({ nodes: validNodes, links: validLinks });
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

  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        graph.d3Force('charge')?.strength(-3000); 
        graph.d3Force('link')?.distance(180).strength(0.8);
        graph.d3Force('center')?.strength(0.4);
        
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(600, 80), 800);
        }
    }
  }, [data]);

  const handleNodeClick = async (node: SimulationNode) => {
      setSelectedNode(node);
      
      setAnalysisLoading(true);
      setRealAnalysis(null); 
      
      const analysis = await fetchRealNodeAnalysis(caseId, node.id);
      
      setAnalysisLoading(false);
      setRealAnalysis(analysis);
      
      if (node.x !== undefined && node.y !== undefined) {
          fgRef.current?.centerAt(node.x, node.y, 800);
          fgRef.current?.zoom(1.1, 800);
      }
  };

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const normGroup = normalizeGroup(node.group);
    const primaryColor = (THEME.colors as any)[normGroup];
    const bgColor = (THEME.bgColors as any)[normGroup];
    const icon = (THEME.icons as any)[normGroup];
    
    const scale = node.id === selectedNode?.id ? 1.15 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    const x = node.x!;
    const y = node.y!;
    const r = BORDER_RADIUS * scale;

    // Shadow
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
    ctx.shadowBlur = node.id === selectedNode?.id ? 25 : 10;
    ctx.shadowOffsetY = 4;

    // Card Base
    ctx.fillStyle = '#ffffff'; 
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2, w, h, r);
    ctx.fill();
    ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;

    // Top Strip
    ctx.fillStyle = primaryColor;
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2, w, 5 * scale, [r, r, 0, 0]);
    ctx.fill();

    // Icon Area
    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2 + (5 * scale), 48 * scale, h - (5 * scale), [0, 0, 0, r]);
    ctx.fill();
    
    // Separator
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x - w/2 + (48 * scale), y - h/2 + (5 * scale));
    ctx.lineTo(x - w/2 + (48 * scale), y + h/2);
    ctx.stroke();

    // Icon
    ctx.font = `${20 * scale}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon, x - w/2 + (24 * scale), y + (2 * scale));

    // Text Content
    const textStartX = x - w/2 + (60 * scale);
    
    ctx.font = `700 ${10 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = primaryColor;
    ctx.textAlign = 'left';
    ctx.fillText(normGroup.toUpperCase(), textStartX, y - (10 * scale));

    ctx.font = `bold ${12 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#0f172a';
    let label = node.name || node.id;
    if (label.length > 22) label = label.substring(0, 21) + '...';
    ctx.fillText(label, textStartX, y + (5 * scale));

    // Selection Border
    if (node.id === selectedNode?.id) {
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.roundRect(x - w/2, y - h/2, w, h, r);
        ctx.stroke();
    }
  }, [selectedNode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-sans">
        <div ref={containerRef} className="lg:col-span-2 relative w-full h-[650px] bg-slate-950 rounded border border-slate-800 shadow-2xl overflow-hidden">
            
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-slate-900/95 backdrop-blur px-4 py-2 rounded border border-slate-700 shadow-lg pointer-events-none">
                <ShieldAlert size={14} className="text-emerald-500" />
                <span className="text-xs font-bold text-slate-100 uppercase tracking-widest">{t('caseGraph.title', 'CASE INTELLIGENCE MAP')}</span>
            </div>

            {isLoading && ( 
                <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-950/90 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-4">
                        <Scale className="w-8 h-8 text-slate-500 animate-bounce" />
                        <span className="text-xs font-mono text-slate-400 tracking-[0.2em]">{t('caseGraph.loading', 'INITIALIZING NEURAL GRAPH...')}</span>
                    </div>
                </div> 
            )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={data}
                nodeCanvasObject={nodeCanvasObject}
                nodePointerAreaPaint={(node: any, color, ctx) => {
                    ctx.fillStyle = color;
                    const w = CARD_WIDTH;
                    const h = CARD_HEIGHT;
                    ctx.fillRect(node.x! - w/2, node.y! - h/2, w, h);
                }}
                backgroundColor="#0f172a" 
                
                // --- STRICT ARROWS CONFIGURATION ---
                linkDirectionalArrowLength={6} 
                linkDirectionalArrowRelPos={1} 
                linkDirectionalArrowColor={() => '#cbd5e1'} 
                linkColor={() => '#475569'} 
                linkWidth={1.5}
                
                onNodeClick={(node) => handleNodeClick(node as SimulationNode)}
                onBackgroundClick={() => { setSelectedNode(null); setRealAnalysis(null); }}
                minZoom={0.2}
                maxZoom={4.0}
            />
        </div>

        {/* SIDE PANEL */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded h-[650px] flex flex-col shadow-xl overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-slate-400" />
                    {t('caseGraph.panelTitle', 'Analysis Panel')}
                </h3>
                <div className="w-2 h-2 rounded-full bg-emerald-500" title="System Online"></div>
            </div>

            <div className="flex-grow p-6 overflow-y-auto custom-scrollbar bg-white">
                {selectedNode ? (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        {/* Node Info */}
                        <div className="flex items-start gap-4 mb-6">
                            <div className="w-12 h-12 rounded bg-slate-50 flex items-center justify-center border border-slate-200 shrink-0">
                                {getNodeIcon(normalizeGroup(selectedNode.group))}
                            </div>
                            <div>
                                <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-1 text-white bg-slate-800">
                                    {normalizeGroup(selectedNode.group)}
                                </span>
                                <h2 className="text-xl font-bold text-slate-900 leading-tight">{selectedNode.name}</h2>
                            </div>
                        </div>

                        {/* Analysis Section */}
                        <div className="mt-6">
                            <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="text-amber-500" size={16} />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-widest">
                                    {t('caseGraph.aiTitle', 'AI ANALYSIS')}
                                </span>
                            </div>

                            {/* LOADING STATE FOR ANALYSIS */}
                            {analysisLoading && (
                                <div className="p-4 bg-slate-50 border border-slate-100 rounded text-center">
                                    <BrainCircuit className="w-6 h-6 text-indigo-500 animate-spin mx-auto mb-2" />
                                    <p className="text-xs text-slate-500">Retrieving intelligence from Server...</p>
                                </div>
                            )}

                            {/* REAL DATA DISPLAY */}
                            {!analysisLoading && realAnalysis && (
                                <div className="bg-slate-900 text-white p-5 rounded border border-slate-800 shadow-md">
                                    <h4 className="text-[10px] font-bold text-slate-400 uppercase mb-2">Summary</h4>
                                    <p className="text-sm font-light leading-relaxed mb-4 border-l-2 border-indigo-500 pl-3">
                                        {realAnalysis.summary}
                                    </p>
                                    
                                    <h4 className="text-[10px] font-bold text-emerald-400 uppercase mb-2">Strategic Value</h4>
                                    <p className="text-sm font-medium">
                                        {realAnalysis.strategic_value}
                                    </p>
                                </div>
                            )}

                            {/* NO DATA STATE */}
                            {!analysisLoading && !realAnalysis && (
                                <div className="p-4 bg-orange-50 border border-orange-100 rounded">
                                    <div className="flex items-center gap-2 mb-1">
                                        <AlertTriangle size={14} className="text-orange-500" />
                                        <h4 className="text-xs font-bold text-orange-700 uppercase">No Intelligence Found</h4>
                                    </div>
                                    <p className="text-xs text-orange-600 leading-relaxed">
                                        The backend has not processed this node yet. 
                                        Please run the "Deep Scan" on this document in the Documents tab.
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Action Buttons */}
                        <div className="mt-6 pt-6 border-t border-slate-100">
                            <button className="w-full py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-bold uppercase rounded flex items-center justify-center gap-2 transition-colors">
                                <FileCheck size={14} />
                                Open Document
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-60">
                        <ArrowRight size={24} className="text-slate-300 mb-4" />
                        <h3 className="text-sm font-bold text-slate-400">Waiting for Selection</h3>
                        <p className="text-xs text-slate-400">Select a node to view server data.</p>
                    </div>
                )}
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;