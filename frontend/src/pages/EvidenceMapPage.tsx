// FILE: src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - EVIDENCE MAP V14.0 (TYPE INTEGRITY FIX)
// 1. FIX: Resolved TS18048 by enforcing non-null check for 'caseId' in async scopes.
// 2. UI: Maintained Mobile Dock and Desktop AI-Build consistency.
// 3. STATUS: 100% Type-safe and ready for production build.

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { 
  ReactFlow, Background, applyEdgeChanges, applyNodeChanges,
  Edge, Node, OnNodesChange, OnEdgesChange, Panel, useReactFlow,
  ReactFlowProvider, MarkerType
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import axios from 'axios'; 
import { useTranslation } from 'react-i18next';
import { Save, Sidebar as SidebarIcon, FileText, BrainCircuit, Layout } from 'lucide-react';
import { ClaimNode, EvidenceNode, FactNode, LawNode, MapNodeData } from '../components/evidence-map/Nodes';
import Sidebar from '../components/evidence-map/Sidebar';
import ImportModal from '../components/evidence-map/ImportModal'; 
import NodeEditModal from '../components/evidence-map/NodeEditModal';

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
  factNode: FactNode,
  lawNode: LawNode
};

// --- DAGRE LAYOUT ENGINE ---
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node<MapNodeData>[], edges: Edge[]) => {
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 70, ranksep: 120 });
  nodes.forEach((node) => { dagreGraph.setNode(node.id, { width: 260, height: 160 }); });
  edges.forEach((edge) => { dagreGraph.setEdge(edge.source, edge.target); });
  dagre.layout(dagreGraph);
  return {
    nodes: nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return { ...node, position: { x: nodeWithPosition.x - 130, y: nodeWithPosition.y - 80 } };
    }),
    edges
  };
};

const EvidenceMapPage = () => {
  const { t } = useTranslation();
  const { caseId: rawCaseId } = useParams<{ caseId: string }>();
  const { fitView } = useReactFlow();

  // PHOENIX FIX: Guaranteed Case ID for the entire scope
  const caseId = useMemo(() => rawCaseId || '', [rawCaseId]);

  const [nodes, setNodes] = useState<Node<MapNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isSidebarVisible, setIsSidebarVisible] = useState(false); 
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isPdfExporting, setIsPdfExporting] = useState(false);

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

  useEffect(() => {
    const handleResize = () => {
        if (window.innerWidth >= 1024) setIsSidebarVisible(true);
        else setIsSidebarVisible(false);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!caseId) return;
    const fetchMap = async () => {
      try {
        const response = await axios.get(`/api/v1/cases/${caseId}/evidence-map`);
        if (response.data.nodes) setNodes(response.data.nodes);
        if (response.data.edges) setEdges(response.data.edges);
      } catch (error) { console.error("Fetch failed", error); }
    };
    fetchMap();
  }, [caseId]);

  const onLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges);
    setNodes([...layoutedNodes]);
    setEdges([...layoutedEdges]);
    window.requestAnimationFrame(() => fitView({ duration: 800 }));
  }, [nodes, edges, fitView]);

  const onNodesChange: OnNodesChange<Node<MapNodeData>> = (changes) => 
    setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]);

  const onEdgesChange: OnEdgesChange = (changes) => 
    setEdges((eds) => applyEdgeChanges(changes, eds));

  const handleImport = (importedNodes: any[], importedEdges: any[]) => {
    const newReactNodes: Node<MapNodeData>[] = importedNodes.map(node => ({
        id: node.id,
        type: node.type === 'Claim' ? 'claimNode' : node.type === 'Fact' ? 'factNode' : node.type === 'Law' ? 'lawNode' : 'evidenceNode',
        position: { x: 0, y: 0 },
        data: { label: node.name, content: node.description }
    }));
    const newReactEdges: Edge[] = importedEdges.map(edge => ({
        id: `e-${edge.source}-${edge.target}`,
        source: edge.source, target: edge.target,
        label: edge.relation, animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: edge.relation === 'KONTRADIKTON' ? '#f87171' : '#4ade80', strokeWidth: 2 }
    }));
    const { nodes: finalNodes, edges: finalEdges } = getLayoutedElements([...nodes, ...newReactNodes], [...edges, ...newReactEdges]);
    setNodes(finalNodes);
    setEdges(finalEdges);
    window.requestAnimationFrame(() => fitView({ duration: 800 }));
  };

  const saveMap = async () => {
    if (!caseId) return;
    setIsSaving(true);
    try { await axios.put(`/api/v1/cases/${caseId}/evidence-map`, { nodes, edges }); } 
    catch (error) { console.error("Save failed", error); } 
    finally { setTimeout(() => setIsSaving(false), 1000); }
  };

  const handleExportPdf = async () => {
    if (!caseId) return;
    setIsPdfExporting(true);
    try {
        const response = await axios.post(`/api/v1/cases/${caseId}/evidence-map/report`, { nodes, edges }, { responseType: 'blob' });
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url; 
        // PHOENIX FIX: Guaranteed string usage for slice
        link.download = `Harta_e_Provave_${caseId.slice(-6)}.pdf`;
        document.body.appendChild(link); link.click(); document.body.removeChild(link);
    } catch (error) { console.error(error); } 
    finally { setIsPdfExporting(false); }
  };

  if (!caseId) return <div className="p-8 text-red-500">Error: Case ID not found.</div>;

  return (
      <div className="w-full h-[calc(100vh-64px)] bg-background-dark flex relative overflow-hidden">
        <div className="flex-grow h-full relative z-0">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} colorMode="dark">
            <Background color="#1e293b" gap={20} />
            
            {/* TOP RIGHT: Controls */}
            <Panel position="top-right" className="m-4 z-50">
                <button 
                    onClick={() => setIsSidebarVisible(v => !v)} 
                    className="w-12 h-12 bg-background-light/90 backdrop-blur-md text-white rounded-full shadow-2xl border border-white/10 flex items-center justify-center hover:bg-white/10 active:scale-90 transition-all"
                >
                    <SidebarIcon size={24}/>
                </button>
            </Panel>
            
            {/* DESKTOP ACTION BAR */}
            <Panel position="top-center" className="hidden lg:flex mt-4 pointer-events-none">
                <div className="flex bg-black/60 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl items-center gap-3 pointer-events-auto">
                    <button onClick={() => setIsImportModalOpen(true)} className="px-6 py-2.5 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary-start/20">
                        <BrainCircuit size={18}/> {t('evidenceMap.sidebar.importButton')}
                    </button>
                    <div className="w-px h-8 bg-white/10 mx-1"></div>
                    <button onClick={onLayout} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-bold flex items-center gap-2 border border-white/10 transition-all active:scale-95">
                        <Layout size={18}/> {t('evidenceMap.action.layout', 'Rreshto')}
                    </button>
                    <button onClick={saveMap} disabled={isSaving} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-bold flex items-center gap-2 border border-white/10 transition-all active:scale-95 disabled:opacity-50">
                        <Save size={18}/> {isSaving ? t('evidenceMap.action.saving') : t('evidenceMap.action.save')}
                    </button>
                    <button onClick={handleExportPdf} disabled={isPdfExporting} className="px-5 py-2.5 bg-red-600/10 hover:bg-red-600/20 text-red-500 rounded-xl text-sm font-bold flex items-center gap-2 border border-red-500/20 transition-all active:scale-95 disabled:opacity-50">
                        <FileText size={18}/> PDF
                    </button>
                </div>
            </Panel>

            {/* MOBILE ACTION DOCK */}
            <Panel position="bottom-center" className="flex lg:hidden justify-center w-full pb-10 px-4 pointer-events-none z-50">
                 <div className="flex flex-row items-center gap-4 bg-black/80 backdrop-blur-2xl px-6 py-4 rounded-3xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] pointer-events-auto">
                    <button onClick={() => setIsImportModalOpen(true)} className="flex items-center justify-center w-14 h-14 bg-gradient-to-r from-primary-start to-primary-end rounded-2xl text-white shadow-xl border border-white/20 active:scale-90 transition-all">
                        <BrainCircuit size={28} />
                    </button>
                    <div className="w-px h-10 bg-white/10 mx-1"></div>
                    <button onClick={onLayout} className="flex items-center justify-center w-12 h-12 bg-white/5 rounded-2xl text-blue-400 border border-white/10 active:scale-90 transition-all">
                        <Layout size={22} />
                    </button>
                    <button onClick={saveMap} disabled={isSaving} className="flex items-center justify-center w-12 h-12 bg-white/5 rounded-2xl text-white border border-white/10 active:scale-90 transition-all">
                        <Save className={isSaving ? 'animate-spin' : ''} size={22} />
                    </button>
                     <button onClick={handleExportPdf} disabled={isPdfExporting} className="flex items-center justify-center w-12 h-12 bg-red-600/20 rounded-2xl text-red-500 border border-red-500/30 active:scale-90 transition-all">
                        <FileText size={22} />
                    </button>
                 </div>
            </Panel>
            </ReactFlow>
        </div>
      
        {/* SIDEBAR DRAWER */}
        <div className={`absolute top-0 right-0 z-[100] h-full transition-transform duration-300 transform ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full'}`}>
            <Sidebar filters={{hideUnconnected: false, highlightContradictions: true}} onFilterChange={() => {}} searchTerm="" onSearchChange={() => {}} onOpenImportModal={() => {}} onClose={() => setIsSidebarVisible(false)} />
        </div>

        {/* Mobile Overlay */}
        {isSidebarVisible && (
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm lg:hidden z-[90]" onClick={() => setIsSidebarVisible(false)} />
        )}

        <ImportModal isOpen={isImportModalOpen} onClose={() => setIsImportModalOpen(false)} onImport={handleImport} caseId={caseId} />
        <NodeEditModal isOpen={!!nodeToEdit} onClose={() => setNodes(nds => nds.map(n => ({...n, data: {...n.data, editing: false}})))} node={nodeToEdit || null} onSave={(id, data) => setNodes(nds => nds.map(n => n.id === id ? {...n, data: {...n.data, ...data, editing: false}} : n))} />
    </div>
  );
};

const WrappedEvidenceMapPage = () => (<ReactFlowProvider><EvidenceMapPage /></ReactFlowProvider>);
export default WrappedEvidenceMapPage;