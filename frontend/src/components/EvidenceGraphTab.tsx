// FILE: frontend/src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - MINI-FOUNDRY EVIDENCE GRAPH TAB V8.0 (UNUSED TIMELINE SLIDER REMOVED)

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { apiService } from '../services/api';
import {
  Network,
  Search,
  RefreshCw,
  User,
  Building2,
  CreditCard,
  MapPin,
  Calendar,
  FileText,
  X,
  ExternalLink,
  ShieldAlert,
  Sparkles,
  Layers,
  ChevronRight,
  Info,
  LucideIcon,
  Download,
  Plus,
  GitMerge,
  Euro,
  AlertTriangle
} from 'lucide-react';

export type EntityType = 'PERSON' | 'ORGANIZATION' | 'ACCOUNT' | 'LOCATION' | 'EVENT' | 'DOCUMENT';

export interface OntologyNode {
  id: string;
  label: string;
  type: EntityType;
  description?: string;
  source_doc_ids?: string[];
  metadata?: Record<string, any>;
}

export interface OntologyEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  amount_eur?: number | null;
  date_iso?: string;
  evidence_text?: string;
  source_doc_ids?: string[];
}

export interface CaseGraphData {
  case_id: string;
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  updated_at?: string | null;
}

export interface CrossCaseMatch {
  case_id: string;
  case_title: string;
  matched_entity: OntologyNode;
  connected_edges: OntologyEdge[];
}

interface EvidenceGraphTabProps {
  caseId: string;
  caseTitle?: string;
}

const ENTITY_CONFIG: Record<EntityType, { albanianLabel: string; color: string; border: string; bg: string; icon: LucideIcon }> = {
  PERSON: { albanianLabel: 'Persona', color: '#3b82f6', border: '#1d4ed8', bg: 'rgba(59, 130, 246, 0.25)', icon: User },
  ORGANIZATION: { albanianLabel: 'Institucione', color: '#8b5cf6', border: '#6d28d9', bg: 'rgba(139, 92, 246, 0.25)', icon: Building2 },
  ACCOUNT: { albanianLabel: 'Llogari', color: '#10b981', border: '#047857', bg: 'rgba(16, 185, 129, 0.25)', icon: CreditCard },
  LOCATION: { albanianLabel: 'Lokacione', color: '#f59e0b', border: '#b45309', bg: 'rgba(245, 158, 11, 0.25)', icon: MapPin },
  EVENT: { albanianLabel: 'Ngjarje', color: '#ef4444', border: '#b91c1c', bg: 'rgba(239, 68, 68, 0.25)', icon: Calendar },
  DOCUMENT: { albanianLabel: 'Dokumente', color: '#64748b', border: '#334155', bg: 'rgba(100, 116, 139, 0.25)', icon: FileText },
};

const RELATION_ALBANIAN_MAP: Record<string, string> = {
  REPRESENTED_BY: 'PËRFAQËSOHET NGA',
  ASSOCIATED_WITH: 'I LIDHUR ME',
  TRANSFERRED_FUNDS: 'TRANSAKSION',
  EMPLOYED_BY: 'I PUNËSUAR NË',
  OWNED_BY: 'PRONËSI E',
  PRESENT_AT: 'I PRANISHËM NË',
  CONTRADICTS: 'KUNDËRTHËNJE',
  OWES_MONEY: 'DETYRIM',
  SIGNED: 'NËNSHKRUAR',
  MENTIONED_IN: 'PËRMENDUR NË'
};

const formatRelationText = (rel: string): string => {
  const clean = rel.toUpperCase().trim().replace(/ /g, '_');
  return RELATION_ALBANIAN_MAP[clean] || clean.replace(/_/g, ' ');
};

export const EvidenceGraphTab: React.FC<EvidenceGraphTabProps> = ({ caseId, caseTitle }) => {
  const [graphData, setGraphData] = useState<CaseGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Selection & Hover State for Focus Dimming
  const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<OntologyEdge | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Filters
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Rebuild & Export State
  const [rebuilding, setRebuilding] = useState<boolean>(false);
  const [rebuildStatus, setRebuildStatus] = useState<string | null>(null);
  const [exporting, setExporting] = useState<boolean>(false);

  // Modals State
  const [mergeModalOpen, setMergeModalOpen] = useState<boolean>(false);
  const [secondaryNodeIdToMerge, setSecondaryNodeIdToMerge] = useState<string>('');
  const [isMerging, setIsMerging] = useState<boolean>(false);

  const [customEdgeModalOpen, setCustomEdgeModalOpen] = useState<boolean>(false);
  const [edgeSourceId, setEdgeSourceId] = useState<string>('');
  const [edgeTargetId, setEdgeTargetId] = useState<string>('');
  const [edgeRelation, setEdgeRelation] = useState<string>('ASSOCIATED_WITH');
  const [edgeEvidenceText, setEdgeEvidenceText] = useState<string>('');
  const [edgeAmountEur, setEdgeAmountEur] = useState<string>('');
  const [isAddingEdge, setIsAddingEdge] = useState<boolean>(false);

  const [crossCaseSearchOpen, setCrossCaseSearchOpen] = useState<boolean>(false);
  const [crossCaseQuery, setCrossCaseQuery] = useState<string>('');
  const [crossCaseResults, setCrossCaseResults] = useState<CrossCaseMatch[]>([]);
  const [crossCaseLoading, setCrossCaseLoading] = useState<boolean>(false);

  // SVG Pan & Zoom (OPTIMAL 1100 x 750 VIEWBOX FOR LARGE CLEAR TEXT)
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [viewBox, setViewBox] = useState({ x: -550, y: -375, width: 1100, height: 750 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPoint, setStartPoint] = useState({ x: 0, y: 0 });

  const fetchGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data: CaseGraphData = await apiService.getCaseGraph(caseId);
      setGraphData(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Gabim gjatë lidhjes me serverin.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) fetchGraph();
  }, [caseId]);

  const handleRebuildGraph = async () => {
    setRebuilding(true);
    setRebuildStatus(null);
    try {
      const result = await apiService.rebuildCaseGraph(caseId);
      setRebuildStatus(result.message);
      setTimeout(() => fetchGraph(), 3000);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Gabim gjatë kërkesës për rindërtim të grafikut.';
      setRebuildStatus(msg);
    } finally {
      setRebuilding(false);
    }
  };

  const handleExportCourtReport = async () => {
    setExporting(true);
    try {
      await apiService.downloadCourtGraphReport(caseId);
    } catch (err) {
      alert('Dështoi eksporti i raportit gjyqësor.');
    } finally {
      setExporting(false);
    }
  };

  const handleExecuteNodeMerge = async () => {
    if (!selectedNode || !secondaryNodeIdToMerge) return;
    setIsMerging(true);
    try {
      await apiService.mergeGraphNodes(caseId, selectedNode.id, secondaryNodeIdToMerge);
      setMergeModalOpen(false);
      setSelectedNode(null);
      await fetchGraph();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Dështoi bashkimi i entiteteve.');
    } finally {
      setIsMerging(false);
    }
  };

  const handleExecuteAddEdge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!edgeSourceId || !edgeTargetId || !edgeRelation) return;
    setIsAddingEdge(true);
    try {
      await apiService.createCustomGraphEdge(caseId, {
        source: edgeSourceId,
        target: edgeTargetId,
        relation: edgeRelation,
        evidence_text: edgeEvidenceText,
        amount_eur: edgeAmountEur ? parseFloat(edgeAmountEur) : undefined,
      });
      setCustomEdgeModalOpen(false);
      setEdgeEvidenceText('');
      setEdgeAmountEur('');
      await fetchGraph();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Dështoi krijimi i lidhjes manuale.');
    } finally {
      setIsAddingEdge(false);
    }
  };

  const handleCrossCaseSearch = async (queryToSearch?: string) => {
    const q = queryToSearch || crossCaseQuery;
    if (!q || q.trim().length < 2) return;
    
    setCrossCaseLoading(true);
    try {
      const data: CrossCaseMatch[] = await apiService.searchFirmGraph(q.trim());
      setCrossCaseResults(data);
    } catch (err) {
      console.error('Cross-case search error:', err);
    } finally {
      setCrossCaseLoading(false);
    }
  };

  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.filter((node) => {
      const matchesType = activeFilter === 'ALL' || node.type === activeFilter;
      const matchesSearch =
        !searchQuery ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (node.description && node.description.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesType && matchesSearch;
    });
  }, [graphData?.nodes, activeFilter, searchQuery]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    return graphData.edges.filter(
      (edge) => filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target)
    );
  }, [graphData?.edges, filteredNodeIds]);

  const activeFocusNodeId = selectedNode?.id || hoveredNodeId;
  const connectedNodeIdsForFocus = useMemo(() => {
    if (!activeFocusNodeId || !graphData?.edges) return new Set<string>();
    const set = new Set<string>([activeFocusNodeId]);
    graphData.edges.forEach((edge) => {
      if (edge.source === activeFocusNodeId) set.add(edge.target);
      if (edge.target === activeFocusNodeId) set.add(edge.source);
    });
    return set;
  }, [activeFocusNodeId, graphData?.edges]);

  const financialTotalsForSelectedNode = useMemo(() => {
    if (!selectedNode || !graphData?.edges) return { inEur: 0, outEur: 0, netEur: 0 };
    let inEur = 0;
    let outEur = 0;

    graphData.edges.forEach((edge) => {
      if (edge.amount_eur && edge.amount_eur > 0) {
        if (edge.target === selectedNode.id) inEur += edge.amount_eur;
        if (edge.source === selectedNode.id) outEur += edge.amount_eur;
      }
    });

    return { inEur, outEur, netEur: inEur - outEur };
  }, [selectedNode, graphData?.edges]);

  // BALANCED ORGANIC LAYOUT (RADIUS STEP 240PX FOR CLEAR LARGE LABELS)
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const nodes = filteredNodes;
    const total = nodes.length;

    if (total === 0) return positions;

    const typeGroups: Record<string, OntologyNode[]> = {};
    nodes.forEach((n) => {
      if (!typeGroups[n.type]) typeGroups[n.type] = [];
      typeGroups[n.type].push(n);
    });

    const groupKeys = Object.keys(typeGroups);
    const radiusStep = 240;

    groupKeys.forEach((typeKey, gIndex) => {
      const groupNodes = typeGroups[typeKey];
      const radius = 180 + gIndex * radiusStep;
      const angleStep = (2 * Math.PI) / groupNodes.length;

      groupNodes.forEach((node, nIndex) => {
        const angle = nIndex * angleStep + (gIndex * Math.PI) / 5;
        positions[node.id] = {
          x: Math.round(radius * Math.cos(angle)),
          y: Math.round(radius * Math.sin(angle)),
        };
      });
    });

    return positions;
  }, [filteredNodes]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === svgRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsPanning(true);
      setStartPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning) return;
    const dx = (e.clientX - startPoint.x) * (viewBox.width / 1100);
    const dy = (e.clientY - startPoint.y) * (viewBox.height / 750);
    setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
    setStartPoint({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => setIsPanning(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
    setViewBox((prev) => ({
      x: prev.x + (prev.width * (1 - zoomFactor)) / 2,
      y: prev.y + (prev.height * (1 - zoomFactor)) / 2,
      width: prev.width * zoomFactor,
      height: prev.height * zoomFactor,
    }));
  };

  const connectedEdgesForSelectedNode = useMemo(() => {
    if (!selectedNode || !graphData?.edges) return [];
    return graphData.edges.filter(
      (e) => e.source === selectedNode.id || e.target === selectedNode.id
    );
  }, [selectedNode, graphData?.edges]);

  return (
    <div className="flex flex-col h-full w-full bg-canvas text-text-primary rounded-2xl border border-main overflow-hidden shadow-xl relative">
      
      {/* SINGLE CONSOLIDATED 1-ROW EXECUTIVE CONTROL BAR */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface border-b border-main gap-2 z-10 shrink-0 h-12">
        
        {/* Left: Badge, Title & Search */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-primary-start/10 border border-primary-start/20 rounded-lg text-primary-start font-black text-[10px] uppercase tracking-wider shrink-0">
            <Network className="w-3.5 h-3.5 text-primary-start" />
            <span className="truncate">{caseTitle || 'Lënda'}</span>
          </div>

          <div className="relative w-36 sm:w-48">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Kërko entitetin..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-canvas border border-main rounded-lg pl-8 pr-2 py-1 text-[11px] text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-primary-start"
            />
          </div>

          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            <button
              onClick={() => setActiveFilter('ALL')}
              className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase transition-all whitespace-nowrap ${
                activeFilter === 'ALL' ? 'bg-primary-start text-white shadow-sm' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              Gjithë ({graphData?.nodes?.length || 0})
            </button>

            {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((type) => {
              const count = graphData?.nodes?.filter((n) => n.type === type).length || 0;
              if (count === 0) return null;
              const conf = ENTITY_CONFIG[type];
              return (
                <button
                  key={type}
                  onClick={() => setActiveFilter(type)}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase transition-all whitespace-nowrap ${
                    activeFilter === type
                      ? 'bg-surface text-text-primary border border-main shadow-sm'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: conf.color }} />
                  <span>{conf.albanianLabel}</span>
                  <span className="font-mono text-text-secondary">({count})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => setCustomEdgeModalOpen(true)}
            className="flex items-center gap-1 px-2.5 py-1 bg-surface hover:bg-hover border border-main text-text-primary rounded-lg text-[10px] font-bold uppercase transition-all"
            title="Krijo lidhje manuale"
          >
            <Plus className="w-3 h-3 text-primary-start" />
            <span className="hidden sm:inline">Lidhje</span>
          </button>

          <button
            onClick={handleExportCourtReport}
            disabled={exporting}
            className="flex items-center gap-1 px-2.5 py-1 bg-surface hover:bg-hover border border-main text-text-primary rounded-lg text-[10px] font-bold uppercase transition-all disabled:opacity-50"
            title="Shkarko raportin"
          >
            <Download className="w-3 h-3 text-primary-start" />
            <span className="hidden sm:inline">{exporting ? 'Eksporton...' : 'Eksporto'}</span>
          </button>

          <button
            onClick={handleRebuildGraph}
            disabled={rebuilding}
            className="flex items-center gap-1 px-3 py-1 bg-primary-start hover:bg-primary-start/90 text-white rounded-lg text-[10px] font-bold uppercase transition-all disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`w-3 h-3 ${rebuilding ? 'animate-spin' : ''}`} />
            <span>{rebuilding ? 'Proceson...' : 'Rirregullo'}</span>
          </button>
        </div>
      </div>

      {/* REBUILD BANNER */}
      {rebuildStatus && (
        <div className="bg-primary-start/10 border-b border-primary-start/30 px-3 py-1 flex items-center justify-between text-[11px] text-primary-start font-medium z-10 shrink-0">
          <div className="flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-primary-start" />
            <span>{rebuildStatus}</span>
          </div>
          <button onClick={() => setRebuildStatus(null)} className="text-primary-start hover:opacity-80">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* GRAPH CANVAS CONTAINER */}
      <div className="flex-1 flex relative overflow-hidden bg-canvas">
        
        {/* SVG GRAPH CANVAS AREA */}
        <div className="flex-1 h-full w-full relative">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted">
              <RefreshCw className="w-8 h-8 animate-spin text-primary-start" />
              <p className="text-xs font-semibold">Po ngarkohet Ontologjia e Provave...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-rose-500">
              <ShieldAlert className="w-8 h-8" />
              <p className="text-xs font-semibold">{error}</p>
              <button onClick={fetchGraph} className="mt-2 text-xs bg-surface border border-main px-3 py-1 rounded-xl text-text-primary font-bold">
                Riprovo Ngarkimin
              </button>
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted p-6 text-center">
              <Layers className="w-12 h-12 text-text-muted/60" />
              <h3 className="text-sm font-bold text-text-primary">Nuk u gjetën entitete të nxjerra në këtë lëndë</h3>
              <p className="text-xs text-text-secondary max-w-md leading-relaxed">
                Klikoni butonin &quot;Rirregullo&quot; më sipër që inteligjenca artificiale të skanojë dokumentet dhe të ndërtojë grafikun.
              </p>
              <button
                onClick={handleRebuildGraph}
                className="mt-2 px-5 py-2 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase shadow-md transition-all"
              >
                Gjenero Grafikun Tani
              </button>
            </div>
          ) : (
            <svg
              ref={svgRef}
              className="w-full h-full cursor-grab active:cursor-grabbing select-none"
              viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onWheel={handleWheel}
            >
              <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="40" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" className="text-text-muted/60" />
                </marker>
                <marker id="arrowhead-selected" markerWidth="10" markerHeight="7" refX="40" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
                </marker>
                <marker id="arrowhead-contradiction" markerWidth="10" markerHeight="7" refX="40" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
                </marker>
              </defs>

              {/* EDGES & ALBANIAN LABELS */}
              <g className="edges">
                {filteredEdges.map((edge, index) => {
                  const sourcePos = nodePositions[edge.source];
                  const targetPos = nodePositions[edge.target];
                  if (!sourcePos || !targetPos) return null;

                  const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');
                  const isSelected = selectedEdge?.id === edge.id;
                  const isConnectedToActiveFocus =
                    activeFocusNodeId && (edge.source === activeFocusNodeId || edge.target === activeFocusNodeId);

                  const dx = targetPos.x - sourcePos.x;
                  const dy = targetPos.y - sourcePos.y;
                  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                  
                  const curveDirection = index % 2 === 0 ? 1 : -1;
                  const curveOffset = Math.min(dist * 0.22, 80) * curveDirection;

                  const midX = (sourcePos.x + targetPos.x) / 2;
                  const midY = (sourcePos.y + targetPos.y) / 2;

                  const ctrlX = midX - (dy / dist) * curveOffset;
                  const ctrlY = midY + (dx / dist) * curveOffset;

                  const pathData = `M ${sourcePos.x} ${sourcePos.y} Q ${ctrlX} ${ctrlY} ${targetPos.x} ${targetPos.y}`;
                  const albanianLabel = formatRelationText(edge.relation);

                  const isDimmed = activeFocusNodeId && !isConnectedToActiveFocus && !isSelected;

                  return (
                    <g
                      key={edge.id}
                      className={`group cursor-pointer transition-opacity duration-300 ${isDimmed ? 'opacity-20' : 'opacity-100'}`}
                      onClick={() => setSelectedEdge(edge)}
                    >
                      <path
                        d={pathData}
                        fill="none"
                        stroke={
                          isContradiction
                            ? '#ef4444'
                            : isSelected || isConnectedToActiveFocus
                            ? '#3b82f6'
                            : 'currentColor'
                        }
                        className={`${
                          isContradiction
                            ? 'animate-pulse'
                            : isSelected || isConnectedToActiveFocus
                            ? ''
                            : 'text-text-muted/40'
                        } transition-all duration-200`}
                        strokeWidth={isContradiction || isSelected || isConnectedToActiveFocus ? 3 : 1.5}
                        strokeDasharray={isContradiction ? '6,6' : 'none'}
                        markerEnd={
                          isContradiction
                            ? 'url(#arrowhead-contradiction)'
                            : isSelected || isConnectedToActiveFocus
                            ? 'url(#arrowhead-selected)'
                            : 'url(#arrowhead)'
                        }
                      />

                      {/* HIGH-CONTRAST EXPANDED BADGE (130px x 26px) */}
                      <rect
                        x={ctrlX - 65}
                        y={ctrlY - 13}
                        width="130"
                        height="26"
                        rx="7"
                        fill={isContradiction ? '#450a0a' : 'var(--bg-surface, #ffffff)'}
                        stroke={isContradiction ? '#ef4444' : isSelected ? '#3b82f6' : 'currentColor'}
                        className={isContradiction ? '' : isSelected ? '' : 'text-main'}
                        strokeWidth="1.5"
                      />
                      <text
                        x={ctrlX}
                        y={ctrlY + 4}
                        textAnchor="middle"
                        fill={isContradiction ? '#fca5a5' : isSelected ? '#3b82f6' : 'currentColor'}
                        className={isContradiction ? 'font-black' : isSelected ? 'font-black' : 'text-text-muted font-bold'}
                        fontSize="12"
                      >
                        {edge.amount_eur
                          ? `€${edge.amount_eur.toLocaleString()}`
                          : albanianLabel.length > 16
                          ? `${albanianLabel.substring(0, 14)}..`
                          : albanianLabel}
                      </text>
                    </g>
                  );
                })}
              </g>

              {/* ENLARGED ENTITY NODES (28PX RADIUS & 14PX BOLD TEXT) */}
              <g className="nodes">
                {filteredNodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;

                  const config = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
                  const isSelected = selectedNode?.id === node.id;
                  const isConnectedToFocus = connectedNodeIdsForFocus.has(node.id);
                  const isDimmed = activeFocusNodeId && !isConnectedToFocus;
                  const Icon = config.icon;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      className={`cursor-pointer group transition-opacity duration-300 ${
                        isDimmed ? 'opacity-20' : 'opacity-100'
                      }`}
                      onMouseEnter={() => setHoveredNodeId(node.id)}
                      onMouseLeave={() => setHoveredNodeId(null)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNode(node);
                        setSelectedEdge(null);
                      }}
                    >
                      {isSelected && (
                        <circle
                          r="38"
                          fill="none"
                          stroke="#3b82f6"
                          strokeWidth="3"
                          className="animate-pulse"
                        />
                      )}

                      <circle
                        r="28"
                        fill={config.bg}
                        stroke={isSelected ? '#3b82f6' : config.color}
                        strokeWidth={isSelected ? '3.5' : '2.5'}
                        className="transition-all duration-200 group-hover:scale-110 shadow-xl"
                      />

                      <foreignObject x="-14" y="-14" width="28" height="28" className="pointer-events-none">
                        <div className="w-full h-full flex items-center justify-center">
                          <Icon className="w-6 h-6" style={{ color: config.color }} />
                        </div>
                      </foreignObject>

                      {/* CLEAR LARGE 14PX BOLD NODE TEXT */}
                      <text
                        y="48"
                        textAnchor="middle"
                        fill="currentColor"
                        fontSize="14"
                        fontWeight="bold"
                        className="text-text-primary pointer-events-none drop-shadow-md"
                      >
                        {node.label.length > 22 ? `${node.label.substring(0, 20)}...` : node.label}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
        </div>

        {/* RIGHT DRAWER: ENTITY INSPECTOR */}
        {(selectedNode || selectedEdge) && (
          <div className="w-80 bg-surface border-l border-main p-4 overflow-y-auto flex flex-col gap-4 z-20 shadow-2xl animate-in slide-in-from-right duration-200 shrink-0">
            
            <div className="flex items-center justify-between border-b border-main pb-3">
              <span className="text-xs font-bold text-primary-start uppercase tracking-wider">
                {selectedNode ? 'Inspektori i Entitetit' : 'Inspektori i Lidhjes'}
              </span>
              <button
                onClick={() => {
                  setSelectedNode(null);
                  setSelectedEdge(null);
                }}
                className="p-1 text-text-muted hover:text-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {selectedNode && (
              <>
                <div className="flex items-start gap-3">
                  <div
                    className="p-2.5 rounded-xl border shrink-0"
                    style={{
                      backgroundColor: ENTITY_CONFIG[selectedNode.type].bg,
                      borderColor: ENTITY_CONFIG[selectedNode.type].color,
                    }}
                  >
                    {React.createElement(ENTITY_CONFIG[selectedNode.type].icon, {
                      className: 'w-6 h-6',
                      style: { color: ENTITY_CONFIG[selectedNode.type].color },
                    })}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-text-primary">{selectedNode.label}</h4>
                    <span
                      className="inline-block mt-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase"
                      style={{
                        backgroundColor: ENTITY_CONFIG[selectedNode.type].bg,
                        color: ENTITY_CONFIG[selectedNode.type].color,
                      }}
                    >
                      {ENTITY_CONFIG[selectedNode.type].albanianLabel}
                    </span>
                  </div>
                </div>

                {(financialTotalsForSelectedNode.inEur > 0 || financialTotalsForSelectedNode.outEur > 0) && (
                  <div className="bg-canvas p-3 rounded-xl border border-main text-xs flex flex-col gap-1.5 shadow-sm">
                    <span className="text-[10px] font-black text-primary-start uppercase tracking-wider flex items-center gap-1">
                      <Euro size={12} /> Bilanct e Transaksioneve
                    </span>
                    <div className="flex justify-between text-emerald-600 font-bold">
                      <span>Të Pranuara:</span>
                      <span>+€{financialTotalsForSelectedNode.inEur.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-rose-500 font-bold">
                      <span>Të Paguara:</span>
                      <span>-€{financialTotalsForSelectedNode.outEur.toLocaleString()}</span>
                    </div>
                    <div className="border-t border-main pt-1 flex justify-between font-black text-text-primary">
                      <span>Neto:</span>
                      <span>€{financialTotalsForSelectedNode.netEur.toLocaleString()}</span>
                    </div>
                  </div>
                )}

                {selectedNode.description && (
                  <div className="bg-canvas p-3 rounded-xl border border-main text-xs text-text-secondary leading-relaxed">
                    <span className="text-[10px] font-bold text-text-muted uppercase block mb-1">Roli / Konteksti Ligjor</span>
                    {selectedNode.description}
                  </div>
                )}

                <div>
                  <span className="text-[10px] font-bold text-text-muted uppercase block mb-2">
                    Lidhjet e Dokumentuara ({connectedEdgesForSelectedNode.length})
                  </span>
                  <div className="flex flex-col gap-2">
                    {connectedEdgesForSelectedNode.map((e) => {
                      const isContradiction = e.relation.includes('CONTRADICT') || e.relation.includes('KUNDËR');
                      return (
                        <div
                          key={e.id}
                          onClick={() => setSelectedEdge(e)}
                          className={`p-3 rounded-xl border cursor-pointer text-xs flex flex-col gap-1 transition-all ${
                            isContradiction
                              ? 'bg-rose-500/10 border-rose-500/40 hover:bg-rose-500/20'
                              : 'bg-canvas border-main hover:border-primary-start'
                          }`}
                        >
                          <div className="flex items-center justify-between font-bold text-[11px]">
                            <span className={isContradiction ? 'text-rose-500 flex items-center gap-1' : 'text-text-primary'}>
                              {isContradiction && <AlertTriangle size={12} />}
                              {formatRelationText(e.relation)}
                            </span>
                            <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
                          </div>
                          {e.evidence_text && (
                            <p className="text-[11px] text-text-secondary italic line-clamp-2">&quot;{e.evidence_text}&quot;</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="flex flex-col gap-2 mt-2">
                  <button
                    onClick={() => setMergeModalOpen(true)}
                    className="w-full py-2 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase flex items-center justify-center gap-2 transition-all shadow-sm"
                  >
                    <GitMerge size={14} className="text-primary-start" />
                    <span>Bashko Entitetin</span>
                  </button>

                  <button
                    onClick={() => {
                      setCrossCaseQuery(selectedNode.label);
                      setCrossCaseSearchOpen(true);
                      handleCrossCaseSearch(selectedNode.label);
                    }}
                    className="w-full py-2 bg-purple-600/10 hover:bg-purple-600/20 text-purple-600 border border-purple-500/30 rounded-xl text-xs font-bold uppercase flex items-center justify-center gap-2 transition-all"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Kërko në lëndët tjera</span>
                  </button>
                </div>
              </>
            )}

            {selectedEdge && (
              <>
                <div className={`p-3 rounded-xl border flex flex-col gap-1 ${
                  selectedEdge.relation.includes('CONTRADICT') ? 'bg-rose-500/10 border-rose-500/30' : 'bg-canvas border-main'
                }`}>
                  <span className="text-[10px] font-bold text-text-muted uppercase">Lidhja Ligjore</span>
                  <span className="font-bold text-sm text-primary-start">{formatRelationText(selectedEdge.relation)}</span>
                  {selectedEdge.amount_eur && (
                    <span className="text-xs font-mono font-bold text-emerald-600">Shuma: €{selectedEdge.amount_eur.toLocaleString()}</span>
                  )}
                </div>

                {selectedEdge.evidence_text && (
                  <div className="bg-canvas p-3 rounded-xl border border-main text-xs text-text-secondary leading-relaxed">
                    <span className="text-[10px] font-bold text-text-muted uppercase block mb-1">Prova nga Teksti</span>
                    <p className="italic text-text-primary">&quot;{selectedEdge.evidence_text}&quot;</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* MERGE NODE MODAL */}
      {mergeModalOpen && selectedNode && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-surface border border-main rounded-3xl w-full max-w-md p-6 flex flex-col gap-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-main pb-3">
              <div className="flex items-center gap-2 text-primary-start">
                <GitMerge size={20} />
                <h3 className="font-bold text-text-primary text-sm uppercase">Bashko Entitetin</h3>
              </div>
              <button onClick={() => setMergeModalOpen(false)} className="text-text-muted hover:text-text-primary">
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Zgjidhni entitetin dytësor që dëshironi ta bashkoni brenda kryesorit <strong className="text-text-primary">&quot;{selectedNode.label}&quot;</strong>.
            </p>

            <select
              value={secondaryNodeIdToMerge}
              onChange={(e) => setSecondaryNodeIdToMerge(e.target.value)}
              className="w-full p-2.5 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
            >
              <option value="">-- Zgjidh entitetin për ta shkrirë --</option>
              {graphData?.nodes
                .filter((n) => n.id !== selectedNode.id)
                .map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.label} ({n.type})
                  </option>
                ))}
            </select>

            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setMergeModalOpen(false)} className="px-4 py-2 rounded-xl text-xs font-bold border border-main text-text-secondary hover:bg-hover">
                Anulo
              </button>
              <button
                onClick={handleExecuteNodeMerge}
                disabled={!secondaryNodeIdToMerge || isMerging}
                className="px-5 py-2 rounded-xl text-xs font-bold uppercase bg-primary-start text-white shadow-md hover:bg-primary-start/90 disabled:opacity-50"
              >
                {isMerging ? 'Duke bashkuar...' : 'Bashko Tani'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CUSTOM EDGE MODAL */}
      {customEdgeModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <form onSubmit={handleExecuteAddEdge} className="bg-surface border border-main rounded-3xl w-full max-w-lg p-6 flex flex-col gap-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-main pb-3">
              <div className="flex items-center gap-2 text-primary-start">
                <Plus size={20} />
                <h3 className="font-bold text-text-primary text-sm uppercase">Shto Lidhje Manuale</h3>
              </div>
              <button type="button" onClick={() => setCustomEdgeModalOpen(false)} className="text-text-muted hover:text-text-primary">
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-bold text-text-muted uppercase block mb-1">Entiteti Burim</label>
                <select
                  value={edgeSourceId}
                  onChange={(e) => setEdgeSourceId(e.target.value)}
                  className="w-full p-2.5 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none"
                  required
                >
                  <option value="">-- Zgjidh Burimin --</option>
                  {graphData?.nodes.map((n) => (
                    <option key={n.id} value={n.id}>{n.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-text-muted uppercase block mb-1">Entiteti Synim</label>
                <select
                  value={edgeTargetId}
                  onChange={(e) => setEdgeTargetId(e.target.value)}
                  className="w-full p-2.5 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none"
                  required
                >
                  <option value="">-- Zgjidh Synimin --</option>
                  {graphData?.nodes.map((n) => (
                    <option key={n.id} value={n.id}>{n.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-bold text-text-muted uppercase block mb-1">Tipi i Marëdhënies</label>
                <select
                  value={edgeRelation}
                  onChange={(e) => setEdgeRelation(e.target.value)}
                  className="w-full p-2.5 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none font-bold"
                >
                  <option value="TRANSFERRED_FUNDS">TRANSAKSION FINANCIAR</option>
                  <option value="CONTRADICTS">KUNDËRTHËNJE</option>
                  <option value="ASSOCIATED_WITH">I LIDHUR ME</option>
                  <option value="EMPLOYED_BY">I PUNËSUAR NË</option>
                  <option value="OWNED_BY">PRONËSI E</option>
                  <option value="REPRESENTED_BY">PËRFAQËSOHET NGA</option>
                  <option value="OWES_MONEY">DETYRIM FINANCIAR</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-text-muted uppercase block mb-1">Shuma në Euro (€)</label>
                <input
                  type="number"
                  placeholder="p.sh. 15000"
                  value={edgeAmountEur}
                  onChange={(e) => setEdgeAmountEur(e.target.value)}
                  className="w-full p-2.5 bg-canvas border border-main rounded-xl text-xs font-mono text-text-primary focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] font-bold text-text-muted uppercase block mb-1">Citat nga Prova (Evidence Text)</label>
              <textarea
                placeholder="Shkruaj citatin apo shënimin mbrojtës nga dokumenti..."
                value={edgeEvidenceText}
                onChange={(e) => setEdgeEvidenceText(e.target.value)}
                rows={2}
                className="w-full p-2.5 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setCustomEdgeModalOpen(false)} className="px-4 py-2 rounded-xl text-xs font-bold border border-main text-text-secondary hover:bg-hover">
                Anulo
              </button>
              <button
                type="submit"
                disabled={isAddingEdge}
                className="px-5 py-2 rounded-xl text-xs font-bold uppercase bg-primary-start text-white shadow-md hover:bg-primary-start/90 disabled:opacity-50"
              >
                {isAddingEdge ? 'Duke ruajtur...' : 'Ruaj Lidhjen'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* CROSS-CASE SEARCH MODAL */}
      {crossCaseSearchOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden shadow-2xl animate-in zoom-in-95 text-slate-900 dark:text-slate-100">
            
            <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
              <div className="flex items-center gap-2.5 text-purple-600 dark:text-purple-400">
                <Sparkles className="w-5 h-5" />
                <h3 className="font-extrabold text-slate-900 dark:text-slate-100 text-sm uppercase tracking-wider">
                  Inteligjenca e Ndërsjellë e Zyrës
                </h3>
              </div>
              <button onClick={() => setCrossCaseSearchOpen(false)} className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 bg-slate-100/70 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <input
                type="text"
                placeholder="Shkruaj emrin e dëshmitarit, kompanisë ose llogarisë bankare..."
                value={crossCaseQuery}
                onChange={(e) => setCrossCaseQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCrossCaseSearch()}
                className="flex-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-sm"
              />
              <button
                onClick={() => handleCrossCaseSearch()}
                disabled={crossCaseLoading}
                className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-extrabold uppercase tracking-wider transition-all disabled:opacity-50 shadow-md"
              >
                {crossCaseLoading ? 'Kërkon...' : 'Kërko'}
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
              {crossCaseLoading ? (
                <div className="flex justify-center p-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-purple-600 dark:text-purple-400" />
                </div>
              ) : crossCaseResults.length === 0 ? (
                <div className="text-center p-8 flex flex-col items-center gap-2">
                  <Search className="w-8 h-8 text-slate-300 dark:text-slate-600 mb-1" />
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 max-w-sm">
                    Nuk u gjetën përputhje ndër-lëndore për këtë kërkim në arkivin e zyrës suaj.
                  </p>
                </div>
              ) : (
                crossCaseResults.map((match, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-50 dark:bg-slate-950 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col gap-2 shadow-sm"
                  >
                    <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                      <span className="text-xs font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        Lënda: {match.case_title}
                      </span>
                      <a
                        href={`/cases/${match.case_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-purple-600 dark:text-purple-400 hover:underline flex items-center gap-1 font-bold"
                      >
                        Hap Lëndën <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        {match.matched_entity.label}
                      </span>
                      <span className="px-2 py-0.5 rounded-md text-[9px] font-bold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 uppercase">
                        {ENTITY_CONFIG[match.matched_entity.type]?.albanianLabel || match.matched_entity.type}
                      </span>
                    </div>

                    {match.matched_entity.description && (
                      <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                        {match.matched_entity.description}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EvidenceGraphTab;