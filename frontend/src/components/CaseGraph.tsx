// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - HIGH FIDELITY GRAPH (FLEXIBLE HEIGHT)
// 1. FIX: Added 'className' to support full-height layout in parent.
// 2. RESIZE: Uses ResizeObserver for robust dimension tracking.
// 3. VISUALS: Preserved "Image 1" style renderers.

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { Loader2, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface GraphNode {
    id: string;
    name: string;
    group: string;
    val: number;
    x?: number;
    y?: number;
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
    label: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

interface CaseGraphProps {
    caseId: string;
    // PHOENIX FIX: Allow external sizing
    className?: string;
}

const CaseGraph: React.FC<CaseGraphProps> = ({ caseId, className }) => {
    const { t } = useTranslation();
    const fgRef = useRef<ForceGraphMethods>();
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

    const getNodeColor = (group: string) => {
        switch (group?.toLowerCase()) {
            case 'document': return '#ef4444'; 
            case 'person': return '#3b82f6';   
            case 'organization': return '#10b981'; 
            case 'money': return '#f59e0b';    
            case 'date': return '#8b5cf6';     
            case 'location': return '#ec4899'; 
            default: return '#6b7280';         
        }
    };

    const fetchData = useCallback(async () => {
        if (!caseId) return;
        setLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            setData({ nodes: graphData.nodes || [], links: graphData.links || [] });
        } catch (error) {
            console.error("Graph load failed:", error);
        } finally {
            setLoading(false);
        }
    }, [caseId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // PHOENIX FIX: Robust Resize Observer
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

        const resizeObserver = new ResizeObserver(() => {
            updateDims();
        });

        resizeObserver.observe(containerRef.current);
        updateDims(); // Initial call

        return () => resizeObserver.disconnect();
    }, []);

    const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.name;
        const baseRadius = node.group === 'DOCUMENT' ? 12 : 8; 
        const radius = baseRadius * 1.5; 
        
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = getNodeColor(node.group);
        ctx.fill();
        
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();

        if (globalScale > 0.6) {
            const fontSize = (radius / 2) + 2; 
            ctx.font = `bold ${fontSize}px Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#ffffff';
            
            let displayLabel = label;
            if (label.length > 10 && globalScale < 1.5) {
                displayLabel = label.substring(0, 8) + '..';
            }
            
            ctx.fillText(displayLabel, node.x, node.y);
        }
    }, []);

    const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const start = link.source;
        const end = link.target;

        if (typeof start !== 'object' || typeof end !== 'object') return;

        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.strokeStyle = '#4b5563'; 
        ctx.lineWidth = 1 / globalScale;
        ctx.stroke();

        if (globalScale > 0.8 && link.label) {
            const textPos = {
                x: start.x + (end.x - start.x) * 0.5,
                y: start.y + (end.y - start.y) * 0.5,
            };
            
            const fontSize = 4 / globalScale; 
            ctx.font = `${fontSize}px Sans-Serif`;
            const textWidth = ctx.measureText(link.label).width;
            
            ctx.save();
            ctx.translate(textPos.x, textPos.y);
            const angle = Math.atan2(end.y - start.y, end.x - start.x);
            ctx.rotate(angle > Math.PI / 2 || angle < -Math.PI / 2 ? angle + Math.PI : angle); 
            
            ctx.fillStyle = '#0f172a'; 
            ctx.fillRect(-textWidth / 2 - 1, -fontSize / 2 - 1, textWidth + 2, fontSize + 2);
            
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#9ca3af'; 
            ctx.fillText(link.label, 0, 0);
            ctx.restore();
        }
    }, []);

    // PHOENIX FIX: Apply className to container
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
            <div className="absolute top-4 right-4 z-10 bg-black/60 backdrop-blur-md p-3 rounded-xl border border-white/10 text-xs text-white shadow-xl pointer-events-none">
                <div className="font-bold mb-2 text-gray-300">LEGJENDA</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-red-500"></span> {t('graph.legend.document', 'Dokumenti')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-blue-500"></span> {t('graph.legend.person', 'Person')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-green-500"></span> {t('graph.legend.organization', 'Organizatë')}</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-yellow-500"></span> {t('graph.legend.money', 'Para/Vlerë')}</div>
            </div>

            <ForceGraph2D
                ref={fgRef}
                width={dimensions.width}
                height={dimensions.height}
                graphData={data}
                nodeLabel="name"
                nodeCanvasObject={paintNode}
                linkCanvasObject={paintLink}
                dagMode="radialout"
                d3VelocityDecay={0.3}
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