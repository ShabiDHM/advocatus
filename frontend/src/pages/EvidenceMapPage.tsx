// FILE: src/pages/EvidenceMapPage.tsx (FINAL COMPLETE REPLACEMENT)
// PHOENIX PROTOCOL - FIX V5.6 (FINAL FRONTEND FIXES)
// 1. FIX: Corrected typo 'onEdgesChanges' to 'onEdgesChange' (TS2552).
// 2. FIX: Passed 'nodeTypes' directly to ReactFlow.
// 3. FIX: Removed redundant/unused imports (TS6133).

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { 
  ReactFlow, Background, Controls, applyEdgeChanges, applyNodeChanges, addEdge,
  Connection, Edge, Node, OnNodesChange, OnEdgesChange, OnConnect, Panel, MarkerType, useReactFlow,
  ReactFlowProvider, XYPosition
} from '@xyflow/react';
import domtoimage from 'dom-to-image-more';
import '@xyflow/react/dist/style.css';
import axios from 'axios'; 
import { useTranslation } from 'react-i18next';
// PHOENIX FIX: Cleaned up lucide-react imports (TS6133)
import { Save, PlusCircle, Database, Sidebar as SidebarIcon, Download, FileText } from 'lucide-react';
import { ClaimNode, EvidenceNode, MapNodeData } from '../components/evidence-map/Nodes'; // PHOENIX FIX: Cleaned up imports (TS6133)
import Sidebar, { IFilters } from '../components/evidence-map/Sidebar';
import ImportModal from '../components/evidence-map/ImportModal'; 
import RelationshipModal, { RelationshipType } from '../components/evidence-map/RelationshipModal';
import NodeEditModal from '../components/evidence-map/NodeEditModal';
// PHOENIX FIX: Removed unused apiService import (TS6133)
// Removed unused ClaimNode/EvidenceNode (they are only used in nodeTypes object)

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
};

// ... (ExportMap component remains unchanged) ...
interface ExportBounds { x: number; y: number; xMax: number; yMax: number; } 

const ExportMap = () => {
    const { t } = useTranslation();
    const instance = useReactFlow();
    const [isExporting, setIsExporting] = useState(false);

    const calculateNodeBounds = useCallback((): ExportBounds => {
        return instance.getNodes().reduce((bounds, node) => {
            const n = node as (Node & { positionAbsolute?: XYPosition, width?: number, height?: number });
            
            if (n.positionAbsolute && n.width && n.height) {
                bounds.x = Math.min(bounds.x, n.positionAbsolute.x);
                bounds.y = Math.min(bounds.y, n.positionAbsolute.y);
                bounds.xMax = Math.max(bounds.xMax, n.positionAbsolute.x + n.width);
                bounds.yMax = Math.max(bounds.yMax, n.positionAbsolute.y + n.height);
            }
            return bounds;
        }, { x: Infinity, y: Infinity, xMax: -Infinity, yMax: -Infinity } as ExportBounds);
    }, [instance]);


    const handleExport = useCallback(() => {
        setIsExporting(true);
        const viewportElement = document.querySelector('.react-flow__viewport');
        if (!viewportElement) {
            alert(t('export.errorView', "Nuk u gjet elementi kryesor i hartës."));
            setIsExporting(false);
            return;
        }

        const nodesBounds = calculateNodeBounds();

        if (nodesBounds.x === Infinity) {
             alert(t('export.errorEmpty', "Nuk ka asnjë kartelë për të eksportuar."));
             setIsExporting(false);
             return;
        }

        const padding = 50;
        const width = nodesBounds.xMax - nodesBounds.x + 2 * padding;
        const height = nodesBounds.yMax - nodesBounds.y + 2 * padding;
        const x = nodesBounds.x - padding;
        const y = nodesBounds.y - padding;

        domtoimage.toPng(viewportElement as HTMLElement, {
            width: width,
            height: height,
            style: {
                transform: `translate(${-x}px, ${-y}px) scale(1)`,
            },
            quality: 0.95,
            cacheBust: true,
        })
        .then((dataUrl: string) => { 
            const link = document.createElement('a');
            link.download = `EvidenceMap_${new Date().toISOString().slice(0, 10)}.png`;
            link.href = dataUrl;
            link.click();
            setIsExporting(false);
        })
        .catch((error: Error) => { 
            console.error('oops, something went wrong!', error);
            alert(t('export.error', 'Dështoi eksportimi i hartës!'));
            setIsExporting(false);
        });
    }, [calculateNodeBounds, t]);

    return (
        <button onClick={handleExport} disabled={isExporting} className={`flex items-center px-4 py-2 rounded-md text-sm transition-all shadow-lg ${isExporting ? 'bg-gray-600' : 'bg-yellow-600 hover:bg-yellow-700'} text-white`}>
            <Download className={`w-4 h-4 mr-2 ${isExporting ? 'animate-spin' : ''}`} />
            {isExporting ? t('export.exporting', 'Eksportimi...') : t('export.toPNG', 'Eksporto PNG')}
        </button>
    );
};


const EvidenceMapPage = () => {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  if (!caseId) return <div className="p-8 text-red-500">Error: Case ID not found.</div>;

  const [nodes, setNodes] = useState<Node<MapNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  
  const [isSaving, setIsSaving] = useState(false);
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isPdfExporting, setIsPdfExporting] = useState(false);
  
  const [isRelModalOpen, setIsRelModalOpen] = useState(false);
  const [tempConnection, setTempConnection] = useState<Connection | null>(null);

  const [filters, setFilters] = useState<IFilters>({
    hideUnconnected: false,
    highlightContradictions: true,
  });
  const [searchTerm, setSearchTerm] = useState('');

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

  // --- Data Fetching (Unchanged) ---
  useEffect(() => {
    const fetchMap = async () => {
      try {
        const response = await axios.get(`/api/v1/cases/${caseId}/evidence-map`);
        setNodes(response.data.nodes || []);
        setEdges(response.data.edges || []);
      } catch (error) { console.error("Failed to load map:", error); }
    };
    fetchMap();
  }, [caseId]);

  // --- Memoized Logic (Unchanged) ---
  const nodeStats = useMemo(() => {
    const stats: Record<string, { supports: number; contradicts: number }> = {};
    for (const edge of edges) {
      const claimId = edge.target;
      if (!stats[claimId]) {
        stats[claimId] = { supports: 0, contradicts: 0 };
      }
      if (edge.type === 'contradicts') {
        stats[claimId].contradicts += 1;
      } else if (edge.type === 'supports') {
        stats[claimId].supports += 1;
      }
    }
    return stats;
  }, [edges]);

  const displayedNodes = useMemo(() => {
    const connectedNodeIds = new Set(edges.flatMap(e => [e.source, e.target]));
    
    return nodes
      .filter(node => {
        if (filters.hideUnconnected && node.type === 'evidenceNode' && !connectedNodeIds.has(node.id)) {
          return false;
        }
        return true;
      })
      .map(node => {
        const isMatch = searchTerm.length > 1 && node.data.label.toLowerCase().includes(searchTerm.toLowerCase());
        return {
          ...node,
          data: {
            ...node.data,
            stats: node.type === 'claimNode' ? nodeStats[node.id] : undefined,
            isHighlighted: isMatch,
          },
        };
      });
  }, [nodes, edges, filters, searchTerm, nodeStats]);
  
  const displayedEdges = useMemo(() => {
    return edges.map(edge => {
        const labelText = edge.data?.label ? String(edge.data.label) : '';
        const isContradicts = edge.type === 'contradicts';
        const isRelated = edge.type === 'related';
        const isSupports = edge.type === 'supports';
        
        return {
            ...edge,
            label: labelText, 
            style: {
                stroke: isContradicts && filters.highlightContradictions ? '#f87171' : isSupports ? '#4ade80' : '#52525b',
                strokeDasharray: isContradicts ? '5 5' : isRelated ? '2 8' : 'none',
                strokeWidth: isContradicts && filters.highlightContradictions ? 2.5 : 1.5,
            },
            animated: isContradicts && filters.highlightContradictions,
            type: 'default',
        } as Edge;
    });
  }, [edges, filters.highlightContradictions]);


  // --- Node Editing Handler (PHOENIX: Phase 5) ---
  const handleNodeDataSave = useCallback((nodeId: string, newContent: Partial<MapNodeData>) => {
    setNodes(nds => nds.map(n => {
        if (n.id === nodeId) {
            return { ...n, data: { ...n.data, ...newContent, editing: false } };
        }
        return n;
    }));
  }, [setNodes]);

  // --- Event Handlers ---
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
        const selectChange = changes.find((c) => c.type === 'select' && c.selected);
        if (selectChange) { }
        setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]);
    }, 
    [setNodes, nodes]
  );
  
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), 
    [setEdges]
  );
    
  const onConnect: OnConnect = useCallback((connection: Connection) => {
      const targetNode = nodes.find(n => n.id === connection.target);
      const sourceNode = nodes.find(n => n.id === connection.source);
      
      if (sourceNode?.type === 'claimNode' && targetNode?.type === 'evidenceNode') {
          alert(t('relationship.invalidConnection', 'Lidhjet duhet të shkojnë nga Prova tek Pretendimi.'));
          return;
      }
      
      setTempConnection(connection);
      setIsRelModalOpen(true);
    }, [nodes, t]
  );
  
  const handleSaveRelationship = useCallback((type: RelationshipType, strength: number, label: string) => {
      if (!tempConnection) return;
      
      const newEdge: Edge = {
          ...tempConnection,
          id: `e-${tempConnection.source}-${tempConnection.target}-${Date.now()}`,
          type: type, 
          animated: type === 'contradicts',
          markerEnd: { type: MarkerType.ArrowClosed },
          data: { label, strength } 
      };

      setEdges((eds) => addEdge(newEdge, eds));
      setTempConnection(null);
  }, [tempConnection, setEdges]);
  

  const saveMap = async () => {
    setIsSaving(true);
    try {
      await axios.put(`/api/v1/cases/${caseId}/evidence-map`, { nodes, edges, viewport: { x: 0, y: 0, zoom: 1 } });
    } catch (error) { console.error("Failed to save map:", error); } 
    finally { setTimeout(() => setIsSaving(false), 1000); }
  };

  const addNewNode = (type: 'claimNode' | 'evidenceNode', label?: string) => {
    const newNode: Node<MapNodeData> = {
      id: `${type}-${Date.now()}`,
      type,
      position: { x: Math.random() * 400 + 50, y: Math.random() * 400 + 50 },
      data: { 
        label: label || (type === 'claimNode' ? t('evidenceMap.node.newClaim') : t('evidenceMap.node.newEvidence')), 
        content: t('evidenceMap.node.editPlaceholder') 
      },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const handleFilterChange = <K extends keyof IFilters>(key: K, value: IFilters[K]) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleImport = (selectedNames: string[]) => {
    selectedNames.forEach(name => {
        if (!nodes.some(node => node.data.label === name)) {
            addNewNode('evidenceNode', name);
        }
    });
  };

  const handleCloseEditModal = useCallback(() => {
    setNodes(nds => nds.map(n => n.data.editing ? { ...n, data: { ...n.data, editing: false } } : n));
  }, [setNodes]);

  const handleExportPdf = async () => {
      setIsPdfExporting(true);
      try {
          // PHOENIX FIX: Removed unnecessary apiService usage, using direct axios is fine here
          const response = await axios.post(
              `/api/v1/cases/${caseId}/evidence-map/report`, 
              { nodes, edges }, 
              { responseType: 'blob' } 
          );
          
          const blob = new Blob([response.data], { type: 'application/pdf' });
          const url = window.URL.createObjectURL(blob);
          
          // Safely extract filename
          const disposition = response.headers['content-disposition'];
          const filenameMatch = disposition && disposition.match(/filename="?([^"]+)"?/);
          const filename = filenameMatch ? filenameMatch[1] : `EvidenceMap_Report_${caseId}.pdf`;

          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', filename);
          document.body.appendChild(link);
          link.click();
          link.parentNode?.removeChild(link);
          window.URL.revokeObjectURL(url);

      } catch (error) {
          console.error("PDF Export failed:", error);
          alert(t('export.pdfError', 'Dështoi gjenerimi i raportit PDF.'));
      } finally {
          setIsPdfExporting(false);
      }
  };


  return (
      <div className="w-full h-[calc(100vh-64px)] bg-background-dark flex">
        <div className="flex-grow h-full">
            <ReactFlow 
            nodes={displayedNodes} 
            edges={displayedEdges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange} // PHOENIX FIX: Corrected typo 'onEdgesChanges'
            onConnect={onConnect} 
            nodeTypes={nodeTypes} 
            fitView 
            colorMode="dark"
            >
            <Background color="#1e293b" gap={20} />
            <Controls />
            
            {/* LEFT PANEL: Sidebar Toggle */}
            <Panel position="top-left" className="flex gap-2">
                <button onClick={() => setIsSidebarVisible(v => !v)} className="flex items-center p-2 bg-background-light hover:bg-white/10 text-white rounded-md text-sm transition-colors shadow-lg">
                    <SidebarIcon className="w-5 h-5" />
                </button>
            </Panel>
            
            {/* CENTER PANEL: Core Actions */}
            <Panel position="top-center" className="flex gap-2">
                <button onClick={() => addNewNode('claimNode')} className="flex items-center px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm transition-colors shadow-lg">
                <PlusCircle className="w-4 h-4 mr-2" /> {t('evidenceMap.action.addClaim')}
                </button>
                <button onClick={() => addNewNode('evidenceNode')} className="flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors shadow-lg">
                <Database className="w-4 h-4 mr-2" /> {t('evidenceMap.action.addEvidence')}
                </button>
                <button onClick={saveMap} disabled={isSaving} className={`flex items-center px-4 py-2 rounded-md text-sm transition-all shadow-lg ${isSaving ? 'bg-gray-600' : 'bg-primary-start hover:opacity-90'} text-white`}>
                <Save className={`w-4 h-4 mr-2 ${isSaving ? 'animate-spin' : ''}`} />
                {isSaving ? t('evidenceMap.action.saving') : t('evidenceMap.action.save')}
                </button>
                <ExportMap />
                {/* PHOENIX: PDF Export Button */}
                <button onClick={handleExportPdf} disabled={isPdfExporting} className={`flex items-center px-4 py-2 rounded-md text-sm transition-all shadow-lg ${isPdfExporting ? 'bg-gray-600' : 'bg-red-600 hover:bg-red-700'} text-white`}>
                    <FileText className={`w-4 h-4 mr-2 ${isPdfExporting ? 'animate-spin' : ''}`} />
                    {isPdfExporting ? t('export.exporting', 'Eksportimi...') : t('export.toPDF', 'Eksporto PDF')}
                </button>
            </Panel>
            </ReactFlow>
        </div>
      
      {/* RIGHT SIDEBAR: Filters & AI Import */}
      {isSidebarVisible && (
        <Sidebar 
          filters={filters} 
          onFilterChange={handleFilterChange}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          onOpenImportModal={() => setIsImportModalOpen(true)}
        />
      )}

      {/* PHASE 6: AI Import Modal */}
      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImport}
        caseId={caseId}
      />
      
      {/* PHASE 2: Relationship Modal */}
      <RelationshipModal
        isOpen={isRelModalOpen}
        onClose={() => { setIsRelModalOpen(false); setTempConnection(null); }}
        onSave={handleSaveRelationship}
        tempEdge={tempConnection ? { 
            id: 'temp', 
            source: tempConnection.source, 
            target: tempConnection.target,
            data: {} 
        } as Edge : null}
      />
      
      {/* PHASE 5: Node Edit Modal */}
      <NodeEditModal
        isOpen={!!nodeToEdit}
        onClose={handleCloseEditModal}
        node={nodeToEdit || null}
        onSave={handleNodeDataSave}
      />
    </div>
  );
};

const WrappedEvidenceMapPage = () => (
    <ReactFlowProvider>
        <EvidenceMapPage />
    </ReactFlowProvider>
);

export default WrappedEvidenceMapPage;