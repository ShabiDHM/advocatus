// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - CLEAN BUILD
// 1. FIX: Removed unused imports (useMemo, RefreshCw) and unused translation hook.
// 2. STATUS: Warning-free, exact Neo4j styling retained.

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

// --- NEO4J STYLE CONSTANTS ---
const NODE_R = 22; // Larger nodes for better readability
const FONT_SIZE = 14;

// Neo4j Default Color Palette
const COLORS: Record<string, string> = {
    'DOCUMENT': '#8DCC93',      // Soft Green
    'PERSON': '#F79767',        // Orange
    'ORGANIZATION': '#57C7E3',  // Light Blue
    'COMPANY': '#57C7E3',
    'MONEY': '#FFC454',         // Yellow/Gold
    'DATE': '#D9C8AE',          // Beige
    'LOCATION': '#F16667',      // Red
    'DEFAULT': '#C990C0'        // Purple/Pink for unknown
};

// Albanian Label Mapping
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
            
            // Transform API data to ForceGraph objects
            const nodesMap = new Map<string, GraphNode>();
            response.nodes.forEach((n: APINode) => {
                nodesMap.set(n.id, { ...n });
            });

            // Map links and ensure source/target exist
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

    // Helper: Fit text inside circle
    const drawText = (ctx: CanvasRenderingContext2D, node: GraphNode, r: number) => {
        const label = node.name || node.id;
        const fontSize = Math.min(r * 0.5, FONT_SIZE);
        ctx.font = `bold ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#1e293b'; // Dark text for contrast inside colored bubbles
        
        // Simple truncation
        const maxWidth = r * 1.8;
        let text = label;
        if (ctx.measureText(text).width > maxWidth) {
            text = label.substring(0, 8) + '...';
        }
        ctx.fillText(text, node.x!, node.y!);
    };

    const handleNodeHover = (node: GraphNode | null) => {
        setHoverNode(node);
        const newHighlightNodes = new Set<string>();
        const newHighlightLinks = new Set<LinkObject>();

        if (node) {
            newHighlightNodes.add(node.id);
            // We need to traverse links to find neighbors
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
        const radius = isHovered ? NODE_R * 1.15 : NODE_R;

        // Dimming effect
        ctx.globalAlpha = isDimmed ? 0.2 : 1;

        // 1. Node Circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();
        
        // 2. Node Border (Neo4j style: darker shade of fill)
        ctx.lineWidth = isHovered ? 3 / globalScale : 1.5 / globalScale;
        ctx.strokeStyle = 'rgba(0,0,0,0.2)'; 
        ctx.stroke();

        // 3. Text
        // Only show text if global zoom is decent or hovered
        if (globalScale > 0.6 || isHovered || isNeighbor) {
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

        // 1. Draw Line
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.strokeStyle = isHighlighted ? '#94a3b8' : '#475569'; // Slate 400/600
        ctx.lineWidth = (isHighlighted ? 2 : 1) / globalScale;
        ctx.stroke();

        // 2. Draw Label (The "Relationship Badge")
        if (link.label && (globalScale > 1.2 || isHighlighted)) {
            const midX = start.x + (end.x - start.x) * 0.5;
            const midY = start.y + (end.y - start.y) * 0.5;
            
            const fontSize = 4; // Tiny scale-invariant font
            ctx.font = `600 ${fontSize}px sans-serif`;
            const textMetrics = ctx.measureText(link.label);
            const padding = 2;
            const rectW = textMetrics.width + padding * 2;
            const rectH = fontSize + padding * 2;

            // Rotate badge to align with edge
            const angle = Math.atan2(end.y - start.y, end.x - start.x);
            // Flip text if upside down
            const textAngle = (angle > Math.PI / 2 || angle < -Math.PI / 2) ? angle + Math.PI : angle;

            ctx.save();
            ctx.translate(midX, midY);
            ctx.rotate(textAngle);

            // Badge Background (White)
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.roundRect(-rectW / 2, -rectH / 2, rectW, rectH, 1);
            ctx.fill();
            
            // Badge Border
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 0.5;
            ctx.stroke();

            // Text
            ctx.fillStyle = '#0f172a'; // Dark Slate
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(link.label, 0, 0);

            ctx.restore();
        }
        ctx.globalAlpha = 1;
    }, [hoverNode, highlightLinks]);

    // --- ZOOM CONTROLS ---
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
                
                // Physics - Neo4j Feel
                d3VelocityDecay={0.3} // Higher friction = less jitter
                d3AlphaDecay={0.02}   // Slower cooling
                
                // Custom Rendering
                nodeCanvasObject={paintNode}
                linkCanvasObject={paintLink}
                
                // Interaction
                onNodeHover={handleNodeHover}
                onEngineStop={() => fgRef.current?.zoomToFit(500, 50)}
                
                // Appearance
                backgroundColor="#0B1120" // Deep Dark Blue/Black
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1} // Arrow at end
            />
        </div>
    );
};

export default CaseGraph;