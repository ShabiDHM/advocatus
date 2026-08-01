// FILE: frontend/src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - EVIDENCE GRAPH TAB V40.0 (5-COLUMN LEGAL PIPELINE & EXECUTIVE CARDS)

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { apiService } from '../services/api';
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
  Layers,
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
  Link2
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

const ENTITY_CONFIG: Record<EntityType, { albanianLabel: string; bg: string; border: string; glow: string; icon: LucideIcon }> = {
  PERSON: { albanianLabel: 'Persona', bg: '#2563eb', border: '#60a5fa', glow: 'rgba(37, 99, 235, 0.4)', icon: User },
  ORGANIZATION: { albanianLabel: 'Institucione', bg: '#7c3aed', border: '#a78bfa', glow: 'rgba(124, 58, 237, 0.4)', icon: Building2 },
  ACCOUNT: { albanianLabel: 'Llogari', bg: '#059669', border: '#34d399', glow: 'rgba(5, 150, 105, 0.4)', icon: CreditCard },
  DOCUMENT: { albanianLabel: 'Dokumente', bg: '#4b5563', border: '#9ca3af', glow: 'rgba(75, 85, 99, 0.4)', icon: FileText },
  LOCATION: { albanianLabel: 'Lokacione', bg: '#d97706', border: '#fbbf24', glow: 'rgba(217, 119, 6, 0.4)', icon: MapPin },
  EVENT: { albanianLabel: 'Ngjarje / Seanca', bg: '#dc2626', border: '#f87171', glow: 'rgba(220, 38, 38, 0.4)', icon: Calendar },
};

const RELATION_ALBANIAN_MAP: Record<string, string> = {
  REPRESENTED_BY: 'PËRFAQËSOHET NGA',
  REPRESENTS: 'PËRFAQËSON',
  ASSOCIATED_WITH: 'LIDHUR ME',
  TRANSFERRED_FUNDS: 'TRANSAKSION',
  EMPLOYED_BY: 'PUNËSUAR NË',
  OWNED_BY: 'PRONËSI E',
  OWNS: 'PRONËSI E',
  PRESENT_AT: 'PRANISHËM NË',
  LOCATED_AT: 'LOKACIONI',
  LOCATED_IN: 'LOKACIONI',
  CONTRADICTS: 'KUNDËRTHËNIE',
  KUNDËRTHËNIE: 'KUNDËRTHËNIE',
  KUNDËRTHËNJE: 'KUNDËRTHËNIE',
  OWES_MONEY: 'DETYRIM',
  SIGNED: 'NËNSHKRUAR',
  MENTIONED_IN: 'PËRMENDUR NË',
  HAS_ACCOUNT: 'LLOGARI BANKARE',
  WORKED_AT: 'PUNËSUAR NË',
  PARTY_TO: 'PALË NË',
  ISSUED_BY: 'LËSHUAR NGA',
  FINANCED_BY: 'FINANCUAR NGA'
};

const formatRelationText = (rel: string): string => {
  if (!rel) return '';
  const clean = rel.toUpperCase().trim().replace(/ /g, '_');
  return RELATION_ALBANIAN_MAP[clean] || clean.replace(/_/g, ' ');
};

export const EvidenceGraphTab: React.FC<EvidenceGraphTabProps> = ({ caseId }) => {
  const [graphData, setGraphData] = useState<CaseGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [clientPosition, setClientPosition] = useState<'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'>('DEFENDANT');

  const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<OntologyEdge | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<OntologyEdge | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [simplifiedView, setSimplifiedView] = useState<boolean>(true);

  const [rebuilding, setRebuilding] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);

  // In-Modal Entity Chat State
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

  const fetchGraphAndCaseDetails = async () => {
    setLoading(true);
    try {
      const [gData, cDetails] = await Promise.all([
        apiService.getCaseGraph(caseId),
        apiService.getCaseDetails(caseId)
      ]);
      setGraphData(gData);
      
      const pos = (cDetails as any)?.client_position || 'DEFENDANT';
      if (pos === 'PLAINTIFF') setClientPosition('PLAINTIFF');
      else if (pos === 'NEUTRAL') setClientPosition('NEUTRAL');
      else setClientPosition('DEFENDANT');
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

    if (simplifiedView && !searchQuery && activeFilter === 'ALL' && base.length > 18) {
      const edgeCounts = new Map<string, number>();
      graphData.edges.forEach(e => {
        edgeCounts.set(e.source, (edgeCounts.get(e.source) || 0) + 1);
        edgeCounts.set(e.target, (edgeCounts.get(e.target) || 0) + 1);
      });

      base = base.sort((a, b) => (edgeCounts.get(b.id) || 0) - (edgeCounts.get(a.id) || 0)).slice(0, 20);
    }

    return base;
  }, [graphData?.nodes, graphData?.edges, activeFilter, searchQuery, simplifiedView]);

  const { connectedNodeIds, connectedEdgeIds } = useMemo(() => {
    if (!selectedNode || !graphData?.edges) {
      return { connectedNodeIds: new Set<string>(), connectedEdgeIds: new Set<string>() };
    }
    const nodeSet = new Set<string>([selectedNode.id]);
    const edgeSet = new Set<string>();

    graphData.edges.forEach((edge) => {
      if (edge.source === selectedNode.id || edge.target === selectedNode.id) {
        edgeSet.add(edge.id);
        nodeSet.add(edge.source);
        nodeSet.add(edge.target);
      }
    });

    return { connectedNodeIds: nodeSet, connectedEdgeIds: edgeSet };
  }, [selectedNode, graphData?.edges]);

  // STRUCTURED 5-COLUMN LEGAL PIPELINE DISTRIBUTION
  useEffect(() => {
    if (filteredNodes.length === 0) return;
    const initialPos: Record<string, { x: number; y: number }> = {};
    
    const colPersons: OntologyNode[] = [];
    const colOrgs: OntologyNode[] = [];
    const colAccountsLocs: OntologyNode[] = [];
    const colDocs: OntologyNode[] = [];
    const colEvents: OntologyNode[] = [];

    filteredNodes.forEach((node) => {
      if (node.type === 'PERSON') colPersons.push(node);
      else if (node.type === 'ORGANIZATION') colOrgs.push(node);
      else if (node.type === 'ACCOUNT' || node.type === 'LOCATION') colAccountsLocs.push(node);
      else if (node.type === 'DOCUMENT') colDocs.push(node);
      else colEvents.push(node);
    });

    const calculateColumn = (nodes: OntologyNode[], xPos: number, spacingY: number = 180) => {
      const startY = -((nodes.length - 1) * spacingY) / 2;
      nodes.forEach((node, idx) => {
        initialPos[node.id] = {
          x: xPos,
          y: Math.round(startY + idx * spacingY)
        };
      });
    };

    calculateColumn(colPersons, -1100, 180);       // Col 1: Persons
    calculateColumn(colOrgs, -550, 180);          // Col 2: Organizations
    calculateColumn(colAccountsLocs, 0, 180);     // Col 3: Accounts & Locations
    calculateColumn(colDocs, 550, 180);           // Col 4: Documents
    calculateColumn(colEvents, 1100, 180);         // Col 5: Events / Courts

    setPositions(initialPos);
  }, [filteredNodes]);

  // Dynamic Camera ViewBox Auto-Fit
  useEffect(() => {
    const keys = Object.keys(positions);
    if (keys.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    keys.forEach(id => {
      const p = positions[id];
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    });

    const calcWidth = Math.max(2200, (maxX - minX) + 700);
    const calcHeight = Math.max(1400, (maxY - minY) + 500);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    setViewBox({
      x: Math.round(centerX - calcWidth / 2),
      y: Math.round(centerY - calcHeight / 2),
      width: Math.round(calcWidth),
      height: Math.round(calcHeight)
    });
  }, [positions]);

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 1.12 : 0.88;
      setViewBox((prev) => ({
        x: prev.x + (prev.width * (1 - zoomFactor)) / 2,
        y: prev.y + (prev.height * (1 - zoomFactor)) / 2,
        width: prev.width * zoomFactor,
        height: prev.height * zoomFactor,
      }));
    };

    svgEl.addEventListener('wheel', handleWheel, { passive: false });
    return () => svgEl.removeEventListener('wheel', handleWheel);
  }, [loading]);

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
    return graphData.edges.filter(
      (edge) => filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target)
    );
  }, [graphData?.edges, filteredNodeIds]);

  const connectedEdgesForSelectedNode = useMemo(() => {
    if (!selectedNode || !graphData?.edges) return [];
    return graphData.edges.filter(
      (e) => e.source === selectedNode.id || e.target === selectedNode.id
    );
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
      setTooltipPos({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedNodeId(null);
  };

  // TOUCH GESTURES FOR MOBILE PINCH ZOOM & PANNING
  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const dist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
      touchDistRef.current = dist;
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

    const userMsg: ChatMsg = { id: Date.now().toString(), role: 'user', content: q };
    const aiMsgPlaceholder: ChatMsg = { id: (Date.now() + 1).toString(), role: 'ai', content: '' };

    setEntityMessages(prev => [...prev, userMsg, aiMsgPlaceholder]);
    if (!customPrompt) setInputQuestion('');
    setIsSending(true);

    try {
      const mandateText = clientPosition === 'DEFENDANT' 
        ? "POZICIONI E TUAJ: I PADITUR / MBROJTJE. Detyra jote është të rrëzosh kërkesëpadinë, të gjejshe gabime procedurale dhe të shfajësosh klientin tonë." 
        : clientPosition === 'PLAINTIFF'
        ? "POZICIONI E TUAJ: PADITËS / SULM. Detyra jote është të provosh përgjegjësinë e palës tjetër, të forcosh kërkesëpadinë dhe të sigurosh dëmshpërblimin."
        : "POZICIONI E TUAJ: NEUTRAL / OBJEKTIV. Detyra jote është të vlerësosh rastin në mënyrë të paanshme, të peshosh barrën e provës dhe argumentet e të dyja palëve.";

      const fullPrompt = `${mandateText}\n\nLidhja me Entitetin: "${chatEntity.label}" (${chatEntity.type}).\nPyetja e Avokatit: ${q}`;
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
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: "[Gabim gjatë marrjes së përgjigjes në chat.]" };
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
      
      {/* CONTROL & FILTER TOOLBAR */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface border-b border-main gap-2 z-10 shrink-0 h-12">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          
          <button
            onClick={() => setSimplifiedView(!simplifiedView)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-black uppercase transition-all shadow-sm ${
              simplifiedView 
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-amber-500/10' 
                : 'bg-slate-800 text-slate-300 border border-slate-700'
            }`}
            title="Shtyp për të ndërruar ndërmjet pamjes së thjeshtuar me provat kryesore dhe pamjes së plotë"
          >
            <Sparkles size={13} className={simplifiedView ? 'text-amber-400 animate-pulse' : ''} />
            <span>{simplifiedView ? '⚡ Provat Kryesore' : '🌐 Pamja e Plotë'}</span>
          </button>

          <div className="relative w-36 sm:w-48 shrink-0">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Kërko entitetin..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-canvas border border-main rounded-lg pl-8 pr-2 py-1 text-[11px] text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
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
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: conf.bg }} />
                  <span className="hidden sm:inline">{conf.albanianLabel}</span>
                  <span className="font-mono text-text-secondary">({count})</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <div className="flex items-center gap-0.5 bg-canvas p-0.5 rounded-lg border border-main">
            <button type="button" onClick={handleZoomIn} className="p-1.5 text-text-muted hover:text-text-primary rounded" title="Zmadho"><ZoomIn size={14} /></button>
            <button type="button" onClick={handleResetZoom} className="p-1.5 text-text-muted hover:text-text-primary rounded" title="Reset"><Maximize2 size={13} /></button>
            <button type="button" onClick={handleZoomOut} className="p-1.5 text-text-muted hover:text-text-primary rounded" title="Zvogëlo"><ZoomOut size={14} /></button>
          </div>

          <button onClick={handleExportCourtReport} disabled={exporting} className="flex items-center gap-1 px-2.5 py-1 bg-surface hover:bg-hover border border-main text-text-primary rounded-lg text-[10px] font-bold uppercase disabled:opacity-50">
            <Download className="w-3.5 h-3.5 text-primary-start" /> <span className="hidden sm:inline">{exporting ? '...' : 'Eksporto'}</span>
          </button>

          <button onClick={handleRebuildGraph} disabled={rebuilding} className="flex items-center gap-1 px-3 py-1 bg-primary-start hover:bg-primary-start/90 text-white rounded-lg text-[10px] font-bold uppercase shadow-sm">
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} /> <span className="hidden sm:inline">Rirregullo</span>
          </button>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 flex relative overflow-hidden bg-canvas">
        <div className="flex-1 h-full w-full relative">

          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted">
              <RefreshCw className="w-8 h-8 animate-spin text-primary-start" />
              <p className="text-xs font-semibold">Po ngarkohet Ontologjia e Provave...</p>
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted p-6 text-center">
              <Layers className="w-12 h-12 opacity-40" />
              <h3 className="text-sm font-bold text-text-primary">Nuk u gjetën entitete të nxjerra</h3>
              <button onClick={handleRebuildGraph} className="mt-2 px-5 py-2 bg-primary-start text-white rounded-xl text-xs font-bold uppercase shadow-md">
                Gjenero Grafikun Tani
              </button>
            </div>
          ) : (
            <svg
              ref={svgRef}
              className="w-full h-full cursor-grab active:cursor-grabbing select-none touch-none bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:28px_28px]"
              viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
            >
              <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto">
                  <polygon points="0 0, 10 4, 0 8" fill="#64748b" />
                </marker>
                <marker id="arrowhead-selected" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto">
                  <polygon points="0 0, 10 4, 0 8" fill="#3b82f6" />
                </marker>
                <marker id="arrowhead-contradiction" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto">
                  <polygon points="0 0, 10 4, 0 8" fill="#ef4444" />
                </marker>
              </defs>

              {/* 5-COLUMN LEGAL PIPELINE HEADERS */}
              <g className="lane-headers" pointerEvents="none">
                <g transform="translate(-1100, -780)">
                  <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#2563eb" strokeWidth="2" />
                  <text x="0" y="6" textAnchor="middle" fill="#60a5fa" fontSize="16" fontWeight="900" letterSpacing="1px">
                    👤 PERSONA
                  </text>
                </g>

                <g transform="translate(-550, -780)">
                  <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#7c3aed" strokeWidth="2" />
                  <text x="0" y="6" textAnchor="middle" fill="#a78bfa" fontSize="16" fontWeight="900" letterSpacing="1px">
                    🏢 INSTITUCIONE
                  </text>
                </g>

                <g transform="translate(0, -780)">
                  <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#059669" strokeWidth="2" />
                  <text x="0" y="6" textAnchor="middle" fill="#34d399" fontSize="16" fontWeight="900" letterSpacing="1px">
                    💳 LLOGARI & LOKACIONE
                  </text>
                </g>

                <g transform="translate(550, -780)">
                  <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#4b5563" strokeWidth="2" />
                  <text x="0" y="6" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="900" letterSpacing="1px">
                    📄 PROVAT & DOKUMENTET
                  </text>
                </g>

                <g transform="translate(1100, -780)">
                  <rect x="-140" y="-26" width="280" height="52" rx="26" fill="#0f172a" stroke="#dc2626" strokeWidth="2" />
                  <text x="0" y="6" textAnchor="middle" fill="#f87171" fontSize="16" fontWeight="900" letterSpacing="1px">
                    ⚖️ ORGANET & SEANCAT
                  </text>
                </g>
              </g>

              {/* CURVED BEZIER EDGES / RELATIONSHIP LINES */}
              <g className="edges">
                {filteredEdges.map((edge) => {
                  const sourcePos = positions[edge.source];
                  const targetPos = positions[edge.target];
                  if (!sourcePos || !targetPos) return null;

                  const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');
                  const isSelected = selectedEdge?.id === edge.id;
                  const isHovered = hoveredEdge?.id === edge.id;

                  const isFocusedMode = Boolean(selectedNode);
                  const isEdgeConnected = connectedEdgeIds.has(edge.id);
                  const edgeOpacity = isFocusedMode ? (isEdgeConnected ? 1 : 0.05) : (isHovered || isSelected || isContradiction ? 1 : 0.65);
                  const isEdgeDisabled = isFocusedMode && !isEdgeConnected;

                  const dx = targetPos.x - sourcePos.x;
                  const dy = targetPos.y - sourcePos.y;
                  const curveOffset = dx === 0 ? 120 : (dy > 0 ? 70 : -70);
                  
                  const controlX1 = sourcePos.x + dx * 0.4;
                  const controlY1 = sourcePos.y + curveOffset;
                  const controlX2 = sourcePos.x + dx * 0.6;
                  const controlY2 = targetPos.y - curveOffset;

                  const pathD = `M ${sourcePos.x},${sourcePos.y} C ${controlX1},${controlY1} ${controlX2},${controlY2} ${targetPos.x},${targetPos.y}`;
                  
                  const midX = (sourcePos.x + targetPos.x) / 2;
                  const midY = (sourcePos.y + targetPos.y) / 2 + (curveOffset / 3);

                  const albanianLabel = formatRelationText(edge.relation);
                  const labelDisplayText = edge.amount_eur ? `€${edge.amount_eur.toLocaleString()}` : albanianLabel;
                  const badgeWidth = Math.max(120, labelDisplayText.length * 11);

                  return (
                    <g
                      key={edge.id}
                      className={`group cursor-pointer transition-opacity duration-300 ${isEdgeDisabled ? 'pointer-events-none' : ''}`}
                      onClick={() => {
                        setSelectedEdge(edge);
                        setSelectedNode(null);
                      }}
                      onMouseEnter={() => setHoveredEdge(edge)}
                      onMouseLeave={() => setHoveredEdge(null)}
                      style={{ opacity: edgeOpacity }}
                    >
                      <path d={pathD} fill="none" stroke="transparent" strokeWidth="32" />

                      <path
                        d={pathD}
                        fill="none"
                        stroke={isContradiction ? '#ef4444' : isSelected || isHovered ? '#3b82f6' : '#475569'}
                        strokeWidth={isContradiction || isSelected || isHovered ? 4.5 : 2.5}
                        strokeDasharray={isContradiction ? '8,8' : 'none'}
                        markerEnd={isContradiction ? 'url(#arrowhead-contradiction)' : isSelected || isHovered ? 'url(#arrowhead-selected)' : 'url(#arrowhead)'}
                      />

                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect
                          x={-badgeWidth / 2}
                          y={-14}
                          width={badgeWidth}
                          height={28}
                          fill={isContradiction ? '#450a0a' : isHovered || isSelected ? '#1e3a8a' : '#090d16'}
                          stroke={isContradiction ? '#ef4444' : isHovered || isSelected ? '#60a5fa' : '#334155'}
                          strokeWidth={isHovered || isSelected ? '2' : '1.5'}
                          rx={14}
                          className="shadow-xl transition-all"
                        />
                        <text
                          x={0}
                          y={4}
                          textAnchor="middle"
                          fill={isContradiction ? '#fca5a5' : isSelected || isHovered ? '#ffffff' : '#cbd5e1'}
                          fontSize="12"
                          fontWeight="800"
                          letterSpacing="0.5px"
                          className="select-none uppercase font-mono pointer-events-none"
                        >
                          {labelDisplayText}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </g>

              {/* HIGH-RESOLUTION EXECUTIVE GLASS CARDS */}
              <g className="nodes">
                {filteredNodes.map((node) => {
                  const pos = positions[node.id] || { x: 0, y: 0 };
                  const config = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
                  const IconComponent = config.icon;
                  const isSelected = selectedNode?.id === node.id;

                  const isFocusedMode = Boolean(selectedNode);
                  const isNodeConnected = connectedNodeIds.has(node.id);
                  const nodeOpacity = isFocusedMode ? (isNodeConnected ? 1 : 0.05) : 1;
                  const isNodeDisabled = isFocusedMode && !isNodeConnected;

                  const cardWidth = 280;
                  const cardHeight = 84;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      className={`cursor-grab active:cursor-grabbing group transition-opacity duration-300 ${isNodeDisabled ? 'pointer-events-none' : ''}`}
                      style={{ opacity: nodeOpacity }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        setDraggedNodeId(node.id);
                        setSelectedNode(node);
                        setSelectedEdge(null);
                      }}
                    >
                      {/* Active Halo Glow */}
                      {isSelected && (
                        <rect
                          x={-cardWidth / 2 - 8}
                          y={-cardHeight / 2 - 8}
                          width={cardWidth + 16}
                          height={cardHeight + 16}
                          rx={22}
                          fill="none"
                          stroke={config.border}
                          strokeWidth="4"
                          className="animate-pulse"
                        />
                      )}

                      {/* Card Background Rect */}
                      <rect
                        x={-cardWidth / 2}
                        y={-cardHeight / 2}
                        width={cardWidth}
                        height={cardHeight}
                        rx={18}
                        fill="#0b0f19"
                        stroke={isSelected ? '#ffffff' : '#1e293b'}
                        strokeWidth={isSelected ? '3' : '2'}
                        className="shadow-2xl transition-transform duration-100 group-hover:scale-105"
                      />

                      {/* Colored Type Side Indicator Strip */}
                      <rect
                        x={-cardWidth / 2}
                        y={-cardHeight / 2}
                        width="10"
                        height={cardHeight}
                        rx="5"
                        fill={config.bg}
                      />

                      {/* Entity Icon Container */}
                      <g transform={`translate(${-cardWidth / 2 + 36}, 0)`}>
                        <circle r="20" fill={config.bg} />
                        <foreignObject x={-11} y={-11} width={22} height={22} className="pointer-events-none">
                          <div className="w-full h-full flex items-center justify-center text-white">
                            <IconComponent className="w-4.5 h-4.5" />
                          </div>
                        </foreignObject>
                      </g>

                      {/* Label Text */}
                      <text
                        x={-cardWidth / 2 + 68}
                        y={-8}
                        fill="#ffffff"
                        fontSize="16"
                        fontWeight="800"
                        className="select-none tracking-tight pointer-events-none font-sans"
                      >
                        {node.label.length > 20 ? `${node.label.substring(0, 18)}..` : node.label}
                      </text>

                      {/* Category Badge Pill */}
                      <g transform={`translate(${-cardWidth / 2 + 68}, 18)`}>
                        <rect
                          x="0"
                          y="-11"
                          width="120"
                          height="20"
                          rx="10"
                          fill={config.bg}
                          fillOpacity="0.25"
                          stroke={config.border}
                          strokeWidth="1"
                        />
                        <text
                          x="60"
                          y="3"
                          textAnchor="middle"
                          fill={config.border}
                          fontSize="11"
                          fontWeight="800"
                          className="select-none uppercase tracking-wider font-sans"
                        >
                          {config.albanianLabel}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}

          {/* FLOATING HOVER EVIDENCE TOOLTIP CARD */}
          <AnimatePresence>
            {hoveredEdge && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                style={{
                  position: 'absolute',
                  left: Math.min(window.innerWidth - 380, tooltipPos.x + 20),
                  top: Math.max(20, tooltipPos.y - 40),
                  pointerEvents: 'none'
                }}
                className="z-[200] w-80 p-4 bg-[#090d1a]/95 border border-slate-700/80 rounded-2xl shadow-2xl backdrop-blur-xl space-y-2.5 font-sans"
              >
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                    hoveredEdge.relation.includes('CONTRADICT') || hoveredEdge.relation.includes('KUNDËR')
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse'
                      : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                  }`}>
                    {hoveredEdge.relation.includes('CONTRADICT') || hoveredEdge.relation.includes('KUNDËR') ? '⚠️ ' : '⚖️ '}
                    {formatRelationText(hoveredEdge.relation)}
                  </span>

                  {hoveredEdge.amount_eur && (
                    <span className="text-xs font-mono font-black text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      €{hoveredEdge.amount_eur.toLocaleString()}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-[11px] font-bold text-slate-300 bg-slate-900/60 p-2 rounded-xl border border-slate-800/80">
                  <span className="truncate max-w-[110px] text-white">
                    {nodeMap.get(hoveredEdge.source)?.label || 'Burimi'}
                  </span>
                  <Link2 size={12} className="text-blue-400 shrink-0 mx-1" />
                  <span className="truncate max-w-[110px] text-white">
                    {nodeMap.get(hoveredEdge.target)?.label || 'Caku'}
                  </span>
                </div>

                {hoveredEdge.evidence_text ? (
                  <div className="space-y-1">
                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest block">Dëshmia nga Dokumenti:</span>
                    <p className="text-xs text-slate-200 italic leading-relaxed bg-slate-950/80 p-2.5 rounded-xl border border-slate-800/60 line-clamp-4">
                      &quot;<LawCitationText text={hoveredEdge.evidence_text} />&quot;
                    </p>
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-400 italic">Klikoni për të parë detajet e plotë në fashikull.</p>
                )}
              </motion.div>
            )}
          </AnimatePresence>

        </div>

        {/* EXECUTIVE INTELLIGENCE DOSSIER INSPECTOR PANEL */}
        {(selectedNode || selectedEdge) && (
          <div className="w-96 bg-surface border-l border-main p-5 flex flex-col gap-4 z-20 shadow-2xl shrink-0 overflow-y-auto custom-finance-scroll animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between border-b border-main pb-3">
              <span className="text-xs font-black text-primary-start uppercase tracking-widest flex items-center gap-2">
                <FileCheck size={16} /> {selectedNode ? 'Doshja e Entitetit' : 'Detajet e Lidhjes'}
              </span>
              <button onClick={() => { setSelectedNode(null); setSelectedEdge(null); }} className="p-1 text-text-muted hover:text-text-primary rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            {selectedNode && (
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-4 bg-canvas border border-main rounded-2xl">
                  <div className="p-3 rounded-2xl text-white shrink-0 border border-white/20 shadow-md" style={{ backgroundColor: ENTITY_CONFIG[selectedNode.type].bg }}>
                    {React.createElement(ENTITY_CONFIG[selectedNode.type].icon, { className: 'w-6 h-6 text-white' })}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-black text-base text-text-primary leading-snug">{selectedNode.label}</h4>
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
                  <div className="bg-canvas p-4 rounded-2xl border border-main space-y-1.5">
                    <span className="text-[10px] font-black text-text-muted uppercase tracking-widest block">Roli / Përshkrimi i Plotë</span>
                    <div className="text-xs text-text-secondary leading-relaxed font-medium">
                      <LawCitationText text={selectedNode.description} />
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
                                {otherNode.label}
                              </span>
                            )}
                          </div>
                          {e.evidence_text && (
                            <div className="text-[11px] text-text-secondary italic line-clamp-2 mt-1">
                              &quot;<LawCitationText text={e.evidence_text} />&quot;
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleOpenEntityChat(selectedNode)}
                  className="w-full py-3 bg-primary-start hover:bg-opacity-95 text-white rounded-xl text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-primary-start/15 transition-all"
                >
                  <MessageCircle size={16} /> Pyet AI për këtë person
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
                  <div className="bg-surface p-3 rounded-xl border border-main text-xs text-text-secondary leading-relaxed">
                    <span className="text-[10px] font-bold text-text-muted uppercase block mb-1">Dëshmia nga Dokumentet</span>
                    <div className="italic text-text-primary">
                      &quot;<LawCitationText text={selectedEdge.evidence_text} />&quot;
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* IN-MODAL ENTITY CHAT DRAWER */}
      <AnimatePresence>
        {entityChatOpen && chatEntity && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[250] flex items-center justify-end p-4">
            <motion.div
              initial={{ x: 300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 300, opacity: 0 }}
              className="w-full max-w-lg h-[90vh] bg-canvas border border-main rounded-3xl shadow-2xl flex flex-col overflow-hidden"
            >
              <div className="p-5 bg-surface border-b border-main flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                    <Bot size={20} />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-tight">Hetimi AI: {chatEntity.label}</h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-text-muted font-bold uppercase">{ENTITY_CONFIG[chatEntity.type].albanianLabel}</span>
                      <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full ${
                        clientPosition === 'DEFENDANT' ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30' :
                        clientPosition === 'PLAINTIFF' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' :
                        'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                      }`}>
                        {clientPosition === 'DEFENDANT' ? '🛡️ Mandati: I Paditur (Mbrojtje)' :
                         clientPosition === 'PLAINTIFF' ? '⚔️ Mandati: Paditësi (Sulm)' :
                         '⚖️ Mandati: Neutral / Objektiv'}
                      </span>
                    </div>
                  </div>
                </div>
                <button onClick={() => setEntityChatOpen(false)} className="p-2 text-text-muted hover:text-text-primary rounded-xl">
                  <X size={18} />
                </button>
              </div>

              <div className="flex-1 p-5 overflow-y-auto custom-finance-scroll space-y-6">
                
                {entityMessages.length === 0 && (
                  <div className="text-center space-y-3 pt-4">
                    <h2 className="text-lg font-black text-text-primary uppercase tracking-tight">
                      AGJENTI I HETIMIT: {chatEntity.label}
                    </h2>
                    <p className="text-xs text-text-secondary leading-relaxed font-medium max-w-md mx-auto">
                      {clientPosition === 'DEFENDANT' 
                        ? `Asistenti juaj mbrojtës për prapësimin e kërkesëpadisë dhe shfajësimin që lidhet me ${chatEntity.label}.` 
                        : clientPosition === 'PLAINTIFF'
                        ? `Asistenti juaj sulmues për vërtetimin e përgjegjësisë dhe forcat e padisë lidhur me ${chatEntity.label}.`
                        : `Asistenti juaj neutral për vërtetimin objektiv të barrës së provës dhe paanshmërisë lidhur me ${chatEntity.label}.`}
                    </p>
                    
                    <div className="p-2.5 bg-surface/60 border border-main rounded-xl text-[11px] text-text-muted inline-flex items-center gap-2">
                      <Info size={14} className="text-primary-start shrink-0" />
                      <span>Përgjigjet e AI shërbejnë për referencë dhe verifikohen nga avokati.</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-6 text-left">
                      {entitySuggestedCards.map((card, idx) => {
                        const CardIcon = card.icon;
                        return (
                          <div
                            key={idx}
                            onClick={() => handleSendEntityQuestion(card.query)}
                            className="p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 rounded-2xl cursor-pointer transition-all hover-lift flex flex-col justify-between gap-3 group"
                          >
                            <div className="flex justify-between items-center">
                              <span className="text-[9px] font-black uppercase tracking-widest text-primary-start bg-primary-start/10 px-2 py-0.5 rounded border border-primary-start/20">
                                {card.badge}
                              </span>
                              <ChevronRight size={14} className="text-text-muted group-hover:text-primary-start transition-colors" />
                            </div>
                            <div>
                              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide flex items-center gap-1.5 mb-1">
                                <CardIcon size={14} className="text-primary-start" />
                                {card.title}
                              </h4>
                              <p className="text-[11px] text-text-secondary leading-snug line-clamp-2">{card.desc}</p>
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
                    placeholder={`Bëj një pyetje për ${chatEntity.label}...`}
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