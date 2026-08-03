// FILE: frontend/src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - EVIDENCE GRAPH TAB V54.0 (FULL GESTURE INTERACTIVITY & PRISTINE ARCHITECTURE)

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { apiService } from '../services/api';
import { translateToAlbanian, formatRelationText } from '../utils/albanianLegalTranslator';
import {
  Search,
  RefreshCw,
  User,
  Building2,
  CreditCard,
  MapPin,
  Calendar,
  FileText,
  X,
  LucideIcon,
  Download,
  ZoomIn,
  ZoomOut,
  Maximize2,
  AlertTriangle,
  FileCheck,
  MessageCircle,
  Euro,
  Send,
  Loader2,
  Bot,
  Shield,
  Scale,
  Gavel,
  ChevronRight,
  Info,
  Swords,
  Sparkles,
  Link2,
  Clock,
  LayoutGrid,
  Network,
  Filter,
  Languages
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { LawCitationText } from './LawCitationText';

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

interface ChatMsg {
  id: string;
  role: 'user' | 'ai';
  content: string;
}

interface EvidenceGraphTabProps {
  caseId: string;
  caseTitle?: string;
}

const ENTITY_CONFIG: Record<EntityType, { albanianLabel: string; bg: string; border: string; icon: LucideIcon }> = {
  PERSON: { albanianLabel: 'Persona', bg: '#2563eb', border: '#60a5fa', icon: User },
  ORGANIZATION: { albanianLabel: 'Institucione', bg: '#7c3aed', border: '#a78bfa', icon: Building2 },
  ACCOUNT: { albanianLabel: 'Llogari Bankare', bg: '#059669', border: '#34d399', icon: CreditCard },
  DOCUMENT: { albanianLabel: 'Dokumente & Provat', bg: '#4b5563', border: '#9ca3af', icon: FileText },
  LOCATION: { albanianLabel: 'Lokacione', bg: '#d97706', border: '#fbbf24', icon: MapPin },
  EVENT: { albanianLabel: 'Ngjarje / Seanca', bg: '#dc2626', border: '#f87171', icon: Calendar },
};

export const EvidenceGraphTab: React.FC<EvidenceGraphTabProps> = ({ caseId }) => {
  const [graphData, setGraphData] = useState<CaseGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [clientPosition, setClientPosition] = useState<'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'>('DEFENDANT');

  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [mobileTab, setMobileTab] = useState<'entities' | 'timeline' | 'graph'>('entities');

  const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<OntologyEdge | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<OntologyEdge | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

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

  const [viewBox, setViewBox] = useState({ x: -1400, y: -700, width: 2800, height: 1400 });
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
        apiService.getCaseDetails(caseId)
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

    if (simplifiedView && !searchQuery && activeFilter === 'ALL' && base.length > 12) {
      const edgeCounts = new Map<string, number>();
      graphData.edges.forEach(e => {
        edgeCounts.set(e.source, (edgeCounts.get(e.source) || 0) + 1);
        edgeCounts.set(e.target, (edgeCounts.get(e.target) || 0) + 1);
      });

      base = base.sort((a, b) => (edgeCounts.get(b.id) || 0) - (edgeCounts.get(a.id) || 0)).slice(0, 12);
    }

    return base;
  }, [graphData?.nodes, graphData?.edges, activeFilter, searchQuery, simplifiedView]);

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
    graphData.nodes?.forEach(n => nMap.set(n.id, n));

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
        rawEdge: edge
      });
    });

    return items.sort((a, b) => (a.date && b.date ? a.date.localeCompare(b.date) : a.isContradiction ? -1 : 0));
  }, [graphData?.edges, graphData?.nodes]);

  useEffect(() => {
    if (filteredNodes.length === 0) return;
    const initialPos: Record<string, { x: number; y: number }> = {};
    
    const columns: Record<string, OntologyNode[]> = {
      PERSON: [], ORGANIZATION: [], ACCOUNT: [], DOCUMENT: [], EVENT: []
    };

    filteredNodes.forEach((node) => {
      if (node.type === 'PERSON') columns.PERSON.push(node);
      else if (node.type === 'ORGANIZATION') columns.ORGANIZATION.push(node);
      else if (node.type === 'ACCOUNT' || node.type === 'LOCATION') columns.ACCOUNT.push(node);
      else if (node.type === 'DOCUMENT') columns.DOCUMENT.push(node);
      else columns.EVENT.push(node);
    });

    const layoutCol = (nodes: OntologyNode[], xPos: number) => {
      const startY = -((nodes.length - 1) * 180) / 2;
      nodes.forEach((n, idx) => { initialPos[n.id] = { x: xPos, y: Math.round(startY + idx * 180) }; });
    };

    layoutCol(columns.PERSON, -1100);
    layoutCol(columns.ORGANIZATION, -550);
    layoutCol(columns.ACCOUNT, 0);
    layoutCol(columns.DOCUMENT, 550);
    layoutCol(columns.EVENT, 1100);

    setPositions(initialPos);
  }, [filteredNodes]);

  const handleZoomIn = () => {
    const zoomFactor = 0.82;
    setViewBox((prev) => ({
      x: prev.x + (prev.width * (1 - zoomFactor)) / 2,
      y: prev.y + (prev.height * (1 - zoomFactor)) / 2,
      width: prev.width * zoomFactor,
      height: prev.height * zoomFactor,
    }));
  };

  const handleZoomOut = () => {
    const zoomFactor = 1.18;
    setViewBox((prev) => ({
      x: prev.x + (prev.width * (1 - zoomFactor)) / 2,
      y: prev.y + (prev.height * (1 - zoomFactor)) / 2,
      width: prev.width * zoomFactor,
      height: prev.height * zoomFactor,
    }));
  };

  const handleResetZoom = () => {
    setSelectedNode(null);
    setSelectedEdge(null);
    setHoveredEdge(null);
  };

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
      await apiService.downloadCourtGraphReport(caseId);
    } catch (err) {
      alert('Dështoi eksporti i raportit gjyqësor.');
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
    graphData?.nodes?.forEach(n => map.set(n.id, n));
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

  // MOUSE & TOUCH INTERACTIVITY GESTURE LISTENERS
  const handleMouseDown = (e: React.MouseEvent) => {
    if (draggedNodeId) return;
    if (e.target === svgRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsPanning(true);
      setStartPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggedNodeId) {
      const point = getSVGPoint(e.clientX, e.clientY);
      setPositions(prev => ({
        ...prev,
        [draggedNodeId]: { x: Math.round(point.x), y: Math.round(point.y) }
      }));
      return;
    }

    if (isPanning) {
      const dx = (e.clientX - startPoint.x) * (viewBox.width / 2400);
      const dy = (e.clientY - startPoint.y) * (viewBox.height / 1500);
      setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
      setStartPoint({ x: e.clientX, y: e.clientY });
    }

    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedNodeId(null);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      touchDistRef.current = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
    } else if (e.touches.length === 1 && !draggedNodeId) {
      setIsPanning(true);
      setStartPoint({ x: e.touches[0].clientX, y: e.touches[0].clientY });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && touchDistRef.current !== null) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const newDist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
      
      if (newDist > 0 && touchDistRef.current > 0) {
        const zoomFactor = touchDistRef.current / newDist;
        setViewBox((prev) => ({
          x: prev.x + (prev.width * (1 - zoomFactor)) / 2,
          y: prev.y + (prev.height * (1 - zoomFactor)) / 2,
          width: Math.max(800, Math.min(6000, prev.width * zoomFactor)),
          height: Math.max(500, Math.min(4000, prev.height * zoomFactor)),
        }));
      }
      touchDistRef.current = newDist;
    } else if (e.touches.length === 1 && isPanning) {
      const dx = (e.touches[0].clientX - startPoint.x) * (viewBox.width / 2400);
      const dy = (e.touches[0].clientY - startPoint.y) * (viewBox.height / 1500);
      setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
      setStartPoint({ x: e.touches[0].clientX, y: e.touches[0].clientY });
    }
  };

  const handleTouchEnd = () => {
    touchDistRef.current = null;
    setIsPanning(false);
    setDraggedNodeId(null);
  };

  const handleOpenEntityChat = (node: OntologyNode) => {
    setChatEntity(node);
    setEntityMessages([]);
    setEntityChatOpen(true);
  };

  const handleSendEntityQuestion = async (customPrompt?: string) => {
    const q = customPrompt || inputQuestion.trim();
    if (!q || isSending || !chatEntity) return;

    setEntityMessages(prev => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content: q },
      { id: (Date.now() + 1).toString(), role: 'ai', content: '' }
    ]);
    if (!customPrompt) setInputQuestion('');
    setIsSending(true);

    try {
      const fullPrompt = `Lidhja me Entitetin: "${chatEntity.label}" (${chatEntity.type}).\nPyetja e Avokatit: ${q}`;
      const stream = apiService.sendChatMessageStream(caseId, fullPrompt, undefined, 'ks', 'FAST');
      
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setEntityMessages(prev => {
          const copy = [...prev];
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: acc };
          return copy;
        });
      }
    } catch (err) {
      setEntityMessages(prev => {
        const copy = [...prev];
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: "[Gabim gjatë marrjes së përgjigjes.]" };
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
        {
          badge: '🛡️ STRATEGJIA E MBROJTJES',
          title: 'RRËZIMI I PRETENDIMEVE',
          desc: `Si mund ta përdorim entitetin ${chatEntity.label} për të prapësuar padinë dhe mbrojtur klientin?`,
          query: `Si i paditur, si mund ta përdorim entitetin ${chatEntity.label} për të rrëzuar pretendimet e paditësit dhe forcuar mbrojtjen tonë?`,
          icon: Shield
        },
        {
          badge: '⚔️ GODITJA E KUNDËRSHTARIT',
          title: 'HETIMI I MOSPËRPUTHJEVE',
          desc: `Identifiko çdo kontradiktë apo dobësi procedurale që lidhet me ${chatEntity.label}.`,
          query: `Identifiko çdo mospërputhje, kontradiktë apo dobësi ligjore te ${chatEntity.label} që do të prapësonte kërkesëpadinë.`,
          icon: AlertTriangle
        }
      ];
    } else if (clientPosition === 'PLAINTIFF') {
      return [
        {
          badge: '⚔️ FORCIMI I PADISË',
          title: 'PROVA E PËRGJEGJËSISË',
          desc: `Si i vërteton ${chatEntity.label} shkeljet dhe dëmin e kërkuar nga ne?`,
          query: `Si paditës, si i provon ${chatEntity.label} përgjegjësinë dhe dëmin e shkaktuar nga pala tjetër?`,
          icon: Swords
        },
        {
          badge: '⚖️ BAZA LIGJORE & DETYRIMI',
          title: 'KRONOLOGJIA E SHKELJES',
          desc: `Marrja e dëshmive dhe detyrimeve financiare që ngarkojnë ${chatEntity.label}.`,
          query: `Nxirr të gjitha dëshmitë, transaksionet dhe afatet që e ngarkojnë me përgjegjësi ${chatEntity.label}.`,
          icon: Scale
        }
      ];
    } else {
      return [
        {
          badge: '⚖️ ANALIZË NEUTRALE',
          title: 'VLERËSIMI I BARRËS SË PROVËS',
          desc: `Vlerëso në mënyrë objektive peshën e provave që lidhen me ${chatEntity.label}.`,
          query: `Si një auditor i paanshëm, vlerëso barrën e provës dhe rëndësinë e entitetit ${chatEntity.label} për të dyja palët.`,
          icon: Scale
        },
        {
          badge: '🔍 AUDITI PROCEDURAL',
          title: 'SINTEZA E RASTIT',
          desc: `Përmbledhje paanshme e fakteve dhe kornizës ligjore për ${chatEntity.label}.`,
          query: `Jep një përmbledhje të paanshme dhe objektive të fakteve ligjore për ${chatEntity.label}.`,
          icon: Gavel
        }
      ];
    }
  }, [chatEntity, clientPosition]);

  return (
    <div className="flex flex-col h-full w-full bg-canvas text-text-primary rounded-2xl border border-main overflow-hidden shadow-xl relative font-sans select-none">
      
      {/* TOOLBAR */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between px-4 py-2.5 bg-surface border-b border-main gap-3 z-10 shrink-0">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={() => setSimplifiedView(!simplifiedView)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-black uppercase border transition-all ${
              simplifiedView ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            <Sparkles size={14} className={simplifiedView ? 'text-amber-400 animate-pulse' : ''} />
            <span>{simplifiedView ? '⚡ Provat Kryesore' : '🌐 Pamja e Plotë'}</span>
          </button>

          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Kërko entitetin ose fjalën kyçe..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-canvas border border-main rounded-xl pl-9 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
            />
          </div>

          <div className="hidden md:flex items-center gap-2 bg-canvas px-3 py-1 rounded-xl border border-main text-xs font-bold shrink-0">
            <Filter size={13} className="text-primary-start" />
            <select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
              className="bg-transparent text-text-primary focus:outline-none cursor-pointer uppercase font-bold text-xs"
            >
              <option value="ALL" className="bg-surface text-text-primary">Gjithë Entitetet ({graphData?.nodes?.length || 0})</option>
              {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((type) => {
                const count = graphData?.nodes?.filter((n) => n.type === type).length || 0;
                if (count === 0) return null;
                return (
                  <option key={type} value={type} className="bg-surface text-text-primary">
                    {ENTITY_CONFIG[type].albanianLabel} ({count})
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 shrink-0">
          <button onClick={handleExportCourtReport} disabled={exporting} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-hover border border-main text-text-primary rounded-xl text-xs font-bold uppercase disabled:opacity-50">
            <Download className="w-4 h-4 text-primary-start" /> <span>{exporting ? '...' : 'Eksporto'}</span>
          </button>

          <button onClick={handleRebuildGraph} disabled={rebuilding} className="flex items-center gap-1.5 px-3.5 py-1.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-black uppercase shadow-md">
            <RefreshCw className={`w-4 h-4 ${rebuilding ? 'animate-spin' : ''}`} /> <span>{rebuilding ? '...' : 'Rirregullo'}</span>
          </button>
        </div>
      </div>

      {/* MOBILE TABS */}
      {isMobile && (
        <div className="flex items-center justify-around bg-surface border-b border-main p-1.5 gap-1 shrink-0">
          <button onClick={() => setMobileTab('entities')} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold uppercase ${mobileTab === 'entities' ? 'bg-primary-start text-white shadow' : 'text-text-muted'}`}>
            <LayoutGrid size={15} /> <span>👥 Entitetet ({filteredNodes.length})</span>
          </button>
          <button onClick={() => setMobileTab('timeline')} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold uppercase ${mobileTab === 'timeline' ? 'bg-primary-start text-white shadow' : 'text-text-muted'}`}>
            <Clock size={15} /> <span>🕒 Kronologjia ({timelineItems.length})</span>
          </button>
          <button onClick={() => setMobileTab('graph')} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold uppercase ${mobileTab === 'graph' ? 'bg-primary-start text-white shadow' : 'text-text-muted'}`}>
            <Network size={15} /> <span>🗺️ Grafiku</span>
          </button>
        </div>
      )}

      {/* GRAPH CANVAS & MOBILE SWITCHER */}
      <div ref={containerRef} className="flex-1 flex relative overflow-hidden bg-canvas">
        
        {/* MOBILE ENTITY HUB */}
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

        {/* MOBILE TIMELINE */}
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

        {/* DESKTOP SVG CANVAS WITH FULL MOUSE & TOUCH GESTURE LISTENERS */}
        {(!isMobile || mobileTab === 'graph') && (
          <div className="flex-1 h-full w-full relative">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted w-full">
                <RefreshCw className="w-8 h-8 animate-spin text-primary-start" />
                <p className="text-xs font-semibold">Po ngarkohet Ontologjia e Provave...</p>
              </div>
            ) : (
              <svg
                ref={svgRef}
                className="w-full h-full cursor-grab active:cursor-grabbing select-none bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:28px_28px]"
                viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
              >
                {/* SWIMLANE HEADERS */}
                <g pointerEvents="none">
                  {['👤 PERSONA', '🏢 INSTITUCIONE', '💳 LLOGARI & LOKACIONE', '📄 PROVAT & DOKUMENTET', '⚖️ ORGANET & SEANCAT'].map((title, i) => (
                    <g key={i} transform={`translate(${-1100 + i * 550}, -780)`}>
                      <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#2563eb" strokeWidth="2" />
                      <text x="0" y="6" textAnchor="middle" fill="#60a5fa" fontSize="16" fontWeight="900">{title}</text>
                    </g>
                  ))}
                </g>

                {/* EDGES */}
                <g className="edges">
                  {filteredEdges.map((edge) => {
                    const s = positions[edge.source];
                    const t = positions[edge.target];
                    if (!s || !t) return null;

                    const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');
                    const pathD = `M ${s.x},${s.y} C ${s.x + (t.x - s.x) * 0.4},${s.y + 70} ${s.x + (t.x - s.x) * 0.6},${t.y - 70} ${t.x},${t.y}`;
                    const midX = (s.x + t.x) / 2;
                    const midY = (s.y + t.y) / 2 + 20;

                    return (
                      <g key={edge.id} className="cursor-pointer" onClick={() => setSelectedEdge(edge)} onMouseEnter={() => setHoveredEdge(edge)} onMouseLeave={() => setHoveredEdge(null)}>
                        <path d={pathD} fill="none" stroke={isContradiction ? '#ef4444' : '#475569'} strokeWidth={isContradiction ? 4 : 2} />
                        <g transform={`translate(${midX}, ${midY})`}>
                          <rect x="-65" y="-14" width="130" height="28" fill="#090d16" stroke="#334155" rx="14" />
                          <text x="0" y="4" textAnchor="middle" fill="#cbd5e1" fontSize="12" fontWeight="800">{formatRelationText(edge.relation)}</text>
                        </g>
                      </g>
                    );
                  })}
                </g>

                {/* NODES WITH DRAG INITIATION */}
                <g className="nodes">
                  {filteredNodes.map((node) => {
                    const pos = positions[node.id] || { x: 0, y: 0 };
                    const conf = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
                    const IconComponent = conf.icon;

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        className="cursor-grab active:cursor-grabbing"
                        onClick={() => setSelectedNode(node)}
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          setDraggedNodeId(node.id);
                        }}
                      >
                        <rect x="-140" y="-42" width="280" height="84" rx="18" fill="#0b0f19" stroke={selectedNode?.id === node.id ? '#ffffff' : '#1e293b'} strokeWidth="2" />
                        <rect x="-140" y="-42" width="10" height="84" rx="5" fill={conf.bg} />
                        <g transform="translate(-104, 0)">
                          <circle r="20" fill={conf.bg} />
                          <foreignObject x="-10" y="-10" width="20" height="20" className="pointer-events-none">
                            <div className="w-full h-full flex items-center justify-center text-white"><IconComponent size={16} /></div>
                          </foreignObject>
                        </g>
                        <text x="-72" y="-8" fill="#ffffff" fontSize="16" fontWeight="800">{translateToAlbanian(node.label)}</text>
                        <text x="-72" y="18" fill={conf.border} fontSize="11" fontWeight="800" className="uppercase">{conf.albanianLabel}</text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            )}

            {/* FLOATING ZOOM CONTROLS */}
            <div className="absolute bottom-4 right-4 flex items-center gap-1 bg-surface/90 p-1.5 rounded-2xl border border-main shadow-2xl z-20">
              <button type="button" onClick={handleZoomIn} className="p-2 text-text-muted hover:text-text-primary rounded-xl" title="Zmadho"><ZoomIn size={16} /></button>
              <button type="button" onClick={handleResetZoom} className="p-2 text-text-muted hover:text-text-primary rounded-xl" title="Reset View"><Maximize2 size={15} /></button>
              <button type="button" onClick={handleZoomOut} className="p-2 text-text-muted hover:text-text-primary rounded-xl" title="Zvogëlo"><ZoomOut size={16} /></button>
            </div>

            {/* HOVER TOOLTIP */}
            <AnimatePresence>
              {hoveredEdge && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  style={{
                    position: 'absolute',
                    left: Math.min(window.innerWidth - 460, tooltipPos.x + 20),
                    top: Math.max(20, tooltipPos.y - 40),
                    pointerEvents: 'none'
                  }}
                  className="z-[200] w-[440px] p-5 bg-[#090d1a]/98 border border-slate-700 rounded-2xl shadow-2xl space-y-3 font-sans"
                >
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="px-3 py-1 rounded-full text-xs font-black uppercase bg-blue-500/20 text-blue-300">
                      {formatRelationText(hoveredEdge.relation)}
                    </span>
                    {hoveredEdge.amount_eur && (
                      <span className="text-xs font-mono font-black text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                        €{hoveredEdge.amount_eur.toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-200 bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span>{translateToAlbanian(nodeMap.get(hoveredEdge.source)?.label) || 'Burimi'}</span>
                    <Link2 size={14} className="text-blue-400" />
                    <span>{translateToAlbanian(nodeMap.get(hoveredEdge.target)?.label) || 'Caku'}</span>
                  </div>
                  {hoveredEdge.evidence_text && (
                    <p className="text-xs text-slate-200 italic leading-relaxed bg-slate-950 p-3 rounded-xl border border-slate-800">
                      &quot;<LawCitationText text={translateToAlbanian(hoveredEdge.evidence_text)} />&quot;
                    </p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* INSPECTOR PANEL */}
        {(selectedNode || selectedEdge) && (
          <div className="w-96 bg-surface border-l border-main p-5 flex flex-col gap-4 z-20 shadow-2xl shrink-0 overflow-y-auto font-sans">
            <div className="flex items-center justify-between border-b border-main pb-3">
              <span className="text-xs font-black text-primary-start uppercase tracking-widest flex items-center gap-2">
                <FileCheck size={16} /> {selectedNode ? 'Doshja e Entitetit' : 'Detajet e Lidhjes'}
              </span>
              <button onClick={() => { setSelectedNode(null); setSelectedEdge(null); }}><X className="w-5 h-5 text-text-muted" /></button>
            </div>

            {selectedNode && (
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-4 bg-canvas border border-main rounded-2xl">
                  <div className="p-3 rounded-2xl text-white shrink-0 border border-white/20 shadow-md" style={{ backgroundColor: ENTITY_CONFIG[selectedNode.type].bg }}>
                    {React.createElement(ENTITY_CONFIG[selectedNode.type].icon, { className: 'w-6 h-6 text-white' })}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-black text-base text-text-primary leading-snug">{translateToAlbanian(selectedNode.label)}</h4>
                    <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase text-white tracking-wider" style={{ backgroundColor: ENTITY_CONFIG[selectedNode.type].bg }}>
                      {ENTITY_CONFIG[selectedNode.type].albanianLabel}
                    </span>
                  </div>
                </div>

                {(financialTotalsForSelectedNode.inEur > 0 || financialTotalsForSelectedNode.outEur > 0) && (
                  <div className="bg-canvas p-4 rounded-2xl border border-main space-y-2">
                    <span className="text-[10px] font-black text-primary-start uppercase tracking-widest flex items-center gap-1.5">
                      <Euro size={14} /> Balanca e Transaksioneve
                    </span>
                    <div className="flex justify-between text-xs font-bold text-emerald-400">
                      <span>Të Pranuara:</span>
                      <span>+€{financialTotalsForSelectedNode.inEur.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-xs font-bold text-rose-400">
                      <span>Të Paguara:</span>
                      <span>-€{financialTotalsForSelectedNode.outEur.toLocaleString()}</span>
                    </div>
                    <div className="border-t border-main pt-2 flex justify-between font-black text-sm text-text-primary">
                      <span>Bilanci Neto:</span>
                      <span>€{financialTotalsForSelectedNode.netEur.toLocaleString()}</span>
                    </div>
                  </div>
                )}

                {selectedNode.description && (
                  <div className="bg-canvas p-4 rounded-2xl border border-main space-y-2">
                    <span className="text-[10px] font-black text-text-muted uppercase tracking-widest block">Roli / Përshkrimi i Plotë</span>
                    <div className="text-xs text-text-secondary leading-relaxed font-medium">
                      <LawCitationText text={translateToAlbanian(selectedNode.description)} />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <span className="text-[10px] font-black text-text-muted uppercase tracking-widest block">
                    Veprimet & Lidhjet Ligjore ({connectedEdgesForSelectedNode.length})
                  </span>
                  <div className="space-y-2 max-h-60 overflow-y-auto custom-finance-scroll pr-1">
                    {connectedEdgesForSelectedNode.map((e) => {
                      const otherNodeId = e.source === selectedNode.id ? e.target : e.source;
                      const otherNode = nodeMap.get(otherNodeId);
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
                          <div className="flex items-center justify-between font-black text-[11px]">
                            <span className={isContradiction ? 'text-rose-400 flex items-center gap-1 uppercase' : 'text-primary-start uppercase'}>
                              {isContradiction && <AlertTriangle size={12} />}
                              {formatRelationText(e.relation)}
                            </span>
                            {otherNode && (
                              <span className="text-text-primary truncate max-w-[120px] font-bold">
                                {translateToAlbanian(otherNode.label)}
                              </span>
                            )}
                          </div>
                          {e.evidence_text && (
                            <div className="text-[11px] text-text-secondary italic line-clamp-2 mt-1">
                              &quot;<LawCitationText text={translateToAlbanian(e.evidence_text)} />&quot;
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <button onClick={() => handleOpenEntityChat(selectedNode)} className="w-full py-3 bg-primary-start hover:bg-opacity-95 text-white rounded-xl text-xs font-black uppercase flex items-center justify-center gap-2 shadow-lg">
                  <MessageCircle size={16} /> Pyet AI për këtë entitet
                </button>
              </div>
            )}

            {selectedEdge && (
              <div className="bg-canvas p-4 rounded-2xl border border-main space-y-3">
                <div className="flex items-center justify-between border-b border-main pb-2">
                  <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">Lidhja Ligjore</span>
                  {selectedEdge.amount_eur && (
                    <span className="text-xs font-mono font-black text-emerald-400">€{selectedEdge.amount_eur.toLocaleString()}</span>
                  )}
                </div>
                
                <h4 className="font-black text-sm text-primary-start uppercase">{formatRelationText(selectedEdge.relation)}</h4>

                {selectedEdge.evidence_text && (
                  <div className="bg-surface p-3.5 rounded-xl border border-main text-xs text-text-secondary leading-relaxed space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-text-muted uppercase block">Dëshmia nga Dokumentet Origjinale</span>
                      <span className="text-[9px] font-black uppercase text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 flex items-center gap-1">
                        <Languages size={10} /> 🇦🇱 Përkthyer në Shqip
                      </span>
                    </div>
                    <div className="italic text-text-primary font-medium text-xs leading-relaxed">
                      &quot;<LawCitationText text={translateToAlbanian(selectedEdge.evidence_text)} />&quot;
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* IN-MODAL AI CHAT DRAWER */}
      <AnimatePresence>
        {entityChatOpen && chatEntity && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[250] flex items-center justify-end p-2 sm:p-4">
            <motion.div
              initial={{ x: 300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 300, opacity: 0 }}
              className="w-full max-w-lg h-[90vh] bg-canvas border border-main rounded-3xl shadow-2xl flex flex-col overflow-hidden"
            >
              <div className="p-4 sm:p-5 bg-surface border-b border-main flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                    <Bot size={20} />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-tight">Hetimi AI: {translateToAlbanian(chatEntity.label)}</h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-text-muted font-bold uppercase">{ENTITY_CONFIG[chatEntity.type].albanianLabel}</span>
                      <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                        {clientPosition === 'DEFENDANT' ? '🛡️ Mandati: I Paditur (Mbrojtje)' : clientPosition === 'PLAINTIFF' ? '⚔️ Mandati: Paditësi (Sulm)' : '⚖️ Mandati: Neutral'}
                      </span>
                    </div>
                  </div>
                </div>
                <button onClick={() => setEntityChatOpen(false)} className="p-2 text-text-muted hover:text-text-primary rounded-xl">
                  <X size={18} />
                </button>
              </div>

              <div className="flex-1 p-4 sm:p-5 overflow-y-auto custom-finance-scroll space-y-6">
                {entityMessages.length === 0 && (
                  <div className="text-center space-y-3 pt-2">
                    <h2 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight">
                      AGJENTI I HETIMIT: {translateToAlbanian(chatEntity.label)}
                    </h2>
                    <div className="p-2.5 bg-surface/60 border border-main rounded-xl text-[11px] text-text-muted inline-flex items-center gap-2 text-left">
                      <Info size={14} className="text-primary-start shrink-0" />
                      <span>Përgjigjet e AI shërbejnë për referencë dhe verifikohen nga avokati.</span>
                    </div>

                    <div className="grid grid-cols-1 gap-3 pt-4 text-left">
                      {entitySuggestedCards.map((card, idx) => {
                        const CardIcon = card.icon;
                        return (
                          <div
                            key={idx}
                            onClick={() => handleSendEntityQuestion(card.query)}
                            className="p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 rounded-2xl cursor-pointer transition-all flex flex-col justify-between gap-3 group"
                          >
                            <div className="flex justify-between items-center">
                              <span className="text-[9px] font-black uppercase tracking-widest text-primary-start bg-primary-start/10 px-2 py-0.5 rounded border border-primary-start/20">
                                {card.badge}
                              </span>
                              <ChevronRight size={14} className="text-text-muted group-hover:text-primary-start" />
                            </div>
                            <div>
                              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide flex items-center gap-1.5 mb-1">
                                <CardIcon size={14} className="text-primary-start" />
                                {card.title}
                              </h4>
                              <p className="text-[11px] text-text-secondary line-clamp-2">{card.desc}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {entityMessages.map((m) => (
                  <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[88%] p-4 rounded-2xl text-xs leading-relaxed ${
                      m.role === 'user' ? 'bg-primary-start text-white font-medium' : 'bg-surface border border-main text-text-primary font-medium'
                    }`}>
                      {m.content ? <LawCitationText text={m.content} /> : <Loader2 className="animate-spin h-4 w-4 text-primary-start" />}
                    </div>
                  </div>
                ))}
                <div ref={chatScrollRef} />
              </div>

              <div className="p-4 bg-surface border-t border-main shrink-0 space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputQuestion}
                    onChange={(e) => setInputQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendEntityQuestion()}
                    placeholder={`Bëj një pyetje për ${translateToAlbanian(chatEntity.label)}...`}
                    className="flex-1 h-11 px-4 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
                  />
                  <button
                    onClick={() => handleSendEntityQuestion()}
                    disabled={!inputQuestion.trim() || isSending}
                    className="h-11 px-5 bg-primary-start text-white font-bold rounded-xl text-xs uppercase tracking-wider flex items-center justify-center shadow-md disabled:opacity-40"
                  >
                    {isSending ? <Loader2 className="animate-spin h-4 w-4" /> : <Send size={16} />}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
};

export default EvidenceGraphTab;