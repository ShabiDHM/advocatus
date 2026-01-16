/* FILE: src/components/CaseGraphVisualization.tsx
   PHOENIX PROTOCOL - LEGAL INTELLIGENCE MAP V7 (VISIBILITY FIX)
   1. CRITICAL FIX: Classifier now checks 'properties.group' to correctly identify People/Judges.
   2. VISIBILITY: Raised dimming floor to 25% so nodes are never invisible.
   3. LOGIC: Any node involved in a CONFLICT link is forced visible, regardless of type.
*/

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphNode } from '../data/types';
import { 
    FileText, Search, Sparkles, Gavel, Users, 
    FileCheck, Landmark, Network, Scale, Banknote, AlertTriangle, Eye
} from 'lucide-react';

// --- CONFIGURATION ---
const NODE_REL_SIZE = 8;
const ARROW_REL_POS = 1;
const ARROW_LENGTH = 5;

interface CaseGraphProps {
    caseId: string;
}

interface SimulationNode extends GraphNode {
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    detectedGroup?: string; 
    displayLabel?: string;
    properties?: any;
}

interface SimulationLink {
    source: SimulationNode | string;
    target: SimulationNode | string;
    label?: string;
    type?: 'CONFLICT' | 'FAMILY' | 'FINANCE' | 'PROCEDURAL';
}

interface RealAnalysisData {
    summary: string;
    strategic_value: string;
    confidence_score: number;
    details: string[];
}

// --- LEGAL THEME ENGINE ---
const THEME = {
  nodes: {
    court:      '#475569', // Slate-600
    judge:      '#dc2626', // Red-600
    person:     '#10b981', // Emerald-500
    document:   '#3b82f6', // Blue-500
    law:        '#d97706', // Amber-600
    default:    '#64748b'
  },
  links: {
    CONFLICT:   '#ef4444', 
    FAMILY:     '#10b981', 
    FINANCE:    '#d97706', 
    PROCEDURAL: '#cbd5e1'
  },
  icons: {
    court:      <Landmark size={24} className="text-slate-700" />,
    judge:      <Gavel size={24} className="text-red-600" />,
    person:     <Users size={24} className="text-emerald-600" />,
    document:   <FileText size={24} className="text-blue-500" />,
    law:        <Scale size={24} className="text-amber-600" />,
    default:    <Network size={24} className="text-slate-400" />
  }
};

// --- ROBUST CLASSIFIER ---
const classifyNode = (node: any): string => {
    // 1. Check Deep Properties First (Critical Fix)
    const propGroup = (node.properties?.group || '').toUpperCase();
    if (propGroup === 'PERSON') return 'person';
    if (propGroup === 'JUDGE') return 'judge';
    if (propGroup === 'COURT') return 'court';
    if (propGroup === 'DOCUMENT') return 'document';

    // 2. Fallback to Name Analysis
    const name = (node.name || '').toLowerCase();
    const rawGroup = (node.group || '').toUpperCase();

    if (rawGroup === 'DOCUMENT') return 'document';
    if (name.includes('gjykata') || name.includes('themelore')) return 'court';
    if (name.includes('ligji') || name.includes('neni')) return 'law';
    if (name.includes('ministria') || name.includes('policia')) return 'court'; 
    if (name.includes('aktvendim') || name.includes('aktgjykim')) return 'document';
    
    // 3. Last Resort
    if (rawGroup === 'PERSON' || rawGroup === 'USER') return 'person';
    
    return 'default';
};

const classifyLink = (label: string): 'CONFLICT' | 'FAMILY' | 'FINANCE' | 'PROCEDURAL' => {
    const l = (label || '').toUpperCase();
    if (['PADITËSE', 'I PADITURI', 'KUNDËRSHTON', 'ACCUSES', 'VS', 'KUNDER'].some(k => l.includes(k))) return 'CONFLICT';
    if (['PRIND', 'BASHKËSHORT', 'VËLLA', 'MOTËR', 'FAMILJA', 'MARTESË'].some(k => l.includes(k))) return 'FAMILY';
    if (['ALIMENTACION', 'BORXH', 'PAGUAN', 'FINANCE', 'MONEY', 'SHUMA', 'DETYRIM'].some(k => l.includes(k))) return 'FINANCE';
    return 'PROCEDURAL';
};

const CaseGraphVisualization: React.FC<CaseGraphProps> = ({ caseId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [height, setHeight] = useState(600);
  
  const [graphData, setGraphData] = useState<{nodes: SimulationNode[], links: SimulationLink[]}>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);
  const [hoverNode, setHoverNode] = useState<SimulationNode | null>(null);
  const [viewMode, setViewMode] = useState<'ALL' | 'PEOPLE_ONLY' | 'DOCS_ONLY'>('ALL');

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [realAnalysis, setRealAnalysis] = useState<RealAnalysisData | null>(null);
  
  const fgRef = useRef<ForceGraphMethods>();

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
        if (entries[0]) {
            setWidth(entries[0].contentRect.width);
            setHeight(entries[0].contentRect.height);
        }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // 1. Load Data
  useEffect(() => {
    if (!caseId) return;
    let isMounted = true;
    const loadGraph = async () => {
        setIsLoading(true);
        try {
            const raw = await apiService.getCaseGraph(caseId);
            if (isMounted) {
                const processedNodes = raw.nodes.map((n: any) => ({
                    ...n,
                    detectedGroup: classifyNode(n),
                    displayLabel: n.name.length > 25 ? n.name.substring(0, 24) + '...' : n.name
                }));
                const processedLinks = raw.links.map((l: any) => ({
                    ...l,
                    type: classifyLink(l.label)
                }));
                setGraphData({ nodes: processedNodes, links: processedLinks });
            }
        } catch (e) { console.error(e); } 
        finally { if (isMounted) setIsLoading(false); }
    };
    loadGraph();
    return () => { isMounted = false; };
  }, [caseId]);

  // 2. Physics - Auto Re-Center when filtering
  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        graph.d3Force('charge')?.strength(-600).distanceMax(500);
        graph.d3Force('link')?.distance(150);
        graph.d3Force('center')?.strength(0.4);
        
        // Slight delay to allow filter to apply before re-centering
        setTimeout(() => {
            if (graphData.nodes.length > 0) graph.zoomToFit(400, 50);
        }, 500);
    }
  }, [graphData, viewMode]);

  // 3. Insight Generation
  const generateInsight = (node: SimulationNode) => {
      const links = graphData.links.filter(l => 
          (l.source as any).id === node.id || (l.target as any).id === node.id
      );

      const conflicts = links.filter(l => l.type === 'CONFLICT');
      const financial = links.filter(l => l.type === 'FINANCE');
      
      let summary = "";
      let details: string[] = [];
      let score = 0.5;

      if (node.detectedGroup === 'law') {
           summary = "Statutory Basis (Legal Authority).";
           score = 0.9;
      } else if (node.detectedGroup === 'court') {
           summary = "Adjudicating Body.";
           score = 0.7;
      } else {
          if (conflicts.length > 0) {
              summary += `⚠️ Involved in ${conflicts.length} Conflict(s). `;
              score += 0.3;
              conflicts.forEach(c => details.push(`Conflict with ${(c.target as any).name}`));
          }
          if (financial.length > 0) {
              summary += `💰 Linked to financial obligations. `;
              score += 0.15;
              financial.forEach(f => details.push(`Financial: "${f.label}"`));
          }
          if (summary === "") summary = "Standard entity with procedural connections.";
      }

      return {
          summary,
          strategic_value: score > 0.8 ? "CRITICAL" : score > 0.6 ? "HIGH" : "STANDARD",
          confidence_score: 0.98,
          details
      };
  };

  const handleNodeClick = (node: SimulationNode) => {
      setSelectedNode(node);
      setRealAnalysis(null);
      setAnalysisLoading(true);

      setTimeout(() => {
          const insight = generateInsight(node);
          setRealAnalysis(insight);
          setAnalysisLoading(false);
      }, 300);

      fgRef.current?.centerAt(node.x, node.y, 800);
      fgRef.current?.zoom(3.0, 800);
  };

  // --- RENDERING LOGIC (The Safe Focus Engine) ---
  
  const isNodeDimmed = (node: SimulationNode) => {
      if (viewMode === 'ALL') return false;
      
      // If selected, never dim
      if (node.id === selectedNode?.id) return false;

      const group = node.detectedGroup || '';
      
      // Check connections: If a node is part of a CONFLICT link, NEVER dim it in Party view
      if (viewMode === 'PEOPLE_ONLY') {
          const isParty = ['person', 'judge'].includes(group);
          if (isParty) return false;

          // Check if this node is connected via Conflict/Finance
          const hasConflict = graphData.links.some(l => 
            ((l.source as any).id === node.id || (l.target as any).id === node.id) && 
            (l.type === 'CONFLICT' || l.type === 'FINANCE')
          );
          if (hasConflict) return false;
          
          return true; // Dim everyone else
      }
      
      if (viewMode === 'DOCS_ONLY') {
          return group !== 'document';
      }
      return false;
  };

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const dimmed = isNodeDimmed(node);
    const group = node.detectedGroup || 'default';
    const color = (THEME.nodes as any)[group] || THEME.nodes.default;
    const isSelected = node.id === selectedNode?.id;
    const isHovered = node.id === hoverNode?.id;

    // DIMMING: 0.25 is safe (visible but faint). 0.1 was too low.
    const alpha = dimmed ? 0.25 : 1;
    const baseSize = dimmed ? 4 : NODE_REL_SIZE; 
    const size = isSelected ? baseSize * 1.5 : baseSize;

    ctx.globalAlpha = alpha;
    
    // Draw Node
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    if ((isSelected || isHovered) && !dimmed) {
        ctx.globalAlpha = 1;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3 / globalScale;
        ctx.stroke();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
    }

    // --- TEXT RENDERING ---
    ctx.globalAlpha = 1; 
    const showText = !dimmed && (isSelected || isHovered || globalScale > 1.0);

    if (showText) {
        const fontSize = Math.max(12 / globalScale, 12);
        
        ctx.font = `${isSelected ? 'bold' : 'normal'} ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const label = node.displayLabel;
        const textWidth = ctx.measureText(label).width;
        const pad = fontSize * 0.5;
        const offset = size + 6;

        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.beginPath();
        ctx.roundRect(node.x - textWidth/2 - pad/2, node.y + offset, textWidth + pad, fontSize + pad/2, 4);
        ctx.fill();

        ctx.fillStyle = '#1e293b'; 
        ctx.fillText(label, node.x, node.y + offset + fontSize/2 + 2);
    }
  }, [selectedNode, hoverNode, viewMode]);

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const sourceDimmed = isNodeDimmed(link.source);
      const targetDimmed = isNodeDimmed(link.target);
      // Link is dimmed only if BOTH ends are dimmed
      const isDimmed = sourceDimmed && targetDimmed;

      const type = link.type || 'PROCEDURAL';
      const color = THEME.links[type as keyof typeof THEME.links];
      const isImportant = type === 'CONFLICT' || type === 'FINANCE';
      
      const alpha = isDimmed ? 0.1 : (type === 'PROCEDURAL' ? 0.4 : 1);
      const width = (isImportant && !isDimmed) ? 2 / globalScale : 1 / globalScale;

      ctx.globalAlpha = alpha;
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.stroke();

      const isHovered = link.source.id === hoverNode?.id || link.target.id === hoverNode?.id;
      const shouldShowLabel = !isDimmed && ((isImportant && globalScale > 1.2) || isHovered);

      if (shouldShowLabel) {
          ctx.globalAlpha = 1;
          const midX = link.source.x + (link.target.x - link.source.x) * 0.5;
          const midY = link.source.y + (link.target.y - link.source.y) * 0.5;
          
          const fontSize = Math.max(10 / globalScale, 10);
          ctx.font = `bold ${fontSize}px Inter, sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          
          const labelText = link.label;
          const textWidth = ctx.measureText(labelText).width;
          const pad = 6 / globalScale;

          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.roundRect(midX - textWidth/2 - pad/2, midY - fontSize/2 - pad/2, textWidth + pad, fontSize + pad, 3);
          ctx.fill();

          ctx.fillStyle = '#fff';
          ctx.fillText(labelText, midX, midY);
      }
  }, [hoverNode, viewMode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 font-sans h-full">
        {/* GRAPH AREA */}
        <div ref={containerRef} className="lg:col-span-3 relative w-full h-[650px] bg-slate-950 rounded border border-slate-800 shadow-xl overflow-hidden group flex flex-col">
            
            {/* VIEW CONTROLS */}
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 flex gap-2">
                <button onClick={() => setViewMode('ALL')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${viewMode === 'ALL' ? 'bg-white text-slate-900 shadow-lg scale-105' : 'bg-slate-900/80 text-slate-400 border border-slate-700'}`}>Overview</button>
                <button onClick={() => setViewMode('PEOPLE_ONLY')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all flex items-center gap-2 ${viewMode === 'PEOPLE_ONLY' ? 'bg-emerald-500 text-white shadow-lg scale-105' : 'bg-slate-900/80 text-slate-400 border border-slate-700'}`}>
                    <Users size={12} /> Parties & Conflict
                </button>
                <button onClick={() => setViewMode('DOCS_ONLY')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all flex items-center gap-2 ${viewMode === 'DOCS_ONLY' ? 'bg-blue-500 text-white shadow-lg scale-105' : 'bg-slate-900/80 text-slate-400 border border-slate-700'}`}>
                    <FileText size={12} /> Evidence
                </button>
            </div>

            {/* LOADING */}
            {isLoading && (
                <div className="absolute inset-0 z-20 bg-slate-950 flex items-center justify-center">
                    <div className="flex flex-col items-center gap-3">
                        <Network className="animate-spin text-blue-500" size={32} />
                        <span className="text-xs text-blue-400 font-mono tracking-widest">BUILDING INTELLIGENCE MAP...</span>
                    </div>
                </div>
            )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={graphData}
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                backgroundColor="#0f172a"
                
                onNodeClick={(node) => handleNodeClick(node as SimulationNode)}
                onNodeHover={(node) => setHoverNode(node as SimulationNode || null)}
                onBackgroundClick={() => { setSelectedNode(null); setRealAnalysis(null); }}
                
                linkDirectionalArrowLength={ARROW_LENGTH}
                linkDirectionalArrowRelPos={ARROW_REL_POS}
                linkDirectionalArrowColor={(link: any) => {
                     // Ghost arrows if dimmed
                     if (isNodeDimmed(link.source) && isNodeDimmed(link.target)) return 'rgba(255,255,255,0.05)';
                     return THEME.links[link.type as keyof typeof THEME.links] || '#334155';
                }}
                
                minZoom={0.5}
                maxZoom={6.0}
            />
        </div>

        {/* SIDEBAR */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded h-[650px] flex flex-col shadow-lg">
            <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-slate-400" />
                    Case Analysis
                </h3>
                <div className="flex items-center gap-1">
                    <Eye size={12} className="text-slate-400" />
                    <span className="text-[10px] text-slate-400 font-mono">
                         {graphData.nodes.length} Ent.
                    </span>
                </div>
            </div>

            <div className="flex-grow p-5 overflow-y-auto bg-white custom-scrollbar">
                {selectedNode ? (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        {/* HEADER */}
                        <div className="flex items-start gap-4 mb-6">
                            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 shadow-sm text-slate-700">
                                {(THEME.icons as any)[selectedNode.detectedGroup || 'default']}
                            </div>
                            <div>
                                <span className="inline-block mb-1 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                                    {selectedNode.detectedGroup?.toUpperCase()}
                                </span>
                                <h2 className="text-lg font-bold text-slate-900 leading-tight break-words">{selectedNode.name}</h2>
                            </div>
                        </div>

                        {/* ANALYSIS BOX */}
                        <div className={`p-4 rounded-lg shadow-sm border mb-6 ${
                            realAnalysis?.strategic_value === 'CRITICAL' ? 'bg-red-50 border-red-100' : 'bg-slate-900 text-white border-slate-800'
                        }`}>
                            <div className="flex items-center gap-2 mb-3">
                                <Sparkles size={14} className={realAnalysis?.strategic_value === 'CRITICAL' ? 'text-red-500' : 'text-amber-400'} />
                                <span className={`text-[10px] font-bold uppercase ${realAnalysis?.strategic_value === 'CRITICAL' ? 'text-red-800' : 'text-slate-400'}`}>
                                    Assessment
                                </span>
                            </div>
                            
                            {analysisLoading ? (
                                <div className="py-2 text-xs opacity-70 italic">Scanning relationships...</div>
                            ) : realAnalysis ? (
                                <>
                                    <p className={`text-sm font-medium leading-relaxed mb-3 ${realAnalysis.strategic_value === 'CRITICAL' ? 'text-red-900' : 'text-slate-100'}`}>
                                        {realAnalysis.summary}
                                    </p>
                                    
                                    {/* DETAILS LIST */}
                                    {realAnalysis.details.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
                                            {realAnalysis.details.map((detail, i) => (
                                                <div key={i} className="flex items-start gap-2 text-xs opacity-90">
                                                    {detail.includes('Financial') ? <Banknote size={12} className="mt-0.5 text-amber-500" /> : 
                                                     detail.includes('Conflict') ? <AlertTriangle size={12} className="mt-0.5 text-red-500" /> :
                                                     <Network size={12} className="mt-0.5" />}
                                                    <span>{detail}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </>
                            ) : null}
                        </div>

                        {/* ACTIONS */}
                        <div className="mt-auto pt-4 border-t border-slate-100">
                            <button className="w-full py-2.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-bold uppercase rounded flex items-center justify-center gap-2 transition-all shadow-sm">
                                <FileCheck size={14} />
                                View Source Files
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-40">
                        <Scale size={40} className="text-slate-300 mb-4" />
                        <h3 className="text-sm font-bold text-slate-500 uppercase">Select an Entity</h3>
                        <p className="text-xs text-slate-400 mt-2 max-w-[200px]">
                            Click on a node to reveal conflicts, financial ties, and legal standing.
                        </p>
                    </div>
                )}
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;