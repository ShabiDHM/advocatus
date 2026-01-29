// FILE: frontend/src/pages/EvidenceMapPage.tsx
// PHOENIX PROTOCOL - FIX V11.2 (DESKTOP UX POLISH)
// 1. UI: Un-colored the toolbar buttons. They now use a unified "Glass/Dark" background.
// 2. UI: Used colored text/icons (Yellow for PNG, Red for PDF) to maintain visual cues without the "Fruit Salad" effect.
// 3. UI: Increased the backdrop-blur for the desktop toolbar to look more premium.

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { 
  ReactFlow, Background, Controls, applyEdgeChanges, applyNodeChanges,
  Edge, Node, OnNodesChange, OnEdgesChange, Panel, useReactFlow,
  ReactFlowProvider, XYPosition
} from '@xyflow/react';
import domtoimage from 'dom-to-image-more';
import '@xyflow/react/dist/style.css';
import axios from 'axios'; 
import { useTranslation } from 'react-i18next';
import { Save, Sidebar as SidebarIcon, Download, FileText, BrainCircuit } from 'lucide-react';
import { ClaimNode, EvidenceNode, MapNodeData } from '../components/evidence-map/Nodes';
import Sidebar, { IFilters } from '../components/evidence-map/Sidebar';
import ImportModal from '../components/evidence-map/ImportModal'; 
import NodeEditModal from '../components/evidence-map/NodeEditModal';

const nodeTypes = {
  claimNode: ClaimNode,
  evidenceNode: EvidenceNode,
};

interface ExportBounds { x: number; y: number; xMax: number; yMax: number; } 

interface GraphNode {
  id: string;
  name: string;
  group: string;
  description?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

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
            style: { transform: `translate(${-x}px, ${-y}px) scale(1)` },
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
            console.error('Export error:', error);
            alert(t('export.error', 'Dështoi eksportimi i hartës!'));
            setIsExporting(false);
        });
    }, [calculateNodeBounds, t]);

    return (
        <button 
            onClick={handleExport} 
            disabled={isExporting} 
            // PHOENIX POLISH: Unified dark button, yellow text for visual cue
            className={`group flex items-center justify-center p-2 sm:px-5 sm:py-2.5 rounded-xl text-sm transition-all shadow-lg text-yellow-500 bg-white/5 hover:bg-white/10 border border-white/10 active:scale-95 font-semibold ${isExporting ? 'opacity-50' : ''}`}
            title={t('export.toPNG')}
        >
            <Download className={`w-5 h-5 sm:mr-2 ${isExporting ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isExporting ? t('export.exporting') : t('export.toPNG')}</span>
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

  const [filters, setFilters] = useState<IFilters>({
    hideUnconnected: false,
    highlightContradictions: true,
  });
  const [searchTerm, setSearchTerm] = useState('');

  const nodeToEdit = useMemo(() => nodes.find(n => n.data.editing), [nodes]);

  useEffect(() => {
    const handleResize = () => {
        if (window.innerWidth >= 768) setIsSidebarVisible(true);
        else setIsSidebarVisible(false);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
    (changes) => {
        setNodes((nds) => applyNodeChanges(changes, nds) as Node<MapNodeData>[]);
    }, 
    [setNodes]
  );
  
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), 
    [setEdges]
  );

  const saveMap = async () => {
    setIsSaving(true);
    try {
      await axios.put(`/api/v1/cases/${caseId}/evidence-map`, { nodes, edges, viewport: { x: 0, y: 0, zoom: 1 } });
    } catch (error) { console.error("Failed to save map:", error); } 
    finally { setTimeout(() => setIsSaving(false), 1000); }
  };

  const handleFilterChange = <K extends keyof IFilters>(key: K, value: IFilters[K]) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleImport = (importedNodes: GraphNode[], importedEdges: GraphEdge[]) => {
    const newReactNodes: Node<MapNodeData>[] = [];
    const startX = Math.random() * 200 + 100;
    const startY = Math.random() * 200 + 100;

    importedNodes.forEach((node, index) => {
        if (nodes.some(n => n.id === node.id || n.data.label === node.name)) return;

        const isClaim = node.group === 'CLAIM';
        
        let content = node.description || "";
        if (node.group && node.group !== 'CLAIM' && node.group !== 'EVIDENCE') {
            content = `[${node.group}] ${content}`;
        } else if (!content) {
            content = t('evidenceMap.node.editPlaceholder');
        }

        const newNode: Node<MapNodeData> = {
            id: node.id,
            type: isClaim ? 'claimNode' : 'evidenceNode',
            position: { 
                x: startX + (index % 3) * 250, 
                y: startY + Math.floor(index / 3) * 150 
            },
            data: {
                label: node.name,
                content: content,
                isProven: isClaim ? false : undefined, 
                isAuthenticated: node.group === 'EVIDENCE' ? false : undefined,
                exhibitNumber: node.group === 'EVIDENCE' ? 'Auto-Import' : undefined
            }
        };
        newReactNodes.push(newNode);
    });

    const newReactEdges: Edge[] = importedEdges.map(edge => ({
        id: `e-${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        type: 'default',
        animated: true,
        style: { stroke: edge.label === 'KONTRADIKTON' ? '#f87171' : '#4ade80' },
        data: { label: edge.label } 
    }));

    setNodes(nds => [...nds, ...newReactNodes]);
    setEdges(eds => [...eds, ...newReactEdges]);
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
          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', `EvidenceMap_Report_${caseId}.pdf`);
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
      } catch (error) {
          alert(t('export.pdfError', 'Dështoi gjenerimi i raportit PDF.'));
      } finally {
          setIsPdfExporting(false);
      }
  };


  return (
      <div className="w-full h-[calc(100vh-64px)] bg-background-dark flex relative overflow-hidden">
        <div className="flex-grow h-full relative z-0">
            <ReactFlow 
            nodes={displayedNodes} 
            edges={displayedEdges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange} 
            nodeTypes={nodeTypes} 
            fitView 
            colorMode="dark"
            >
            <Background color="#1e293b" gap={20} />
            <Controls showInteractive={false} className="hidden sm:block" /> 
            
            {/* 1. SIDEBAR TOGGLE: Top Right */}
            <Panel position="top-right" className="flex gap-2 m-4">
                <button 
                    onClick={() => setIsSidebarVisible(v => !v)} 
                    className="flex items-center justify-center w-12 h-12 bg-background-light/90 backdrop-blur-md hover:bg-white/10 text-white rounded-full transition-all shadow-xl border border-white/10 active:scale-95"
                >
                    <SidebarIcon className="w-6 h-6" />
                </button>
            </Panel>
            
            {/* 2. DESKTOP ACTION BAR - PHOENIX POLISHED */}
            <Panel position="top-center" className="hidden sm:flex justify-center w-full px-2 mt-4 pointer-events-none">
                <div className="flex flex-row items-center gap-2 bg-black/60 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl pointer-events-auto">
                    {/* Primary AI Button - Remains Gradient */}
                    <button onClick={() => setIsImportModalOpen(true)} className="flex items-center px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white rounded-xl text-sm transition-transform active:scale-95 shadow-lg border border-white/10 font-bold">
                        <BrainCircuit className="w-5 h-5 mr-2" /> {t('evidenceMap.sidebar.importButton', 'Gjenero Hartën (AI)')}
                    </button>
                    
                    <div className="w-px h-8 bg-white/10 mx-1"></div>

                    {/* Secondary Buttons - Unified Glass Style with Color Accents */}
                    <button onClick={saveMap} disabled={isSaving} className={`flex items-center px-5 py-2.5 rounded-xl text-sm transition-all shadow-lg text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 active:scale-95 font-semibold ${isSaving ? 'opacity-50' : ''}`}>
                        <Save className={`w-5 h-5 mr-2 ${isSaving ? 'animate-spin' : ''}`} /> {isSaving ? t('evidenceMap.action.saving') : t('evidenceMap.action.save')}
                    </button>
                    
                    <ExportMap />

                    <button onClick={handleExportPdf} disabled={isPdfExporting} className={`flex items-center px-5 py-2.5 rounded-xl text-sm transition-all shadow-lg text-red-500 bg-white/5 hover:bg-white/10 border border-white/10 active:scale-95 font-semibold ${isPdfExporting ? 'opacity-50' : ''}`}>
                        <FileText className={`w-5 h-5 mr-2 ${isPdfExporting ? 'animate-spin' : ''}`} /> PDF
                    </button>
                </div>
            </Panel>

            {/* 3. MOBILE FLOATING DOCK (Unchanged from V10.5) */}
            <Panel position="bottom-center" className="flex sm:hidden justify-center w-full pb-8 pointer-events-none z-10">
                 <div className="flex flex-row items-center gap-4 bg-black/80 backdrop-blur-xl px-6 py-4 rounded-full border border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.5)] pointer-events-auto">
                    
                    <button onClick={() => setIsImportModalOpen(true)} className="group flex items-center justify-center w-14 h-14 bg-gradient-to-r from-primary-start to-primary-end rounded-full text-white shadow-xl border border-white/20 active:scale-90 transition-transform">
                        <BrainCircuit className="w-7 h-7" />
                    </button>

                    <div className="w-px h-10 bg-white/20"></div>

                    <button onClick={saveMap} disabled={isSaving} className="flex items-center justify-center w-12 h-12 bg-gray-700 hover:bg-gray-600 rounded-full text-white shadow-lg active:scale-90 transition-transform">
                        <Save className={`w-6 h-6 ${isSaving ? 'animate-spin' : ''}`} />
                    </button>
                    
                    <div className="flex items-center justify-center w-12 h-12 rounded-full active:scale-90 transition-transform">
                        <ExportMap />
                    </div>

                     <button onClick={handleExportPdf} disabled={isPdfExporting} className="flex items-center justify-center w-12 h-12 bg-red-600 hover:bg-red-500 rounded-full text-white shadow-lg active:scale-90 transition-transform">
                        <FileText className={`w-6 h-6 ${isPdfExporting ? 'animate-spin' : ''}`} />
                    </button>
                 </div>
            </Panel>
            </ReactFlow>
        </div>
      
        {/* RESPONSIVE DRAWER */}
        <div className={`absolute top-0 right-0 z-40 h-full w-full sm:w-80 transition-transform duration-300 transform ${isSidebarVisible ? 'translate-x-0' : 'translate-x-full'}`}>
            <Sidebar 
                filters={filters} 
                onFilterChange={handleFilterChange}
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                onOpenImportModal={() => setIsImportModalOpen(true)}
                onClose={() => setIsSidebarVisible(false)}
            />
        </div>

        {/* Mobile Overlay */}
        {isSidebarVisible && (
            <div 
                className="fixed inset-0 bg-black/60 backdrop-blur-sm md:hidden z-30" 
                onClick={() => setIsSidebarVisible(false)} 
            />
        )}

        <ImportModal
            isOpen={isImportModalOpen}
            onClose={() => setIsImportModalOpen(false)}
            onImport={handleImport}
            caseId={caseId}
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