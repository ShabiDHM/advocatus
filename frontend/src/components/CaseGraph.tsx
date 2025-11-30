// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - SCALING & PHYSICS FIX
// 1. SCALING: Reduced node radius (22 -> 6) to fix massive overlapping.
// 2. PHYSICS: Added active force configuration (Charge -120, Link Distance 70).
// 3. TEXT: Capped font size and added zoom-level constraints for cleanliness.

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods, NodeObject, LinkObject } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { Loader2, ZoomIn, ZoomOut, Maximize, Share2 } from 'lucide-react';
import { GraphNode as APINode, GraphLink as APILink } from '../data/types';

// --- INTERNAL TYPES FOR FORCE GRAPH ---
interface GraphNode extends NodeObject {
    id: string;
    name: string;
    group: string;
    val: number;
    x?: number;
    y?: number;
}

interface GraphLink extends LinkObject {
    source: GraphNode;
    target: GraphNode;
    label: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

interface CaseGraphProps {
    caseId: string;
    className?: string;
}

// --- CONFIGURATION ---
const NODE_R = 6; // Significantly reduced for correct scaling
const FONT_SIZE_MAX = 4; // Capped font size in graph units

// Neo4j Color Palette
const COLORS: Record<string, string> = {
    'DOCUMENT': '#8DCC93',      
    'PERSON': '#F79767',        
    'ORGANIZATION': '#57C7E3',  
    'COMPANY': '#57C7E3',
    'MONEY': '#FFC454',         
    'DATE': '#D9C8AE',          
    'LOCATION': '#F16667',      
    'DEFAULT': '#C990C0'        
};

const LEGEND_LABELS: Record<string, string> = {
    'DOCUMENT': 'Dokument',
    'PERSON': 'Person',
    'ORGANIZATION': 'Organizatë',
    'COMPANY': 'Kompania',
    'MONEY': 'Vlera',
    'DATE': 'Data',
    'LOCATION': 'Lokacioni',
    'DEFAULT': 'Tjetër'
};

const CaseGraph: React.FC<CaseGraphProps> = ({ caseId, className }) => {
    const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink>>();
    const containerRef = useRef<HTMLDivElement>(null);
    
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    
    // Interaction State
    const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
    const [highlightLinks, setHighlightLinks] = useState(new Set<LinkObject>());
    const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);

    // --- DATA FETCHING ---
    const fetchData = useCallback(async () => {
        if (!caseId) return;
        setLoading(true);
        try {
            const response = await apiService.getCaseGraph(caseId);
            
            const nodesMap = new Map<string, GraphNode>();
            response.nodes.forEach((n: APINode) => {
                nodesMap.set(n.id, { ...n });
            });

            const validLinks: any[] = response.links
                .filter((l: APILink) => nodesMap.has(l.source) && nodesMap.has(l.target))
                .map((l: APILink) => ({
                    source: l.source,
                    target: l.target,
                    label: l.label
                }));

            setData({ 
                nodes: Array.from(nodesMap.values()), 
                links: validLinks 
            });
        } catch (error) {
            console.error("Graph load failed:", error);
        } finally {
            setLoading(false);
        }
    }, [caseId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // --- PHYSICS ENGINE CONFIGURATION ---
    useEffect(() => {
        if (fgRef.current) {
            // Apply stronger repulsive forces to spread nodes out
            fgRef.current.d3Force('charge')?.strength(-120);
            fgRef.current.d3Force('link')?.distance(70);
            // Re-heat simulation to apply changes
            fgRef.current.d3ReheatSimulation();
        }
    }, [data]);

    // --- RESIZE OBSERVER ---
    useEffect(() => {
        if (!containerRef.current) return;
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                setDimensions({
                    width: entry.contentRect.width,
                    height: entry.contentRect.height
                });
            }
        });
        resizeObserver.observe(containerRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    // --- RENDERING HELPERS ---

    const getNodeColor = (group: string) => {
        const key = group?.toUpperCase();
        return COLORS[key] || COLORS['DEFAULT'];
    };

    const drawText = (ctx: CanvasRenderingContext2D, node: GraphNode, r: number) => {
        const label = node.name || node.id;
        // Keep font size relative to node, but capped
        const fontSize = Math.min(r * 0.8, FONT_SIZE_MAX); 
        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#1e293b'; 
        
        const maxWidth = r * 2.5;
        let text = label;
        // Aggressive truncation for cleanliness
        if (ctx.measureText(text).width > maxWidth) {
            // Approx char count based on width
            text = label.substring(0, 10) + '..';
        }
        ctx.fillText(text, node.x!, node.y!);
    };

    const handleNodeHover = (node: GraphNode | null) => {
        setHoverNode(node);
        const newHighlightNodes = new Set<string>();
        const newHighlightLinks = new Set<LinkObject>();

        if (node) {
            newHighlightNodes.add(node.id);
            data.links.forEach(link => {
                if (link.source.id === node.id) {
                    newHighlightNodes.add(link.target.id);
                    newHighlightLinks.add(link);
                }
                if (link.target.id === node.id) {
                    newHighlightNodes.add(link.source.id);
                    newHighlightLinks.add(link);
                }
            });
        }

        setHighlightNodes(newHighlightNodes);
        setHighlightLinks(newHighlightLinks);
    };

    // --- CANVAS PAINTERS ---

    const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
        if (node.x === undefined || node.y === undefined) return;

        const isHovered = node === hoverNode;
        const isNeighbor = highlightNodes.has(node.id);
        const isDimmed = hoverNode && !isHovered && !isNeighbor;
        
        const color = getNodeColor(node.group);
        const radius = isHovered ? NODE_R * 1.3 : NODE_R;

        ctx.globalAlpha = isDimmed ? 0.2 : 1;

        // 1. Circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();
        
        // 2. Border
        ctx.lineWidth = isHovered ? 2 / globalScale : 1 / globalScale;
        ctx.strokeStyle = 'rgba(0,0,0,0.3)'; 
        ctx.stroke();

        // 3. Text - Only draw if zoomed in enough or hovered
        // k = globalScale. If k=1, 1px = 1 unit.
        // We want text to appear when nodes are large enough to read.
        if (globalScale > 2 || isHovered) {
            drawText(ctx, node, radius);
        }
        
        ctx.globalAlpha = 1;
    }, [hoverNode, highlightNodes]);

    const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const start = link.source;
        const end = link.target;
        if (start.x === undefined || start.y === undefined || end.x === undefined || end.y === undefined) return;

        const isHighlighted = highlightLinks.has(link);
        const isDimmed = hoverNode && !isHighlighted;

        ctx.globalAlpha = isDimmed ? 0.1 : (isHighlighted ? 1 : 0.6);

        // 1. Line
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.strokeStyle = isHighlighted ? '#94a3b8' : '#475569'; 
        ctx.lineWidth = (isHighlighted ? 1.5 : 0.5) / globalScale;
        ctx.stroke();

        // 2. Badge (Only if zoomed in very close)
        if (link.label && (globalScale > 3.5 || isHighlighted)) {
            const midX = start.x + (end.x - start.x) * 0.5;
            const midY = start.y + (end.y - start.y) * 0.5;
            
            const fontSize = 2.5; 
            ctx.font = `600 ${fontSize}px sans-serif`;
            const textMetrics = ctx.measureText(link.label);
            const padding = 1;
            const rectW = textMetrics.width + padding * 2;
            const rectH = fontSize + padding * 2;

            const angle = Math.atan2(end.y - start.y, end.x - start.x);
            const textAngle = (angle > Math.PI / 2 || angle < -Math.PI / 2) ? angle + Math.PI : angle;

            ctx.save();
            ctx.translate(midX, midY);
            ctx.rotate(textAngle);

            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.roundRect(-rectW / 2, -rectH / 2, rectW, rectH, 1);
            ctx.fill();
            
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 0.2;
            ctx.stroke();

            ctx.fillStyle = '#0f172a';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(link.label, 0, 0);

            ctx.restore();
        }
        ctx.globalAlpha = 1;
    }, [hoverNode, highlightLinks]);

    // --- CONTROLS ---
    const zoomIn = () => fgRef.current?.zoom(fgRef.current.zoom() * 1.5, 400);
    const zoomOut = () => fgRef.current?.zoom(fgRef.current.zoom() * 0.6, 400);
    const zoomFit = () => fgRef.current?.zoomToFit(400, 50);

    const containerClass = `relative w-full bg-[#111827] rounded-2xl border border-glass-edge overflow-hidden ${className || 'h-[600px]'}`;

    if (loading) return (
        <div className={containerClass}>
            <div className="flex flex-col justify-center items-center h-full text-slate-400">
                <Loader2 className="w-10 h-10 animate-spin text-primary-start mb-4" />
                <p>Duke gjeneruar hartën e çështjes...</p>
            </div>
        </div>
    );

    if (data.nodes.length === 0) {
        return (
            <div className={containerClass}>
                <div className="flex flex-col justify-center items-center h-full text-slate-400">
                    <Share2 className="w-16 h-16 text-slate-700 mb-4" />
                    <h3 className="text-lg font-medium text-slate-300">Harta e zbrazët</h3>
                    <p className="text-sm mt-2">Nuk u gjetën entitete të ndërlidhura.</p>
                </div>
            </div>
        );
    }

    return (
        <div ref={containerRef} className={containerClass}>
            {/* Controls */}
            <div className="absolute bottom-6 right-6 z-20 flex gap-2">
                <button onClick={zoomIn} className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-white rounded-lg border border-slate-700 shadow-lg backdrop-blur-sm transition-all"><ZoomIn size={20} /></button>
                <button onClick={zoomOut} className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-white rounded-lg border border-slate-700 shadow-lg backdrop-blur-sm transition-all"><ZoomOut size={20} /></button>
                <button onClick={zoomFit} className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-white rounded-lg border border-slate-700 shadow-lg backdrop-blur-sm transition-all"><Maximize size={20} /></button>
            </div>

            {/* Legend */}
            <div className="absolute top-6 left-6 z-20 bg-slate-900/90 backdrop-blur-md p-4 rounded-xl border border-slate-700 shadow-xl pointer-events-none min-w-[160px]">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Legjenda</div>
                {Object.entries(COLORS).filter(([key]) => key !== 'DEFAULT').map(([key, color]) => (
                    <div key={key} className="flex items-center gap-3 mb-2 last:mb-0">
                        <span className="w-3.5 h-3.5 rounded-full shadow-sm" style={{ backgroundColor: color }}></span>
                        <span className="text-xs font-medium text-slate-200 capitalize">
                            {LEGEND_LABELS[key] || key.toLowerCase()}
                        </span>
                    </div>
                ))}
            </div>

            <ForceGraph2D
                ref={fgRef}
                width={dimensions.width}
                height={dimensions.height}
                graphData={data}
                
                // Physics Config
                d3VelocityDecay={0.3}
                d3AlphaDecay={0.02}
                
                // Custom Rendering
                nodeCanvasObject={paintNode}
                linkCanvasObject={paintLink}
                
                // Interaction
                onNodeHover={handleNodeHover}
                onEngineStop={() => fgRef.current?.zoomToFit(500, 50)}
                
                // Appearance
                backgroundColor="#0B1120"
                linkDirectionalArrowLength={3}
                linkDirectionalArrowRelPos={1}
            />
        </div>
    );
};

export default CaseGraph;