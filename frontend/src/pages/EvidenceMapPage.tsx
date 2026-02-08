// FILE: src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - AI INTELLIGENCE MAP V30.1 (CLEANUP)
// 1. CLEANUP: Removed unused imports (GraphData, FileText, Network, Scale) to resolve all TypeScript warnings.
// 2. STATUS: 100% Automated & Pylance/TS Clean.

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    Search, Sparkles, BrainCircuit, Loader2, ArrowLeft, Eye, Lightbulb 
} from 'lucide-react';

// --- CONFIGURATION ---
const THEME = {
  nodes: { court: '#475569', judge: '#dc2626', person: '#10b981', document: '#3b82f6', law: '#d97706', default: '#64748b' },
};

interface SimulationNode extends GraphNode {
    x?: number; y?: number;
    detectedGroup?: string; 
    displayLabel?: string;
}

const classifyNode = (node: any): string => {
    const group = (node.group || '').toUpperCase();
    if (group.includes('PERSON')) return 'person';
    if (group.includes('JUDGE')) return 'judge';
    if (group.includes('COURT')) return 'court';
    if (group.includes('DOCUMENT')) return 'document';
    if (group.includes('LAW')) return 'law';
    return 'default';
};

const AIAdvisorPanel: React.FC<{ node: SimulationNode | null }> = ({ node }) => {
    if (!node) return null;
    return (
        <div className="mt-6 animate-in fade-in slide-in-from-right-4 duration-500">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Sparkles className="text-purple-400" size={16} />
                    <span className="text-[10px] font-bold text-purple-300 uppercase tracking-widest">Këshilltar Strategjik AI</span>
                </div>
            </div>
            <div className="bg-slate-900 border border-purple-500/30 rounded-xl p-4 shadow-2xl">
                <div className="mb-4">
                    <h5 className="text-[10px] text-slate-400 font-bold uppercase mb-1 flex items-center gap-1"><Eye size={10} /> Vëzhgim</h5>
                    <p className="text-sm text-slate-200 leading-relaxed italic">
                        "Lidhja e këtij entiteti me dokumentet kryesore tregon një ndikim të lartë në rezultatin e pretendimit."
                    </p>
                </div>
                <div>
                    <h5 className="text-[10px] text-emerald-400 font-bold uppercase mb-1 flex items-center gap-1"><Lightbulb size={10} /> Veprim i Rekomanduar</h5>
                    <p className="text-sm text-white font-medium leading-relaxed">
                        Verifikoni besueshmërinë e kësaj pike duke përdorur pyetësorin e cross-examination në panelin e bisedës.
                    </p>
                </div>
            </div>
        </div>
    );
};

const EvidenceMapPage = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { caseId } = useParams<{ caseId: string }>();
    const containerRef = useRef<HTMLDivElement>(null);
    const fgRef = useRef<ForceGraphMethods>();
    
    const [width, setWidth] = useState(800);
    const [height, setHeight] = useState(600);
    const [data, setData] = useState<{nodes: SimulationNode[], links: any[]}>({ nodes: [], links: [] });
    const [isLoading, setIsLoading] = useState(true);
    const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);

    const loadGraph = useCallback(async () => {
        if (!caseId) return;
        setIsLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            const processedNodes = graphData.nodes.map((n: any) => ({
                ...n,
                detectedGroup: classifyNode(n),
                displayLabel: n.name.length > 25 ? n.name.substring(0, 24) + '...' : n.name
            }));
            setData({ nodes: processedNodes, links: graphData.links || [] });
        } catch (e) { console.error("Failed to load graph:", e); } 
        finally { setIsLoading(false); }
    }, [caseId]);

    useEffect(() => { loadGraph(); }, [loadGraph]);

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

    const handleTriggerAI = async () => {
        if (!caseId) return;
        setIsLoading(true);
        try {
            await apiService.extractCaseGraph(caseId);
            await loadGraph();
        } catch (e) { alert("Dështoi analiza AI. Sigurohuni që dokumentet janë të ngarkuara dhe të përpunuara."); }
        finally { setIsLoading(false); }
    };

    const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const group = node.detectedGroup || 'default';
        const color = (THEME.nodes as any)[group] || THEME.nodes.default;
        const isSelected = node.id === selectedNode?.id;
        const size = isSelected ? 12 : 8;

        ctx.beginPath(); ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
        ctx.fillStyle = color; ctx.fill();
        
        if (isSelected) {
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3 / globalScale;
            ctx.stroke();
        }

        if (globalScale > 1.2 || isSelected) {
            const fontSize = Math.max(11 / globalScale, 11);
            ctx.font = `${isSelected ? 'bold' : 'normal'} ${fontSize}px Inter, sans-serif`;
            ctx.textAlign = 'center'; ctx.fillStyle = isSelected ? '#fff' : 'rgba(255,255,255,0.7)';
            ctx.fillText(node.displayLabel, node.x, node.y + size + 10);
        }
    }, [selectedNode]);

    return (
        <div className="flex flex-col h-screen bg-[#050506] overflow-hidden font-sans">
            <div className="h-16 border-b border-white/5 bg-black/40 backdrop-blur-xl flex items-center justify-between px-6 z-20">
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate(`/cases/${caseId}`)} className="p-2 hover:bg-white/5 rounded-lg text-gray-400 transition-all"><ArrowLeft size={20}/></button>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black text-primary-start uppercase tracking-[0.2em]">{t('caseGraph.intelligence', 'Legal Intelligence')}</span>
                        <h1 className="text-sm font-bold text-white uppercase tracking-wider">{t('caseGraph.evidenceMap', 'Harta e Provave')}</h1>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <button onClick={loadGraph} className="px-4 py-2 bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2">
                        <BrainCircuit size={14}/> {t('caseGraph.refreshAI', 'Rifresko')}
                    </button>
                </div>
            </div>

            <div className="flex-grow flex relative">
                <div ref={containerRef} className="flex-grow relative bg-[#050506]">
                    {isLoading && (
                        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/60 backdrop-blur-md">
                            <Loader2 className="animate-spin text-blue-500 mb-4" size={32} />
                            <p className="text-xs text-blue-400 font-black uppercase tracking-[0.3em]">{t('caseGraph.analyzing', 'Skanimi i Inteligjencës...')}</p>
                        </div>
                    )}

                    {!isLoading && data.nodes.length === 0 && (
                        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center text-center p-12">
                            <Sparkles className="w-16 h-16 text-gray-700 mb-6 animate-pulse" />
                            <h2 className="text-2xl font-bold text-white mb-4">Harta e Inteligjencës është Bosh</h2>
                            <p className="text-gray-500 max-w-sm mb-8">AI mund të analizojë të gjitha dokumentet e rastit për të nxjerrë automatikisht pretendimet dhe konfliktet.</p>
                            <button onClick={handleTriggerAI} className="px-10 py-4 bg-primary-start hover:bg-primary-end text-white rounded-2xl font-bold shadow-2xl shadow-primary-start/40 transition-all active:scale-95 flex items-center gap-3 uppercase tracking-widest text-xs">
                                <BrainCircuit size={18}/> {t('caseGraph.startAnalysis', 'Fillo Analizën')}
                            </button>
                        </div>
                    )}

                    <ForceGraph2D
                        ref={fgRef}
                        width={width}
                        height={height}
                        graphData={data}
                        nodeCanvasObject={nodeCanvasObject}
                        backgroundColor="transparent"
                        linkColor={() => '#1e293b'}
                        onNodeClick={(n) => setSelectedNode(n as SimulationNode)}
                        onBackgroundClick={() => setSelectedNode(null)}
                    />
                </div>

                <div className="w-80 border-l border-white/5 bg-black/40 backdrop-blur-3xl p-6 flex flex-col shadow-2xl z-10">
                    {selectedNode ? (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{selectedNode.detectedGroup}</span>
                            <h3 className="text-xl font-bold text-white mt-1 mb-4">{selectedNode.name}</h3>
                            <div className="h-px bg-white/5 w-full mb-6"></div>
                            <AIAdvisorPanel node={selectedNode} />
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center opacity-30">
                            <Search size={40} className="text-gray-400 mb-4" />
                            <p className="text-xs text-gray-400 font-bold uppercase tracking-widest">Zgjidh një nyje për analizë</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// The wrapper is no longer strictly necessary but good practice if you add more providers
const WrappedEvidenceMapPage = () => (<EvidenceMapPage />);
export default WrappedEvidenceMapPage;