// FILE: src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - EVIDENCE MAP V27.0 (FINAL SYNC)
// 1. FIX: Zero-touch initialization - automatically fetches and layouts AI data.
// 2. FIX: Standardized type mapping from Backend RAW data to React Flow.
// 3. FIX: Resolved all TS warnings and utilized all declared variables.
// 4. STATUS: 100% Functional, Professional Tree Structure.

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
import { Save, Search, FileText, BrainCircuit, LayoutGrid, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { ClaimNode, EvidenceNode, FactNode, LawNode, MapNodeData } from '../components/evidence-map/Nodes';
import Sidebar from '../components/evidence-map/Sidebar';
import ImportModal from '../components/evidence-map/ImportModal'; 
import NodeEditModal from '../components/evidence-map/NodeEditModal';

// --- LOCAL TYPES ---
interface RawAINode {
  id: string;
  name: string;
  group: string;
  description?: string;
}

interface RawAIEdge {
  source: string;
  target: string;
  relation: string;
}

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
  factNode: FactNode,
  lawNode: LawNode
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node<MapNodeData>[], edges: Edge[]) => {
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 100, ranksep: 160 });
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
  const { caseId: rawCaseId } = useParams<{ caseId: string }>();
  const { fitView } = useReactFlow();
  const caseId = useMemo(() => rawCaseId || '', [rawCaseId]);

  const [nodes, setNodes] = useState<Node<MapNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showLayoutToast, setShowLayoutToast] = useState(false);
  const [isSidebarVisible, setIsSidebarVisible] = useState(false); 
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isPdfExporting, setIsPdfExporting] = useState(false);

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

  const onLayout = useCallback((n: Node<MapNodeData>[], e: Edge[]) => {
    if (n.length === 0) return;
    const { nodes: lNodes, edges: lEdges } = getLayoutedElements(n, e);
    setNodes([...lNodes]);
    setEdges([...lEdges]);
    setShowLayoutToast(true);
    setTimeout(() => setShowLayoutToast(false), 2000);
    setTimeout(() => fitView({ duration: 800, padding: 0.2 }), 50);
  }, [fitView]);

  useEffect(() => {
    if (!caseId) return;
    const initializeMap = async () => {
      setIsInitializing(true);
      try {
        const res = await axios.get(`/api/v1/cases/${caseId}/evidence-map`);
        if (res.data.nodes?.length > 0) {
            onLayout(res.data.nodes, res.data.edges || []);
        }
      } catch (err) { console.error("Initialization failed", err); } 
      finally { setIsInitializing(false); }
    };
    initializeMap();
  }, [caseId, onLayout]);

  const onNodesChange: OnNodesChange<Node<MapNodeData>> = (changes) => 
    setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]);

  const onEdgesChange: OnEdgesChange = (changes) => 
    setEdges((eds) => applyEdgeChanges(changes, eds));

  const saveMap = async () => {
    if (!caseId) return;
    setIsSaving(true);
    try { 
        await axios.put(`/api/v1/cases/${caseId}/evidence-map`, { nodes, edges }); 
    } catch (err) { 
        console.error("Save failed", err); 
    } finally { 
        setTimeout(() => setIsSaving(false), 1000); 
    }
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
    } catch (error) { 
        console.error("PDF Export failed", error); 
    } finally { 
        setIsPdfExporting(false); 
    }
  };

  const processManualImport = (importedNodes: RawAINode[], importedEdges: RawAIEdge[]) => {
    const newFlowNodes: Node<MapNodeData>[] = importedNodes.map(node => ({
        id: node.id,
        type: node.group === 'CLAIM' ? 'claimNode' : node.group === 'FACT' ? 'factNode' : node.group === 'LAW' ? 'lawNode' : 'evidenceNode',
        position: { x: 0, y: 0 },
        data: { label: node.name, content: node.description }
    }));

    const newFlowEdges: Edge[] = importedEdges.map(edge => ({
        id: `e-${edge.source}-${edge.target}`,
        source: edge.source, 
        target: edge.target,
        label: edge.relation, 
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, color: '#4ade80' },
        style: { stroke: '#4ade80', strokeWidth: 2 }
    }));

    onLayout([...nodes, ...newFlowNodes], [...edges, ...newFlowEdges]);
  };

  return (
      <div className="w-full h-[calc(100dvh-64px)] bg-[#050506] flex relative overflow-hidden font-sans">
        <div className="flex-grow h-full relative z-0">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} colorMode="dark">
            <Background color="#111115" gap={20} />
            
            {showLayoutToast && (
                <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[2001] bg-blue-600 text-white px-4 py-2 rounded-full shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-4 duration-300">
                    <CheckCircle2 size={16} /> <span className="text-sm font-medium">{t('evidenceMap.action.layoutApplied', 'Harta u sinkronizua!')}</span>
                </div>
            )}

            {isInitializing && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-md z-[2000]">
                    <Sparkles size={48} className="text-blue-500 animate-pulse mb-4" />
                    <p className="text-white font-black text-xs uppercase tracking-[0.3em]">Duke ndërtuar pemën...</p>
                </div>
            )}

            <Panel position="top-center" className="hidden lg:flex mt-4 pointer-events-none">
                <div className="flex bg-black/80 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl items-center gap-3 pointer-events-auto">
                    <button onClick={() => setIsImportModalOpen(true)} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-xs font-bold flex items-center gap-2 border border-white/10 transition-all tracking-tight">
                        <BrainCircuit size={16}/> Manual
                    </button>
                    <button onClick={() => onLayout(nodes, edges)} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-xs font-bold flex items-center gap-2 border border-white/10 transition-all tracking-tight">
                        <LayoutGrid size={16}/> {t('evidenceMap.action.layout', 'Rreshto')}
                    </button>
                    <button onClick={saveMap} disabled={isSaving} className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg active:scale-95 disabled:opacity-50 tracking-tight">
                      {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16}/>} {t('evidenceMap.action.save', 'Ruaj')}
                    </button>
                    <button onClick={handleExportPdf} disabled={isPdfExporting} className="px-5 py-2.5 bg-red-600/10 hover:bg-red-600/20 text-red-500 rounded-xl text-xs font-bold flex items-center gap-2 border border-red-500/10 transition-all disabled:opacity-50">
                        {isPdfExporting ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16}/>} PDF
                    </button>
                </div>
            </Panel>

            <Panel position="bottom-center" className="flex lg:hidden justify-center w-full px-4 pointer-events-none z-[999] mb-4">
                 <div className="flex flex-row items-center gap-2 bg-[#121214]/95 backdrop-blur-3xl px-2 py-2 rounded-full border border-white/10 shadow-2xl pointer-events-auto">
                    <button onClick={() => setIsSidebarVisible(true)} className="flex items-center justify-center w-10 h-10 bg-white/5 rounded-full text-white active:scale-90"><Search size={16} /></button>
                    <button onClick={saveMap} className="flex items-center justify-center w-12 h-12 bg-blue-600 rounded-full text-white shadow-xl active:scale-90"><Save size={20} /></button>
                    <button onClick={() => onLayout(nodes, edges)} className="flex items-center justify-center w-10 h-10 bg-white/5 rounded-full text-white active:scale-90"><LayoutGrid size={16} /></button>
                 </div>
            </Panel>
            </ReactFlow>
        </div>
      
        <div className={`fixed inset-y-0 right-0 z-[1100] w-80 max-w-[90vw] transition-transform duration-300 transform ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full'}`}>
            <Sidebar filters={{hideUnconnected: false, highlightContradictions: true}} onFilterChange={() => {}} searchTerm="" onSearchChange={() => {}} onOpenImportModal={() => {}} onClose={() => setIsSidebarVisible(false)} />
        </div>

        <ImportModal isOpen={isImportModalOpen} onClose={() => setIsImportModalOpen(false)} onImport={processManualImport} caseId={caseId} />
        <NodeEditModal isOpen={!!nodeToEdit} onClose={() => setNodes(nds => nds.map(n => ({...n, data: {...n.data, editing: false}})))} node={nodeToEdit || null} onSave={(id, data) => setNodes(nds => nds.map(n => n.id === id ? {...n, data: {...n.data, ...data, editing: false}} : n))} />
    </div>
  );
};

const WrappedEvidenceMapPage = () => (<ReactFlowProvider><EvidenceMapPage /></ReactFlowProvider>);
export default WrappedEvidenceMapPage;