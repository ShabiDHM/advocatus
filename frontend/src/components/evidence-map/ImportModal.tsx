// FILE: frontend/src/components/evidence-map/ImportModal.tsx
// PHOENIX PROTOCOL - FIX V9.0 (MOBILE UI RECONSTRUCTION)
// 1. FIX: Switched from fixed h-[80vh] to responsive max-h-[90dvh] for mobile safety.
// 2. FIX: Reduced padding on mobile (p-4) vs desktop (p-6) to reclaim screen space.
// 3. FIX: Enhanced text-wrapping for long legal entity names to prevent layout breaking.
// 4. FIX: Optimized footer button layout for touch targets on narrow screens.

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
  label: string;
}

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  caseId: string;
}

const TypeBadge = ({ type }: { type: string }) => {
    let color = "bg-gray-500/20 text-gray-400";
    let icon = <BrainCircuit size={10} />;
    
    switch(type.toUpperCase()) {
        case 'CLAIM': color = "bg-green-500/20 text-green-400 border-green-500/30"; icon = <Gavel size={10} />; break;
        case 'FACT': color = "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"; icon = <Shield size={10} />; break;
        case 'EVIDENCE': color = "bg-blue-500/20 text-blue-400 border-blue-500/30"; icon = <FileText size={10} />; break;
        case 'LAW': color = "bg-purple-500/20 text-purple-400 border-purple-500/30"; icon = <Scale size={10} />; break; 
        case 'PARTY': color = "bg-orange-500/20 text-orange-400 border-orange-500/30"; icon = <User size={10} />; break;
    }

    return (
        <span className={`flex items-center gap-1 text-[9px] sm:text-[10px] font-bold px-1.5 py-0.5 rounded border ${color} uppercase tracking-wider whitespace-nowrap`}>
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
      const validEdges = graphResponse.links || [];
      setNodes(validNodes);
      setEdges(validEdges);
    } catch (err) {
      setError(t('evidenceMap.importModal.error', 'Dështoi ngarkimi i të dhënave.'));
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
    setReprocessStatus(t('reprocess.starting', 'Duke filluar...'));
    try {
        await apiService.reprocessCaseDocuments(caseId);
        setReprocessStatus(t('reprocess.success', 'U nis me sukses.'));
        setTimeout(() => { setReprocessStatus(null); fetchGraphData(); }, 3000);
    } catch (e) {
        setReprocessStatus(t('reprocess.error', 'Gabim.'));
        setTimeout(() => setReprocessStatus(null), 3000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-xl flex items-center justify-center z-[1100] p-3 sm:p-4">
      <div className="bg-[#121214] border border-white/10 w-full max-w-2xl max-h-[90dvh] flex flex-col rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* HEADER */}
        <div className="flex justify-between items-center p-4 sm:p-6 border-b border-white/5 bg-white/[0.02]">
          <div className="pr-4">
              <h3 className="flex items-center gap-2 text-lg sm:text-xl font-bold text-white leading-tight">
                <BrainCircuit className="text-blue-500 shrink-0" size={24} />
                {t('evidenceMap.importModal.title', 'Importo nga Analiza e AI')}
              </h3>
              <p className="text-[11px] sm:text-xs text-gray-400 mt-1">AI ka strukturuar dokumentet në argumente logjike.</p>
          </div>
          <button onClick={onClose} className="shrink-0 text-gray-500 hover:text-white p-2 rounded-full hover:bg-white/5 transition-colors"><X size={24} /></button>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 sm:p-6 space-y-5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <Loader2 className="animate-spin h-10 w-10 text-blue-500" />
                <p className="text-gray-400 text-sm animate-pulse">{t('general.loading', 'Duke analizuar logjikën ligjore...')}</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-10 text-red-400 space-y-4 text-center">
                 <AlertTriangle size={32} />
                 <span className="text-sm px-4">{error}</span>
                 <button onClick={fetchGraphData} className="px-6 py-2 bg-white/5 rounded-full text-white hover:bg-white/10 text-sm border border-white/10">Provo Përsëri</button>
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500 space-y-6">
                <BrainCircuit size={48} className="opacity-10" />
                <p className="text-white text-sm font-medium">{t('evidenceMap.importModal.noEntities', 'Nuk u gjetën struktura ligjore.')}</p>
                {user?.role === 'ADMIN' && (
                    <button onClick={handleForceReprocess} disabled={!!reprocessStatus} className="flex items-center gap-2 px-6 py-2.5 bg-blue-600/10 text-blue-400 border border-blue-600/30 rounded-full hover:bg-blue-600/20 text-xs font-bold uppercase tracking-wider transition-all">
                        <RefreshCw size={14} className={reprocessStatus ? 'animate-spin' : ''} /> 
                        {reprocessStatus || "Ri-analizo (Admin)"}
                    </button>
                )}
            </div>
          ) : (
            <>
                {argumentGroups.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em] px-1">Argumentet & Pretendimet</h4>
                        {argumentGroups.map(group => {
                            const groupIds = [group.claim.id, ...group.children.map(c => c.id)];
                            const allSelected = groupIds.every(id => selectedIds.has(id));
                            const isExpanded = expandedGroups.has(group.claim.id);

                            return (
                                <div key={group.claim.id} className={`rounded-2xl border transition-all ${allSelected ? 'bg-blue-600/5 border-blue-500/30' : 'bg-white/[0.03] border-white/5 hover:border-white/10'}`}>
                                    <div className="flex items-start p-3 gap-3 cursor-pointer" onClick={() => toggleExpand(group.claim.id)}>
                                        <button onClick={(e) => { e.stopPropagation(); toggleSelection(group.claim.id, groupIds); }} className={`mt-1 shrink-0 w-5 h-5 rounded-md border flex items-center justify-center transition-all ${allSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-600 hover:border-gray-400'}`}>
                                            {allSelected && <Check size={12} className="text-white" strokeWidth={4} />}
                                        </button>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex flex-wrap items-center gap-2 mb-1">
                                                <TypeBadge type="CLAIM" />
                                                <span className="font-bold text-sm text-white truncate">{group.claim.name}</span>
                                            </div>
                                            {group.claim.description && <p className="text-[11px] text-gray-500 line-clamp-2 leading-relaxed">{group.claim.description}</p>}
                                        </div>
                                        <div className="shrink-0 mt-1">{isExpanded ? <ChevronDown size={18} className="text-gray-500"/> : <ChevronRight size={18} className="text-gray-500"/>}</div>
                                    </div>
                                    
                                    {isExpanded && (
                                        <div className="border-t border-white/5 bg-black/40 p-2 space-y-1">
                                            {group.children.map(child => (
                                                <div key={child.id} onClick={() => toggleSelection(child.id)} className="flex items-start gap-3 p-2 rounded-xl hover:bg-white/5 cursor-pointer ml-4 sm:ml-6">
                                                    <button className={`mt-0.5 shrink-0 w-4 h-4 rounded border flex items-center justify-center transition-all ${selectedIds.has(child.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-700 hover:border-gray-500'}`}>
                                                        {selectedIds.has(child.id) && <Check size={10} className="text-white" strokeWidth={4} />}
                                                    </button>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <TypeBadge type={child.group} />
                                                            <span className="text-xs text-gray-300 font-medium truncate">{child.name}</span>
                                                        </div>
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
                    <div className="space-y-2 mt-6">
                        <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em] px-1">Entitete Tjera</h4>
                        <div className="grid grid-cols-1 gap-2">
                            {orphanedNodes.map(node => (
                                <div key={node.id} onClick={() => toggleSelection(node.id)} className={`flex items-center justify-between p-3 rounded-2xl border cursor-pointer transition-all ${selectedIds.has(node.id) ? 'bg-blue-600/10 border-blue-500/30' : 'bg-white/[0.03] border-white/5 hover:bg-white/10'}`}>
                                    <div className="flex items-center gap-3 overflow-hidden">
                                        <TypeBadge type={node.group} />
                                        <span className="font-semibold text-xs text-gray-200 truncate">{node.name}</span>
                                    </div>
                                    {selectedIds.has(node.id) && <div className="shrink-0 bg-blue-500 rounded-full p-0.5"><Check size={12} className="text-white" strokeWidth={4} /></div>}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </>
          )}
        </div>

        {/* FOOTER */}
        <div className="p-4 sm:p-6 border-t border-white/5 bg-white/[0.01] flex flex-col sm:flex-row gap-4 justify-between items-center">
            <div className="text-[11px] font-bold text-gray-500 uppercase tracking-widest order-2 sm:order-1">
                {selectedIds.size} {t('evidenceMap.importModal.selected', 'elemente të zgjedhura')}
            </div>
            <div className="flex gap-3 w-full sm:w-auto order-1 sm:order-2">
                <button onClick={onClose} className="flex-1 sm:flex-none px-6 py-2.5 text-xs font-bold text-gray-400 hover:text-white transition-colors">
                    {t('general.cancel', 'Anulo')}
                </button>
                <button
                    onClick={handleImportClick}
                    disabled={selectedIds.size === 0}
                    className="flex-1 sm:flex-none px-8 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 text-white rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl shadow-blue-900/20 transition-all active:scale-95 disabled:text-gray-600 disabled:cursor-not-allowed"
                >
                    {t('evidenceMap.importModal.importBtn', 'Importo')}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
};

export default ImportModal;