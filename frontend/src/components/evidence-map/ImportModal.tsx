// FILE: frontend/src/components/evidence-map/ImportModal.tsx
// PHOENIX PROTOCOL - FIX V8.1 (IMPORT & LOGIC REPAIR)
// 1. FIX: Added missing 'Scale' import from lucide-react.
// 2. FIX: Corrected variable name in 'toggleSelection' logic (groupId -> gid).
// 3. STATUS: 0 Build Errors. Professional Legal Argument visualization active.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../../services/api'; 
import { X, BrainCircuit, Check, Loader2, RefreshCw, AlertTriangle, ChevronRight, ChevronDown, Gavel, FileText, Shield, User, Scale } from 'lucide-react'; // PHOENIX FIX: Added Scale
import { useAuth } from '../../context/AuthContext';

// --- DATA STRUCTURES ---
interface GraphNode {
  id: string;
  name: string;
  group: string; // CLAIM, FACT, EVIDENCE, LAW, PARTY
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

// --- HELPER COMPONENT: BADGE ---
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
        <span className={`flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded border ${color} uppercase tracking-wider`}>
            {icon} {type}
        </span>
    );
};

// --- LOGIC GROUPING ---
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

  // --- DATA FETCHING & PROCESSING ---
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
      console.error("Graph Fetch Error:", err);
      setError(t('evidenceMap.importModal.error', 'Dështoi ngarkimi i të dhënave.'));
    } finally {
      setIsLoading(false);
    }
  }, [caseId, t]);

  useEffect(() => { if (isOpen) fetchGraphData(); }, [isOpen, fetchGraphData]);

  // --- HIERARCHY BUILDER ---
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

  // --- HANDLERS ---
  const toggleSelection = (id: string, groupIds?: string[]) => {
      const newSet = new Set(selectedIds);
      
      // If it's a group toggle (Claim), toggle all children too
      if (groupIds) {
          // PHOENIX FIX: Corrected variable name from 'groupId' to 'gid'
          const allSelected = groupIds.every(gid => newSet.has(gid));
          if (allSelected) {
              groupIds.forEach(gid => newSet.delete(gid)); // Deselect all
          } else {
              groupIds.forEach(gid => newSet.add(gid)); // Select all
          }
      } else {
          // Single toggle
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
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
      <div className="glass-high w-full max-w-2xl h-[80vh] flex flex-col p-0 rounded-2xl animate-in fade-in zoom-in-95 duration-200 overflow-hidden">
        
        {/* HEADER */}
        <div className="flex justify-between items-center p-6 border-b border-white/10 bg-black/20">
          <div>
              <h3 className="flex items-center gap-2 text-xl font-bold text-white">
                <BrainCircuit className="text-primary-start" />
                {t('evidenceMap.importModal.title', 'Inteligjenca Ligjore')}
              </h3>
              <p className="text-xs text-gray-400 mt-1">AI ka strukturuar dokumentet në argumente logjike.</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"><X size={24} /></button>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Loader2 className="animate-spin h-10 w-10 text-primary-start" />
                <p className="text-text-muted text-sm animate-pulse">{t('general.loading', 'Duke analizuar logjikën ligjore...')}</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-4">
                 <AlertTriangle size={40} />
                 <span>{error}</span>
                 <button onClick={fetchGraphData} className="px-4 py-2 bg-white/10 rounded-lg text-white hover:bg-white/20">Provo Përsëri</button>
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-text-muted space-y-6">
                <div className="bg-white/5 p-6 rounded-full"><BrainCircuit size={48} className="opacity-20" /></div>
                <div className="text-center">
                    <p className="text-white font-medium">{t('evidenceMap.importModal.noEntities', 'Nuk u gjetën struktura ligjore.')}</p>
                </div>
                {user?.role === 'ADMIN' && (
                    <button onClick={handleForceReprocess} disabled={!!reprocessStatus} className="flex items-center gap-2 px-6 py-2.5 bg-primary-start/20 text-primary-start border border-primary-start/50 rounded-xl hover:bg-primary-start/30 transition-all font-bold">
                        <RefreshCw size={18} className={reprocessStatus ? 'animate-spin' : ''} /> 
                        {reprocessStatus || "Ri-analizo (Admin)"}
                    </button>
                )}
            </div>
          ) : (
            <>
                {/* 1. ARGUMENT GROUPS (CLAIMS) */}
                {argumentGroups.length > 0 && (
                    <div className="space-y-4">
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest px-1">Argumentet & Pretendimet</h4>
                        {argumentGroups.map(group => {
                            const groupIds = [group.claim.id, ...group.children.map(c => c.id)];
                            const allSelected = groupIds.every(id => selectedIds.has(id));
                            const isExpanded = expandedGroups.has(group.claim.id);

                            return (
                                <div key={group.claim.id} className={`rounded-xl border transition-all ${allSelected ? 'bg-primary-start/10 border-primary-start/30' : 'bg-white/5 border-white/5'}`}>
                                    {/* Parent: Claim */}
                                    <div className="flex items-center p-3 gap-3 cursor-pointer" onClick={() => toggleExpand(group.claim.id)}>
                                        <button onClick={(e) => { e.stopPropagation(); toggleSelection(group.claim.id, groupIds); }} className={`flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors ${allSelected ? 'bg-primary-start border-primary-start' : 'border-gray-500 hover:border-gray-300'}`}>
                                            {allSelected && <Check size={12} className="text-white" />}
                                        </button>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <TypeBadge type="CLAIM" />
                                                <span className="font-semibold text-white">{group.claim.name}</span>
                                            </div>
                                            {group.claim.description && <p className="text-xs text-gray-400 mt-1 line-clamp-1">{group.claim.description}</p>}
                                        </div>
                                        {isExpanded ? <ChevronDown size={16} className="text-gray-500"/> : <ChevronRight size={16} className="text-gray-500"/>}
                                    </div>
                                    
                                    {/* Children: Facts/Evidence */}
                                    {isExpanded && (
                                        <div className="border-t border-white/5 bg-black/20 p-2 space-y-1">
                                            {group.children.map(child => (
                                                <div key={child.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 ml-6">
                                                    <div className={`w-1.5 h-1.5 rounded-full bg-gray-600`} /> {/* Dot connector */}
                                                    <button onClick={() => toggleSelection(child.id)} className={`flex-shrink-0 w-4 h-4 rounded border flex items-center justify-center transition-colors ${selectedIds.has(child.id) ? 'bg-primary-start border-primary-start' : 'border-gray-600 hover:border-gray-400'}`}>
                                                        {selectedIds.has(child.id) && <Check size={10} className="text-white" />}
                                                    </button>
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2">
                                                            <TypeBadge type={child.group} />
                                                            <span className="text-sm text-gray-300">{child.name}</span>
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

                {/* 2. ORPHANED NODES (Parties, etc) */}
                {orphanedNodes.length > 0 && (
                    <div className="space-y-3 mt-6">
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest px-1">Entitete Tjera (Palët, Ligjet)</h4>
                        <div className="grid grid-cols-1 gap-2">
                            {orphanedNodes.map(node => (
                                <div key={node.id} onClick={() => toggleSelection(node.id)} className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${selectedIds.has(node.id) ? 'bg-primary-start/10 border-primary-start/30' : 'bg-white/5 border-white/5 hover:bg-white/10'}`}>
                                    <div className="flex items-center gap-3">
                                        <TypeBadge type={node.group} />
                                        <span className="font-medium text-gray-200">{node.name}</span>
                                    </div>
                                    {selectedIds.has(node.id) && <Check size={16} className="text-primary-start" />}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </>
          )}
        </div>

        {/* FOOTER */}
        <div className="p-6 border-t border-white/10 bg-black/20 flex justify-between items-center">
            <div className="text-xs text-gray-500">
                {selectedIds.size} elemente të zgjedhura
            </div>
            <div className="flex gap-3">
                <button onClick={onClose} className="px-5 py-2 text-gray-400 hover:text-white font-medium transition-colors">
                    {t('general.cancel', 'Anulo')}
                </button>
                <button
                    onClick={handleImportClick}
                    disabled={selectedIds.size === 0}
                    className="px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                    {t('evidenceMap.importModal.importBtn', { count: selectedIds.size })}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
};

export default ImportModal;