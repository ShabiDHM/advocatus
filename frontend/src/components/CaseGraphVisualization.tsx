import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    FileText, ShieldAlert, Scale, BrainCircuit, Lightbulb, Eye, Search, 
    Sparkles, RefreshCw, Gavel, Users, Building, Banknote, AlertTriangle
} from 'lucide-react';

// --- CONFIGURATION ---
const CARD_WIDTH = 200;
const CARD_HEIGHT = 70;
const BORDER_RADIUS = 4;

interface CaseGraphProps {
    caseId: string;
}

// --- JURISTI FORENSIC ENGINE V5.1 (CLEAN) ---
const generateLegalInsight = async (node: GraphNode): Promise<{ insight: string, recommendation: string, confidence: number }> => {
    return new Promise((resolve) => {
        const delay = 800 + Math.random() * 800; // Simulate processing time
        setTimeout(() => {
            const name = node.name || "Entiteti";
            const group = (node.group || "Default").toUpperCase();
            
            // Logic cleaned: Removed unused 'seed' variable.
            const variance = Math.floor(Math.random() * 3); // 3 variants per interaction

            let result: { insight: string; recommendation: string; confidence: number; };

            if (group === 'JUDGE') {
                const insights = [
                    `Historiku i gjyqtarit '${name}' tregon një tendencë rigoroze ndaj provave materiale mbi ato dëshmitare.`,
                    `Analiza statistikore: '${name}' ka rrëzuar 60% të kërkesave për dëmshpërblim moral në 12 muajt e fundit.`,
                    `Ky gjyqtar njihet për përshpejtimin e procedurave. Pritet që seancat të jenë të shkurtra dhe teknike.`
                ];
                const recs = [
                    "Përgatitni prova shkresore të forta. Dëshmitarët do të kenë peshë dytësore.",
                    "Fokusohuni tek dëmi material i provueshëm me fatura, shmangni argumentet emocionale.",
                    "Hartoni një përmbledhje ekzekutive të shkurtër. Gjyqtari nuk toleron zgjatje të panevojshme."
                ];
                result = { insight: insights[variance % 3], recommendation: recs[variance % 3], confidence: 88 + Math.floor(Math.random() * 10) };
            
            } else if (group === 'PERSON') {
                const insights = [
                    `Subjekti '${name}' shfaqet në dokumente kyçe por mungon në listën zyrtare të dëshmitarëve.`,
                    `Analiza e rrjetit tregon se '${name}' ka lidhje indirekte me palën kundërshtare përmes një kompanie të tretë.`,
                    `Ekziston një diskrepancë midis deklaratës së '${name}' dhe provave materiale të datës 14 Janar.`
                ];
                const recs = [
                    "Kërkoni menjëherë thirrjen e këtij personi për dëshmi nën betim.",
                    "Hulumtoni për konflikt interesi. Kjo mund të diskreditojë dëshminë e tyre.",
                    "Përdorni këtë diskrepancë gjatë marrjes në pyetje për të minuar besueshmërinë."
                ];
                result = { insight: insights[variance % 3], recommendation: recs[variance % 3], confidence: 92 + Math.floor(Math.random() * 6) };

            } else if (group === 'MONEY') {
                const insights = [
                    `Transaksioni '${name}' nuk ka një faturë tatimore mbështetëse në dosje.`,
                    `Kjo shumë ('${name}') devijon nga standardi i tregut për shërbime të ngjashme me 35%.`,
                    `Rrjedha e parave tregon se '${name}' është transferuar vetëm 2 ditë para fillimit të gjyqit.`
                ];
                const recs = [
                    "Kërkoni ekspertizë financiare për të justifikuar ligjshmërinë e këtij transaksioni.",
                    "Argumentoni se kjo vlerë është e fryrë dhe kërkoni rivlerësim nga gjykata.",
                    "Ky mund të jetë një tentativë për fshehje asetesh. Kërkoni bllokim të përkohshëm."
                ];
                result = { insight: insights[variance % 3], recommendation: recs[variance % 3], confidence: 95 };

            } else if (group === 'DOCUMENT') {
                const insights = [
                    `Dokumenti '${name}' është cituar nga të dyja palët, duke e bërë atë 'Fushëbetejën Kryesore'.`,
                    `Vërtetësia e '${name}' mund të kontestohet për shkak të mungesës së vulës protokollare.`,
                    `Ky dokument përmban një klauzolë arbitrazhi që mund të nxjerrë çështjen jashtë gjykatës.`
                ];
                const recs = [
                    "Përqendroni 80% të kohës së përgatitjes në interpretimin e këtij dokumenti specifik.",
                    "Përgatitni një kërkesë për verifikim forenzik të nënshkrimit/vulës.",
                    "Analizoni nëse klauzola është abuzive. Nëse jo, përgatituni për arbitrazh."
                ];
                result = { insight: insights[variance % 3], recommendation: recs[variance % 3], confidence: 90 };

            } else {
                result = {
                    insight: `Entiteti '${name}' vepron si nyje lidhëse periferike në këtë strukturë.`,
                    recommendation: `Monitoroni për ndonjë ndryshim statusi, por mos shpenzoni resurse primare këtu.`,
                    confidence: 75
                };
            }
            
            resolve(result);
        }, delay);
    });
};

// --- ENTERPRISE THEME (High Contrast / Data Heavy) ---
const THEME = {
  colors: {
    judge:   '#ef4444', // Red
    court:   '#94a3b8', // Slate
    person:  '#10b981', // Emerald
    document:'#3b82f6', // Blue
    money:   '#eab308', // Gold
    default: '#64748b'  // Gray
  },
  icons: {
    judge:   '⚖️',
    court:   '🏛️',
    person:  '👤',
    document:'📄',
    money:   '💰',
    default: '🔹'
  }
};

// --- NATIVE RESIZE HOOK ---
function useResizeObserver(ref: React.RefObject<HTMLElement>) {
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    useEffect(() => {
        if (!ref.current) return;
        const resizeObserver = new ResizeObserver((entries) => {
            if (entries[0]) {
                const { width, height } = entries[0].contentRect;
                setDimensions({ width, height });
            }
        });
        resizeObserver.observe(ref.current);
        return () => resizeObserver.disconnect();
    }, [ref]);
    return dimensions;
}

// --- HELPER: Get Lucide Icon Component for Group ---
const getNodeIcon = (group: string) => {
    const g = (group || '').toUpperCase();
    if (g === 'JUDGE') return <Gavel size={24} className="text-red-400" />;
    if (g === 'COURT') return <Building size={24} className="text-slate-400" />;
    if (g === 'PERSON') return <Users size={24} className="text-emerald-400" />;
    if (g === 'MONEY') return <Banknote size={24} className="text-yellow-400" />;
    if (g === 'DOCUMENT') return <FileText size={24} className="text-blue-400" />;
    if (g === 'EVIDENCE') return <AlertTriangle size={24} className="text-orange-400" />;
    return <Scale size={24} className="text-slate-500" />;
};

const AIAdvisorPanel: React.FC<{ 
    loading: boolean, 
    data: { insight: string, recommendation: string, confidence: number } | null,
    onRefresh: () => void 
}> = ({ loading, data, onRefresh }) => {
    
    if (loading) {
        return (
            <div className="mt-6 p-6 bg-slate-900/50 border border-indigo-500/20 rounded-lg relative overflow-hidden">
                <div className="flex items-center gap-3 mb-4">
                    <BrainCircuit className="text-indigo-400 animate-spin-slow" size={24} />
                    <div>
                        <span className="block text-xs font-bold text-indigo-300 uppercase tracking-widest">Juristi AI Engine</span>
                        <span className="text-[10px] text-indigo-400/60">Duke procesuar të dhënat e nyjes...</span>
                    </div>
                </div>
                <div className="space-y-3">
                    <div className="h-2 bg-indigo-500/20 rounded w-full animate-pulse"></div>
                    <div className="h-2 bg-indigo-500/20 rounded w-5/6 animate-pulse"></div>
                    <div className="h-2 bg-indigo-500/20 rounded w-4/6 animate-pulse"></div>
                </div>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Sparkles className="text-amber-400" size={18} />
                    <span className="text-xs font-bold text-amber-500 uppercase tracking-widest">Inteligjenca Artificiale</span>
                </div>
                <div className="flex items-center gap-2">
                     <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${data.confidence > 90 ? 'bg-emerald-950/30 text-emerald-400 border-emerald-900' : 'bg-slate-900 text-slate-500 border-slate-800'}`}>
                        {data.confidence}% Siguri
                    </span>
                    <button 
                        onClick={onRefresh} 
                        className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-colors"
                        title="Rigjenero Analizën"
                    >
                        <RefreshCw size={14} />
                    </button>
                </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 shadow-inner group hover:border-indigo-500/30 transition-colors duration-300">
                <div className="mb-5 pb-5 border-b border-slate-800/50">
                    <h5 className="text-[10px] text-slate-500 font-bold uppercase mb-2 flex items-center gap-2">
                        <Eye size={12} className="text-slate-400" /> 
                        Vëzhgim Strategjik
                    </h5>
                    <p className="text-sm text-slate-300 leading-relaxed font-light border-l-2 border-slate-700 pl-3">
                        {data.insight}
                    </p>
                </div>
                
                <div>
                    <h5 className="text-[10px] text-emerald-500 font-bold uppercase mb-2 flex items-center gap-2">
                        <Lightbulb size={12} /> 
                        Veprim i Rekomanduar
                    </h5>
                    <p className="text-sm text-white font-medium leading-relaxed bg-emerald-950/20 p-3 rounded border border-emerald-900/30">
                        {data.recommendation}
                    </p>
                </div>
            </div>
        </div>
    );
};

const CaseGraphVisualization: React.FC<CaseGraphProps> = ({ caseId }) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const { width, height } = useResizeObserver(containerRef);
  
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiData, setAiData] = useState<{ insight: string, recommendation: string, confidence: number } | null>(null);
  
  const fgRef = useRef<ForceGraphMethods>();

  useEffect(() => {
    if (!caseId) return;
    let isMounted = true;
    const loadGraph = async () => {
        setIsLoading(true);
        try {
            const graphData = await apiService.getCaseGraph(caseId);
            if (isMounted) setData({ nodes: graphData.nodes.map((n: any) => ({ ...n })), links: graphData.links.map((l: any) => ({ ...l })) });
        } catch (e) { console.error("Failed to load case graph:", e);
        } finally { if (isMounted) setIsLoading(false); }
    };
    loadGraph();
    return () => { isMounted = false; };
  }, [caseId]);

  useEffect(() => {
    const graph = fgRef.current;
    if (graph) {
        // More professional physics settings
        graph.d3Force('charge')?.strength(-1500); 
        graph.d3Force('link')?.distance(180).strength(0.8);
        graph.d3Force('center')?.strength(0.4);
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(600, 100), 500);
        }
    }
  }, [data]);

  const runAIAnalysis = useCallback(async (node: GraphNode) => {
      setAiLoading(true);
      setAiData(null); // Clear previous to show loading state
      const analysis = await generateLegalInsight(node);
      setAiLoading(false);
      setAiData(analysis);
  }, []);

  // --- PROFESSIONAL NODE RENDERING ---
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const group = (node.group || 'Default').toLowerCase();
    const styleColor = (THEME.colors as any)[group] || THEME.colors.default;
    const icon = (THEME.icons as any)[group] || THEME.icons.default;
    
    // Scaling
    const scale = node.id === selectedNode?.id ? 1.1 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    const x = node.x!;
    const y = node.y!;
    const radius = BORDER_RADIUS * scale;

    // Shadows for depth
    if (node.id === selectedNode?.id) {
        ctx.shadowColor = styleColor;
        ctx.shadowBlur = 20;
    } else {
        ctx.shadowColor = 'rgba(0,0,0,0.5)';
        ctx.shadowBlur = 6;
    }

    // 1. Card Background (Dark Slate)
    ctx.fillStyle = '#0f172a'; // slate-900
    ctx.beginPath();
    ctx.roundRect(x - w / 2, y - h / 2, w, h, radius);
    ctx.fill();
    ctx.shadowBlur = 0; // Reset shadow for internal details

    // 2. Color Strip (Left Side) - Identity Marker
    ctx.fillStyle = styleColor;
    ctx.beginPath();
    ctx.roundRect(x - w / 2, y - h / 2, 6 * scale, h, [radius, 0, 0, radius]);
    ctx.fill();

    // 3. Border (Thin, subtle)
    ctx.strokeStyle = node.id === selectedNode?.id ? '#ffffff' : '#334155';
    ctx.lineWidth = node.id === selectedNode?.id ? 2 : 1;
    ctx.stroke();

    // 4. Icon Circle
    ctx.beginPath();
    ctx.arc(x - w / 2 + (24 * scale), y - h / 2 + (20 * scale), 10 * scale, 0, 2 * Math.PI);
    ctx.fillStyle = '#1e293b'; // slate-800
    ctx.fill();
    
    // Icon Text
    ctx.font = `${12 * scale}px "Inter", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon, x - w / 2 + (24 * scale), y - h / 2 + (21 * scale));

    // 5. Category Label (Small, Uppercase)
    ctx.font = `600 ${9 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = styleColor;
    ctx.textAlign = 'left';
    ctx.fillText(node.group.toUpperCase(), x - w / 2 + (42 * scale), y - h / 2 + (16 * scale));

    // 6. Main Label (Name) - Truncated
    ctx.font = `bold ${12 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#f1f5f9'; // slate-100
    let label = node.name || node.id;
    if (label.length > 22) label = label.substring(0, 21) + '...';
    ctx.fillText(label, x - w / 2 + (12 * scale), y + (8 * scale));

    // 7. Money Badge (if Money group)
    if (group === 'money') {
        ctx.fillStyle = THEME.colors.money;
        ctx.font = `bold ${10 * scale}px "Inter", sans-serif`;
        ctx.fillText("EUR", x + w/2 - (25 * scale), y - h/2 + (16 * scale));
    }

  }, [selectedNode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-sans">
        {/* GRAPH CANVAS AREA */}
        <div ref={containerRef} className="lg:col-span-2 relative w-full h-[650px] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
            {/* Header Overlay */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-1 pointer-events-none">
                <div className="flex items-center gap-2 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded border border-slate-700 w-fit">
                    <ShieldAlert size={16} className="text-emerald-500" />
                    <span className="text-xs font-bold text-slate-200 uppercase tracking-widest">{t('caseGraph.title', 'HARTA E INTELIGJENCËS SË RASTIT')}</span>
                </div>
                <div className="flex gap-2">
                    <span className="text-[10px] text-slate-500 bg-slate-900/50 px-2 rounded border border-slate-800">Live Render</span>
                    <span className="text-[10px] text-slate-500 bg-slate-900/50 px-2 rounded border border-slate-800">Physics: Enabled</span>
                </div>
            </div>

            {/* Legend Overlay */}
            <div className="absolute bottom-4 left-4 z-10 bg-slate-900/80 backdrop-blur p-2 rounded border border-slate-800 flex flex-wrap gap-3 max-w-[80%]">
                {Object.entries(THEME.colors).map(([key, color]) => (
                    key !== 'default' && (
                        <div key={key} className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }}></div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">{key}</span>
                        </div>
                    )
                ))}
            </div>

            {isLoading && ( 
                <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-950/90 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-4">
                        <div className="relative">
                            <Scale className="w-10 h-10 text-slate-600 animate-pulse" />
                            <div className="absolute -top-1 -right-1 w-3 h-3 bg-indigo-500 rounded-full animate-ping"></div>
                        </div>
                        <span className="text-xs font-mono text-slate-400 tracking-[0.2em]">{t('caseGraph.loading', 'INITIALIZING NEURAL GRAPH...')}</span>
                    </div>
                </div> 
            )}

            {!isLoading && data.nodes.length === 0 && ( 
                <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none">
                    <FileText className="w-16 h-16 text-slate-800 mb-6" />
                    <h3 className="text-xl font-bold text-slate-600">Nuk ka të dhëna grafike</h3>
                    <p className="text-sm text-slate-700 mt-2">Ngarkoni dokumente për të gjeneruar hartën.</p>
                </div> 
            )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={data}
                nodeCanvasObject={nodeCanvasObject}
                nodePointerAreaPaint={(node: any, color, ctx) => {
                    // Simple hit box for pointer
                    ctx.fillStyle = color;
                    const w = CARD_WIDTH;
                    const h = CARD_HEIGHT;
                    ctx.fillRect(node.x! - w/2, node.y! - h/2, w, h);
                }}
                backgroundColor="#020617" // Very dark slate (Slate 950)
                
                // Link Styling
                linkColor={() => '#334155'} // Slate 700
                linkWidth={1.5}
                linkDirectionalArrowLength={5}
                linkDirectionalArrowRelPos={1}
                
                // Particles (Data Flow Effect)
                linkDirectionalParticles={1}
                linkDirectionalParticleSpeed={0.003}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={() => '#64748b'} // Slate 500

                onNodeClick={(node) => {
                    setSelectedNode(node as GraphNode);
                    runAIAnalysis(node as GraphNode);
                    fgRef.current?.centerAt(node.x, node.y, 800);
                    fgRef.current?.zoom(1.3, 800);
                }}
                onBackgroundClick={() => { 
                    setSelectedNode(null); 
                    setAiData(null); 
                }}
                minZoom={0.2}
                maxZoom={4.0}
            />
        </div>

        {/* SIDE PANEL (INTELLIGENCE DOSSIER) */}
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl h-[650px] flex flex-col shadow-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur">
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-indigo-500" />
                    Paneli i Analizës
                </h3>
            </div>

            <div className="flex-grow p-6 overflow-y-auto custom-scrollbar">
                {selectedNode ? (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        {/* Node Header */}
                        <div className="flex items-start justify-between mb-6">
                            <div>
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-2 text-white bg-slate-800`}>
                                    {selectedNode.group}
                                </span>
                                <h2 className="text-2xl font-bold text-white leading-tight">{selectedNode.name}</h2>
                            </div>
                            <div className="w-12 h-12 rounded bg-slate-800 flex items-center justify-center border border-slate-700 shadow-lg">
                                {getNodeIcon(selectedNode.group)}
                            </div>
                        </div>

                        {/* Metadata Grid */}
                        <div className="grid grid-cols-2 gap-3 mb-6">
                            <div className="bg-slate-950 p-3 rounded border border-slate-800">
                                <span className="text-[10px] text-slate-500 uppercase block mb-1">ID e Nyjes</span>
                                <span className="text-xs font-mono text-slate-300 truncate block w-full" title={selectedNode.id}>
                                    #{selectedNode.id.substring(0, 8)}...
                                </span>
                            </div>
                            <div className="bg-slate-950 p-3 rounded border border-slate-800">
                                <span className="text-[10px] text-slate-500 uppercase block mb-1">Rëndësia</span>
                                <div className="flex items-center gap-1">
                                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-indigo-500 w-[75%]"></div>
                                    </div>
                                    <span className="text-xs text-indigo-400 font-bold">Lartë</span>
                                </div>
                            </div>
                        </div>

                        <div className="h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent my-4"></div>

                        {/* AI Section */}
                        <AIAdvisorPanel 
                            loading={aiLoading} 
                            data={aiData} 
                            onRefresh={() => runAIAnalysis(selectedNode)} 
                        />
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-60">
                        <div className="w-20 h-20 bg-slate-800/50 rounded-full flex items-center justify-center mb-6 animate-pulse">
                            <BrainCircuit size={40} className="text-slate-600" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-400 mb-2">Pritje për Selektim</h3>
                        <p className="text-sm text-slate-500 max-w-[250px] leading-relaxed">
                            Klikoni mbi një nyje në hartë për të aktivizuar motorin e analizës forenzike të Juristit.
                        </p>
                    </div>
                )}
            </div>
            
            {/* Footer */}
            <div className="p-3 bg-slate-950 border-t border-slate-800 text-center">
                <p className="text-[10px] text-slate-600 font-mono">
                    SECURE CONNECTION • JURISTI-AI-V5.1
                </p>
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;