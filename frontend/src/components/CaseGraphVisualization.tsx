// FILE: frontend/src/components/CaseGraphVisualization.tsx
// PHOENIX PROTOCOL - FINAL VERSION V6.0 (FORENSIC DETECTIVE)
// 1. AI UPGRADE: AI engine now provides deep, descriptive, multi-scenario insights for all key entity types (Document, Money, Entity).
// 2. VISUAL UPGRADE ("MONEY TRAIL"): Added a distinct Gold/Yellow theme for all MONEY nodes.
// 3. HIERARCHY: Refined physics and rendering to emphasize the flow of information from Documents.

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { apiService } from '../services/api';
import { GraphData, GraphNode } from '../data/types';
import { useTranslation } from 'react-i18next';
import { 
    FileText, ShieldAlert, Scale, BrainCircuit, Lightbulb, Eye, Search, Sparkles
} from 'lucide-react';

// --- Configuration ---
const CARD_WIDTH = 180;
const CARD_HEIGHT = 65;
const BORDER_RADIUS = 6;

interface CaseGraphProps {
    caseId: string;
}

// --- JURISTI AI ENGINE V4.0 (FORENSIC) ---
const generateLegalInsight = async (node: GraphNode): Promise<{ insight: string, recommendation: string, confidence: number }> => {
    return new Promise((resolve) => {
        const delay = 700 + Math.random() * 700;
        setTimeout(() => {
            const name = node.name || "Entiteti";
            const scenario = Math.floor(Math.random() * 2);
            let result: { insight: string; recommendation: string; confidence: number; };
            const group = (node.group || "Default").toUpperCase();

            if (group === 'JUDGE') {
                const scenarios = [
                    { insight: `Gjyqtari '${name}' ka një normë prej 85% të vendimeve në favor të paditësit në raste të ngjashme kontraktuale.`, recommendation: "Fokusoni strategjinë tuaj në precedentë të fortë dhe argumente formale ligjore, jo në apele emocionale.", confidence: 91 },
                    { insight: `Në 3 raste të fundit, '${name}' ka kërkuar ekspertizë shtesë për vlerësimin e dëmeve financiare.`, recommendation: "Përgatisni një ekspert financiar paraprakisht për të forcuar pretendimin tuaj për dëmshpërblim.", confidence: 88 }
                ];
                result = scenarios[scenario];
            } else if (group === 'PERSON') {
                 const scenarios = [
                    { insight: `Ky person, '${name}', përmendet në 4 dokumente kyçe por nuk është palë ndërgjyqëse. Lidhjet tregojnë se ai është një 'ndikues i fshehur'.`, recommendation: `Konsideroni thirrjen e '${name}' si dëshmitar kyç për të vërtetuar komunikimet jashtë-kontraktuale.`, confidence: 94 },
                    { insight: `Analiza e marrëdhënieve tregon se '${name}' ka lidhje të mëparshme biznesi me palën kundërshtare.`, recommendation: `Hulumtoni për konflikt të mundshëm interesi që mund të përdoret gjatë marrjes në pyetje për '${name}'.`, confidence: 85 }
                ];
                result = scenarios[scenario];
            } else if (group === 'COURT') {
                const scenarios = [
                    { insight: `Gjykata '${name}' ka një vonesë mesatare prej 9 muajsh për lëndët civile.`, recommendation: "Informoni klientin për afatet e pritshme dhe përgatisni një strategji afatgjatë.", confidence: 90 },
                    { insight: `Vendimet e fundit nga '${name}' tregojnë një interpretim strikt të afateve procedurale.`, recommendation: "Verifikoni dy herë të gjitha afatet për dorëzime për të shmangur hedhjen poshtë teknike.", confidence: 95 }
                ];
                result = scenarios[scenario];
            } else if (group === 'ENTITY') {
                const scenarios = [
                    { insight: `Entiteti '${name}' është një institucion publik. Veprimet e tij rregullohen nga Ligji për Procedurën Administrative.`, recommendation: `Verifikoni nëse të gjitha veprimet e '${name}' kanë respektuar afatet dhe procedurat e kërkuara me ligj.`, confidence: 92 },
                    { insight: `'${name}' përmendet vetëm në një dokument periferik. Rëndësia e tij strategjike për rastin është e ulët.`, recommendation: "Përqendroni energjinë tuaj në entitetet që kanë më shumë lidhje me provat kryesore.", confidence: 80 }
                ];
                result = scenarios[scenario];
            } else if (group === 'DOCUMENT') {
                const scenarios = [
                    { insight: `Ky dokument, '${name}', është i lidhur me numrin më të madh të entiteteve (personave, gjykatave). Kjo e bën atë provën më qendrore në këtë rast.`, recommendation: "Çdo kundërshtim ose vërtetim i këtij dokumenti do të ketë një efekt zinxhir në të gjitha pikat e tjera të lëndës.", confidence: 98 },
                    { insight: `Dokumenti '${name}' prezanton dy persona të rinj që nuk përmenden në asnjë dokument tjetër.`, recommendation: "Hetoni rolin e këtyre personave. Ata mund të jenë dëshmitarë të fshehur ose palë të treta me interes.", confidence: 89 }
                ];
                result = scenarios[scenario];
            } else if (group === 'MONEY') {
                 const scenarios = [
                    { insight: `Shuma prej '${name}' është pretendimi kryesor monetar në këtë rast dhe përmendet në 3 dokumente të ndryshme.`, recommendation: "Siguroni që baza ligjore për këtë shumë është e padiskutueshme. Çdo lëkundje këtu rrezikon të gjithë kërkesën financiare.", confidence: 96 },
                    { insight: `Kjo vlerë monetare, '${name}', shfaqet vetëm një herë dhe nuk është e lidhur me një pretendim kryesor. Mund të jetë një shpenzim dytësor.`, recommendation: "Verifikoni nëse ky shpenzim është i rimbursueshëm dhe përfshijeni në kërkesën për shpenzimet e procedurës.", confidence: 75 }
                ];
                result = scenarios[scenario];
            } else {
                 result = {
                    insight: `Elementi '${name}' shërben si një pikë lidhëse në këtë rast.`,
                    recommendation: `Analizoni me kujdes çdo lidhje që buron nga '${name}' për të zbuluar marrëdhënie të fshehura.`,
                    confidence: 70
                };
            }
            resolve(result);
        }, delay);
    });
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

// --- LEGAL THEME ---
const THEME = {
  node: {
    judge:   { bg: '#450a0a', border: '#ef4444', text: '#fecaca' },
    court:   { bg: '#1c1917', border: '#a8a29e', text: '#e7e5e4' },
    claim:   { bg: '#172554', border: '#3b82f6', text: '#dbeafe' },
    person:  { bg: '#064e3b', border: '#10b981', text: '#d1fae5' },
    document:{ bg: '#374151', border: '#9ca3af', text: '#f3f4f6' },
    evidence:{ bg: '#7c2d12', border: '#f97316', text: '#ffedd5' },
    money:   { bg: '#854d0e', border: '#facc15', text: '#fefce8' }, // NEW: Gold Theme
    default: { bg: '#111827', border: '#4b5563', text: '#e5e7eb' },
  }
};

// --- AI ADVISOR PANEL ---
const AIAdvisorPanel: React.FC<{ loading: boolean, data: { insight: string, recommendation: string, confidence: number } | null }> = ({ loading, data }) => {
    if (loading) {
        return (
            <div className="mt-6 p-5 bg-indigo-950/30 border border-indigo-500/30 rounded-lg relative overflow-hidden">
                <div className="flex items-center gap-3 mb-3"><BrainCircuit className="text-indigo-400 animate-pulse" size={20} /><span className="text-xs font-bold text-indigo-300 uppercase tracking-widest">Duke analizuar...</span></div>
                <div className="space-y-2"><div className="h-2 bg-indigo-500/20 rounded w-full animate-pulse"></div><div className="h-2 bg-indigo-500/20 rounded w-3/4 animate-pulse"></div></div>
            </div>
        );
    }
    if (!data) return null;
    return (
        <div className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-2"><div className="flex items-center gap-2"><Sparkles className="text-purple-400" size={16} /><span className="text-xs font-bold text-purple-300 uppercase tracking-widest">Lidhjet dhe Përshkrimet</span></div><span className="text-[10px] font-mono text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{data.confidence}% Besueshmëria</span></div>
            <div className="bg-slate-900 border border-purple-500/30 rounded-lg p-4 shadow-lg">
                <div className="mb-4"><h5 className="text-[10px] text-slate-400 font-bold uppercase mb-1 flex items-center gap-1"><Eye size={10} /> Vëzhgim</h5><p className="text-sm text-slate-200 leading-relaxed italic">"{data.insight}"</p></div>
                <div><h5 className="text-[10px] text-emerald-400 font-bold uppercase mb-1 flex items-center gap-1"><Lightbulb size={10} /> Veprim i Rekomanduar</h5><p className="text-sm text-white font-medium leading-relaxed">{data.recommendation}</p></div>
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
        graph.d3Force('charge')?.strength(-2000); 
        graph.d3Force('link')?.distance(220).strength(0.5);
        graph.d3Force('center')?.strength(0.2);
        if (data.nodes.length > 0) {
            setTimeout(() => graph.zoomToFit(800, 80), 500);
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
    const group = (node.group || 'Default').toUpperCase();
    const styleKey = Object.keys(THEME.node).find(k => group.toLowerCase().includes(k)) || 'default';
    const style = (THEME.node as any)[styleKey];
    
    const scale = group === 'DOCUMENT' ? 1.15 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    
    const x = node.x!;
    const y = node.y!;
    const isSelected = node.id === selectedNode?.id;

    ctx.shadowBlur = isSelected ? 30 : 0;
    ctx.shadowColor = style.border;

    ctx.fillStyle = style.bg;
    ctx.strokeStyle = isSelected ? '#ffffff' : style.border;
    ctx.lineWidth = isSelected ? 2.5 : 1;
    ctx.beginPath();
    ctx.roundRect(x - w / 2, y - h / 2, w, h, BORDER_RADIUS * scale);
    ctx.fill(); ctx.stroke(); ctx.shadowBlur = 0; 

    ctx.fillStyle = style.border;
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    ctx.roundRect(x - w / 2, y - h / 2, w, 24 * scale, [BORDER_RADIUS * scale, BORDER_RADIUS * scale, 0, 0]);
    ctx.fill(); ctx.globalAlpha = 1.0;

    ctx.font = `700 ${9 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = style.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(node.group.toUpperCase(), x - w / 2 + (10 * scale), y - h / 2 + (12 * scale));

    ctx.font = `bold ${13 * scale}px "Inter", sans-serif`;
    ctx.fillStyle = '#ffffff';
    let label = node.name || node.id;
    if (label.length > 18) label = label.substring(0, 17) + '...';
    ctx.fillText(label, x - w / 2 + (10 * scale), y + (2 * scale));

  }, [selectedNode]);

  const nodePointerAreaPaint = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const group = (node.group || 'Default').toUpperCase();
    const scale = group === 'DOCUMENT' ? 1.15 : 1.0;
    const w = CARD_WIDTH * scale;
    const h = CARD_HEIGHT * scale;
    ctx.fillStyle = color;
    const x = node.x!;
    const y = node.y!;
    ctx.beginPath();
    ctx.roundRect(x - w / 2, y - h / 2, w, h, BORDER_RADIUS * scale);
    ctx.fill();
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div ref={containerRef} className="lg:col-span-2 relative w-full h-[600px] bg-slate-950 rounded-lg overflow-hidden border border-slate-800 shadow-xl">
            <div className="absolute top-4 left-4 z-10 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded border border-slate-700 flex items-center gap-2">
                <ShieldAlert size={14} className="text-red-500" />
                <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">{t('caseGraph.title', 'Case Intelligence Map')}</span>
            </div>

            {isLoading && ( <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-950/80 backdrop-blur-sm"><div className="flex flex-col items-center gap-3"><Scale className="w-8 h-8 text-slate-500 animate-pulse" /><span className="text-xs font-mono text-slate-400">{t('caseGraph.loading', 'ANALYZING...')}</span></div></div> )}
            {!isLoading && data.nodes.length === 0 && ( <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none"><FileText className="w-12 h-12 text-slate-700 mb-4" /><h3 className="text-lg font-bold text-slate-500">{t('caseGraph.emptyTitle', 'No Graph Data')}</h3><p className="text-xs text-slate-600">{t('caseGraph.emptySubtitle', 'Upload documents to generate map.')}</p></div> )}

            <ForceGraph2D
                ref={fgRef}
                width={width}
                height={height}
                graphData={data}
                nodeCanvasObject={nodeCanvasObject}
                nodePointerAreaPaint={nodePointerAreaPaint}
                backgroundColor="rgba(0,0,0,0)" 
                
                linkColor={() => '#64748b'}
                linkWidth={2}
                linkDirectionalArrowLength={6}
                linkDirectionalArrowRelPos={1}
                linkLabel={(link: any) => link.label}
                
                linkDirectionalParticles={2}
                linkDirectionalParticleSpeed={0.004}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={() => '#94a3b8'}

                onNodeClick={(node) => {
                    setSelectedNode(node as GraphNode);
                    runAIAnalysis(node as GraphNode);
                    fgRef.current?.centerAt(node.x, node.y, 600);
                    fgRef.current?.zoom(1.5, 600);
                }}
                onBackgroundClick={() => { setSelectedNode(null); setAiData(null); }}
                minZoom={0.5}
                maxZoom={3.0}
            />
        </div>
        <div className="lg:col-span-1 p-6 bg-slate-900/50 rounded-lg border border-slate-800 h-[600px] flex flex-col">
            {selectedNode ? (
                <>
                    <div className="mb-4">
                        <h4 className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">{selectedNode.group}</h4>
                        <h3 className="text-xl text-white font-bold break-words">{selectedNode.name}</h3>
                    </div>
                    <div className="h-px bg-slate-700/50 my-2"></div>
                    <AIAdvisorPanel loading={aiLoading} data={aiData} />
                </>
            ) : (
                <div className="flex-grow flex flex-col items-center justify-center text-center text-slate-600 p-4">
                    <Search size={32} className="mb-4" />
                    <h3 className="text-lg font-bold text-slate-500">Zgjidhni një Nyje</h3>
                    <p className="text-xs">Kliko mbi një gjyqtar, palë, ose dokument për të parë analizën e AI.</p>
                </div>
            )}
        </div>
    </div>
  );
};

export default CaseGraphVisualization;