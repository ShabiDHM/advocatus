// FILE: src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - EVIDENCE MAP V29.0 (FRONTEND INITIALIZATION FIX)
// 1. FIX: Corrected the useEffect dependency array to ensure the initial data fetch is always triggered.
// 2. FIX: Re-introduced the 'force_refresh' button with correct API call (`?refresh=true`).
// 3. UI: Refined the loading and empty states for a more professional and informative user experience.
// 4. STATUS: 100% Automated. The frontend now correctly initiates the backend's AI pipeline.

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { 
  ReactFlow, Background, applyEdgeChanges, applyNodeChanges,
  Edge, Node, OnNodesChange, OnEdgesChange, Panel, useReactFlow,
  ReactFlowProvider
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import axios from 'axios'; 
import { useTranslation } from 'react-i18next';
import { Save, Search, FileText, LayoutGrid, CheckCircle2, Loader2, Sparkles, RefreshCcw } from 'lucide-react';
import { ClaimNode, EvidenceNode, FactNode, LawNode, MapNodeData } from '../components/evidence-map/Nodes';
import Sidebar from '../components/evidence-map/Sidebar';
import NodeEditModal from '../components/evidence-map/NodeEditModal';

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
  factNode: FactNode,
  lawNode: LawNode
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node<MapNodeData>[], edges: Edge[]) => {
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 120, ranksep: 180 });
  nodes.forEach((node) => { dagreGraph.setNode(node.id, { width: 260, height: 180 }); });
  edges.forEach((edge) => { dagreGraph.setEdge(edge.source, edge.target); });
  dagre.layout(dagreGraph);
  return {
    nodes: nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return { ...node, position: { x: nodeWithPosition.x - 130, y: nodeWithPosition.y - 90 } };
    }),
    edges
  };
};

const EvidenceMapPage = () => {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  const { fitView } = useReactFlow();

  const [nodes, setNodes] = useState<Node<MapNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showLayoutToast, setShowLayoutToast] = useState(false);
  const [isSidebarVisible, setIsSidebarVisible] = useState(false); 
  const [isPdfExporting, setIsPdfExporting] = useState(false);

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

  const onLayout = useCallback((n: Node<MapNodeData>[], e: Edge[]) => {
    if (n.length === 0) return;
    const { nodes: lNodes, edges: lEdges } = getLayoutedElements(n, e);
    setNodes([...lNodes]);
    setEdges([...lEdges]);
    setShowLayoutToast(true);
    setTimeout(() => setShowLayoutToast(false), 2000);
    setTimeout(() => fitView({ duration: 800, padding: 0.2 }), 100);
  }, [fitView]);

  const fetchEvidenceMap = useCallback(async (forceRefresh = false) => {
    if (!caseId) return;
    setIsInitializing(true);
    try {
      const url = `/api/v1/cases/${caseId}/evidence-map${forceRefresh ? '?refresh=true' : ''}`;
      const res = await axios.get(url);
      if (res.data.nodes?.length > 0) {
          onLayout(res.data.nodes, res.data.edges || []);
      } else {
          setNodes([]); setEdges([]);
      }
    } catch (err) { console.error("Fetch failed", err); } 
    finally { setIsInitializing(false); }
  }, [caseId, onLayout]);

  useEffect(() => {
    // PHOENIX FIX: This ensures the fetch is called exactly once when the component mounts with a valid caseId.
    fetchEvidenceMap(false);
  }, [fetchEvidenceMap]);

  const onNodesChange: OnNodesChange<Node<MapNodeData>> = (changes) => 
    setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]);

  const onEdgesChange: OnEdgesChange = (changes) => 
    setEdges((eds) => applyEdgeChanges(changes, eds));

  const saveMap = async () => {
    if (!caseId) return;
    setIsSaving(true);
    try { await axios.put(`/api/v1/cases/${caseId}/evidence-map`, { nodes, edges }); } 
    catch (err) { console.error(err); } 
    finally { setTimeout(() => setIsSaving(false), 1000); }
  };

  const handleExportPdf = async () => {
    if (!caseId) return;
    setIsPdfExporting(true);
    try {
        const response = await axios.post(`/api/v1/cases/${caseId}/evidence-map/report`, { nodes, edges }, { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
        const link = document.createElement('a'); link.href = url; link.download = `Harta_Provave.pdf`;
        document.body.appendChild(link); link.click(); document.body.removeChild(link);
    } catch (err) { console.error(err); } 
    finally { setIsPdfExporting(false); }
  };

  return (
      <div className="w-full h-[calc(100dvh-64px)] bg-[#050506] flex relative overflow-hidden font-sans">
        <div className="flex-grow h-full relative z-0">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} colorMode="dark">
            <Background color="#111115" gap={20} />
            
            {showLayoutToast && (
                <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[2001] bg-blue-600 text-white px-4 py-2 rounded-full shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-4 duration-300">
                    <CheckCircle2 size={16} /> <span className="text-sm font-medium">Harta u sinkronizua!</span>
                </div>
            )}

            {isInitializing && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-md z-[2000]">
                    <Sparkles size={48} className="text-blue-500 animate-pulse mb-4" />
                    <p className="text-white font-black text-xs uppercase tracking-[0.3em] animate-pulse">Inteligjenca po ndërton pemën...</p>
                </div>
            )}

            {nodes.length === 0 && !isInitializing && (
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
                    <div className="text-center space-y-4 max-w-sm">
                        <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto border border-white/10">
                            <Sparkles size={32} className="text-gray-600" />
                        </div>
                        <h2 className="text-xl font-bold text-white tracking-tight">Harta është gati</h2>
                        <p className="text-gray-500 text-xs px-10">Sapo AI të përfundojë analizën e dokumenteve, pema do të shfaqet këtu. Klikoni për të rifreskuar.</p>
                        <button onClick={() => fetchEvidenceMap(true)} className="pointer-events-auto mt-2 px-5 py-2 bg-white/5 hover:bg-white/10 text-white text-[10px] font-black uppercase tracking-widest rounded-full border border-white/10 transition-all">
                           Rifresko Analizën
                        </button>
                    </div>
                </div>
            )}

            <Panel position="top-center" className="hidden lg:flex mt-4 pointer-events-none">
                <div className="flex bg-[#0f0f11]/90 backdrop-blur-xl p-1.5 rounded-2xl border border-white/10 shadow-2xl items-center gap-2 pointer-events-auto">
                    <button onClick={() => fetchEvidenceMap(true)} className="px-4 py-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 rounded-xl text-[11px] font-black uppercase tracking-wider flex items-center gap-2 transition-all">
                        <RefreshCcw size={14}/> {t('evidenceMap.action.refresh', 'Rifresko me AI')}
                    </button>
                    <div className="w-px h-6 bg-white/10 mx-1"></div>
                    <button onClick={() => onLayout(nodes, edges)} className="px-4 py-2 hover:bg-white/5 text-white rounded-xl text-[11px] font-bold flex items-center gap-2 transition-all">
                        <LayoutGrid size={14}/> {t('evidenceMap.action.layout', 'Rreshto')}
                    </button>
                    <button onClick={saveMap} disabled={isSaving} className="px-5 py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl text-[11px] font-bold flex items-center gap-2 transition-all disabled:opacity-50">
                      {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14}/>} {t('evidenceMap.action.save', 'Ruaj Layout')}
                    </button>
                    <button onClick={handleExportPdf} disabled={isPdfExporting} className="px-4 py-2 bg-red-600/10 hover:bg-red-600/20 text-red-500 rounded-xl text-[11px] font-bold flex items-center gap-2 transition-all disabled:opacity-50">
                        {isPdfExporting ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14}/>} PDF
                    </button>
                </div>
            </Panel>

            <Panel position="bottom-center" className="flex lg:hidden justify-center w-full px-4 pointer-events-none z-[999] mb-4">
                 <div className="flex flex-row items-center gap-2 bg-[#121214]/95 backdrop-blur-3xl px-2.5 py-2.5 rounded-full border border-white/10 shadow-2xl pointer-events-auto">
                    <button onClick={() => setIsSidebarVisible(true)} className="flex items-center justify-center w-10 h-10 bg-white/5 rounded-full text-white active:scale-90"><Search size={16} /></button>
                    <button onClick={() => fetchEvidenceMap(true)} className="flex items-center justify-center w-12 h-12 bg-blue-600 rounded-full text-white shadow-xl active:scale-90"><RefreshCcw size={20} /></button>
                    <button onClick={() => onLayout(nodes, edges)} className="flex items-center justify-center w-10 h-10 bg-white/5 rounded-full text-white active:scale-90"><LayoutGrid size={16} /></button>
                 </div>
            </Panel>
            </ReactFlow>
        </div>
      
        <div className={`fixed inset-y-0 right-0 z-[1100] w-80 max-w-[90vw] transition-transform duration-300 transform ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full'}`}>
            <Sidebar filters={{hideUnconnected: false, highlightContradictions: true}} onFilterChange={() => {}} searchTerm="" onSearchChange={() => {}} onOpenImportModal={() => {}} onClose={() => setIsSidebarVisible(false)} />
        </div>

        <NodeEditModal isOpen={!!nodeToEdit} onClose={() => setNodes(nds => nds.map(n => ({...n, data: {...n.data, editing: false}})))} node={nodeToEdit || null} onSave={(id, data) => setNodes(nds => nds.map(n => n.id === id ? {...n, data: {...n.data, ...data, editing: false}} : n))} />
    </div>
  );
};

const WrappedEvidenceMapPage = () => (<ReactFlowProvider><EvidenceMapPage /></ReactFlowProvider>);
export default WrappedEvidenceMapPage;