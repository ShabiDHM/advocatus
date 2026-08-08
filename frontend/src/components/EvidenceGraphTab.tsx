// FILE: src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - EVIDENCE GRAPH TAB V65.0 (AUTO-SAVE PDF REPORT TO CASE ARCHIVE)

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { apiService } from '../services/api';
import { translateToAlbanian, formatRelationText } from '../utils/albanianLegalTranslator';
import { ChevronRight, Link2, Shield, AlertTriangle, Swords, Scale, Gavel } from 'lucide-react';

import {
  OntologyNode,
  OntologyEdge,
  CaseGraphData,
  ChatMsg,
  EvidenceGraphTabProps,
  ENTITY_CONFIG,
} from './graph/graphTypes';
import { GraphToolbar } from './graph/GraphToolbar';
import { EvidenceCanvas } from './graph/EvidenceCanvas';
import { EvidenceTooltip } from './graph/EvidenceTooltip';
import { EvidenceInspector } from './graph/EvidenceInspector';
import { EntityChatDrawer } from './graph/EntityChatDrawer';

export const EvidenceGraphTab: React.FC<EvidenceGraphTabProps> = ({ caseId }) => {
  const [graphData, setGraphData] = useState<CaseGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [clientPosition, setClientPosition] = useState<'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'>('DEFENDANT');

  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [mobileTab, setMobileTab] = useState<'entities' | 'timeline' | 'graph'>('entities');

  const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<OntologyEdge | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<OntologyEdge | null>(null);

  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 100, y: 100 });

  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [simplifiedView, setSimplifiedView] = useState<boolean>(false);

  const [rebuilding, setRebuilding] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);

  const [entityChatOpen, setEntityChatOpen] = useState<boolean>(false);
  const [chatEntity, setChatEntity] = useState<OntologyNode | null>(null);
  const [entityMessages, setEntityMessages] = useState<ChatMsg[]>([]);
  const [inputQuestion, setInputQuestion] = useState<string>('');
  const [isSending, setIsSending] = useState<boolean>(false);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [viewBox, setViewBox] = useState({ x: -500, y: -300, width: 1000, height: 600 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPoint, setStartPoint] = useState({ x: 0, y: 0 });
  const touchDistRef = useRef<number | null>(null);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchGraphAndCaseDetails = async () => {
    setLoading(true);
    try {
      const [gData, cDetails] = await Promise.all([
        apiService.getCaseGraph(caseId),
        apiService.getCaseDetails(caseId),
      ]);
      setGraphData(gData);
      const pos = (cDetails as any)?.client_position || 'DEFENDANT';
      setClientPosition(pos === 'PLAINTIFF' ? 'PLAINTIFF' : pos === 'NEUTRAL' ? 'NEUTRAL' : 'DEFENDANT');
    } catch (err) {
      console.error('Failed to load graph data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) fetchGraphAndCaseDetails();
  }, [caseId]);

  useEffect(() => {
    if (loading) return;
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const zoomFactor = e.deltaY > 0 ? 1.12 : 0.88;
      setViewBox((prev) => ({
        x: Math.round(prev.x + (prev.width * (1 - zoomFactor)) / 2),
        y: Math.round(prev.y + (prev.height * (1 - zoomFactor)) / 2),
        width: Math.round(Math.max(400, Math.min(5000, prev.width * zoomFactor))),
        height: Math.round(Math.max(250, Math.min(3500, prev.height * zoomFactor))),
      }));
    };

    svgEl.addEventListener('wheel', handleWheel, { passive: false });
    return () => svgEl.removeEventListener('wheel', handleWheel);
  }, [loading]);

  useEffect(() => {
    chatScrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entityMessages, isSending]);

  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    let base = graphData.nodes.filter((node) => {
      const matchesType = activeFilter === 'ALL' || node.type === activeFilter;
      const matchesSearch =
        !searchQuery ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (node.description && node.description.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesType && matchesSearch;
    });

    if (simplifiedView && !searchQuery && activeFilter === 'ALL' && base.length > 4) {
      const edgeCounts = new Map<string, number>();
      graphData.edges.forEach((e) => {
        edgeCounts.set(e.source, (edgeCounts.get(e.source) || 0) + 1);
        edgeCounts.set(e.target, (edgeCounts.get(e.target) || 0) + 1);
      });
      base = base.sort((a, b) => (edgeCounts.get(b.id) || 0) - (edgeCounts.get(a.id) || 0)).slice(0, 4);
    }
    return base;
  }, [graphData?.nodes, graphData?.edges, activeFilter, searchQuery, simplifiedView]);

  const { connectedNodeIds, connectedEdgeIds } = useMemo(() => {
    const activeNode = selectedNode;
    const activeEdge = hoveredEdge || selectedEdge;

    if (!activeNode && !activeEdge) {
      return { connectedNodeIds: new Set<string>(), connectedEdgeIds: new Set<string>() };
    }

    const nodeSet = new Set<string>();
    const edgeSet = new Set<string>();

    if (activeNode) {
      nodeSet.add(activeNode.id);
      graphData?.edges.forEach((e) => {
        if (e.source === activeNode.id || e.target === activeNode.id) {
          edgeSet.add(e.id);
          nodeSet.add(e.source);
          nodeSet.add(e.target);
        }
      });
    }

    if (activeEdge) {
      edgeSet.add(activeEdge.id);
      nodeSet.add(activeEdge.source);
      nodeSet.add(activeEdge.target);
    }

    return { connectedNodeIds: nodeSet, connectedEdgeIds: edgeSet };
  }, [selectedNode, hoveredEdge, selectedEdge, graphData?.edges]);

  const timelineItems = useMemo(() => {
    if (!graphData?.edges) return [];
    const items: Array<{
      id: string;
      title: string;
      date?: string;
      sourceLabel: string;
      targetLabel: string;
      evidence?: string;
      amount?: number | null;
      isContradiction: boolean;
      rawEdge: OntologyEdge;
    }> = [];

    const nMap = new Map<string, OntologyNode>();
    graphData.nodes?.forEach((n) => nMap.set(n.id, n));

    graphData.edges.forEach((edge) => {
      const src = nMap.get(edge.source);
      const tgt = nMap.get(edge.target);
      const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');

      items.push({
        id: edge.id,
        title: formatRelationText(edge.relation),
        date: edge.date_iso || undefined,
        sourceLabel: translateToAlbanian(src?.label) || 'Burimi',
        targetLabel: translateToAlbanian(tgt?.label) || 'Caku',
        evidence: translateToAlbanian(edge.evidence_text),
        amount: edge.amount_eur,
        isContradiction,
        rawEdge: edge,
      });
    });

    return items.sort((a, b) => (a.date && b.date ? a.date.localeCompare(b.date) : a.isContradiction ? -1 : 0));
  }, [graphData?.edges, graphData?.nodes]);

  useEffect(() => {
    if (filteredNodes.length === 0) return;
    const initialPos: Record<string, { x: number; y: number }> = {};
    
    const colKeys = ['PERSON', 'ORGANIZATION', 'ACCOUNT', 'DOCUMENT', 'EVENT'];
    const activeColumns: Record<string, OntologyNode[]> = {};

    filteredNodes.forEach((node) => {
      let key = 'EVENT';
      if (node.type === 'PERSON') key = 'PERSON';
      else if (node.type === 'ORGANIZATION') key = 'ORGANIZATION';
      else if (node.type === 'ACCOUNT' || node.type === 'LOCATION') key = 'ACCOUNT';
      else if (node.type === 'DOCUMENT') key = 'DOCUMENT';

      if (!activeColumns[key]) activeColumns[key] = [];
      activeColumns[key].push(node);
    });

    const presentKeys = colKeys.filter(k => activeColumns[k] && activeColumns[k].length > 0);
    const numActiveCols = presentKeys.length;

    const colSpacing = numActiveCols <= 2 ? 800 : numActiveCols === 3 ? 650 : 500;
    const startX = -((numActiveCols - 1) * colSpacing) / 2;

    presentKeys.forEach((key, colIdx) => {
      const nodesInCol = activeColumns[key];
      const xPos = Math.round(startX + colIdx * colSpacing);
      const startY = -((nodesInCol.length - 1) * 160) / 2;

      nodesInCol.forEach((n, idx) => {
        initialPos[n.id] = { x: xPos, y: Math.round(startY + idx * 160) };
      });
    });

    setPositions(initialPos);

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    Object.values(initialPos).forEach((p) => {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    });

    const cardW = 240;
    const cardH = 62;

    const contentW = Math.round((maxX - minX) + cardW + 280);
    const contentH = Math.round((maxY - minY) + cardH + 220);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    setViewBox({
      x: Math.round(centerX - contentW / 2),
      y: Math.round(centerY - contentH / 2),
      width: Math.max(600, contentW),
      height: Math.max(400, contentH),
    });
  }, [filteredNodes]);

  const handleZoomIn = () => setViewBox((prev) => ({ ...prev, x: Math.round(prev.x + prev.width * 0.09), y: Math.round(prev.y + prev.height * 0.09), width: Math.round(prev.width * 0.82), height: Math.round(prev.height * 0.82) }));
  const handleZoomOut = () => setViewBox((prev) => ({ ...prev, x: Math.round(prev.x - prev.width * 0.09), y: Math.round(prev.y - prev.height * 0.09), width: Math.round(prev.width * 1.18), height: Math.round(prev.height * 1.18) }));
  const handleResetZoom = () => { setSelectedNode(null); setSelectedEdge(null); setHoveredEdge(null); };

  const handleRebuildGraph = async () => {
    setRebuilding(true);
    try {
      await apiService.rebuildCaseGraph(caseId);
      setTimeout(() => fetchGraphAndCaseDetails(), 3000);
    } catch (err) {
      console.error('Rebuild failed:', err);
    } finally {
      setRebuilding(false);
    }
  };

  const handleExportCourtReport = async () => {
    setExporting(true);
    try {
      const result = await apiService.downloadCourtGraphReport(caseId);
      alert(`✅ ${result?.message || 'Raporti PDF i Ontologjisë u ruajt me sukses në Arkivin e Lëndës!'}`);
    } catch (err) {
      console.error('Export error:', err);
      alert('Dështoi ruajtja e raportit në arkiv.');
    } finally {
      setExporting(false);
    }
  };

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);
  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    return graphData.edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [graphData?.edges, filteredNodeIds]);

  const connectedEdgesForSelectedNode = useMemo(() => {
    if (!selectedNode || !graphData?.edges) return [];
    return graphData.edges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id);
  }, [selectedNode, graphData?.edges]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, OntologyNode>();
    graphData?.nodes?.forEach((n) => map.set(n.id, n));
    return map;
  }, [graphData?.nodes]);

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

  const getSVGPoint = (clientX: number, clientY: number) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const pt = svgRef.current.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const transformed = pt.matrixTransform(svgRef.current.getScreenCTM()?.inverse());
    return { x: transformed.x, y: transformed.y };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (draggedNodeId) return;
    if (e.target === svgRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsPanning(true);
      setStartPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setTooltipPos({ x: Math.round(e.clientX - rect.left), y: Math.round(e.clientY - rect.top) });
    }

    if (draggedNodeId) {
      const point = getSVGPoint(e.clientX, e.clientY);
      setPositions((prev) => ({ ...prev, [draggedNodeId]: { x: Math.round(point.x), y: Math.round(point.y) } }));
      return;
    }

    if (isPanning) {
      const dx = (e.clientX - startPoint.x) * (viewBox.width / 2400);
      const dy = (e.clientY - startPoint.y) * (viewBox.height / 1500);
      setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
      setStartPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      touchDistRef.current = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    } else if (e.touches.length === 1 && !draggedNodeId) {
      setIsPanning(true);
      setStartPoint({ x: e.touches[0].clientX, y: e.touches[0].clientY });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (containerRef.current && e.touches.length > 0) {
      const rect = containerRef.current.getBoundingClientRect();
      setTooltipPos({ x: Math.round(e.touches[0].clientX - rect.left), y: Math.round(e.touches[0].clientY - rect.top) });
    }

    if (e.touches.length === 2 && touchDistRef.current !== null) {
      const newDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      if (newDist > 0 && touchDistRef.current > 0) {
        const zoomFactor = touchDistRef.current / newDist;
        setViewBox((prev) => ({ ...prev, x: Math.round(prev.x + (prev.width * (1 - zoomFactor)) / 2), y: Math.round(prev.y + (prev.height * (1 - zoomFactor)) / 2), width: Math.round(Math.max(500, Math.min(6000, prev.width * zoomFactor))), height: Math.round(Math.max(300, Math.min(4000, prev.height * zoomFactor))) }));
      }
      touchDistRef.current = newDist;
    } else if (e.touches.length === 1 && isPanning) {
      const dx = (e.touches[0].clientX - startPoint.x) * (viewBox.width / 2400);
      const dy = (e.touches[0].clientY - startPoint.y) * (viewBox.height / 1500);
      setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
      setStartPoint({ x: e.touches[0].clientX, y: e.touches[0].clientY });
    }
  };

  const handleOpenEntityChat = (node: OntologyNode) => {
    setChatEntity(node);
    setEntityMessages([]);
    setEntityChatOpen(true);
  };

  const handleSendEntityQuestion = async (customPrompt?: string) => {
    const q = customPrompt || inputQuestion.trim();
    if (!q || isSending || !chatEntity) return;

    setEntityMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content: q },
      { id: (Date.now() + 1).toString(), role: 'ai', content: '' },
    ]);
    if (!customPrompt) setInputQuestion('');
    setIsSending(true);

    try {
      const fullPrompt = `Lidhja me Entitetin: "${chatEntity.label}" (${chatEntity.type}).\nPyetja e Avokatit: ${q}`;
      const stream = apiService.sendChatMessageStream(caseId, fullPrompt, undefined, 'ks', 'FAST');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setEntityMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: acc };
          return copy;
        });
      }
    } catch {
      setEntityMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: '[Gabim gjatë marrjes së përgjigjes.]' };
        return copy;
      });
    } finally {
      setIsSending(false);
    }
  };

  const entitySuggestedCards = useMemo(() => {
    if (!chatEntity) return [];
    if (clientPosition === 'DEFENDANT') {
      return [
        { badge: '🛡️ STRATEGJIA E MBROJTJES', title: 'RRËZIMI I PRETENDIMEVE', desc: `Si mund ta përdorim entitetin ${chatEntity.label} për të prapësuar padinë dhe mbrojtur klientin?`, query: `Si i paditur, si mund ta përdorim entitetin ${chatEntity.label} për të rrëzuar pretendimet e paditësit dhe forcuar mbrojtjen tonë?`, icon: Shield },
        { badge: '⚔️ GODITJA E KUNDËRSHTARIT', title: 'HETIMI I MOSPËRPUTHJEVE', desc: `Identifiko çdo kontradiktë apo dobësi procedurale që lidhet me ${chatEntity.label}.`, query: `Identifiko çdo mospërputhje, kontradiktë apo dobësi ligjore te ${chatEntity.label} që do të prapësonte kërkesëpadinë.`, icon: AlertTriangle }
      ];
    } else if (clientPosition === 'PLAINTIFF') {
      return [
        { badge: '⚔️ FORCIMI I PADISË', title: 'PROVA E PËRGJEGJËSISË', desc: `Si i vërteton ${chatEntity.label} shkeljet dhe dëmin e kërkuar nga ne?`, query: `Si paditës, si i provon ${chatEntity.label} përgjegjësinë dhe dëmin e shkaktuar nga pala tjetër?`, icon: Swords },
        { badge: '⚖️ BAZA LIGJORE & DETYRIMI', title: 'KRONOLOGJIA E SHKELJES', desc: `Marrja e dëshmive dhe detyrimeve financiare që ngarkojnë ${chatEntity.label}.`, query: `Nxirr të gjitha dëshmitë, transaksionet dhe afatet që e ngarkojnë me përgjegjësi ${chatEntity.label}.`, icon: Scale }
      ];
    }
    return [
      { badge: '⚖️ ANALIZË NEUTRALE', title: 'VLERËSIMI I BARRËS SË PROVËS', desc: `Vlerëso në mënyrë objektive peshën e provave që lidhen me ${chatEntity.label}.`, query: `Si një auditor i paanshëm, vlerëso barrën e provës dhe rëndësinë e entitetit ${chatEntity.label} për të dyja palët.`, icon: Scale },
      { badge: '🔍 AUDITI PROCEDURAL', title: 'SINTEZA E RASTIT', desc: `Përmbledhje paanshme e fakteve dhe kornizës ligjore për ${chatEntity.label}.`, query: `Jep një përmbledhje të paanshme dhe objektive të fakteve ligjore për ${chatEntity.label}.`, icon: Gavel }
    ];
  }, [chatEntity, clientPosition]);

  const isFocusMode = selectedNode !== null || hoveredEdge !== null || selectedEdge !== null;

  return (
    <div className="flex flex-col h-full w-full bg-canvas text-text-primary rounded-2xl border border-main overflow-hidden shadow-xl relative font-sans select-none">
      <GraphToolbar
        simplifiedView={simplifiedView}
        onToggleSimplified={() => setSimplifiedView(!simplifiedView)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        nodes={graphData?.nodes || []}
        filteredCount={filteredNodes.length}
        onExportCourtReport={handleExportCourtReport}
        exporting={exporting}
        onRebuildGraph={handleRebuildGraph}
        rebuilding={rebuilding}
        isMobile={isMobile}
        mobileTab={mobileTab}
        onMobileTabChange={setMobileTab}
        timelineCount={timelineItems.length}
      />

      <div ref={containerRef} className="flex-1 flex relative overflow-hidden bg-canvas" onMouseMove={handleMouseMove}>
        {isMobile && mobileTab === 'entities' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-finance-scroll">
            {filteredNodes.map((node) => {
              const conf = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
              const IconComp = conf.icon;
              return (
                <div key={node.id} onClick={() => setSelectedNode(node)} className="p-4 bg-surface border border-main rounded-2xl cursor-pointer flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white" style={{ backgroundColor: conf.bg }}>
                        <IconComp size={20} />
                      </div>
                      <div>
                        <h4 className="text-sm font-black text-text-primary">{translateToAlbanian(node.label)}</h4>
                        <span className="text-[10px] font-bold uppercase" style={{ color: conf.border }}>{conf.albanianLabel}</span>
                      </div>
                    </div>
                    <ChevronRight size={16} className="text-text-muted" />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {isMobile && mobileTab === 'timeline' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-finance-scroll">
            <div className="relative border-l-2 border-main ml-4 space-y-4 pl-6">
              {timelineItems.map((item) => (
                <div key={item.id} onClick={() => setSelectedEdge(item.rawEdge)} className="p-3 bg-surface border border-main rounded-2xl cursor-pointer">
                  <span className="text-xs font-black text-primary-start uppercase">{item.title}</span>
                  <div className="text-xs font-bold text-text-primary my-1 flex items-center gap-1">
                    <span>{item.sourceLabel}</span> <Link2 size={12} /> <span>{item.targetLabel}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(!isMobile || mobileTab === 'graph') && (
          <EvidenceCanvas
            loading={loading}
            svgRef={svgRef}
            viewBox={viewBox}
            positions={positions}
            filteredNodes={filteredNodes}
            filteredEdges={filteredEdges}
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            hoveredEdge={hoveredEdge}
            connectedNodeIds={connectedNodeIds}
            connectedEdgeIds={connectedEdgeIds}
            isFocusMode={isFocusMode}
            onSelectNode={(node) => { setSelectedNode(node); setSelectedEdge(null); }}
            onSelectEdge={(edge) => { setSelectedEdge(edge); setSelectedNode(null); }}
            onHoverEdge={setHoveredEdge}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={() => { setIsPanning(false); setDraggedNodeId(null); }}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={() => { touchDistRef.current = null; setIsPanning(false); setDraggedNodeId(null); }}
            onNodeDragStart={setDraggedNodeId}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onResetZoom={handleResetZoom}
          />
        )}

        <EvidenceTooltip hoveredEdge={hoveredEdge} tooltipPos={tooltipPos} nodeMap={nodeMap} />

        <EvidenceInspector
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onClose={() => { setSelectedNode(null); setSelectedEdge(null); }}
          nodeMap={nodeMap}
          financialTotals={financialTotalsForSelectedNode}
          connectedEdges={connectedEdgesForSelectedNode}
          onSelectEdge={(edge) => { setSelectedEdge(edge); setSelectedNode(null); }}
          onOpenEntityChat={handleOpenEntityChat}
        />
      </div>

      <EntityChatDrawer
        isOpen={entityChatOpen}
        onClose={() => setEntityChatOpen(false)}
        chatEntity={chatEntity}
        clientPosition={clientPosition}
        entityMessages={entityMessages}
        inputQuestion={inputQuestion}
        onInputChange={setInputQuestion}
        isSending={isSending}
        onSendQuestion={handleSendEntityQuestion}
        suggestedCards={entitySuggestedCards}
        chatScrollRef={chatScrollRef}
      />
    </div>
  );
};

export default EvidenceGraphTab;