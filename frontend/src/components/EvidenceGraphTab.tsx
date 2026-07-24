// FILE: frontend/src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - MINI-FOUNDRY EVIDENCE GRAPH TAB V2.6 (TOP FLOATING SCROLLABLE LEGEND)

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
  LucideIcon
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
  PERSON: { albanianLabel: 'Persona / Palë', color: '#3b82f6', border: '#1d4ed8', bg: 'rgba(59, 130, 246, 0.15)', icon: User },
  ORGANIZATION: { albanianLabel: 'Kompani / Institucione', color: '#8b5cf6', border: '#6d28d9', bg: 'rgba(139, 92, 246, 0.15)', icon: Building2 },
  ACCOUNT: { albanianLabel: 'Llogari Bankare / IBAN', color: '#10b981', border: '#047857', bg: 'rgba(16, 185, 129, 0.15)', icon: CreditCard },
  LOCATION: { albanianLabel: 'Lokacione / Adresa', color: '#f59e0b', border: '#b45309', bg: 'rgba(245, 158, 11, 0.15)', icon: MapPin },
  EVENT: { albanianLabel: 'Ngjarje / Seanca', color: '#ef4444', border: '#b91c1c', bg: 'rgba(239, 68, 68, 0.15)', icon: Calendar },
  DOCUMENT: { albanianLabel: 'Dokumente / Kontrata', color: '#64748b', border: '#334155', bg: 'rgba(100, 116, 139, 0.15)', icon: FileText },
};

export const EvidenceGraphTab: React.FC<EvidenceGraphTabProps> = ({ caseId, caseTitle }) => {
  const [graphData, setGraphData] = useState<CaseGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<OntologyEdge | null>(null);

  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [rebuilding, setRebuilding] = useState<boolean>(false);
  const [rebuildStatus, setRebuildStatus] = useState<string | null>(null);

  const [crossCaseSearchOpen, setCrossCaseSearchOpen] = useState<boolean>(false);
  const [crossCaseQuery, setCrossCaseQuery] = useState<string>('');
  const [crossCaseResults, setCrossCaseResults] = useState<CrossCaseMatch[]>([]);
  const [crossCaseLoading, setCrossCaseLoading] = useState<boolean>(false);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const [viewBox, setViewBox] = useState({ x: -400, y: -300, width: 800, height: 600 });
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
    const radiusStep = 180;

    groupKeys.forEach((typeKey, gIndex) => {
      const groupNodes = typeGroups[typeKey];
      const radius = 120 + gIndex * radiusStep;
      const angleStep = (2 * Math.PI) / groupNodes.length;

      groupNodes.forEach((node, nIndex) => {
        const angle = nIndex * angleStep + (gIndex * Math.PI) / 4;
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
    const dx = (e.clientX - startPoint.x) * (viewBox.width / 800);
    const dy = (e.clientY - startPoint.y) * (viewBox.height / 600);
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
    <div className="flex flex-col h-[calc(100vh-200px)] min-h-[500px] bg-canvas text-text-primary rounded-2xl border border-main overflow-hidden shadow-xl relative">
      
      {/* TOP CONTROL BAR */}
      <div className="flex flex-wrap items-center justify-between p-3 bg-surface border-b border-main gap-3 z-10">
        
        {/* Left: Title & Case Badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-primary-start/10 border border-primary-start/30 rounded-xl text-primary-start font-bold text-xs uppercase tracking-wider">
            <Network className="w-4 h-4 text-primary-start" />
            <span>Ontologjia</span>
            {caseTitle && <span className="text-text-muted font-normal">| {caseTitle}</span>}
          </div>

          <div className="relative w-56">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Kërko personin, kompaninë..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-canvas border border-main rounded-xl pl-9 pr-3 py-1.5 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-primary-start"
            />
          </div>
        </div>

        {/* Center: Entity Filter Pills */}
        <div className="flex items-center gap-1 bg-canvas p-1 rounded-xl border border-main overflow-x-auto">
          <button
            onClick={() => setActiveFilter('ALL')}
            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
              activeFilter === 'ALL' ? 'bg-primary-start text-white shadow' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Të gjitha ({graphData?.nodes?.length || 0})
          </button>
          
          {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((type) => {
            const count = graphData?.nodes?.filter((n) => n.type === type).length || 0;
            if (count === 0) return null;
            const conf = ENTITY_CONFIG[type];
            const ConfigIcon = conf.icon;
            return (
              <button
                key={type}
                onClick={() => setActiveFilter(type)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  activeFilter === type
                    ? 'bg-surface text-text-primary border border-main shadow'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                <ConfigIcon className="w-3.5 h-3.5" style={{ color: conf.color }} />
                <span>{conf.albanianLabel}</span>
                <span className="px-1.5 py-0.2 bg-canvas text-[10px] rounded-full text-text-secondary font-mono">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setCrossCaseSearchOpen(true);
              if (selectedNode) {
                setCrossCaseQuery(selectedNode.label);
                handleCrossCaseSearch(selectedNode.label);
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600/10 hover:bg-purple-600/20 text-purple-600 border border-purple-500/30 rounded-xl text-xs font-bold uppercase transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Kërkim në Zyrë</span>
          </button>

          <button
            onClick={handleRebuildGraph}
            disabled={rebuilding}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase transition-all disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            <span>{rebuilding ? 'Proceson...' : 'Rirregullo Grafikun'}</span>
          </button>
        </div>
      </div>

      {/* REBUILD NOTIFICATION BANNER */}
      {rebuildStatus && (
        <div className="bg-primary-start/10 border-b border-primary-start/30 px-4 py-2 flex items-center justify-between text-xs text-primary-start font-medium z-10">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-primary-start" />
            <span>{rebuildStatus}</span>
          </div>
          <button onClick={() => setRebuildStatus(null)} className="text-primary-start hover:opacity-80">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* GRAPH CANVAS CONTAINER */}
      <div className="flex-1 flex relative overflow-hidden bg-canvas">
        
        {/* TOP FLOATING SCROLLABLE LEGEND BAR (PERMANENTLY VISIBLE & SCROLLABLE) */}
        <div className="absolute top-3 left-4 right-4 bg-surface/95 backdrop-blur-md border border-main px-4 py-2 rounded-xl text-xs text-text-primary flex items-center justify-between gap-3 shadow-md z-20 overflow-x-auto custom-finance-scroll pointer-events-auto">
          <span className="text-[10px] font-black text-text-muted uppercase tracking-wider shrink-0">
            Kategoritë e Ontologjisë:
          </span>
          <div className="flex items-center gap-x-5 gap-y-1 shrink-0">
            {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((type) => {
              const conf = ENTITY_CONFIG[type];
              return (
                <div key={type} className="flex items-center gap-1.5 text-[11px] font-medium shrink-0">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: conf.color }} />
                  <span className="text-text-secondary whitespace-nowrap">{conf.albanianLabel}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* SVG GRAPH CANVAS AREA */}
        <div className="flex-1 h-full w-full relative pt-14">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted">
              <RefreshCw className="w-8 h-8 animate-spin text-primary-start" />
              <p className="text-sm font-semibold">Po ngarkohet Ontologjia e Provave...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-rose-500">
              <ShieldAlert className="w-8 h-8" />
              <p className="text-sm font-semibold">{error}</p>
              <button onClick={fetchGraph} className="mt-2 text-xs bg-surface border border-main px-3 py-1.5 rounded-xl text-text-primary hover:bg-hover font-bold">
                Riprovo Ngarkimin
              </button>
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted p-6 text-center">
              <Layers className="w-12 h-12 text-text-muted/60" />
              <h3 className="text-base font-bold text-text-primary">Nuk u gjetën entitete të nxjerra në këtë lëndë</h3>
              <p className="text-xs text-text-secondary max-w-md leading-relaxed">
                Klikoni butonin &quot;Rirregullo Grafikun&quot; më sipër që inteligjenca artificiale të skanojë të gjitha dokumentet e lëndës dhe të ndërtojë grafikun e provave.
              </p>
              <button
                onClick={handleRebuildGraph}
                className="mt-2 px-5 py-2.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase shadow-md transition-all"
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
                <marker
                  id="arrowhead"
                  markerWidth="10"
                  markerHeight="7"
                  refX="28"
                  refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" className="text-text-muted/60" />
                </marker>
                <marker
                  id="arrowhead-selected"
                  markerWidth="10"
                  markerHeight="7"
                  refX="28"
                  refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
                </marker>
              </defs>

              <g className="edges">
                {filteredEdges.map((edge) => {
                  const sourcePos = nodePositions[edge.source];
                  const targetPos = nodePositions[edge.target];
                  if (!sourcePos || !targetPos) return null;

                  const isSelected = selectedEdge?.id === edge.id;
                  const isConnectedToSelectedNode =
                    selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id);

                  const midX = (sourcePos.x + targetPos.x) / 2;
                  const midY = (sourcePos.y + targetPos.y) / 2;

                  return (
                    <g key={edge.id} className="group cursor-pointer" onClick={() => setSelectedEdge(edge)}>
                      <line
                        x1={sourcePos.x}
                        y1={sourcePos.y}
                        x2={targetPos.x}
                        y2={targetPos.y}
                        stroke={isSelected || isConnectedToSelectedNode ? '#3b82f6' : 'currentColor'}
                        className={`${isSelected || isConnectedToSelectedNode ? '' : 'text-text-muted/40'} transition-all duration-200`}
                        strokeWidth={isSelected || isConnectedToSelectedNode ? 2.5 : 1.2}
                        strokeDasharray={edge.relation.includes('CONTRADICT') ? '4,4' : 'none'}
                        markerEnd={isSelected || isConnectedToSelectedNode ? 'url(#arrowhead-selected)' : 'url(#arrowhead)'}
                      />
                      <rect
                        x={midX - 35}
                        y={midY - 10}
                        width="70"
                        height="16"
                        rx="4"
                        fill="var(--bg-surface, #ffffff)"
                        stroke={isSelected ? '#3b82f6' : 'currentColor'}
                        className={isSelected ? '' : 'text-main'}
                        strokeWidth="1"
                      />
                      <text
                        x={midX}
                        y={midY + 2}
                        textAnchor="middle"
                        fill={isSelected ? '#3b82f6' : 'currentColor'}
                        className={isSelected ? '' : 'text-text-muted'}
                        fontSize="8"
                        fontWeight="bold"
                      >
                        {edge.relation.length > 12 ? `${edge.relation.substring(0, 10)}..` : edge.relation}
                      </text>
                    </g>
                  );
                })}
              </g>

              <g className="nodes">
                {filteredNodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;

                  const config = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
                  const isSelected = selectedNode?.id === node.id;
                  const Icon = config.icon;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      className="cursor-pointer group"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNode(node);
                        setSelectedEdge(null);
                      }}
                    >
                      {isSelected && (
                        <circle
                          r="28"
                          fill="none"
                          stroke="#3b82f6"
                          strokeWidth="2.5"
                          className="animate-pulse"
                        />
                      )}

                      <circle
                        r="20"
                        fill={config.bg}
                        stroke={isSelected ? '#3b82f6' : config.color}
                        strokeWidth={isSelected ? '3' : '2'}
                        className="transition-all duration-200 group-hover:scale-110"
                      />

                      <foreignObject x="-10" y="-10" width="20" height="20" className="pointer-events-none">
                        <div className="w-full h-full flex items-center justify-center">
                          <Icon className="w-4 h-4" style={{ color: config.color }} />
                        </div>
                      </foreignObject>

                      <text
                        y="34"
                        textAnchor="middle"
                        fill="currentColor"
                        className="text-text-primary text-[10px] font-semibold pointer-events-none"
                      >
                        {node.label.length > 18 ? `${node.label.substring(0, 16)}...` : node.label}
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
          <div className="w-80 bg-surface border-l border-main p-4 overflow-y-auto flex flex-col gap-4 z-20 shadow-2xl animate-in slide-in-from-right duration-200">
            
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

                {selectedNode.description && (
                  <div className="bg-canvas p-3 rounded-xl border border-main text-xs text-text-secondary leading-relaxed">
                    <span className="text-[10px] font-bold text-text-muted uppercase block mb-1">Roli / Konteksti Ligjor</span>
                    {selectedNode.description}
                  </div>
                )}

                {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                  <div className="bg-canvas p-3 rounded-xl border border-main text-xs flex flex-col gap-1.5">
                    <span className="text-[10px] font-bold text-text-muted uppercase block">Meta-të dhënat</span>
                    {Object.entries(selectedNode.metadata).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-text-secondary">
                        <span className="text-text-muted capitalize">{k}:</span>
                        <span className="font-mono text-text-primary">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div>
                  <span className="text-[10px] font-bold text-text-muted uppercase block mb-2">
                    Lidhjet e Dokumentuara ({connectedEdgesForSelectedNode.length})
                  </span>
                  <div className="flex flex-col gap-2">
                    {connectedEdgesForSelectedNode.map((e) => (
                      <div
                        key={e.id}
                        onClick={() => setSelectedEdge(e)}
                        className="bg-canvas p-3 rounded-xl border border-main hover:border-primary-start cursor-pointer text-xs flex flex-col gap-1 transition-all"
                      >
                        <div className="flex items-center justify-between text-text-primary font-bold text-[11px]">
                          <span>{e.relation}</span>
                          <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
                        </div>
                        {e.evidence_text && (
                          <p className="text-[11px] text-text-secondary italic line-clamp-2">&quot;{e.evidence_text}&quot;</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => {
                    setCrossCaseQuery(selectedNode.label);
                    setCrossCaseSearchOpen(true);
                    handleCrossCaseSearch(selectedNode.label);
                  }}
                  className="w-full mt-2 py-2.5 bg-purple-600/10 hover:bg-purple-600/20 text-purple-600 border border-purple-500/30 rounded-xl text-xs font-bold uppercase flex items-center justify-center gap-2 transition-all"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Kërko &quot;{selectedNode.label}&quot; në lëndët tjera</span>
                </button>
              </>
            )}

            {selectedEdge && (
              <>
                <div className="bg-canvas p-3 rounded-xl border border-main flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-text-muted uppercase">Lidhja Ligjore</span>
                  <span className="font-bold text-sm text-primary-start">{selectedEdge.relation}</span>
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
              <button
                onClick={() => setCrossCaseSearchOpen(false)}
                className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
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