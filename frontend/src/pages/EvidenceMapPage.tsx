// FILE: src/pages/EvidenceMapPage.tsx
import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  ReactFlow, 
  Background, 
  Controls, 
  applyEdgeChanges, 
  applyNodeChanges, 
  addEdge,
  Connection,
  Edge,
  Node,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  Panel,
  MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import axios from 'axios'; 
import { Save, PlusCircle, Database } from 'lucide-react';

import { ClaimNode, EvidenceNode } from '../components/evidence-map/Nodes';

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
};

const EvidenceMapPage = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // 1. Load Map Data
  useEffect(() => {
    const fetchMap = async () => {
      try {
        // NOTE: If your app requires an Auth Header, ensure axios is configured or attach the token here.
        const response = await axios.get(`/api/v1/cases/${caseId}/evidence-map`);
        setNodes(response.data.nodes || []);
        setEdges(response.data.edges || []);
      } catch (error) {
        console.error("Failed to load map:", error);
      }
    };
    fetchMap();
  }, [caseId]);

  // 2. Event Handlers
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  
  // Phase 2: Connection System (Arrows & Styles)
  const onConnect: OnConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ 
      ...params, 
      animated: true, 
      type: 'smoothstep', 
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { strokeWidth: 2 }
    }, eds)),
    []
  );

  // 3. Save Function (Auto-save Logic)
  const saveMap = async () => {
    setIsSaving(true);
    try {
      await axios.put(`/api/v1/cases/${caseId}/evidence-map`, {
        nodes,
        edges,
        viewport: { x: 0, y: 0, zoom: 1 } 
      });
    } catch (error) {
      console.error("Failed to save map:", error);
    } finally {
      setTimeout(() => setIsSaving(false), 1000);
    }
  };

  const addNewNode = (type: 'claimNode' | 'evidenceNode') => {
    const newNode: Node = {
      id: `${type}-${Date.now()}`,
      type,
      position: { x: Math.random() * 400 + 50, y: Math.random() * 400 + 50 },
      data: { label: `New ${type === 'claimNode' ? 'Claim' : 'Evidence'}`, content: 'Double click to edit' },
    };
    setNodes((nds) => nds.concat(newNode));
  };

  return (
    <div className="w-full h-[calc(100vh-64px)] bg-background-dark">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        colorMode="dark"
      >
        <Background color="#1e293b" gap={20} />
        <Controls />
        
        <Panel position="top-right" className="flex gap-2">
          <button 
            onClick={() => addNewNode('claimNode')}
            className="flex items-center px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm transition-colors shadow-lg"
          >
            <PlusCircle className="w-4 h-4 mr-2" /> Add Claim
          </button>
          <button 
            onClick={() => addNewNode('evidenceNode')}
            className="flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors shadow-lg"
          >
            <Database className="w-4 h-4 mr-2" /> Add Evidence
          </button>
          <button 
            onClick={saveMap}
            disabled={isSaving}
            className={`flex items-center px-4 py-2 rounded-md text-sm transition-all shadow-lg ${isSaving ? 'bg-gray-600' : 'bg-primary-start hover:opacity-90'} text-white`}
          >
            <Save className={`w-4 h-4 mr-2 ${isSaving ? 'animate-spin' : ''}`} />
            {isSaving ? 'Saving...' : 'Save Map'}
          </button>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default EvidenceMapPage;