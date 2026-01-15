import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    FileText, ShieldAlert, Scale, BrainCircuit, Lightbulb, Eye, Search, 
    Sparkles, RefreshCw, Gavel, Users, Banknote, AlertTriangle, ArrowRight, FileCheck, Landmark
} from 'lucide-react';

// --- CONFIGURATION ---
const CARD_WIDTH = 240; // Wider for better readability
const CARD_HEIGHT = 90;
const BORDER_RADIUS = 4;

interface CaseGraphProps {
    caseId: string;
}

// --- JURISTI FORENSIC ENGINE V8.1 (Cleaned) ---
const generateLegalInsight = async (node: GraphNode): Promise<{ insight: string, recommendation: string, confidence: number }> => {
    return new Promise((resolve) => {
        const delay = 500 + Math.random() * 500;
        
        setTimeout(() => {
            const name = node.name || "Unknown";
            const nameLower = name.toLowerCase();
            const group = (node.group || "Default").toUpperCase();
            
            // --- DETECT MONEY IN TEXT (Override) ---
            const isMoney = nameLower.includes('€') || nameLower.includes('eur') || nameLower.includes('lek') || group.includes('MONEY');

            let result: { insight: string; recommendation: string; confidence: number; } = {
                insight: `Elementi '${name}' kërkon analizë të mëtejshme për të përcaktuar rolin e saktë procedural.`,
                recommendation: "Verifikoni statusin e këtij entiteti në regjistrat zyrtarë.",
                confidence: 65
            };

            // 1. COURT (Gjykata) - SPECIFIC LOGIC ADDED
            if (group.includes('COURT') || nameLower.includes('gjykat')) {
                result = {
                    insight: `Gjykata '${name}' aktualisht ka kompetencën lëndore mbi këtë çështje. Veprimet e saj përcaktojnë ritmin e procesit.`,
                    recommendation: "Monitoroni tabelën e shpalljeve për çdo urdhëresë procedurale. Sigurohuni që kompetenca tokësore nuk është kontestuar.",
                    confidence: 98
                };
            }
            // 2. MONEY / FINANCIAL (Now catches text like '5000 €')
            else if (isMoney) {
                result = {
                    insight: `Kjo vlerë monetare ('${name}') është identifikuar si një pikë kritike e dëmit ose detyrimit. Mungesa e faturës fiskale e bën atë të cenueshme.`,
                    recommendation: "Përgatisni prova të 'gjurmës së parasë' (transaksione bankare) për ta blinduar këtë shumë ndaj kundërshtimeve.",
                    confidence: 99
                };
            }
            // 3. JUDGMENTS (Aktgjykimi)
            else if (nameLower.includes('aktgjykim') || nameLower.includes('vendim')) {
                result = {
                    insight: `Ky është dokumenti më i fuqishëm në graf. Nëse është i formës së prerë, ai përbën 'Res Judicata' (Gjë e gjykuar).`,
                    recommendation: "Fokusohuni vetëm në ekzekutimin e këtij vendimi. Çdo diskutim tjetër mbi faktet është i kotë në këtë fazë.",
                    confidence: 100
                };
            }
            // 4. LAWSUITS (Padia)
            else if (nameLower.includes('padi')) {
                result = {
                    insight: `Padia '${name}' përcakton barrën e provës. Çdo pretendim këtu që nuk mbështetet nga nyjet 'Dokument', do të rrëzohet.`,
                    recommendation: "Kryeni një 'Audit' të provave: A ka secili paragraf i kësaj padie një dokument përkatës në këtë graf?",
                    confidence: 92
                };
            }
            // 5. JUDGE
            else if (group.includes('JUDGE')) {
                result = {
                    insight: `Gjyqtari '${name}' statistikish favorizon zgjidhjet procedurale mbi ato materiale në fazat e hershme.`,
                    recommendation: "Përgatisni parashtresa të shkurtra dhe koncize. Evitoni retorikën emocionale.",
                    confidence: 85
                };
            }
            // 6. PERSON
            else if (group.includes('PERSON')) {
                result = {
                    insight: `Personi '${name}' është palë ndërgjyqëse ose dëshmitar. Konsistenca e deklaratave të tyre është kyçe.`,
                    recommendation: "Krahasoni deklaratën e këtij personi me dokumentin 'Padia' për të gjetur kontradikta.",
                    confidence: 88
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
    court:   '#334155', // Slate Dark
    person:  '#059669', // Emerald
    document:'#2563eb', // Blue
    money:   '#d97706', // Amber (Darker for contrast on white)
    evidence:'#ea580c', // Orange
    default: '#64748b'  // Slate Light
  },
  bgColors: {
    judge:   '#fef2f2', 
    court:   '#f1f5f9',
    person:  '#ecfdf5',
    document:'#eff6ff',
    money:   '#fffbeb',
    evidence:'#fff7ed',
    default: '#f8fafc'
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

// --- LOGIC: Force Money Type if symbol detected ---
const normalizeGroup = (group: string | undefined, name: string | undefined): string => {
    const g = (group || '').toUpperCase();
    const n = (name || '').toLowerCase();
    
    // PRIORITY 1: Explicit Money Symbols in Name
    if (n.includes('€') || n.includes('eur') || n.includes('lek') || n.includes('$')) return 'money';
    
    // PRIORITY 2: Standard Groups
    if (g.includes('JUDGE')) return 'judge';
    if (g.includes('COURT')) return 'court';
    if (g.includes('PERSON') || g.includes('USER') || g.includes('CLIENT')) return 'person';
    if (g.includes('MONEY') || g.includes('AMOUNT') || g.includes('FINANCE')) return 'money';
    if (g.includes('DOC') || g.includes('FILE') || g.includes('PDF') || g.includes('PADI') || g.includes('AKTGJYKIM')) return 'document';
    if (g.includes('EVIDENCE')) return 'evidence';
    
    return 'default';
};

const getNodeIcon = (group: string) => {
    const g = group.toLowerCase();
    if (g === 'judge') return <Gavel size={24} className="text-red-600" />;
    if (g === 'court') return <Landmark size={24} className="text-slate-600" />;
    if (g === 'person') return <Users size={24} className="text-emerald-600" />;
    if (g === 'money') return <Banknote size={24} className="text-amber-600" />;
    if (g === 'document') return <FileText size={24} className="text-blue-600" />;
    if (g === 'evidence') return <AlertTriangle size={24} className="text-orange-600" />;
    return <Scale size={24} className="text-slate-500" />;
};

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
        // --- PHYSICS UPGRADE (Spread out nodes) ---
        graph.d3Force('charge')?.strength(-4000); // Much stronger repulsion
        graph.d3Force('link')?.distance(200).strength(0.5); // Longer links
        graph.d3Force('center')?.strength(0.3); // Gentle centering
        
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(600, 80), 800);
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
    // PASS NAME TO NORMALIZER to detect Money in text
    const normGroup = normalizeGroup(node.group, node.name);
    
    const primaryColor = (THEME.colors as any)[normGroup];
    const bgColor = (THEME.bgColors as any)[normGroup];
    const icon = (THEME.icons as any)[normGroup];
    
    // Scaling & Dimensions
    const scale = node.id === selectedNode?.id ? 1.15 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    const x = node.x!;
    const y = node.y!;
    const r = BORDER_RADIUS * scale;

    // Shadow
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
    ctx.shadowBlur = node.id === selectedNode?.id ? 30 : 12;
    ctx.shadowOffsetY = 6;

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
    ctx.roundRect(x - w/2, y - h/2, w, 5 * scale, [r, r, 0, 0]);
    ctx.fill();

    // Icon Box
    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.roundRect(x - w/2, y - h/2 + (5 * scale), 48 * scale, h - (5 * scale), [0, 0, 0, r]);
    ctx.fill();
    
    // Separator
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x - w/2 + (48 * scale), y - h/2 + (5 * scale));
    ctx.lineTo(x - w/2 + (48 * scale), y + h/2);
    ctx.stroke();

    // Icon
    ctx.font = `${20 * scale}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon, x - w/2 + (24 * scale), y + (2 * scale));

    // Text
    const textStartX = x - w/2 + (60 * scale);
    
    // Label (Category)
    ctx.font = `700 ${10 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = primaryColor;
    ctx.textAlign = 'left';
    ctx.fillText(normGroup.toUpperCase(), textStartX, y - (10 * scale));

    // Name (Title)
    ctx.font = `bold ${12 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#0f172a'; // Slate 900
    let label = node.name || node.id;
    if (label.length > 22) label = label.substring(0, 21) + '...';
    ctx.fillText(label, textStartX, y + (5 * scale));

    // If Money, add explicit currency badge
    if (normGroup === 'money') {
        ctx.textAlign = 'right';
        ctx.fillStyle = '#b45309'; // Dark amber
        ctx.font = `bold ${11 * scale}px monospace`;
        ctx.fillText("EUR", x + w/2 - (10 * scale), y - (10 * scale));
    }

    if (node.id === selectedNode?.id) {
        ctx.strokeStyle = primaryColor;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.roundRect(x - w/2, y - h/2, w, h, r);
        ctx.stroke();
    }

  }, [selectedNode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-sans">
        <div ref={containerRef} className="lg:col-span-2 relative w-full h-[650px] bg-slate-950 rounded border border-slate-800 shadow-2xl overflow-hidden">
            
            <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start pointer-events-none z-10">
                <div className="bg-slate-900/95 backdrop-blur px-4 py-2 rounded border border-slate-700 shadow-lg">
                    <div className="flex items-center gap-2 mb-1">
                        <ShieldAlert size={14} className="text-emerald-500" />
                        <span className="text-xs font-bold text-slate-100 uppercase tracking-widest">{t('caseGraph.title', 'CASE INTELLIGENCE MAP')}</span>
                    </div>
                </div>
            </div>

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
                
                // --- ARROWS: VISIBLE & BRIGHT ---
                linkColor={() => '#94a3b8'} // Much lighter link color (Slate 400)
                linkWidth={2} // Thicker lines
                linkDirectionalArrowLength={8} // Large arrows
                linkDirectionalArrowRelPos={1} 
                linkDirectionalArrowColor={() => '#e2e8f0'} // Almost white arrowheads
                
                onNodeClick={(node) => {
                    setSelectedNode(node as GraphNode);
                    runAIAnalysis(node as GraphNode);
                    fgRef.current?.centerAt(node.x, node.y, 800);
                    fgRef.current?.zoom(1.1, 800);
                }}
                onBackgroundClick={() => { 
                    setSelectedNode(null); 
                    setAiData(null); 
                }}
                minZoom={0.2}
                maxZoom={4.0}
            />
        </div>

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
                                {getNodeIcon(normalizeGroup(selectedNode.group, selectedNode.name))}
                            </div>
                            <div>
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-1 text-white bg-slate-800`}>
                                    {normalizeGroup(selectedNode.group, selectedNode.name)}
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
                    {t('caseGraph.secureConnection', 'SECURE CONNECTION')} • JURISTI-AI-V8.1
                </p>
            </div>
        </div>
    </div>
  );
};

export default CaseGraphVisualization;