// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - PROFESSIONAL GRAPH (TEXT WRAPPING FIX)
// 1. FIX: Utilized 'wrapText' inside 'paintNode' for multi-line labels.
// 2. STATUS: Clean build, enhanced visualization.

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods, NodeObject, LinkObject } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { Loader2, RefreshCw, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// --- TYPES ---
interface GraphNode extends NodeObject {
    id: string;
    name: string;
    group: string;
    val: number;
    x?: number;
    y?: number;
    neighbors?: GraphNode[];
    links?: GraphLink[];
}

interface GraphLink extends LinkObject {
    source: GraphNode | string;
    target: GraphNode | string;
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
const NODE_R = 18; 

const CaseGraph: React.FC<CaseGraphProps> = ({ caseId, className }) => {
    const { t } = useTranslation();
    
    const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink>>();
    const containerRef = useRef<HTMLDivElement>(null);
    
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    
    // Interaction State
    const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
    const [highlightLinks, setHighlightLinks] = useState(new Set<LinkObject>());
    const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);

    const getNodeColor = (group: string) => {
        switch (group?.toUpperCase()) {
            case 'DOCUMENT': return '#a855f7';     
            case 'PERSON': return '#f97316';       
            case 'ORGANIZATION': return '#06b6d4'; 
            case 'MONEY': return '#3b82f6';        
            case 'DATE': return '#22c55e';         
            case 'LOCATION': return '#ef4444';     
            default: return '#6b7280';             
        }
    };

    const fetchData = useCallback(async () => {
        if (!caseId) return;
        setLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            
            const nodesById = new Map<string, GraphNode>(graphData.nodes.map((n: any) => [n.id, { ...n, neighbors: [], links: [] }]));
            const links = graphData.links.map((l: any) => {
                return { ...l, source: l.source, target: l.target }; 
            });

            links.forEach((link: any) => {
                const a = nodesById.get(link.source);
                const b = nodesById.get(link.target);
                if (a && b) {
                    a.neighbors = a.neighbors || [];
                    b.neighbors = b.neighbors || [];
                    a.neighbors.push(b);
                    b.neighbors.push(a);
                    
                    a.links = a.links || [];
                    b.links = b.links || [];
                    a.links.push(link);
                    b.links.push(link);
                }
            });

            setData({ nodes: Array.from(nodesById.values()), links: links as GraphLink[] });
        } catch (error) {
            console.error("Graph load failed:", error);
        } finally {
            setLoading(false);
        }
    }, [caseId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    useEffect(() => {
        if (!containerRef.current) return;
        const updateDims = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.clientWidth,
                    height: containerRef.current.clientHeight
                });
            }
        };
        const resizeObserver = new ResizeObserver(updateDims);
        resizeObserver.observe(containerRef.current);
        updateDims();
        return () => resizeObserver.disconnect();
    }, []);

    const getReadableLabel = (name: string, group: string) => {
        if (/^[0-9a-fA-F]{24}$/.test(name)) {
            return group === 'DOCUMENT' ? "Dokumenti" : group;
        }
        return name;
    };

    // Helper to wrap text inside the circle
    const wrapText = (ctx: CanvasRenderingContext2D, text: string, maxWidth: number) => {
        const words = text.split(' ');
        let lines = [];
        let currentLine = words[0];

        for (let i = 1; i < words.length; i++) {
            const word = words[i];
            const width = ctx.measureText(currentLine + " " + word).width;
            if (width < maxWidth) {
                currentLine += " " + word;
            } else {
                lines.push(currentLine);
                currentLine = word;
            }
        }
        lines.push(currentLine);
        return lines;
    };

    const handleNodeHover = (node: GraphNode | null) => {
        setHoverNode(node);
        const newHighlightNodes = new Set<string>();
        const newHighlightLinks = new Set<LinkObject>();

        if (node) {
            newHighlightNodes.add(node.id);
            node.neighbors?.forEach(neighbor => newHighlightNodes.add(neighbor.id));
            node.links?.forEach(link => newHighlightLinks.add(link));
        }

        setHighlightNodes(newHighlightNodes);
        setHighlightLinks(newHighlightLinks);
    };

    const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
        if (node.x === undefined || node.y === undefined) return;

        const isHovered = node === hoverNode;
        const isNeighbor = highlightNodes.has(node.id);
        const isDimmed = hoverNode && !isHovered && !isNeighbor;
        
        const label = getReadableLabel(node.name, node.group);
        const color = getNodeColor(node.group);
        const radius = isHovered ? NODE_R * 1.2 : NODE_R;

        ctx.globalAlpha = isDimmed ? 0.1 : 1;

        // Circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();
        
        // Border
        ctx.strokeStyle = isHovered ? '#ffffff' : '#e5e7eb';
        ctx.lineWidth = (isHovered ? 3 : 1.5) / globalScale;
        ctx.stroke();

        // Text (Wrapped)
        if (globalScale > 0.7 || isHovered || isNeighbor) {
            ctx.font = `bold ${radius / 2}px Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#ffffff';
            
            const maxWidth = radius * 1.6;
            // PHOENIX FIX: Using wrapText here
            const lines = wrapText(ctx, label, maxWidth);
            const lineHeight = radius / 1.8;
            const startY = node.y - ((lines.length - 1) * lineHeight) / 2;

            lines.forEach((line, i) => {
                if (i < 2) { // Limit to 2 lines to prevent overflow
                    ctx.fillText(line, node.x!, startY + (i * lineHeight));
                }
            });
        }
        
        ctx.globalAlpha = 1;
    }, [hoverNode, highlightNodes]);

    const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const start = link.source as GraphNode;
        const end = link.target as GraphNode;

        if (start.x === undefined || start.y === undefined || end.x === undefined || end.y === undefined) return;

        const isHighlighted = highlightLinks.has(link);
        const isDimmed = hoverNode && !isHighlighted;

        ctx.globalAlpha = isDimmed ? 0.05 : (isHighlighted ? 1 : 0.4);

        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.strokeStyle = isHighlighted ? '#9ca3af' : '#4b5563'; 
        ctx.lineWidth = (isHighlighted ? 2 : 1) / globalScale;
        ctx.stroke();

        if (link.label && (isHighlighted || globalScale > 1.2)) {
            const textPos = {
                x: start.x + (end.x - start.x) * 0.5,
                y: start.y + (end.y - start.y) * 0.5,
            };
            
            const fontSize = 3.5 / globalScale; 
            ctx.font = `${fontSize}px Sans-Serif`;
            const textWidth = ctx.measureText(link.label).width;
            
            ctx.save();
            ctx.translate(textPos.x, textPos.y);
            const angle = Math.atan2(end.y - start.y, end.x - start.x);
            ctx.rotate(angle > Math.PI / 2 || angle < -Math.PI / 2 ? angle + Math.PI : angle); 
            
            ctx.fillStyle = '#0f172a'; 
            ctx.fillRect(-textWidth / 2 - 1, -fontSize / 2 - 0.5, textWidth + 2, fontSize + 1);
            
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = isHighlighted ? '#ffffff' : '#9ca3af'; 
            ctx.fillText(link.label, 0, 0);
            ctx.restore();
        }
        ctx.globalAlpha = 1;
    }, [hoverNode, highlightLinks]);

    const zoomIn = () => fgRef.current?.zoom(2, 500);
    const zoomOut = () => fgRef.current?.zoom(0.5, 500);
    const zoomFit = () => fgRef.current?.zoomToFit(500, 50);

    const containerClass = `relative w-full bg-slate-900 rounded-2xl border border-glass-edge overflow-hidden ${className || 'h-[600px]'}`;

    if (loading) return <div className={containerClass}><div className="flex justify-center items-center h-full"><Loader2 className="w-8 h-8 animate-spin text-primary-start" /></div></div>;

    if (data.nodes.length === 0) {
        return (
            <div className={containerClass}>
                <div className="flex flex-col justify-center items-center h-full">
                    <RefreshCw className="w-12 h-12 text-gray-600 mb-4" />
                    <p className="text-gray-400">Harta është e zbrazët.</p>
                    <p className="text-sm text-gray-500">Ngarkoni dokumente për të parë lidhjet.</p>
                </div>
            </div>
        );
    }

    return (
        <div ref={containerRef} className={containerClass}>
            <div className="absolute bottom-4 right-4 z-10 flex gap-2">
                <button onClick={zoomIn} className="p-2 bg-black/40 hover:bg-white/10 rounded-lg text-white border border-white/10 backdrop-blur-md transition-colors"><ZoomIn size={18} /></button>
                <button onClick={zoomOut} className="p-2 bg-black/40 hover:bg-white/10 rounded-lg text-white border border-white/10 backdrop-blur-md transition-colors"><ZoomOut size={18} /></button>
                <button onClick={zoomFit} className="p-2 bg-black/40 hover:bg-white/10 rounded-lg text-white border border-white/10 backdrop-blur-md transition-colors"><Maximize size={18} /></button>
            </div>

            <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md p-3 rounded-xl border border-white/10 text-xs text-white shadow-xl pointer-events-none">
                <div className="font-bold mb-2 text-gray-300 tracking-wider">LEGJENDA</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#a855f7] shadow-[0_0_6px_rgba(168,85,247,0.6)]"></span> {t('graph.legend.document', 'Dokumenti')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#f97316] shadow-[0_0_6px_rgba(249,115,22,0.6)]"></span> {t('graph.legend.person', 'Person')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#06b6d4] shadow-[0_0_6px_rgba(6,182,212,0.6)]"></span> {t('graph.legend.organization', 'Organizatë')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#3b82f6] shadow-[0_0_6px_rgba(59,130,246,0.6)]"></span> {t('graph.legend.money', 'Para/Vlerë')}</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#22c55e] shadow-[0_0_6px_rgba(34,197,94,0.6)]"></span> {t('graph.legend.date', 'Datë')}</div>
            </div>

            <ForceGraph2D
                ref={fgRef}
                width={dimensions.width}
                height={dimensions.height}
                graphData={data}
                nodeLabel="name"
                
                nodeCanvasObject={paintNode}
                linkCanvasObject={paintLink}
                onNodeHover={handleNodeHover}
                
                d3VelocityDecay={0.1}
                d3AlphaDecay={0.02}
                backgroundColor="#0f172a"
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                cooldownTicks={100}
                onEngineStop={() => fgRef.current?.zoomToFit(400, 50)}
            />
        </div>
    );
};

export default CaseGraph;