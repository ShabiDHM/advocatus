// FILE: src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - EVIDENCE MAP V12.0 (AUTO-LAYOUT & CLEAN TYPES)
// 1. FIX: Resolved all TS2345 errors by strictly typing Dagre output as Node<MapNodeData>[].
// 2. FIX: Added missing MarkerType import and resolved all TS6133 unused warnings.
// 3. REMOVED: PNG Export and manual creation tools for a professional AI-only workflow.

import { useState, useCallback, useEffect, useMemo } from 'react';
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

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 260, height: 160 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 130,
        y: nodeWithPosition.y - 80,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

const EvidenceMapPage = () => {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  const { fitView } = useReactFlow();

  const [nodes, setNodes] = useState<Node<MapNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isSidebarVisible, setIsSidebarVisible] = useState(true); 
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isPdfExporting, setIsPdfExporting] = useState(false);

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

  // Load Data
  useEffect(() => {
    const fetchMap = async () => {
      try {
        const response = await axios.get(`/api/v1/cases/${caseId}/evidence-map`);
        if (response.data.nodes) setNodes(response.data.nodes);
        if (response.data.edges) setEdges(response.data.edges);
      } catch (error) { console.error("Fetch failed", error); }
    };
    fetchMap();
  }, [caseId]);

  // Handle Auto-Layout
  const onLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    window.requestAnimationFrame(() => fitView({ duration: 800 }));
  }, [nodes, edges, fitView]);

  const onNodesChange: OnNodesChange<Node<MapNodeData>> = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]), 
    []
  );
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), 
    []
  );

  // Professional AI Auto-Build
  const handleImport = (importedNodes: any[], importedEdges: any[]) => {
    const newReactNodes: Node<MapNodeData>[] = importedNodes.map(node => ({
        id: node.id,
        type: node.type === 'Claim' ? 'claimNode' : node.type === 'Fact' ? 'factNode' : node.type === 'Law' ? 'lawNode' : 'evidenceNode',
        position: { x: 0, y: 0 },
        data: { label: node.name, content: node.description }
    }));

    const newReactEdges: Edge[] = importedEdges.map(edge => ({
        id: `e-${edge.source}-${edge.target}`,
        source: edge.source, 
        target: edge.target,
        label: edge.relation, 
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: edge.relation === 'KONTRADIKTON' ? '#f87171' : '#4ade80', strokeWidth: 2 }
    }));

    const { nodes: finalNodes, edges: finalEdges } = getLayoutedElements([...nodes, ...newReactNodes], [...edges, ...newReactEdges]);
    setNodes(finalNodes);
    setEdges(finalEdges);
    window.requestAnimationFrame(() => fitView({ duration: 800 }));
  };

  const saveMap = async () => {
    setIsSaving(true);
    try { await axios.put(`/api/v1/cases/${caseId}/evidence-map`, { nodes, edges }); } 
    catch (error) { console.error("Save failed", error); } 
    finally { setTimeout(() => setIsSaving(false), 1000); }
  };

  const handleExportPdf = async () => {
    setIsPdfExporting(true);
    try {
        const response = await axios.post(`/api/v1/cases/${caseId}/evidence-map/report`, { nodes, edges }, { responseType: 'blob' });
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Raporti_i_Provave_${caseId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (error) { console.error(error); } 
    finally { setIsPdfExporting(false); }
  };

  return (
      <div className="w-full h-[calc(100vh-64px)] bg-background-dark flex relative overflow-hidden">
        <div className="flex-grow h-full relative z-0">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} colorMode="dark">
            <Background color="#1e293b" gap={20} />
            
            <Panel position="top-right" className="flex flex-col gap-3 m-4">
                <button onClick={() => setIsSidebarVisible(v => !v)} className="w-12 h-12 bg-background-light/90 backdrop-blur-md text-white rounded-full shadow-2xl border border-white/10 flex items-center justify-center hover:bg-white/10 transition-all"><SidebarIcon size={20}/></button>
                <button onClick={onLayout} className="w-12 h-12 bg-primary-start hover:bg-primary-end text-white rounded-full shadow-2xl flex items-center justify-center transition-all"><Layout size={20}/></button>
            </Panel>
            
            <Panel position="top-center" className="flex gap-2 mt-4">
                <div className="flex bg-black/60 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl items-center gap-3">
                    <button onClick={() => setIsImportModalOpen(true)} className="px-6 py-2.5 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary-start/20"><BrainCircuit size={18}/> {t('evidenceMap.sidebar.importButton', 'Auto-Build AI')}</button>
                    <div className="w-px h-8 bg-white/10 mx-1"></div>
                    <button onClick={saveMap} disabled={isSaving} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-bold flex items-center gap-2 border border-white/10 transition-all active:scale-95 disabled:opacity-50"><Save size={18}/> {isSaving ? 'Ruajtja...' : 'Ruaj'}</button>
                    <button onClick={handleExportPdf} disabled={isPdfExporting} className="px-5 py-2.5 bg-red-600/10 hover:bg-red-600/20 text-red-500 rounded-xl text-sm font-bold flex items-center gap-2 border border-red-500/20 transition-all active:scale-95 disabled:opacity-50"><FileText size={18}/> PDF</button>
                </div>
            </Panel>
            </ReactFlow>
        </div>
      
        <div className={`absolute top-0 right-0 z-30 h-full w-full sm:w-80 transition-transform duration-300 transform ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full'}`}>
            <Sidebar filters={{hideUnconnected: false, highlightContradictions: true}} onFilterChange={() => {}} searchTerm="" onSearchChange={() => {}} onOpenImportModal={() => setIsImportModalOpen(true)} onClose={() => setIsSidebarVisible(false)} />
        </div>

        {isSidebarVisible && <div className="fixed inset-0 bg-black/50 md:hidden z-20" onClick={() => setIsSidebarVisible(false)} />}

        <ImportModal isOpen={isImportModalOpen} onClose={() => setIsImportModalOpen(false)} onImport={handleImport} caseId={caseId || ''} />
        <NodeEditModal isOpen={!!nodeToEdit} onClose={() => setNodes(nds => nds.map(n => ({...n, data: {...n.data, editing: false}})))} node={nodeToEdit || null} onSave={(id, data) => setNodes(nds => nds.map(n => n.id === id ? {...n, data: {...n.data, ...data, editing: false}} : n))} />
    </div>
  );
};

const WrappedEvidenceMapPage = () => (<ReactFlowProvider><EvidenceMapPage /></ReactFlowProvider>);
export default WrappedEvidenceMapPage;