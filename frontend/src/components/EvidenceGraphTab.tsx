// FILE: src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - EVIDENCE GRAPH TAB V80.0 (CLIENT-ANCHORED KEY EVIDENCE & CONTRADICTION HUB)

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
    chatScrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entityMessages, isSending]);

  // Filtri Inteligjent: Provat Kryesore me Klientin gjithmonë të ankoruar në qendër
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

    if (simplifiedView && !searchQuery && activeFilter === 'ALL' && base.length > 20) {
      // 1. Gjej të gjitha nyjet që janë pjesë e kontradiktave dhe shkeljeve kryesore
      const priorityNodeIds = new Set<string>();
      graphData.edges.forEach((e) => {
        const isPriorityRel =
          e.relation.includes('CONTRADICT') ||
          e.relation.includes('KUNDËR') ||
          e.relation.includes('MOSPËRPUTHJE') ||
          e.relation.includes('FALSIFIKIM') ||
          e.relation.includes('SHKELJE') ||
          e.relation.includes('NDIKIM') ||
          e.relation.includes('PADIT');
        if (isPriorityRel) {
          priorityNodeIds.add(e.source);
          priorityNodeIds.add(e.target);
        }
      });

      // 2. Sigurohemi që Klienti kryesor dhe të afërmit thelbësorë janë gjithmonë brenda
      const coreProtagonists = base.filter((n) => {
        const lbl = n.label.toLowerCase();
        return (
          lbl.includes('shaban') ||
          lbl.includes('andi') ||
          lbl.includes('sanije') ||
          lbl.includes('gjykata') ||
          priorityNodeIds.has(n.id)
        );
      });

      // 3. Plotësojmë me nyjet më të ndërlidhura deri në 24 aktorë
      const edgeCounts = new Map<string, number>();
      graphData.edges.forEach((e) => {
        edgeCounts.set(e.source, (edgeCounts.get(e.source) || 0) + 1);
        edgeCounts.set(e.target, (edgeCounts.get(e.target) || 0) + 1);
      });

      const sortedBase = base.sort((a, b) => (edgeCounts.get(b.id) || 0) - (edgeCounts.get(a.id) || 0));
      const combined = Array.from(new Set([...coreProtagonists, ...sortedBase])).slice(0, 24);
      return combined;
    }
    return base;
  }, [graphData?.nodes, graphData?.edges, activeFilter, searchQuery, simplifiedView]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    return graphData.edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [graphData?.edges, filteredNodeIds]);

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
      const isContradiction =
        edge.relation.includes('CONTRADICT') ||
        edge.relation.includes('KUNDËR') ||
        edge.relation.includes('MOSPËRPUTHJE') ||
        edge.relation.includes('FALSIFIKIM') ||
        edge.relation.includes('SHKELJE');

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

  const handleRebuildGraph = async () => {
    setRebuilding(true);
    try {
      await apiService.rebuildCaseGraph(caseId);
      setTimeout(() => fetchGraphAndCaseDetails(), 1500);
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
    <div className="flex flex-col h-full w-full bg-canvas text-text-primary rounded-none overflow-hidden relative font-sans select-none">
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

      <div className="flex-1 flex relative overflow-hidden bg-canvas">
        {isMobile && mobileTab === 'entities' && (
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-finance-scroll">
            {filteredNodes.map((node) => {
              const conf = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
              const IconComp = conf.icon;
              return (
                <div key={node.id} onClick={() => setSelectedNode(node)} className="p-3 bg-surface border border-main rounded-xl cursor-pointer flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ backgroundColor: conf.bg }}>
                        <IconComp size={16} />
                      </div>
                      <div>
                        <h4 className="text-xs font-black text-text-primary">{translateToAlbanian(node.label)}</h4>
                        <span className="text-[9px] font-bold uppercase" style={{ color: conf.border }}>{conf.albanianLabel}</span>
                      </div>
                    </div>
                    <ChevronRight size={14} className="text-text-muted" />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {isMobile && mobileTab === 'timeline' && (
          <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-finance-scroll">
            <div className="relative border-l-2 border-main ml-3 space-y-3 pl-4">
              {timelineItems.map((item) => (
                <div key={item.id} onClick={() => setSelectedEdge(item.rawEdge)} className="p-2.5 bg-surface border border-main rounded-xl cursor-pointer">
                  <span className="text-[11px] font-black text-primary-start uppercase">{item.title}</span>
                  <div className="text-xs font-bold text-text-primary my-1 flex items-center gap-1">
                    <span>{item.sourceLabel}</span> <Link2 size={11} /> <span>{item.targetLabel}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(!isMobile || mobileTab === 'graph') && (
          <EvidenceCanvas
            loading={loading}
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
          />
        )}

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