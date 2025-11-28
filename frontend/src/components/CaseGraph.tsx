// FILE: src/components/CaseGraph.tsx
// PHOENIX PROTOCOL - 2D VISUALIZATION (POLISHED)
// 1. RENDERING: Added text background for readability.
// 2. LAYOUT: Adjusted label position to be tighter to the node.
// 3. UI: Updated Legend to match new backend data.

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
            case 'document': return '#ef4444'; // Red
            case 'person': return '#3b82f6';   // Blue
            case 'organization': return '#10b981'; // Green
            case 'money': return '#f59e0b';    // Orange
            case 'date': return '#8b5cf6';     // Purple
            case 'location': return '#ec4899'; // Pink
            default: return '#9ca3af';         // Gray
        }
    };

    const fetchData = useCallback(async () => {
        if (!caseId) return;
        setLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
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

        // 1. Draw Circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = getNodeColor(node.group);
        ctx.fill();
        
        // 2. Draw Border
        ctx.strokeStyle = '#1f2937'; // Dark border for contrast
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();

        // 3. Draw Text Label (Only if zoomed in or it's a Document)
        if (globalScale > 0.8 || node.group === 'DOCUMENT') {
            ctx.font = `${fontSize}px Sans-Serif`;
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // Padding

            // Text Background (Semi-transparent black)
            ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
            const textY = node.y + radius + 2; // Just below the node
            ctx.fillRect(node.x - bckgDimensions[0] / 2, textY, bckgDimensions[0], bckgDimensions[1]);

            // Text Itself
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top'; // Draw from top
            ctx.fillStyle = '#e5e7eb'; // Light gray text
            ctx.fillText(label, node.x, textY + (fontSize * 0.1));
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
                linkColor={() => '#4b5563'}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                backgroundColor="#0f172a"
                cooldownTicks={100}
                onEngineStop={() => fgRef.current?.zoomToFit(400, 50)}
            />
        </div>
    );
};

export default CaseGraph;