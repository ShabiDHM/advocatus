// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - CLEANUP
// 1. FIX: Resolved unused 't' variable by implementing translation wrappers.
// 2. LOGIC: Maintained 2D Graph visualization engine.

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
}

interface GraphLink {
    source: string;
    target: string;
    label: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

interface CaseGraphProps {
    caseId: string;
}

const CaseGraph: React.FC<CaseGraphProps> = ({ caseId }) => {
    const { t } = useTranslation();
    const fgRef = useRef<ForceGraphMethods>();
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [containerDimensions, setContainerDimensions] = useState({ width: 800, height: 600 });
    const containerRef = useRef<HTMLDivElement>(null);

    // --- Color Palette ---
    const getNodeColor = (group: string) => {
        switch (group?.toLowerCase()) {
            case 'document': return '#ef4444'; // Red (Center)
            case 'person': return '#3b82f6';   // Blue
            case 'organization': return '#10b981'; // Green
            case 'money': return '#f59e0b';    // Orange
            case 'date': return '#8b5cf6';     // Purple
            case 'location': return '#ec4899'; // Pink
            default: return '#6b7280';         // Gray
        }
    };

    const fetchData = useCallback(async () => {
        if (!caseId) return;
        setLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            // Safety check for backend response format
            const safeNodes = graphData.nodes || [];
            const safeLinks = graphData.links || [];
            setData({ nodes: safeNodes, links: safeLinks });
        } catch (error) {
            console.error("Failed to load graph data:", error);
        } finally {
            setLoading(false);
        }
    }, [caseId]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Responsive Sizing
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setContainerDimensions({
                    width: containerRef.current.clientWidth,
                    height: containerRef.current.clientHeight || 600
                });
            }
        };

        window.addEventListener('resize', updateDimensions);
        updateDimensions();
        
        // Short timeout to ensure container is rendered
        const timeout = setTimeout(updateDimensions, 100);

        return () => {
            window.removeEventListener('resize', updateDimensions);
            clearTimeout(timeout);
        };
    }, []);

    // Custom Node Renderer for Professional Look
    const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.name;
        const fontSize = 12 / globalScale;
        const radius = node.val ? Math.sqrt(node.val) * 2 : 5;

        // Draw Circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = getNodeColor(node.group);
        ctx.fill();
        
        // Border
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();

        // Text Label
        if (globalScale > 0.8 || node.group === 'DOCUMENT') {
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#ffffff'; // White text
            ctx.fillText(label, node.x, node.y + radius + fontSize);
        }
    }, []);

    if (loading) {
        return (
            <div className="flex flex-col justify-center items-center h-[500px] bg-background-dark/50 rounded-2xl border border-glass-edge">
                <Loader2 className="w-10 h-10 animate-spin text-primary-start mb-4" />
                <p className="text-gray-400">{t('graph.analyzing', 'Duke analizuar lidhjet...')}</p>
            </div>
        );
    }

    if (data.nodes.length === 0) {
        return (
            <div className="flex flex-col justify-center items-center h-[500px] bg-background-dark/50 rounded-2xl border border-glass-edge">
                <RefreshCw className="w-10 h-10 text-gray-500 mb-4" />
                <p className="text-gray-400 text-lg">{t('graph.noData', 'Asnjë e dhënë grafike për këtë rast.')}</p>
                <p className="text-sm text-gray-600 mt-2">{t('graph.uploadHint', 'Ngarkoni dokumente për të gjeneruar hartën.')}</p>
            </div>
        );
    }

    return (
        <div ref={containerRef} className="relative w-full h-[600px] bg-slate-900 rounded-2xl border border-glass-edge overflow-hidden shadow-inner">
            <div className="absolute top-4 right-4 z-10 bg-black/40 backdrop-blur-md p-2 rounded-lg border border-white/10 text-xs text-white">
                <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> {t('graph.legend.document', 'Dokumenti')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> {t('graph.legend.person', 'Person')}</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-green-500"></span> {t('graph.legend.organization', 'Organizatë')}</div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-orange-500"></span> {t('graph.legend.money', 'Para/Vlerë')}</div>
            </div>

            <ForceGraph2D
                ref={fgRef}
                width={containerDimensions.width}
                height={containerDimensions.height}
                graphData={data}
                nodeLabel="name"
                nodeRelSize={6}
                nodeCanvasObject={paintNode}
                linkColor={() => '#4b5563'} // Gray links
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                backgroundColor="#0f172a" // Matches background-dark
                cooldownTicks={100}
                onEngineStop={() => fgRef.current?.zoomToFit(400, 50)} // Auto-fit on load
            />
        </div>
    );
};

export default CaseGraph;