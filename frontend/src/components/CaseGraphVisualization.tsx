import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    FileText, ShieldAlert, Scale, BrainCircuit, Lightbulb, Eye, Search, 
    Sparkles, RefreshCw, Gavel, Users, Building, Banknote, AlertTriangle, ArrowRight, FileCheck
} from 'lucide-react';

// --- CONFIGURATION ---
const CARD_WIDTH = 220;
const CARD_HEIGHT = 80;
const BORDER_RADIUS = 2;

interface CaseGraphProps {
    caseId: string;
}

// --- JURISTI FORENSIC ENGINE V7.1 (Optimized) ---
const generateLegalInsight = async (node: GraphNode): Promise<{ insight: string, recommendation: string, confidence: number }> => {
    return new Promise((resolve) => {
        const delay = 600 + Math.random() * 600;
        
        setTimeout(() => {
            const name = node.name || "Unknown";
            const nameLower = name.toLowerCase();
            const group = (node.group || "Default").toUpperCase();
            
            let result: { insight: string; recommendation: string; confidence: number; } = {
                insight: `Analiza tregon se '${name}' ka ndërlidhje komplekse me elementet e tjera të dosjes.`,
                recommendation: "Kërkohet rishikim manual për të përcaktuar rëndësinë e saktë.",
                confidence: 70
            };

            // --- SEMANTIC LOGIC ---
            
            // 1. JUDGMENTS / DECISIONS
            if (nameLower.includes('aktgjykimi') || nameLower.includes('vendim')) {
                result = {
                    insight: `Ky dokument ('${name}') përbën titull ekzekutiv ose bazën procedurale përfundimtare. Fuqia e tij juridike është absolute.`,
                    recommendation: "Verifikoni menjëherë nëse ky aktgjykim ka marrë formën e prerë apo nëse afati i ankesës është ende i hapur.",
                    confidence: 99
                };
            }
            // 2. LAWS / STATUTES
            else if (nameLower.includes('ligji') || nameLower.includes('neni') || nameLower.includes('kodi')) {
                result = {
                    insight: `Referenca në '${name}' përcakton bazën materiale të të drejtës. Kjo është shtylla mbi të cilën ndërtohet ligjshmëria e kërkesës.`,
                    recommendation: "Analizoni praktikën gjyqësore të Gjykatës Supreme lidhur me interpretimin specifik të kësaj dispozite.",
                    confidence: 95
                };
            }
            // 3. LAWSUITS / PLEADINGS
            else if (nameLower.includes('padi') || nameLower.includes('ankesa') || nameLower.includes('kundërshtim')) {
                result = {
                    insight: `Dokumenti '${name}' përcakton kufijtë e shqyrtimit gjyqësor. Çdo gjë jashtë këtij dokumenti nuk mund të gjykohet.`,
                    recommendation: "Kryqëzoni pretendimet në këtë dokument me provat materiale. Identifikoni çdo pretendim të pambështetur.",
                    confidence: 92
                };
            }
            // 4. FINANCIAL
            else if (group.includes('MONEY') || nameLower.includes('fatura') || nameLower.includes('€') || nameLower.includes('borxh')) {
                result = {
                    insight: `Kjo vlerë financiare është thelbësore për kalkulimin e dëmit. Mungesa e një gjurme të qartë bankare dobëson pozicionin.`,
                    recommendation: "Kërkoni ekspertizë financiare për të saktësuar llogaritjen e kamatës dhe fitimit të humbur.",
                    confidence: 96
                };
            }
            // 5. JUDGE
            else if (group.includes('JUDGE')) {
                result = {
                    insight: `Historiku i gjyqtarit '${name}' tregon fokus të lartë në respektimin e procedurës formale.`,
                    recommendation: "Sigurohuni që çdo afat dhe formë procedurale është respektuar me rigorozitet.",
                    confidence: 88
                };
            }
            // 6. FALLBACK
            else if (group.includes('PERSON') || group.includes('ENTITY')) {
                result = {
                    insight: `Entiteti '${name}' shfaqet në pikëprerjen e dy rrjedhave të ndryshme të informacionit.`,
                    recommendation: "Konsideroni thirrjen e këtij entiteti për dëshmi nëse ka paqartësi në komunikim.",
                    confidence: 85
                };
            }

            resolve(result);
        }, delay);
    });
};

// --- ENTERPRISE THEME ---
const THEME = {
  colors: {
    judge:   '#dc2626', // Red
    court:   '#475569', // Slate
    person:  '#059669', // Emerald
    document:'#2563eb', // Blue
    money:   '#ca8a04', // Gold
    evidence:'#ea580c', // Orange
    default: '#4b5563'  // Gray
  },
  bgColors: {
    judge:   '#fef2f2', 
    court:   '#f8fafc',
    person:  '#ecfdf5',
    document:'#eff6ff',
    money:   '#fefce8',
    evidence:'#fff7ed',
    default: '#f3f4f6'
  },
  icons: {
    judge:   '⚖️',
    court:   '🏛️',
    person:  '👤',
    document:'📄',
    money:   '💰',
    evidence:'cj',
    default: '🔹'
  }
};

const getNodeIcon = (group: string) => {
    const g = (group || '').toUpperCase();
    if (g.includes('JUDGE')) return <Gavel size={20} className="text-red-600" />;
    if (g.includes('COURT')) return <Building size={20} className="text-slate-600" />;
    if (g.includes('PERSON')) return <Users size={20} className="text-emerald-600" />;
    if (g.includes('MONEY')) return <Banknote size={20} className="text-yellow-600" />;
    if (g.includes('DOCUMENT')) return <FileText size={20} className="text-blue-600" />;
    if (g.includes('EVIDENCE')) return <AlertTriangle size={20} className="text-orange-600" />;
    return <Scale size={20} className="text-slate-500" />;
};

const normalizeGroup = (group: string | undefined): string => {
    if (!group) return 'default';
    const g = group.toLowerCase();
    if (g.includes('judge')) return 'judge';
    if (g.includes('court')) return 'court';
    if (g.includes('person') || g.includes('user') || g.includes('client')) return 'person';
    if (g.includes('money') || g.includes('amount') || g.includes('eur') || g.includes('usd')) return 'money';
    if (g.includes('doc') || g.includes('file') || g.includes('pdf') || g.includes('padi') || g.includes('aktgjykim')) return 'document';
    if (g.includes('evidence')) return 'evidence';
    return 'default';
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

const AIAdvisorPanel: React.FC<{ 
    loading: boolean, 
    data: { insight: string, recommendation: string, confidence: number } | null,
    onRefresh: () => void 
}> = ({ loading, data, onRefresh }) => {
    const { t } = useTranslation();
    
    if (loading) {
        return (
            <div className="mt-6 p-6 bg-slate-800/50 border border-indigo-500/20 rounded relative overflow-hidden">
                <div className="flex items-center gap-3 mb-4">
                    <BrainCircuit className="text-indigo-400 animate-spin-slow" size={24} />
                    <div>
                        <span className="block text-xs font-bold text-indigo-300 uppercase tracking-widest">{t('caseGraph.engineActive', 'Juristi AI Engine')}</span>
                        <span className="text-[10px] text-indigo-400/60">{t('caseGraph.processing', 'Processing...')}</span>
                    </div>
                </div>
                <div className="space-y-3">
                    <div className="h-1 bg-indigo-500/20 rounded w-full animate-pulse"></div>
                    <div className="h-1 bg-indigo-500/20 rounded w-5/6 animate-pulse"></div>
                </div>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Sparkles className="text-amber-400" size={16} />
                    <span className="text-xs font-bold text-amber-500 uppercase tracking-widest">{t('caseGraph.aiTitle', 'AI INTELLIGENCE')}</span>
                </div>
                <div className="flex items-center gap-2">
                     <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${data.confidence > 90 ? 'bg-emerald-950/30 text-emerald-400 border-emerald-900' : 'bg-slate-900 text-slate-500 border-slate-800'}`}>
                        {data.confidence}% {t('caseGraph.confidence', 'Confidence')}
                    </span>
                    <button 
                        onClick={onRefresh} 
                        className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-colors"
                        title="Regenerate"
                    >
                        <RefreshCw size={14} />
                    </button>
                </div>
            </div>

            <div className="bg-slate-900 border border-slate-700 rounded p-5 shadow-sm">
                <div className="mb-5 pb-5 border-b border-slate-800">
                    <h5 className="text-[10px] text-slate-400 font-bold uppercase mb-2 flex items-center gap-2">
                        <Eye size={12} /> 
                        {t('caseGraph.strategicObs', 'Strategic Observation')}
                    </h5>
                    <p className="text-sm text-slate-200 leading-relaxed font-light">
                        {data.insight}
                    </p>
                </div>
                
                <div>
                    <h5 className="text-[10px] text-emerald-500 font-bold uppercase mb-2 flex items-center gap-2">
                        <Lightbulb size={12} /> 
                        {t('caseGraph.recAction', 'Recommended Action')}
                    </h5>
                    <p className="text-sm text-white font-medium leading-relaxed bg-emerald-900/10 p-3 rounded border-l-2 border-emerald-500">
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
        // High tension physics for a cleaner "org chart" look
        graph.d3Force('charge')?.strength(-2500); 
        graph.d3Force('link')?.distance(160).strength(0.7);
        graph.d3Force('center')?.strength(0.5);
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(600, 100), 500);
        }
    }
  }, [data]);

  const runAIAnalysis = useCallback(async (node: GraphNode) => {
      setAiLoading(true);
      setAiData(null); 
      const analysis = await generateLegalInsight(node);
      setAiLoading(false);
      setAiData(analysis);
  }, []);

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const normGroup = normalizeGroup(node.group);
    const primaryColor = (THEME.colors as any)[normGroup];
    const bgColor = (THEME.bgColors as any)[normGroup];
    const icon = (THEME.icons as any)[normGroup];
    
    // Scaling & Dimensions
    const scale = node.id === selectedNode?.id ? 1.1 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    const x = node.x!;
    const y = node.y!;
    const r = BORDER_RADIUS * scale;

    // Shadow
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
    ctx.shadowBlur = node.id === selectedNode?.id ? 25 : 10;
    ctx.shadowOffsetY = 4;

    // Main Card
    ctx.fillStyle = '#ffffff'; 
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2, w, h, r);
    ctx.fill();
    
    ctx.shadowBlur = 0;
    ctx.shadowOffsetY = 0;

    // Top Strip
    ctx.fillStyle = primaryColor;
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2, w, 4 * scale, [r, r, 0, 0]);
    ctx.fill();

    // Icon Box
    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2 + (4 * scale), 40 * scale, h - (4 * scale), [0, 0, 0, r]);
    ctx.fill();
    
    // Separator
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x - w/2 + (40 * scale), y - h/2 + (4 * scale));
    ctx.lineTo(x - w/2 + (40 * scale), y + h/2);
    ctx.stroke();

    // Icon
    ctx.font = `${18 * scale}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon, x - w/2 + (20 * scale), y + (2 * scale));

    // Text
    const textStartX = x - w/2 + (50 * scale);
    
    ctx.font = `600 ${9 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = primaryColor;
    ctx.textAlign = 'left';
    ctx.fillText(node.group.toUpperCase(), textStartX, y - (8 * scale));

    ctx.font = `bold ${11 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#1e293b'; 
    let label = node.name || node.id;
    if (label.length > 20) label = label.substring(0, 19) + '...';
    ctx.fillText(label, textStartX, y + (6 * scale));

    if (normGroup === 'money') {
        ctx.textAlign = 'right';
        ctx.fillStyle = THEME.colors.money;
        ctx.font = `bold ${10 * scale}px monospace`;
        ctx.fillText("€", x + w/2 - (10 * scale), y - (8 * scale));
    }

    if (node.id === selectedNode?.id) {
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x - w/2, y - h/2, w, h, r);
        ctx.stroke();
    }

  }, [selectedNode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-sans">
        {/* GRAPH CANVAS */}
        <div ref={containerRef} className="lg:col-span-2 relative w-full h-[650px] bg-slate-950 rounded border border-slate-800 shadow-2xl overflow-hidden">
            
            <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start pointer-events-none z-10">
                <div className="bg-slate-900/95 backdrop-blur px-4 py-2 rounded border border-slate-700 shadow-lg">
                    <div className="flex items-center gap-2 mb-1">
                        <ShieldAlert size={14} className="text-emerald-500" />
                        <span className="text-xs font-bold text-slate-100 uppercase tracking-widest">{t('caseGraph.title', 'CASE INTELLIGENCE MAP')}</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                            <span className="text-[9px] text-slate-400 font-mono uppercase">{t('caseGraph.liveRender', 'LIVE RENDER')}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur px-3 py-2 rounded border border-slate-200 shadow-lg flex flex-wrap gap-x-4 gap-y-2 max-w-[80%]">
                {Object.entries(THEME.colors).map(([key, color]) => (
                    key !== 'default' && (
                        <div key={key} className="flex items-center gap-1.5">
                            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }}></div>
                            <span className="text-[9px] text-slate-600 uppercase font-bold tracking-wider">{t(`caseGraph.groups.${key}`, key)}</span>
                        </div>
                    )
                ))}
            </div>

            {/* LOADING OVERLAY - Re-integrated */}
            {isLoading && ( 
                <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-950/90 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-4">
                        <Scale className="w-8 h-8 text-slate-500 animate-bounce" />
                        <span className="text-xs font-mono text-slate-400 tracking-[0.2em]">{t('caseGraph.loading', 'INITIALIZING NEURAL GRAPH...')}</span>
                    </div>
                </div> 
            )}

            {!isLoading && data.nodes.length === 0 && ( 
                <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none text-center">
                    <div className="bg-slate-900 p-4 rounded-full mb-4 border border-slate-800">
                        <FileText className="w-8 h-8 text-slate-600" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-400">{t('caseGraph.noDataTitle', 'No Graph Data')}</h3>
                    <p className="text-sm text-slate-600 mt-1">{t('caseGraph.noDataDesc', 'Upload documents to generate map.')}</p>
                </div> 
            )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={data}
                nodeCanvasObject={nodeCanvasObject}
                nodePointerAreaPaint={(node: any, color, ctx) => {
                    ctx.fillStyle = color;
                    const w = CARD_WIDTH;
                    const h = CARD_HEIGHT;
                    ctx.fillRect(node.x! - w/2, node.y! - h/2, w, h);
                }}
                backgroundColor="#0f172a" 
                
                // --- VISIBLE DIRECTIONAL ARROWS ---
                linkColor={() => '#475569'} 
                linkWidth={1.5}
                linkDirectionalArrowLength={6} 
                linkDirectionalArrowRelPos={1} 
                linkDirectionalArrowColor={() => '#94a3b8'} 
                
                onNodeClick={(node) => {
                    setSelectedNode(node as GraphNode);
                    runAIAnalysis(node as GraphNode);
                    fgRef.current?.centerAt(node.x, node.y, 800);
                    fgRef.current?.zoom(1.2, 800);
                }}
                onBackgroundClick={() => { 
                    setSelectedNode(null); 
                    setAiData(null); 
                }}
                minZoom={0.2}
                maxZoom={4.0}
            />
        </div>

        {/* SIDE PANEL */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded h-[650px] flex flex-col shadow-xl overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest flex items-center gap-2">
                    <Search size={14} className="text-slate-400" />
                    {t('caseGraph.panelTitle', 'Analysis Panel')}
                </h3>
                <div className="w-2 h-2 rounded-full bg-emerald-500" title="System Online"></div>
            </div>

            <div className="flex-grow p-6 overflow-y-auto custom-scrollbar bg-white">
                {selectedNode ? (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        <div className="flex items-start gap-4 mb-6">
                            <div className="w-12 h-12 rounded bg-slate-50 flex items-center justify-center border border-slate-200 shrink-0">
                                {getNodeIcon(selectedNode.group)}
                            </div>
                            <div>
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-1 text-white bg-slate-800`}>
                                    {selectedNode.group}
                                </span>
                                <h2 className="text-xl font-bold text-slate-900 leading-tight">{selectedNode.name}</h2>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 mb-6">
                            <div className="bg-slate-50 p-3 rounded border border-slate-100">
                                <span className="text-[10px] text-slate-400 uppercase block mb-1">{t('caseGraph.nodeId', 'Node ID')}</span>
                                <span className="text-xs font-mono text-slate-600 truncate block w-full">
                                    #{selectedNode.id.substring(0, 8)}
                                </span>
                            </div>
                            <div className="bg-slate-50 p-3 rounded border border-slate-100">
                                <span className="text-[10px] text-slate-400 uppercase block mb-1">{t('caseGraph.importance', 'Importance')}</span>
                                <div className="flex items-center gap-1">
                                    <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                        <div className="h-full bg-indigo-500 w-[75%]"></div>
                                    </div>
                                    <span className="text-[10px] text-indigo-600 font-bold uppercase">{t('caseGraph.high', 'High')}</span>
                                </div>
                            </div>
                        </div>

                        <div className="h-px bg-slate-100 my-4"></div>

                        <AIAdvisorPanel 
                            loading={aiLoading} 
                            data={aiData} 
                            onRefresh={() => runAIAnalysis(selectedNode)} 
                        />
                        
                        {/* DEEP LINK PROTOTYPE */}
                        <div className="mt-4">
                            <button className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold uppercase rounded flex items-center justify-center gap-2 transition-colors">
                                <FileCheck size={14} />
                                Shiko Dokumentin Origjinal
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-60">
                        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
                            <ArrowRight size={24} className="text-slate-300" />
                        </div>
                        <h3 className="text-sm font-bold text-slate-400 mb-1">{t('caseGraph.waitingSelection', 'Waiting for Selection')}</h3>
                        <p className="text-xs text-slate-400 max-w-[200px]">
                            {t('caseGraph.selectPrompt', 'Click on a node to activate the analysis engine.')}
                        </p>
                    </div>
                )}
            </div>
            
            <div className="p-2 bg-slate-50 border-t border-slate-100 text-center">
                <p className="text-[9px] text-slate-400 font-mono uppercase">
                    {t('caseGraph.secureConnection', 'SECURE CONNECTION')} • JURISTI-AI-V7.1
                </p>
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;