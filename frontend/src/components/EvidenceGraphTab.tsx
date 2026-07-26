// FILE: frontend/src/components/EvidenceGraphTab.tsx
// PHOENIX PROTOCOL - MINI-FOUNDRY EVIDENCE GRAPH TAB V30.0 (INTEGRATED LAW CITATION TEXT)

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
  Swords
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

const ENTITY_CONFIG: Record<EntityType, { albanianLabel: string; bg: string; icon: LucideIcon; size: number }> = {
  PERSON: { albanianLabel: 'Persona', bg: '#eab308', icon: User, size: 36 },
  ORGANIZATION: { albanianLabel: 'Institucione', bg: '#a855f7', icon: Building2, size: 38 },
  ACCOUNT: { albanianLabel: 'Llogari', bg: '#10b981', icon: CreditCard, size: 34 },
  LOCATION: { albanianLabel: 'Lokacione', bg: '#06b6d4', icon: MapPin, size: 32 },
  EVENT: { albanianLabel: 'Ngjarje', bg: '#ef4444', icon: Calendar, size: 34 },
  DOCUMENT: { albanianLabel: 'Dokumente', bg: '#3b82f6', icon: FileText, size: 32 },
};

const RELATION_ALBANIAN_MAP: Record<string, string> = {
  REPRESENTED_BY: 'PËRFAQËSOHET_NGA',
  ASSOCIATED_WITH: 'LIDHUR_ME',
  TRANSFERRED_FUNDS: 'TRANSAKSION',
  EMPLOYED_BY: 'PUNËSUAR_NË',
  OWNED_BY: 'PRONËSI_E',
  PRESENT_AT: 'PRANISHËM_NË',
  LOCATED_AT: 'LOKACIONI',
  LOCATED_IN: 'LOKACIONI',
  CONTRADICTS: 'KUNDËRTHËNJE',
  OWES_MONEY: 'DETYRIM',
  SIGNED: 'NËNSHKRUAR',
  MENTIONED_IN: 'PËRMENDUR_NË',
  HAS_ACCOUNT: 'LLOGARI_BANKARE',
  WORKED_AT: 'PUNËSUAR_NË',
  PARTY_TO: 'PALË_NË'
};

const formatRelationText = (rel: string): string => {
  const clean = rel.toUpperCase().trim().replace(/ /g, '_');
  return RELATION_ALBANIAN_MAP[clean] || clean;
};

const getLineRotationAngle = (x1: number, y1: number, x2: number, y2: number): number => {
  const dx = x2 - x1;
  const dy = y2 - y1;
  let angle = Math.atan2(dy, dx) * (180 / Math.PI);
  if (angle > 90 || angle < -90) {
    angle += 180;
  }
  return angle;
};

export const EvidenceGraphTab: React.FC<EvidenceGraphTabProps> = ({ caseId }) => {
  const [graphData, setGraphData] = useState<CaseGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [clientPosition, setClientPosition] = useState<'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'>('DEFENDANT');

  const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<OntologyEdge | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);

  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

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
  const [viewBox, setViewBox] = useState({ x: -600, y: -400, width: 1200, height: 800 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPoint, setStartPoint] = useState({ x: 0, y: 0 });

  const lastTouchDistRef = useRef<number | null>(null);

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
    return graphData.nodes.filter((node) => {
      const matchesType = activeFilter === 'ALL' || node.type === activeFilter;
      const matchesSearch =
        !searchQuery ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (node.description && node.description.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesType && matchesSearch;
    });
  }, [graphData?.nodes, activeFilter, searchQuery]);

  useEffect(() => {
    if (filteredNodes.length === 0) return;
    const initialPos: Record<string, { x: number; y: number }> = {};
    
    const clusters: Record<string, OntologyNode[]> = {};
    filteredNodes.forEach(n => {
      if (!clusters[n.type]) clusters[n.type] = [];
      clusters[n.type].push(n);
    });

    const clusterKeys = Object.keys(clusters);
    const numClusters = clusterKeys.length;

    clusterKeys.forEach((typeKey, cIndex) => {
      const clusterNodes = clusters[typeKey];
      const clusterAngle = (cIndex * 2 * Math.PI) / numClusters;
      const clusterCenterX = Math.cos(clusterAngle) * 400;
      const clusterCenterY = Math.sin(clusterAngle) * 280;

      const subRadius = Math.max(150, clusterNodes.length * 36);

      clusterNodes.forEach((node, nIndex) => {
        const subAngle = (nIndex * 2 * Math.PI) / clusterNodes.length;
        initialPos[node.id] = {
          x: Math.round(clusterCenterX + Math.cos(subAngle) * subRadius),
          y: Math.round(clusterCenterY + Math.sin(subAngle) * subRadius)
        };
      });
    });

    setPositions(initialPos);
  }, [filteredNodes]);

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

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        lastTouchDistRef.current = dist;
      } else if (e.touches.length === 1) {
        setIsPanning(true);
        setStartPoint({ x: e.touches[0].clientX, y: e.touches[0].clientY });
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && lastTouchDistRef.current !== null) {
        e.preventDefault();
        const currentDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        
        const delta = currentDist - lastTouchDistRef.current;
        const zoomFactor = delta > 0 ? 0.96 : 1.04;

        setViewBox((prev) => ({
          x: prev.x + (prev.width * (1 - zoomFactor)) / 2,
          y: prev.y + (prev.height * (1 - zoomFactor)) / 2,
          width: prev.width * zoomFactor,
          height: prev.height * zoomFactor,
        }));

        lastTouchDistRef.current = currentDist;
      } else if (e.touches.length === 1 && isPanning) {
        e.preventDefault();
        const dx = (e.touches[0].clientX - startPoint.x) * (viewBox.width / 1200);
        const dy = (e.touches[0].clientY - startPoint.y) * (viewBox.height / 800);
        setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
        setStartPoint({ x: e.touches[0].clientX, y: e.touches[0].clientY });
      }
    };

    const handleTouchEnd = () => {
      lastTouchDistRef.current = null;
      setIsPanning(false);
    };

    svgEl.addEventListener('wheel', handleWheel, { passive: false });
    svgEl.addEventListener('touchstart', handleTouchStart, { passive: false });
    svgEl.addEventListener('touchmove', handleTouchMove, { passive: false });
    svgEl.addEventListener('touchend', handleTouchEnd, { passive: false });

    return () => {
      svgEl.removeEventListener('wheel', handleWheel);
      svgEl.removeEventListener('touchstart', handleTouchStart);
      svgEl.removeEventListener('touchmove', handleTouchMove);
      svgEl.removeEventListener('touchend', handleTouchEnd);
    };
  }, [loading, isPanning, viewBox, startPoint]);

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
    setViewBox({ x: -600, y: -400, width: 1200, height: 800 });
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
      const dx = (e.clientX - startPoint.x) * (viewBox.width / 1200);
      const dy = (e.clientY - startPoint.y) * (viewBox.height / 800);
      setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
      setStartPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
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

  // ROLE-BIASED SUGGESTED ACTION CARDS (STRICTLY TAILORED FOR DEFENDANT VS PLAINTIFF VS NEUTRAL)
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
    <div className="flex flex-col h-full w-full bg-canvas text-text-primary rounded-2xl border border-main overflow-hidden shadow-xl relative">
      
      {/* CONTROL BAR */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface border-b border-main gap-2 z-10 shrink-0 h-12">
        <div className="flex items-center gap-2 min-w-0 flex-1">
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

      <div className="flex-1 flex relative overflow-hidden bg-canvas">
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
              className="w-full h-full cursor-grab active:cursor-grabbing select-none touch-none"
              viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
            >
              <defs>
                <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="36" refY="2" orient="auto">
                  <polygon points="0 0, 6 2, 0 4" fill="#94a3b8" />
                </marker>
                <marker id="arrowhead-selected" markerWidth="6" markerHeight="4" refX="36" refY="2" orient="auto">
                  <polygon points="0 0, 6 2, 0 4" fill="#3b82f6" />
                </marker>
                <marker id="arrowhead-contradiction" markerWidth="6" markerHeight="4" refX="36" refY="2" orient="auto">
                  <polygon points="0 0, 6 2, 0 4" fill="#ef4444" />
                </marker>
              </defs>

              <g className="edges">
                {filteredEdges.map((edge) => {
                  const sourcePos = positions[edge.source];
                  const targetPos = positions[edge.target];
                  if (!sourcePos || !targetPos) return null;

                  const isContradiction = edge.relation.includes('CONTRADICT') || edge.relation.includes('KUNDËR');
                  const isSelected = selectedEdge?.id === edge.id;
                  const isHovered = hoveredEdgeId === edge.id;

                  const midX = (sourcePos.x + targetPos.x) / 2;
                  const midY = (sourcePos.y + targetPos.y) / 2;

                  const albanianLabel = formatRelationText(edge.relation);
                  const angle = getLineRotationAngle(sourcePos.x, sourcePos.y, targetPos.x, targetPos.y);

                  const labelDisplayText = edge.amount_eur ? `€${edge.amount_eur.toLocaleString()}` : albanianLabel;
                  const maskWidth = Math.max(50, labelDisplayText.length * 6.5);

                  return (
                    <g
                      key={edge.id}
                      className="group cursor-pointer"
                      onClick={() => setSelectedEdge(edge)}
                      onMouseEnter={() => setHoveredEdgeId(edge.id)}
                      onMouseLeave={() => setHoveredEdgeId(null)}
                    >
                      <line
                        x1={sourcePos.x}
                        y1={sourcePos.y}
                        x2={targetPos.x}
                        y2={targetPos.y}
                        stroke="transparent"
                        strokeWidth="24"
                      />

                      <line
                        x1={sourcePos.x}
                        y1={sourcePos.y}
                        x2={targetPos.x}
                        y2={targetPos.y}
                        stroke={isContradiction ? '#ef4444' : isSelected || isHovered ? '#3b82f6' : '#94a3b8'}
                        strokeWidth={isContradiction || isSelected || isHovered ? 3 : 1.8}
                        strokeDasharray={isContradiction ? '5,5' : 'none'}
                        markerEnd={isContradiction ? 'url(#arrowhead-contradiction)' : isSelected ? 'url(#arrowhead-selected)' : 'url(#arrowhead)'}
                        opacity={isHovered || isSelected || isContradiction ? 1 : 0.75}
                      />

                      <g transform={`translate(${midX}, ${midY}) rotate(${angle})`}>
                        <rect
                          x={-maskWidth / 2}
                          y={-8}
                          width={maskWidth}
                          height={16}
                          fill="var(--bg-canvas, #090d16)"
                          rx={3}
                        />
                        <text
                          x={0}
                          y={4}
                          textAnchor="middle"
                          fill={isContradiction ? '#ef4444' : isSelected || isHovered ? '#3b82f6' : '#cbd5e1'}
                          fontSize="10"
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

              <g className="nodes">
                {filteredNodes.map((node) => {
                  const pos = positions[node.id] || { x: 0, y: 0 };
                  const config = ENTITY_CONFIG[node.type] || ENTITY_CONFIG.PERSON;
                  const isSelected = selectedNode?.id === node.id;

                  const labelText = node.label.length > 14 ? `${node.label.substring(0, 12)}..` : node.label;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      className="cursor-grab active:cursor-grabbing group"
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        setDraggedNodeId(node.id);
                        setSelectedNode(node);
                        setSelectedEdge(null);
                      }}
                    >
                      {isSelected && (
                        <circle r={config.size + 10} fill="none" stroke="#3b82f6" strokeWidth="3.5" className="animate-pulse" />
                      )}

                      <circle
                        r={config.size}
                        fill={config.bg}
                        stroke="#ffffff"
                        strokeWidth="3"
                        className="transition-transform duration-100 group-hover:scale-110 shadow-2xl"
                      />

                      <text
                        y="4"
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize="11"
                        fontWeight="900"
                        className="select-none uppercase tracking-tight pointer-events-none font-sans"
                      >
                        {labelText}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
        </div>

        {/* EXECUTIVE INTELLIGENCE DOSSIER INSPECTOR PANEL */}
        {(selectedNode || selectedEdge) && (
          <div className="w-96 bg-surface border-l border-main p-5 flex flex-col gap-4 z-20 shadow-2xl shrink-0 overflow-y-auto custom-finance-scroll">
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

      {/* IN-MODAL ENTITY CHAT DRAWER WITH DYNAMIC ROLE MANDATE (DEFENDANT | PLAINTIFF | NEUTRAL) */}
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