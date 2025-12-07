// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - VISUALIZATION FIX
// 1. TYPES: Relaxed 'group' type to 'string' to match API response.
// 2. CLEANUP: Removed unused imports.

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { Loader2, RefreshCw, Maximize2, Share2 } from 'lucide-react';

// Define the Graph Data Types locally to match API flexibility
interface GraphNode {
    id: string;
    name: string;
    group: string; // Changed from strict union to string to match API
    val: number; 
    neighbor_count?: number;
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
    label?: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

interface CaseGraphProps {
    caseId: string;
    height?: number;
    className?: string;
}

// Professional Color Palette
const COLORS: Record<string, string> = {
    PERSON: '#3b82f6',       // Blue
    ORGANIZATION: '#8b5cf6', // Purple
    MONEY: '#10b981',        // Green
    DATE: '#f59e0b',         // Amber
    DOCUMENT: '#6b7280',     // Gray
    ENTITY: '#ec4899',       // Pink
    TEXT: '#f3f4f6',         // White-ish
    BG: '#00000000'          // Transparent
};

const CaseGraph: React.FC<CaseGraphProps> = ({ caseId, height = 500, className = "" }) => {
    const fgRef = useRef<any>();
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [containerWidth, setContainerWidth] = useState(800);
    const containerRef = useRef<HTMLDivElement>(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            // Explicitly cast or trust the data structure matches
            setData(graphData as unknown as GraphData);
        } catch (error) {
            console.error("Graph fetch failed", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (caseId) fetchData();
    }, [caseId]);

    useEffect(() => {
        if (!containerRef.current) return;
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                setContainerWidth(entry.contentRect.width);
            }
        });
        resizeObserver.observe(containerRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.name;
        const fontSize = 12 / globalScale;
        const radius = node.val ? Math.sqrt(node.val) * 2 : 5;
        
        // Safe Color Lookup (Default to ENTITY pink if group unknown)
        const groupKey = node.group ? node.group.toUpperCase() : 'ENTITY';
        const color = COLORS[groupKey] || COLORS.ENTITY;

        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();
        
        if (node.val > 15) {
            ctx.shadowColor = color;
            ctx.shadowBlur = 10;
        } else {
            ctx.shadowBlur = 0;
        }
        
        if (globalScale > 0.8 || node.val > 15) { 
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = COLORS.TEXT;
            ctx.fillText(label, node.x, node.y + radius + (fontSize));
        }
    }, []);

    const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const start = link.source;
        const end = link.target;

        if (typeof start !== 'object' || typeof end !== 'object') return;

        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.lineWidth = 1 / globalScale;
        ctx.strokeStyle = '#4b5563'; 
        ctx.stroke();

        if (globalScale > 1.2 && link.label) {
            const textPos = {
                x: start.x + (end.x - start.x) * 0.5,
                y: start.y + (end.y - start.y) * 0.5,
            };
            const fontSize = 8 / globalScale;
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.fillStyle = '#9ca3af'; 
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(link.label, textPos.x, textPos.y);
        }
    }, []);

    return (
        <div ref={containerRef} className={`relative bg-gray-900/50 backdrop-blur-sm border border-white/10 rounded-2xl overflow-hidden shadow-2xl ${className}`}>
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
                <div className="bg-black/40 backdrop-blur-md p-2 rounded-lg border border-white/5 flex gap-2">
                    <button onClick={fetchData} className="p-1.5 hover:bg-white/10 rounded-md text-gray-400 hover:text-white transition-colors" title="Reload Graph">
                        <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button onClick={() => fgRef.current?.zoomToFit(400)} className="p-1.5 hover:bg-white/10 rounded-md text-gray-400 hover:text-white transition-colors" title="Fit to View">
                        <Maximize2 size={16} />
                    </button>
                </div>
                <div className="hidden sm:flex gap-3 bg-black/40 backdrop-blur-md px-3 py-2 rounded-lg border border-white/5 text-[10px] font-bold uppercase tracking-wider">
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.PERSON}}></span> Person</div>
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.MONEY}}></span> Money</div>
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.ORGANIZATION}}></span> Org</div>
                </div>
            </div>

            {loading ? (
                <div className="flex flex-col items-center justify-center h-full" style={{ height }}>
                    <Loader2 className="w-10 h-10 text-primary-start animate-spin mb-4" />
                    <p className="text-gray-400 text-sm animate-pulse">Analyzing Case Connections...</p>
                </div>
            ) : data.nodes.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full" style={{ height }}>
                    <Share2 className="w-16 h-16 text-gray-700 mb-4" />
                    <h3 className="text-gray-300 font-bold text-lg">Harta e Zbrazët</h3>
                    <p className="text-gray-500 text-sm max-w-xs text-center mt-2">
                        Ngarkoni dokumente (Fatura, Kontrata) për të gjeneruar rrjetin e inteligjencës.
                    </p>
                </div>
            ) : (
                <ForceGraph2D
                    ref={fgRef}
                    width={containerWidth}
                    height={height}
                    graphData={data}
                    nodeLabel="name"
                    nodeCanvasObject={paintNode}
                    linkCanvasObject={paintLink}
                    backgroundColor="rgba(0,0,0,0)"
                    d3AlphaDecay={0.02}
                    d3VelocityDecay={0.3}
                    cooldownTicks={100}
                    onEngineStop={() => fgRef.current?.zoomToFit(400)}
                />
            )}
        </div>
    );
};

export default CaseGraph;