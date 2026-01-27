// FILE: frontend/src/pages/EvidenceMapPage.tsx (FINAL COMPLETE REPLACEMENT)
// PHOENIX PROTOCOL - FIX V9.0 (INSTANT CONNECTIONS UX)
// 1. FIXED: onConnect now instantly creates the edge so the line "sticks" upon release.
// 2. ADDED: onEdgeDoubleClick handler so users can edit the relationship type (Supports/Contradicts) later.
// 3. FIXED: RelationshipModal save logic now updates the existing edge instead of creating a duplicate.

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
import { Save, PlusCircle, Database, Sidebar as SidebarIcon, Download, FileText } from 'lucide-react';
import { ClaimNode, EvidenceNode, MapNodeData } from '../components/evidence-map/Nodes';
import Sidebar, { IFilters } from '../components/evidence-map/Sidebar';
import ImportModal from '../components/evidence-map/ImportModal'; 
import RelationshipModal, { RelationshipType } from '../components/evidence-map/RelationshipModal';
import NodeEditModal from '../components/evidence-map/NodeEditModal';

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
};

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
  // PHOENIX FIX: Allow TempConnection to hold full Edge objects for editing
  const [tempConnection, setTempConnection] = useState<Connection | Edge | null>(null);

  const [filters, setFilters] = useState<IFilters>({
    hideUnconnected: false,
    highlightContradictions: true,
  });
  const [searchTerm, setSearchTerm] = useState('');

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

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

  const handleNodeDataSave = useCallback((nodeId: string, newContent: Partial<MapNodeData>) => {
    setNodes(nds => nds.map(n => {
        if (n.id === nodeId) {
            return { ...n, data: { ...n.data, ...newContent, editing: false } };
        }
        return n;
    }));
  }, [setNodes]);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]), 
    [setNodes]
  );
  
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), 
    [setEdges]
  );
    
  // PHOENIX FIX: Instant Connection Logic
  const onConnect: OnConnect = useCallback((connection: Connection) => {
      const targetNode = nodes.find(n => n.id === connection.target);
      const sourceNode = nodes.find(n => n.id === connection.source);
      
      if (sourceNode?.type === 'claimNode' && targetNode?.type === 'evidenceNode') {
          alert(t('relationship.invalidConnection', 'Lidhjet duhet të shkojnë nga Prova tek Pretendimi.'));
          return;
      }
      
      // 1. Instantly create the Edge so the line sticks immediately.
      const newEdge: Edge = {
          ...connection,
          id: `e-${connection.source}-${connection.target}-${Date.now()}`,
          type: 'supports', // Default to supporting evidence
          markerEnd: { type: MarkerType.ArrowClosed },
          data: { label: '', strength: 5 } 
      };

      setEdges((eds) => addEdge(newEdge, eds));
    }, [nodes, t, setEdges]
  );

  // PHOENIX FIX: Open Modal on Double-Clicking the Line
  const onEdgeDoubleClick = useCallback((event: React.MouseEvent, edge: Edge) => {
      event.preventDefault();
      setTempConnection(edge);
      setIsRelModalOpen(true);
  }, []);
  
  // PHOENIX FIX: Modal Save now UPDATES the existing line instead of adding a new one
  const handleSaveRelationship = useCallback((type: RelationshipType, strength: number, label: string) => {
      if (!tempConnection) return;
      
      const existingEdgeId = (tempConnection as Edge).id;

      setEdges((eds) => eds.map(e => {
          if (e.id === existingEdgeId) {
              return {
                  ...e,
                  type: type, 
                  animated: type === 'contradicts',
                  data: { ...e.data, label, strength }
              };
          }
          return e;
      }));

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
          const response = await axios.post(
              `/api/v1/cases/${caseId}/evidence-map/report`, 
              { nodes, edges }, 
              { responseType: 'blob' } 
          );
          
          const blob = new Blob([response.data], { type: 'application/pdf' });
          const url = window.URL.createObjectURL(blob);
          
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
      <div className="w-full h-[calc(100vh-64px)] bg-background-dark flex relative">
        <div className="flex-grow h-full">
            <ReactFlow 
            nodes={displayedNodes} 
            edges={displayedEdges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange} 
            onConnect={onConnect} 
            onEdgeDoubleClick={onEdgeDoubleClick} // PHOENIX FIX: Added double click handler
            nodeTypes={nodeTypes} 
            fitView 
            colorMode="dark"
            >
            <Background color="#1e293b" gap={20} />
            <Controls />
            
            <Panel position="top-left" className="flex gap-2">
                <button onClick={() => setIsSidebarVisible(v => !v)} className="flex items-center p-2 bg-background-light hover:bg-white/10 text-white rounded-md text-sm transition-colors shadow-lg">
                    <SidebarIcon className="w-5 h-5" />
                </button>
            </Panel>
            
            <Panel position="top-center" className="flex flex-wrap gap-2">
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
                <button onClick={handleExportPdf} disabled={isPdfExporting} className={`flex items-center px-4 py-2 rounded-md text-sm transition-all shadow-lg ${isPdfExporting ? 'bg-gray-600' : 'bg-red-600 hover:bg-red-700'} text-white`}>
                    <FileText className={`w-4 h-4 mr-2 ${isPdfExporting ? 'animate-spin' : ''}`} />
                    {isPdfExporting ? t('export.exporting', 'Eksportimi...') : t('export.toPDF', 'Eksporto PDF')}
                </button>
            </Panel>
            </ReactFlow>
        </div>
      
      <div className={`transition-transform duration-300 md:w-auto ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}`}>
        {isSidebarVisible && (
        <Sidebar 
          filters={filters} 
          onFilterChange={handleFilterChange}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          onOpenImportModal={() => setIsImportModalOpen(true)}
          onClose={() => setIsSidebarVisible(false)} 
        />
        )}
      </div>

      {isSidebarVisible && <div className="fixed inset-0 bg-black/50 md:hidden z-30" onClick={() => setIsSidebarVisible(false)} />}

      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImport}
        caseId={caseId}
      />
      
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