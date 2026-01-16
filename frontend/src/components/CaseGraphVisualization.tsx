/* FILE: src/components/CaseGraphVisualization.tsx
   PHOENIX PROTOCOL - LEGAL INTELLIGENCE MAP V4.1 (CLEANUP)
   1. CLEANUP: Removed unused ShieldAlert import.
   2. FUNCTIONALITY: Retains all High-Contrast and Smart-Insight features.
*/

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphNode } from '../data/types';
import { 
    FileText, Search, Sparkles, Gavel, Users, 
    FileCheck, Landmark, Network, Scale, Banknote, AlertTriangle
} from 'lucide-react';

// --- CONFIGURATION ---
const NODE_REL_SIZE = 8; // Larger base size
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

// --- LEGAL THEME ENGINE (HIGH CONTRAST) ---
const THEME = {
  nodes: {
    court:      '#334155', // Slate-700
    judge:      '#ef4444', // Red-500
    person:     '#10b981', // Emerald-500
    document:   '#3b82f6', // Blue-500
    law:        '#f59e0b', // Amber-500
    default:    '#64748b'
  },
  links: {
    CONFLICT:   '#ef4444', // Red-500
    FAMILY:     '#10b981', // Emerald-500
    FINANCE:    '#d97706', // Amber-600 (Darker for visibility)
    PROCEDURAL: '#e2e8f0'  // Slate-200 (Very light to fade into background)
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

// --- CLASSIFIERS ---
const classifyNode = (node: any): string => {
    const name = (node.name || '').toLowerCase();
    const rawGroup = (node.group || '').toUpperCase();

    if (rawGroup === 'DOCUMENT') return 'document';
    if (name.includes('gjykata') || name.includes('themelore')) return 'court';
    if (name.includes('ligji') || name.includes('neni')) return 'law';
    if (name.includes('ministria') || name.includes('policia')) return 'court'; 
    if (name.includes('aktvendim') || name.includes('aktgjykim')) return 'document';
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
  
  const [fullData, setFullData] = useState<{nodes: SimulationNode[], links: SimulationLink[]}>({ nodes: [], links: [] });
  const [activeData, setActiveData] = useState<{nodes: SimulationNode[], links: SimulationLink[]}>({ nodes: [], links: [] });
  
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);
  const [hoverNode, setHoverNode] = useState<SimulationNode | null>(null);
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
                    displayLabel: n.name.length > 20 ? n.name.substring(0, 19) + '...' : n.name
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

  // 2. View Filter
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

  // 3. Physics
  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        graph.d3Force('charge')?.strength(-600); // Stronger repulsion for clarity
        graph.d3Force('link')?.distance(viewMode === 'PEOPLE_ONLY' ? 200 : 100);
        graph.d3Force('center')?.strength(0.4);
    }
  }, [activeData, viewMode]);

  // 4. GENERATE REAL INSIGHTS (No more placeholders)
  const generateInsight = (node: SimulationNode) => {
      // Find connections
      const links = activeData.links.filter(l => 
          (l.source as any).id === node.id || (l.target as any).id === node.id
      );

      const conflicts = links.filter(l => l.type === 'CONFLICT');
      const financial = links.filter(l => l.type === 'FINANCE');
      const family = links.filter(l => l.type === 'FAMILY');

      let summary = "";
      let details: string[] = [];
      let score = 0.5;

      if (conflicts.length > 0) {
          summary += `⚠️ Active participant in ${conflicts.length} Conflict(s). `;
          score += 0.3;
          conflicts.forEach(c => details.push(`Dispute with ${(c.target as any).name}: "${c.label}"`));
      }
      if (financial.length > 0) {
          summary += `💰 Linked to ${financial.length} Financial Transaction(s) or Obligations. `;
          score += 0.15;
          financial.forEach(f => details.push(`Financial Link: "${f.label}"`));
      }
      if (family.length > 0) {
          summary += `Linked to ${family.length} Family Member(s). `;
          details.push(`Family ties detected.`);
      }
      if (node.detectedGroup === 'document') {
          summary = "Key evidentiary document. ";
          if (links.length > 3) {
              summary += "High centrality: Referenced by multiple entities.";
              score += 0.4;
          }
      }

      if (summary === "") summary = "Procedural entity with standard connections.";

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

      // Simulate specific legal analysis fetch (fast)
      setTimeout(() => {
          const insight = generateInsight(node);
          setRealAnalysis(insight);
          setAnalysisLoading(false);
      }, 400);

      fgRef.current?.centerAt(node.x, node.y, 800);
      fgRef.current?.zoom(3.0, 800);
  };

  // 5. Canvas Renderer
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const group = node.detectedGroup || 'default';
    const color = (THEME.nodes as any)[group] || THEME.nodes.default;
    const isSelected = node.id === selectedNode?.id;
    const isHovered = node.id === hoverNode?.id;

    // Node Size Logic
    let size = NODE_REL_SIZE;
    if (group === 'person' || group === 'judge') size = 12;
    if (group === 'document') size = 8;
    if (isSelected) size *= 1.4;

    // Draw Node
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Selection Ring
    if (isSelected || isHovered) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 4 / globalScale;
        ctx.stroke();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
    }

    // --- TYPOGRAPHY ENGINE ---
    // Calculate optimum font size: Never smaller than 12px visually
    // globalScale = zoom level. If zoom=0.5, font in world space must be 24 to look like 12.
    // We clamp the minimum scale factor to ensure text is always readable.
    const label = node.displayLabel;
    const fontSize = Math.max(14 / globalScale, 4); // Absolute floor in world space
    
    // Only show labels for important nodes when zoomed out, or all nodes when zoomed in
    const showLabel = isSelected || isHovered || globalScale > 1.0 || ['person', 'judge'].includes(group);

    if (showLabel) {
        ctx.font = `bold ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const textWidth = ctx.measureText(label).width;
        const pad = fontSize * 0.4;
        
        // Label Background Pill (High Contrast)
        ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
        ctx.shadowColor = 'rgba(0,0,0,0.3)';
        ctx.shadowBlur = 4;
        ctx.beginPath();
        ctx.roundRect(node.x - textWidth/2 - pad, node.y + size + 4, textWidth + pad*2, fontSize + pad*1.5, 4);
        ctx.fill();
        ctx.shadowBlur = 0; // Reset shadow

        // Label Text
        ctx.fillStyle = '#0f172a'; // Dark Slate text
        ctx.fillText(label, node.x, node.y + size + 4 + fontSize/2 + pad*0.5);
    }
  }, [selectedNode, hoverNode]);

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const type = link.type || 'PROCEDURAL';
      const color = THEME.links[type as keyof typeof THEME.links];
      
      // Line Thickness: Money/Conflict lines are thicker
      const isImportant = type === 'CONFLICT' || type === 'FINANCE';
      const width = isImportant ? 3 / globalScale : 1 / globalScale;
      
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.stroke();

      // --- EDGE LABELS (The "Why") ---
      // Important links (Alimony, Conflict) get big labels. Procedural gets hidden when zoomed out.
      if (isImportant || globalScale > 1.2) {
          const midX = link.source.x + (link.target.x - link.source.x) * 0.5;
          const midY = link.source.y + (link.target.y - link.source.y) * 0.5;
          
          const fontSize = isImportant ? Math.max(12 / globalScale, 3) : Math.max(10 / globalScale, 2);
          ctx.font = `bold ${fontSize}px Inter, sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          
          const labelText = link.label;
          const textWidth = ctx.measureText(labelText).width;
          const pad = 4 / globalScale;
          
          // Label Background (Color-coded)
          ctx.fillStyle = color; 
          ctx.beginPath();
          ctx.roundRect(midX - textWidth/2 - pad, midY - fontSize/2 - pad, textWidth + pad*2, fontSize + pad*2, 3);
          ctx.fill();

          ctx.fillStyle = '#ffffff'; // White text on colored background
          ctx.fillText(labelText, midX, midY);
      }
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 font-sans h-full">
        {/* GRAPH AREA */}
        <div ref={containerRef} className="lg:col-span-3 relative w-full h-[650px] bg-slate-950 rounded border border-slate-800 shadow-xl overflow-hidden group flex flex-col">
            
            {/* VIEW CONTROLS */}
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 flex gap-2">
                <button onClick={() => setViewMode('ALL')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${viewMode === 'ALL' ? 'bg-white text-slate-900' : 'bg-slate-900/80 text-slate-400 border border-slate-700'}`}>Overview</button>
                <button onClick={() => setViewMode('PEOPLE_ONLY')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${viewMode === 'PEOPLE_ONLY' ? 'bg-emerald-500 text-white' : 'bg-slate-900/80 text-slate-400 border border-slate-700'}`}>Parties & Conflict</button>
                <button onClick={() => setViewMode('DOCS_ONLY')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${viewMode === 'DOCS_ONLY' ? 'bg-blue-500 text-white' : 'bg-slate-900/80 text-slate-400 border border-slate-700'}`}>Evidence</button>
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
                graphData={activeData}
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                backgroundColor="#0f172a"
                
                // Interaction
                onNodeClick={(node) => handleNodeClick(node as SimulationNode)}
                onNodeHover={(node) => setHoverNode(node as SimulationNode || null)}
                onBackgroundClick={() => { setSelectedNode(null); setRealAnalysis(null); }}
                
                // Arrows
                linkDirectionalArrowLength={ARROW_LENGTH}
                linkDirectionalArrowRelPos={ARROW_REL_POS}
                linkDirectionalArrowColor={(link: any) => THEME.links[link.type as keyof typeof THEME.links] || '#334155'}
                
                minZoom={0.2}
                maxZoom={8.0}
            />
        </div>

        {/* SIDEBAR */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded h-[650px] flex flex-col shadow-lg">
            <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-slate-400" />
                    Case Analysis
                </h3>
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
                                <h2 className="text-lg font-bold text-slate-900 leading-tight">{selectedNode.name}</h2>
                            </div>
                        </div>

                        {/* ANALYSIS BOX */}
                        <div className={`p-4 rounded-lg shadow-sm border mb-6 ${
                            realAnalysis?.strategic_value === 'CRITICAL' ? 'bg-red-50 border-red-100' : 'bg-slate-900 text-white border-slate-800'
                        }`}>
                            <div className="flex items-center gap-2 mb-3">
                                <Sparkles size={14} className={realAnalysis?.strategic_value === 'CRITICAL' ? 'text-red-500' : 'text-amber-400'} />
                                <span className={`text-[10px] font-bold uppercase ${realAnalysis?.strategic_value === 'CRITICAL' ? 'text-red-800' : 'text-slate-400'}`}>
                                    Relationship Assessment
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
                                                     detail.includes('Dispute') ? <AlertTriangle size={12} className="mt-0.5 text-red-500" /> :
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