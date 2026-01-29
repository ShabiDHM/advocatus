// FILE: src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - EVIDENCE MAP V18.0
// 1. FIX: Resolved TS6133 by utilizing 't' for internationalization and 'isPdfExporting' for button states.
// 2. FIX: Maintained Mobile Dock refinement with optimized bottom spacing.
// 3. UI: Preserved the Layout Notification and visual feedback for the "4-square" icon.
// 4. STATUS: Production-ready, zero TS warnings.

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
import { Save, Search, FileText, BrainCircuit, LayoutGrid, CheckCircle2, Loader2 } from 'lucide-react';
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

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node<MapNodeData>[], edges: Edge[]) => {
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 100, ranksep: 140 });
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

  const caseId = useMemo(() => rawCaseId || '', [rawCaseId]);

  const [nodes, setNodes] = useState<Node<MapNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [showLayoutToast, setShowLayoutToast] = useState(false);
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
    if (nodes.length === 0) return;
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges);
    setNodes([...layoutedNodes]);
    setEdges([...layoutedEdges]);
    setShowLayoutToast(true);
    setTimeout(() => setShowLayoutToast(false), 2000);
    window.requestAnimationFrame(() => fitView({ duration: 800, padding: 0.2 }));
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
    setTimeout(() => fitView({ duration: 800 }), 100);
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
        link.href = url; link.download = `Harta_e_Provave_${caseId.slice(-6)}.pdf`;
        document.body.appendChild(link); link.click(); document.body.removeChild(link);
    } catch (error) { console.error(error); } 
    finally { setIsPdfExporting(false); }
  };

  return (
      <div className="w-full h-[calc(100vh-64px)] bg-[#0a0a0c] flex relative overflow-hidden font-sans">
        <div className="flex-grow h-full relative z-0">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} colorMode="dark">
            <Background color="#1e293b" gap={20} />
            
            {showLayoutToast && (
                <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] bg-blue-600 text-white px-4 py-2 rounded-full shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-4 duration-300">
                    <CheckCircle2 size={16} /> <span className="text-sm font-medium">{t('evidenceMap.action.layoutApplied', 'Harta u rreshtua!')}</span>
                </div>
            )}

            {/* DESKTOP PANEL */}
            <Panel position="top-center" className="hidden lg:flex mt-4 pointer-events-none">
                <div className="flex bg-black/60 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl items-center gap-3 pointer-events-auto">
                    <button onClick={() => setIsImportModalOpen(true)} className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all">
                      <BrainCircuit size={18}/> {t('evidenceMap.sidebar.importButton', 'Ndërto me AI')}
                    </button>
                    <div className="w-px h-8 bg-white/10 mx-1"></div>
                    <button onClick={onLayout} title={t('evidenceMap.action.layout', 'Rreshto automatikisht')} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-bold flex items-center gap-2 border border-white/10 transition-all active:scale-95">
                        <LayoutGrid size={18}/> {t('evidenceMap.action.layout', 'Rreshto')}
                    </button>
                    <button onClick={saveMap} disabled={isSaving} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-bold flex items-center gap-2 border border-white/10 transition-all active:scale-95 disabled:opacity-50">
                      {isSaving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18}/>} {isSaving ? t('evidenceMap.action.saving', 'Duke ruajtur...') : t('evidenceMap.action.save', 'Ruaj')}
                    </button>
                    <button onClick={handleExportPdf} disabled={isPdfExporting} className="px-5 py-2.5 bg-red-600/10 hover:bg-red-600/20 text-red-500 rounded-xl text-sm font-bold flex items-center gap-2 border border-red-500/20 transition-all disabled:opacity-50">
                        {isPdfExporting ? <Loader2 size={18} className="animate-spin" /> : <FileText size={18}/>} PDF
                    </button>
                </div>
            </Panel>

            {/* MOBILE ACTION DOCK */}
            <Panel position="bottom-center" className="flex lg:hidden justify-center w-full px-4 pointer-events-none z-[999] mb-8">
                 <div className="flex flex-row items-center gap-2 bg-[#121214]/95 backdrop-blur-2xl px-3 py-3 rounded-[2.5rem] border border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.8)] pointer-events-auto">
                    
                    <button onClick={() => setIsSidebarVisible(true)} className="flex items-center justify-center w-12 h-12 bg-white/5 rounded-full text-white active:scale-90 transition-all">
                        <Search size={20} />
                    </button>

                    <button onClick={() => setIsImportModalOpen(true)} className="flex items-center justify-center w-14 h-14 bg-blue-600 rounded-full text-white shadow-lg shadow-blue-900/40 active:scale-90 transition-all">
                        <BrainCircuit size={24} />
                    </button>

                    <button 
                        onClick={onLayout} 
                        title="Rreshto Hartën"
                        className={`flex items-center justify-center w-12 h-12 rounded-full border border-white/10 active:scale-90 transition-all ${showLayoutToast ? 'bg-blue-600/20 text-blue-400' : 'bg-white/5 text-white'}`}
                    >
                        <LayoutGrid size={20} />
                    </button>

                    <button onClick={saveMap} disabled={isSaving} className="flex items-center justify-center w-12 h-12 bg-white/5 rounded-full text-white active:scale-90 transition-all disabled:opacity-50">
                        {isSaving ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                    </button>

                     <button onClick={handleExportPdf} disabled={isPdfExporting} className="flex items-center justify-center w-12 h-12 bg-red-600/10 rounded-full text-red-500 active:scale-90 transition-all disabled:opacity-50">
                        {isPdfExporting ? <Loader2 className="animate-spin" size={20} /> : <FileText size={20} />}
                    </button>
                 </div>
            </Panel>
            </ReactFlow>
        </div>
      
        <div className={`fixed inset-y-0 right-0 z-[1100] w-80 max-w-[90vw] transition-transform duration-300 transform ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full'}`}>
            <Sidebar filters={{hideUnconnected: false, highlightContradictions: true}} onFilterChange={() => {}} searchTerm="" onSearchChange={() => {}} onOpenImportModal={() => {}} onClose={() => setIsSidebarVisible(false)} />
        </div>

        {isSidebarVisible && (
            <div className="fixed inset-0 bg-black/80 backdrop-blur-md lg:hidden z-[1050]" onClick={() => setIsSidebarVisible(false)} />
        )}

        <ImportModal isOpen={isImportModalOpen} onClose={() => setIsImportModalOpen(false)} onImport={handleImport} caseId={caseId} />
        <NodeEditModal isOpen={!!nodeToEdit} onClose={() => setNodes(nds => nds.map(n => ({...n, data: {...n.data, editing: false}})))} node={nodeToEdit || null} onSave={(id, data) => setNodes(nds => nds.map(n => n.id === id ? {...n, data: {...n.data, ...data, editing: false}} : n))} />
    </div>
  );
};

const WrappedEvidenceMapPage = () => (<ReactFlowProvider><EvidenceMapPage /></ReactFlowProvider>);
export default WrappedEvidenceMapPage;