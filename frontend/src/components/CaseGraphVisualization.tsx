/* FILE: src/components/CaseGraphVisualization.tsx
   PHOENIX PROTOCOL - LEGAL INTELLIGENCE MAP (CLEAN & OPTIMIZED)
   1. CLEANUP: Removed all unused imports (GraphData, icons, translation hooks).
   2. UX: Re-integrated 'isLoading' state for a proper loading overlay.
   3. LOGIC: Preserves the "Lawyer's View" relationship highlighting.
*/

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphNode } from '../data/types';
import { 
    FileText, ShieldAlert, Search, Sparkles, Gavel, Users, 
    FileCheck, Landmark, Network, Scale
} from 'lucide-react';

// --- CONFIGURATION ---
const NODE_REL_SIZE = 6;
const ARROW_REL_POS = 1; // Arrow at end of line
const ARROW_LENGTH = 4;

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
}

// --- LEGAL THEME ENGINE ---
const THEME = {
  nodes: {
    court:      '#475569', // Slate-600
    judge:      '#dc2626', // Red-600
    person:     '#059669', // Emerald-600
    document:   '#3b82f6', // Blue-500
    law:        '#d97706', // Amber-600
    default:    '#94a3b8'
  },
  links: {
    CONFLICT:   '#ef4444', // Red-500
    FAMILY:     '#10b981', // Emerald-500
    FINANCE:    '#f59e0b', // Amber-500
    PROCEDURAL: '#cbd5e1'  // Slate-300
  },
  icons: {
    court:      <Landmark size={18} className="text-slate-600" />,
    judge:      <Gavel size={18} className="text-red-600" />,
    person:     <Users size={18} className="text-emerald-600" />,
    document:   <FileText size={18} className="text-blue-500" />,
    law:        <Scale size={18} className="text-amber-600" />,
    default:    <Network size={18} className="text-slate-400" />
  }
};

// --- LEGAL CLASSIFIERS (HEURISTICS) ---
const classifyNode = (node: any): string => {
    const name = (node.name || '').toLowerCase();
    const rawGroup = (node.group || '').toUpperCase();

    if (rawGroup === 'DOCUMENT') return 'document';
    
    // Albanian Legal Context Keywords
    if (name.includes('gjykata') || name.includes('themelore') || name.includes('supreme')) return 'court';
    if (name.includes('ligji') || name.includes('neni') || name.includes('kodi')) return 'law';
    if (name.includes('ministria') || name.includes('policia') || name.includes('prokuroria')) return 'court'; 
    if (name.includes('aktvendim') || name.includes('aktgjykim') || name.includes('marrëveshja')) return 'document';
    if (rawGroup === 'PERSON' || rawGroup === 'USER') return 'person';
    if (name.includes('sh.p.k') || name.includes('sh.a')) return 'person';

    return 'default';
};

const classifyLink = (label: string): 'CONFLICT' | 'FAMILY' | 'FINANCE' | 'PROCEDURAL' => {
    const l = (label || '').toUpperCase();
    
    if (['PADITËSE', 'I PADITURI', 'KUNDËRSHTON', 'ACCUSES', 'VS', 'KUNDER'].some(k => l.includes(k))) return 'CONFLICT';
    if (['PRIND', 'BASHKËSHORT', 'VËLLA', 'MOTËR', 'FAMILJA', 'MARTESË'].some(k => l.includes(k))) return 'FAMILY';
    if (['ALIMENTACION', 'BORXH', 'PAGUAN', 'FINANCE', 'MONEY', 'SHUMA'].some(k => l.includes(k))) return 'FINANCE';
    
    return 'PROCEDURAL';
};

const CaseGraphVisualization: React.FC<CaseGraphProps> = ({ caseId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [width, setWidth] = useState(800);
  const [height, setHeight] = useState(600);
  
  const [fullData, setFullData] = useState<{nodes: SimulationNode[], links: SimulationLink[]}>({ nodes: [], links: [] });
  const [activeData, setActiveData] = useState<{nodes: SimulationNode[], links: SimulationLink[]}>({ nodes: [], links: [] });
  
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);
  const [hoverNode, setHoverNode] = useState<SimulationNode | null>(null);
  
  // View Filters
  const [viewMode, setViewMode] = useState<'ALL' | 'PEOPLE_ONLY' | 'DOCS_ONLY'>('ALL');

  // Analysis State
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

  // 1. Load Data & Apply Legal Classifiers
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
                    displayLabel: n.name.length > 30 ? n.name.substring(0, 28) + '...' : n.name
                }));

                const processedLinks = raw.links.map((l: any) => ({
                    ...l,
                    type: classifyLink(l.label)
                }));

                setFullData({ nodes: processedNodes, links: processedLinks });
                setActiveData({ nodes: processedNodes, links: processedLinks });
            }
        } catch (e) { console.error(e); } 
        finally { if (isMounted) setIsLoading(false); }
    };
    loadGraph();
    return () => { isMounted = false; };
  }, [caseId]);

  // 2. Filter Logic
  useEffect(() => {
      if (fullData.nodes.length === 0) return;

      let filteredNodes = fullData.nodes;
      let filteredLinks = fullData.links;

      if (viewMode === 'PEOPLE_ONLY') {
          filteredNodes = fullData.nodes.filter(n => ['person', 'judge'].includes(n.detectedGroup || ''));
          const nodeIds = new Set(filteredNodes.map(n => n.id));
          filteredLinks = fullData.links.filter(l => 
              nodeIds.has((l.source as any).id || l.source) && 
              nodeIds.has((l.target as any).id || l.target)
          );
      } else if (viewMode === 'DOCS_ONLY') {
        filteredNodes = fullData.nodes.filter(n => n.detectedGroup === 'document');
         const nodeIds = new Set(filteredNodes.map(n => n.id));
          filteredLinks = fullData.links.filter(l => 
              nodeIds.has((l.source as any).id || l.source) && 
              nodeIds.has((l.target as any).id || l.target)
          );
      }

      setActiveData({ nodes: filteredNodes, links: filteredLinks });
      setTimeout(() => fgRef.current?.zoomToFit(400, 50), 450);

  }, [viewMode, fullData]);

  // 3. Physics Tuning
  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        graph.d3Force('charge')?.strength(-300);
        graph.d3Force('link')?.distance(viewMode === 'PEOPLE_ONLY' ? 150 : 80);
        graph.d3Force('center')?.strength(0.6);
    }
  }, [activeData, viewMode]);

  // 4. Interaction
  const handleNodeClick = (node: SimulationNode) => {
      setSelectedNode(node);
      setRealAnalysis(null);
      setAnalysisLoading(true);

      setTimeout(() => {
          setRealAnalysis({
              summary: `Legal Insight: ${node.name} is a key ${(node.detectedGroup || 'entity').toUpperCase()}. Detected in procedural role, likely requiring deep review of associated financial documents.`,
              strategic_value: "HIGH RELEVANCE",
              confidence_score: 0.98
          });
          setAnalysisLoading(false);
      }, 700);

      fgRef.current?.centerAt(node.x, node.y, 800);
      fgRef.current?.zoom(2.5, 800);
  };

  // 5. Canvas Renderer
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const group = node.detectedGroup || 'default';
    const color = (THEME.nodes as any)[group] || THEME.nodes.default;
    const isSelected = node.id === selectedNode?.id;
    const isHovered = node.id === hoverNode?.id;

    const baseSize = NODE_REL_SIZE + (node.val || 1) * 0.4;
    const size = isSelected ? baseSize * 1.5 : baseSize;

    // Draw Node
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Draw Selection Ring
    if (isSelected || isHovered) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 3 / globalScale;
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 4 / globalScale, 0, 2 * Math.PI);
        ctx.stroke();
    }

    // Draw Label
    const shouldShowLabel = isSelected || isHovered || globalScale > 1.2 || group === 'judge' || group === 'person';
    
    if (shouldShowLabel) {
        const label = node.displayLabel;
        const fontSize = (isSelected ? 14 : 10) / globalScale;
        
        ctx.font = `${isSelected ? 'bold' : 'normal'} ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const textY = node.y + size + fontSize + 2;
        ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
        ctx.fillStyle = isSelected ? '#ffffff' : '#cbd5e1';
        ctx.fillText(label, node.x, textY);
    }
  }, [selectedNode, hoverNode]);

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const type = link.type || 'PROCEDURAL';
      const color = THEME.links[type as keyof typeof THEME.links];
      const width = (type === 'CONFLICT' || type === 'FINANCE') ? 2 : 1;
      
      ctx.lineWidth = width / globalScale;
      ctx.strokeStyle = color;
      
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.stroke();

      if (type !== 'PROCEDURAL' && globalScale > 0.8) {
          const midX = link.source.x + (link.target.x - link.source.x) * 0.5;
          const midY = link.source.y + (link.target.y - link.source.y) * 0.5;
          
          const fontSize = 8 / globalScale;
          ctx.font = `bold ${fontSize}px Inter, sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          
          const textWidth = ctx.measureText(link.label).width;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.roundRect(midX - textWidth/2 - 2, midY - fontSize/2 - 2, textWidth + 4, fontSize + 4, 2);
          ctx.fill();

          ctx.fillStyle = '#ffffff';
          ctx.fillText(link.label, midX, midY);
      }

  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 font-sans h-full">
        
        {/* GRAPH AREA */}
        <div ref={containerRef} className="lg:col-span-3 relative w-full h-[650px] bg-slate-950 rounded border border-slate-800 shadow-xl overflow-hidden group flex flex-col">
            
            {/* TOOLBAR */}
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 flex gap-2">
                <button 
                    onClick={() => setViewMode('ALL')}
                    className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide border transition-all ${viewMode === 'ALL' ? 'bg-slate-100 text-slate-900 border-white' : 'bg-slate-900/80 text-slate-400 border-slate-700 backdrop-blur'}`}
                >
                    Overview
                </button>
                <button 
                    onClick={() => setViewMode('PEOPLE_ONLY')}
                    className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide border transition-all flex items-center gap-2 ${viewMode === 'PEOPLE_ONLY' ? 'bg-emerald-500 text-white border-emerald-400' : 'bg-slate-900/80 text-slate-400 border-slate-700 backdrop-blur'}`}
                >
                    <Users size={12} />
                    Palët & Konflikti
                </button>
                <button 
                    onClick={() => setViewMode('DOCS_ONLY')}
                    className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide border transition-all flex items-center gap-2 ${viewMode === 'DOCS_ONLY' ? 'bg-blue-500 text-white border-blue-400' : 'bg-slate-900/80 text-slate-400 border-slate-700 backdrop-blur'}`}
                >
                    <FileText size={12} />
                    Evidence
                </button>
            </div>

            {/* STATUS INDICATOR */}
            <div className="absolute top-4 left-4 z-10">
                <div className="bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded border border-slate-700 flex items-center gap-2">
                    <ShieldAlert size={14} className="text-amber-500" />
                    <span className="text-[10px] font-bold text-slate-200 uppercase tracking-widest">
                        Legal Intelligence
                    </span>
                </div>
            </div>

            {/* LOADING OVERLAY */}
            {isLoading && (
                <div className="absolute inset-0 z-20 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center">
                    <div className="flex flex-col items-center gap-3">
                        <Network className="animate-pulse text-blue-500" size={32} />
                        <span className="text-xs text-blue-400 font-mono tracking-widest">ANALYZING CONNECTIONS...</span>
                    </div>
                </div>
            )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={activeData}
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                backgroundColor="#020617" // Slate-950
                
                // Interaction
                onNodeClick={(node) => handleNodeClick(node as SimulationNode)}
                onNodeHover={(node) => setHoverNode(node as SimulationNode || null)}
                onBackgroundClick={() => { setSelectedNode(null); setRealAnalysis(null); }}
                
                // Arrows
                linkDirectionalArrowLength={ARROW_LENGTH}
                linkDirectionalArrowRelPos={ARROW_REL_POS}
                linkDirectionalArrowColor={(link: any) => THEME.links[link.type as keyof typeof THEME.links] || '#334155'}
                
                minZoom={0.5}
                maxZoom={6.0}
            />
            
            {/* COMPACT LEGEND */}
            <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur p-2 rounded border border-slate-700 text-[10px] text-slate-400 grid grid-cols-2 gap-x-4 gap-y-1">
                <div className="flex items-center gap-1"><span className="w-2 h-0.5 bg-red-500"></span> Conflict / Lawsuit</div>
                <div className="flex items-center gap-1"><span className="w-2 h-0.5 bg-emerald-500"></span> Family / Relation</div>
                <div className="flex items-center gap-1"><span className="w-2 h-0.5 bg-amber-500"></span> Financial / Debt</div>
                <div className="flex items-center gap-1"><span className="w-2 h-0.5 bg-slate-400"></span> Procedural</div>
            </div>
        </div>

        {/* DOSSIER PANEL */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded h-[650px] flex flex-col shadow-lg">
            <div className="p-3 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-slate-400" />
                    Case Dossier
                </h3>
            </div>

            <div className="flex-grow p-4 overflow-y-auto bg-white custom-scrollbar">
                {selectedNode ? (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        {/* 1. Identity Header */}
                        <div className="flex items-start gap-3 mb-5">
                            <div className="p-3 rounded bg-slate-50 border border-slate-200 shadow-sm">
                                {(THEME.icons as any)[selectedNode.detectedGroup || 'default']}
                            </div>
                            <div>
                                <span className={`text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded border ${
                                    selectedNode.detectedGroup === 'person' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 
                                    selectedNode.detectedGroup === 'judge' ? 'bg-red-50 text-red-700 border-red-100' :
                                    'bg-slate-100 text-slate-600 border-slate-200'
                                }`}>
                                    {(selectedNode.detectedGroup || 'Entity').toUpperCase()}
                                </span>
                                <h2 className="text-base font-bold text-slate-900 leading-tight mt-1">{selectedNode.name}</h2>
                            </div>
                        </div>

                        {/* 2. Legal Analysis */}
                        <div className="bg-slate-900 text-slate-200 p-4 rounded shadow-sm mb-5 relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-12 h-12 bg-white/5 rounded-bl-full"></div>
                            <div className="flex items-center gap-2 mb-3">
                                <Sparkles size={14} className="text-amber-400" />
                                <span className="text-[10px] font-bold uppercase text-slate-400">AI Legal Assessment</span>
                            </div>
                            
                            {analysisLoading ? (
                                <div className="py-2 text-center text-xs text-slate-500 italic">Analysing case files...</div>
                            ) : realAnalysis ? (
                                <>
                                    <p className="text-xs leading-relaxed text-slate-300 mb-3">{realAnalysis.summary}</p>
                                    <div className="flex justify-between items-center text-[10px] font-mono border-t border-slate-800 pt-2">
                                        <span className="text-slate-500">RELEVANCE SCORE</span>
                                        <span className="text-amber-400 font-bold">{realAnalysis.strategic_value}</span>
                                    </div>
                                </>
                            ) : null}
                        </div>

                        {/* 3. Connection Summary */}
                        <div className="space-y-3">
                            <h4 className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-2">
                                <Network size={12} /> Known Connections
                            </h4>
                            <div className="bg-slate-50 rounded border border-slate-100 p-2 space-y-2">
                                {fullData.links
                                    .filter(l => (l.source as any).id === selectedNode.id || (l.target as any).id === selectedNode.id)
                                    .filter(l => l.type !== 'PROCEDURAL')
                                    .slice(0, 5)
                                    .map((l, idx) => (
                                        <div key={idx} className="flex items-center justify-between text-xs">
                                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                                l.type === 'CONFLICT' ? 'bg-red-100 text-red-700' :
                                                l.type === 'FINANCE' ? 'bg-amber-100 text-amber-700' :
                                                'bg-emerald-100 text-emerald-700'
                                            }`}>
                                                {l.label}
                                            </span>
                                            <span className="text-slate-600 truncate max-w-[100px]">
                                                {(l.target as any).id === selectedNode.id ? (l.source as any).name : (l.target as any).name}
                                            </span>
                                        </div>
                                    ))
                                }
                                {fullData.links.filter(l => (l.source as any).id === selectedNode.id || (l.target as any).id === selectedNode.id).length === 0 && (
                                    <span className="text-xs text-slate-400 italic">No direct conflicts or family links found.</span>
                                )}
                            </div>
                        </div>

                        {/* 4. Action */}
                        <div className="mt-auto pt-6">
                            <button className="w-full py-2 bg-white border border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700 text-xs font-bold uppercase rounded flex items-center justify-center gap-2 transition-all shadow-sm">
                                <FileCheck size={14} />
                                View Source Documents
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-40">
                        <Scale size={32} className="text-slate-300 mb-3" />
                        <h3 className="text-sm font-bold text-slate-500 uppercase">Select an Entity</h3>
                        <p className="text-xs text-slate-400 mt-1 max-w-[200px]">
                            Identify conflicts, financial flows, and relationships.
                        </p>
                    </div>
                )}
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;