// FILE: frontend/src/components/evidence-map/ImportModal.tsx
// PHOENIX PROTOCOL - FIX V13.0 (PROFESSIONAL MOBILE DENSITY)
// 1. FIX: Switched footer to horizontal layout on mobile to reclaim vertical space.
// 2. FIX: Reduced header height and icon scale for mobile viewports.
// 3. UI: Tightened card padding (p-2) and reduced spacing (space-y-2) to maximize content visibility.
// 4. UI: Added subtle glassmorphism to the body area for a high-end feel.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../../services/api'; 
import { X, BrainCircuit, Check, Loader2, RefreshCw, AlertTriangle, ChevronRight, ChevronDown, Gavel, FileText, Shield, User, Scale } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface GraphNode {
  id: string;
  name: string;
  group: string; 
  description?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  caseId: string;
}

const TypeBadge = ({ type }: { type: string }) => {
    let color = "bg-gray-500/20 text-gray-400";
    let icon = <BrainCircuit size={7} />;
    
    switch(type.toUpperCase()) {
        case 'CLAIM': color = "bg-green-500/20 text-green-400 border-green-500/30"; icon = <Gavel size={7} />; break;
        case 'FACT': color = "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"; icon = <Shield size={7} />; break;
        case 'EVIDENCE': color = "bg-blue-500/20 text-blue-400 border-blue-500/30"; icon = <FileText size={7} />; break;
        case 'LAW': color = "bg-purple-500/20 text-purple-400 border-purple-500/30"; icon = <Scale size={7} />; break; 
        case 'PARTY': color = "bg-orange-500/20 text-orange-400 border-orange-500/30"; icon = <User size={7} />; break;
    }

    return (
        <span className={`flex items-center gap-1 text-[7px] sm:text-[9px] font-bold px-1 py-0.5 rounded border ${color} uppercase tracking-tighter whitespace-nowrap`}>
            {icon} {type}
        </span>
    );
};

interface ArgumentGroup {
    claim: GraphNode;
    children: GraphNode[];
}

const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onImport, caseId }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [reprocessStatus, setReprocessStatus] = useState<string | null>(null);

  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const graphResponse = await apiService.getCaseGraph(caseId);
      const validNodes = (graphResponse.nodes || []).filter((n: any) => n.group !== 'DOCUMENT');
      const validEdges = (graphResponse.links || []).map((l: any) => ({
        source: l.source, target: l.target,
        relation: l.label || l.relation || 'LIDHET'
      }));
      setNodes(validNodes);
      setEdges(validEdges);
    } catch (err) {
      setError(t('evidenceMap.importModal.error', 'Dështoi ngarkimi.'));
    } finally {
      setIsLoading(false);
    }
  }, [caseId, t]);

  useEffect(() => { if (isOpen) fetchGraphData(); }, [isOpen, fetchGraphData]);

  const { argumentGroups, orphanedNodes } = useMemo(() => {
      const claims = nodes.filter(n => n.group === 'CLAIM');
      const groupedIds = new Set<string>();
      const groups: ArgumentGroup[] = [];

      claims.forEach(claim => {
          const directLinks = edges.filter(e => e.target === claim.id || e.source === claim.id);
          const childIds = new Set<string>(directLinks.map(e => e.target === claim.id ? e.source : e.target));
          const children = nodes.filter(n => childIds.has(n.id) && n.id !== claim.id);
          children.forEach(c => groupedIds.add(c.id));
          groupedIds.add(claim.id);
          groups.push({ claim, children });
      });

      const orphans = nodes.filter(n => !groupedIds.has(n.id));
      return { argumentGroups: groups, orphanedNodes: orphans };
  }, [nodes, edges]);

  const toggleSelection = (id: string, groupIds?: string[]) => {
      const newSet = new Set(selectedIds);
      if (groupIds) {
          const allSelected = groupIds.every(gid => newSet.has(gid));
          if (allSelected) groupIds.forEach(gid => newSet.delete(gid));
          else groupIds.forEach(gid => newSet.add(gid));
      } else {
          if (newSet.has(id)) newSet.delete(id);
          else newSet.add(id);
      }
      setSelectedIds(newSet);
  };

  const toggleExpand = (id: string) => {
      const newSet = new Set(expandedGroups);
      if (newSet.has(id)) newSet.delete(id);
      else newSet.add(id);
      setExpandedGroups(newSet);
  };

  const handleImportClick = () => {
      const selectedNodes = nodes.filter(n => selectedIds.has(n.id));
      const selectedEdges = edges.filter(e => selectedIds.has(e.source) && selectedIds.has(e.target));
      onImport(selectedNodes, selectedEdges);
      onClose();
      setSelectedIds(new Set());
  };

  const handleForceReprocess = async () => {
    if (user?.role !== 'ADMIN') return;
    setReprocessStatus("Duke u nisur...");
    try {
        await apiService.reprocessCaseDocuments(caseId);
        setReprocessStatus("U nis!");
        setTimeout(() => { setReprocessStatus(null); fetchGraphData(); }, 3000);
    } catch (e) {
        setReprocessStatus("Gabim");
        setTimeout(() => setReprocessStatus(null), 3000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/95 backdrop-blur-md flex items-center justify-center z-[1100] p-3 sm:p-4 font-sans">
      <div className="bg-[#0f0f11] border border-white/10 w-full max-w-xl max-h-[80dvh] flex flex-col rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* COMPACT HEADER */}
        <div className="flex justify-between items-center px-4 py-3 border-b border-white/5 bg-white/[0.02]">
          <div className="flex items-center gap-2">
              <BrainCircuit className="text-blue-500" size={18} />
              <h3 className="text-sm sm:text-base font-bold text-white tracking-tight">
                {t('evidenceMap.importModal.title', 'Analiza e AI')}
              </h3>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1 rounded-full hover:bg-white/5 transition-colors"><X size={18} /></button>
        </div>

        {/* COMPACT BODY */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-3">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-10 space-y-2">
                <Loader2 className="animate-spin h-6 w-6 text-blue-500" />
                <p className="text-gray-500 text-[10px] uppercase tracking-widest animate-pulse">Duke analizuar...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-6 text-red-400 space-y-2 text-center">
                 <AlertTriangle size={20} />
                 <span className="text-[11px] px-4">{error}</span>
                 <button onClick={fetchGraphData} className="px-3 py-1 bg-white/5 rounded-full text-white text-[10px] border border-white/10">Rifillo</button>
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-gray-600 space-y-3">
                <BrainCircuit size={32} className="opacity-10" />
                <p className="text-white text-[11px] font-medium uppercase tracking-tight">Nuk u gjetën të dhëna</p>
                {user?.role === 'ADMIN' && (
                    <button onClick={handleForceReprocess} disabled={!!reprocessStatus} className="px-3 py-1.5 bg-blue-600/10 text-blue-400 border border-blue-600/20 rounded-full text-[9px] font-black uppercase transition-all">
                        <RefreshCw size={10} className={reprocessStatus ? 'animate-spin' : ''} /> {reprocessStatus || "Ri-analizo"}
                    </button>
                )}
            </div>
          ) : (
            <>
                {argumentGroups.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-[8px] font-black text-gray-600 uppercase tracking-[0.2em] px-1">Argumentet</h4>
                        {argumentGroups.map(group => {
                            const groupIds = [group.claim.id, ...group.children.map(c => c.id)];
                            const allSelected = groupIds.every(id => selectedIds.has(id));
                            const isExpanded = expandedGroups.has(group.claim.id);

                            return (
                                <div key={group.claim.id} className={`rounded-xl border transition-all ${allSelected ? 'bg-blue-600/5 border-blue-500/20' : 'bg-white/[0.02] border-white/5'}`}>
                                    <div className="flex items-start p-2 gap-2.5 cursor-pointer" onClick={() => toggleExpand(group.claim.id)}>
                                        <button onClick={(e) => { e.stopPropagation(); toggleSelection(group.claim.id, groupIds); }} className={`mt-0.5 shrink-0 w-4 h-4 rounded-md border flex items-center justify-center transition-all ${allSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-800 hover:border-gray-600'}`}>
                                            {allSelected && <Check size={10} strokeWidth={4} className="text-white" />}
                                        </button>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-1.5 mb-0.5">
                                                <TypeBadge type="CLAIM" />
                                                <span className="font-bold text-[12px] text-white truncate leading-none">{group.claim.name}</span>
                                            </div>
                                            {group.claim.description && <p className="text-[10px] text-gray-500 line-clamp-1 italic">{group.claim.description}</p>}
                                        </div>
                                        <div className="shrink-0 mt-0.5">{isExpanded ? <ChevronDown size={14} className="text-gray-700"/> : <ChevronRight size={14} className="text-gray-700"/>}</div>
                                    </div>
                                    
                                    {isExpanded && (
                                        <div className="border-t border-white/5 bg-black/40 p-1.5 space-y-1">
                                            {group.children.map(child => (
                                                <div key={child.id} onClick={() => toggleSelection(child.id)} className="flex items-start gap-2.5 p-1.5 rounded-lg hover:bg-white/5 cursor-pointer ml-4">
                                                    <button className={`mt-0.5 shrink-0 w-3.5 h-3.5 rounded-sm border flex items-center justify-center transition-all ${selectedIds.has(child.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-800 hover:border-gray-700'}`}>
                                                        {selectedIds.has(child.id) && <Check size={8} strokeWidth={4} className="text-white" />}
                                                    </button>
                                                    <div className="flex-1 min-w-0 flex items-center gap-1.5">
                                                        <TypeBadge type={child.group} />
                                                        <span className="text-[11px] text-gray-400 truncate leading-none">{child.name}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {orphanedNodes.length > 0 && (
                    <div className="space-y-1.5 mt-4">
                        <h4 className="text-[8px] font-black text-gray-600 uppercase tracking-[0.2em] px-1">Tjera</h4>
                        <div className="grid grid-cols-1 gap-1.5">
                            {orphanedNodes.map(node => (
                                <div key={node.id} onClick={() => toggleSelection(node.id)} className={`flex items-center justify-between p-2 rounded-xl border transition-all ${selectedIds.has(node.id) ? 'bg-blue-600/10 border-blue-500/20' : 'bg-white/[0.02] border-white/5'}`}>
                                    <div className="flex items-center gap-2 overflow-hidden">
                                        <TypeBadge type={node.group} />
                                        <span className="font-semibold text-[11px] text-gray-300 truncate">{node.name}</span>
                                    </div>
                                    {selectedIds.has(node.id) && <Check size={12} className="text-blue-500 shrink-0" strokeWidth={3} />}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </>
          )}
        </div>

        {/* TIGHT FOOTER (HORIZONTAL ON MOBILE) */}
        <div className="px-4 py-3 border-t border-white/5 bg-white/[0.01] flex items-center justify-between gap-4">
            <div className="text-[9px] font-black text-gray-600 uppercase tracking-widest whitespace-nowrap">
                {selectedIds.size} ZGTHEDHURA
            </div>
            <div className="flex gap-2 w-auto">
                <button onClick={onClose} className="px-3 py-2 text-[10px] font-bold text-gray-500 hover:text-white transition-colors">
                    ANULO
                </button>
                <button
                    onClick={handleImportClick}
                    disabled={selectedIds.size === 0}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 text-white rounded-xl font-black text-[10px] uppercase tracking-widest transition-all active:scale-95 disabled:text-gray-700"
                >
                    {t('evidenceMap.importModal.importBtn', { defaultValue: 'IMPORTO', count: selectedIds.size })}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
};

export default ImportModal;