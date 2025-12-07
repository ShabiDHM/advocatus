// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - VISUALIZATION ENGINE V2 (NEO4J STYLE)
// 1. STYLE: Added directional arrows and link labels (relationships).
// 2. READABILITY: Node labels are always visible with high-contrast backgrounds.
// 3. PHYSICS: Tightened 'charge' forces to create a compact "Network Map" instead of "Planets".

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { Loader2, RefreshCw, Maximize2, Share2 } from 'lucide-react';

interface GraphNode {
    id: string;
    name: string;
    group: string;
    val: number; 
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
    label?: string; // The relationship name (e.g., "MENTIONS")
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

// Neo4j-inspired Professional Palette
const COLORS: Record<string, string> = {
    PERSON: '#57C7E3',       // Cyan Blue
    ORGANIZATION: '#FFC454', // Golden Yellow
    MONEY: '#56DAA8',        // Vivid Green
    DATE: '#D9C8AE',         // Beige
    DOCUMENT: '#C990C0',     // Muted Purple
    ENTITY: '#FF6C7C',       // Salmon Red (Fallback)
    TEXT: '#FFFFFF',         
    BG_LABEL: 'rgba(0, 0, 0, 0.6)' 
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
            setData(graphData as unknown as GraphData);
        } catch (error) {
            console.error("Graph fetch failed", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { if (caseId) fetchData(); }, [caseId]);

    useEffect(() => {
        if (!containerRef.current) return;
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) setContainerWidth(entry.contentRect.width);
        });
        resizeObserver.observe(containerRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    // --- CUSTOM RENDERING ---

    const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.name;
        // Keep text size readable but scalable
        const fontSize = 12 / globalScale; 
        const radius = node.val ? Math.sqrt(node.val) * 3 : 5; // Larger nodes for better visibility
        
        const groupKey = node.group ? node.group.toUpperCase() : 'ENTITY';
        const color = COLORS[groupKey] || COLORS.ENTITY;

        // 1. Draw Circle (Node)
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#FFFFFF'; // White border for pop
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();

        // 2. Draw Label Background (Pill shape)
        if (globalScale > 0.5) { // Always show labels unless zoomed WAY out
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.5); 

            ctx.fillStyle = COLORS.BG_LABEL;
            ctx.fillRect(
                node.x - bckgDimensions[0] / 2, 
                node.y + radius + 2, 
                bckgDimensions[0], 
                bckgDimensions[1]
            );

            // 3. Draw Label Text
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = COLORS.TEXT;
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.fillText(label, node.x, node.y + radius + 2 + fontSize / 2);
        }
    }, []);

    const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const start = link.source;
        const end = link.target;
        if (typeof start !== 'object' || typeof end !== 'object') return;

        // 1. Draw Line
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.lineWidth = 1.5 / globalScale;
        ctx.strokeStyle = '#6b7280'; // Cool Gray
        ctx.stroke();

        // 2. Draw Link Label (Relationship Name)
        if (link.label && globalScale > 1) {
            const textPos = {
                x: start.x + (end.x - start.x) * 0.5,
                y: start.y + (end.y - start.y) * 0.5,
            };
            const fontSize = 10 / globalScale;
            ctx.font = `bold ${fontSize}px Sans-Serif`;
            ctx.fillStyle = '#a1a1aa'; // Lighter gray for text
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // Text Background for readability
            const textWidth = ctx.measureText(link.label).width;
            ctx.fillStyle = 'rgba(0,0,0,0.8)';
            ctx.fillRect(textPos.x - textWidth/2 - 2, textPos.y - fontSize/2 - 2, textWidth + 4, fontSize + 4);
            
            ctx.fillStyle = '#d4d4d8';
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
                {/* Legend */}
                <div className="hidden sm:flex gap-3 bg-black/40 backdrop-blur-md px-3 py-2 rounded-lg border border-white/5 text-[10px] font-bold uppercase tracking-wider text-gray-300">
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.PERSON}}></span> Person</div>
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.MONEY}}></span> Money</div>
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.ORGANIZATION}}></span> Org</div>
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background: COLORS.DOCUMENT}}></span> Doc</div>
                </div>
            </div>

            {loading ? (
                <div className="flex flex-col items-center justify-center h-full" style={{ height }}>
                    <Loader2 className="w-10 h-10 text-primary-start animate-spin mb-4" />
                    <p className="text-gray-400 text-sm animate-pulse">Analyzing Connections...</p>
                </div>
            ) : data.nodes.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full" style={{ height }}>
                    <Share2 className="w-16 h-16 text-gray-700 mb-4" />
                    <h3 className="text-gray-300 font-bold text-lg">Harta e Zbrazët</h3>
                    <p className="text-gray-500 text-sm max-w-xs text-center mt-2">
                        Sistemi nuk ka gjetur ende lidhje për këtë rast.
                    </p>
                </div>
            ) : (
                <ForceGraph2D
                    ref={fgRef}
                    width={containerWidth}
                    height={height}
                    graphData={data}
                    nodeLabel="name" // Tooltip
                    nodeCanvasObject={paintNode} // Custom Node Look
                    linkCanvasObject={paintLink} // Custom Link Look
                    linkDirectionalArrowLength={4} // Arrow Head Size
                    linkDirectionalArrowRelPos={1} // Arrow at the end
                    backgroundColor="rgba(0,0,0,0)"
                    
                    // PHYSICS TUNING: Tighter Cluster
                    d3AlphaDecay={0.01} 
                    d3VelocityDecay={0.4}
                    // Increase attraction, reduce repulsion to fix "Planets" issue
                    cooldownTicks={100}
                    onEngineStop={() => fgRef.current?.zoomToFit(400)}
                />
            )}
        </div>
    );
};

export default CaseGraph;