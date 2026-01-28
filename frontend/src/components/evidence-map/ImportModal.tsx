// FILE: frontend/src/components/evidence-map/ImportModal.tsx
// PHOENIX PROTOCOL - FIX V7.2 (UNUSED VAR CLEANUP)
// 1. FIX: Removed redundant 'caseDocuments' state to resolve TS6133 warning.
// 2. STATUS: Fully optimized for server-side bulk reprocessing.

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../../services/api'; 
import { X, BrainCircuit, Check, Loader2, RefreshCw, AlertTriangle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface KnowledgeGraphNode {
  id: string;
  name: string;
  group: string;
}

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (selectedNames: string[]) => void;
  caseId: string;
}

const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onImport, caseId }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  
  const [nodes, setNodes] = useState<KnowledgeGraphNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [reprocessStatus, setReprocessStatus] = useState<string | null>(null);

  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // PHOENIX FIX: We no longer need to fetch docs list here as reprocess-all is server-side
      const graphResponse = await apiService.getCaseGraph(caseId);
      if (graphResponse && graphResponse.nodes) {
          const entityNodes = graphResponse.nodes.filter((n: any) => n.group !== 'DOCUMENT');
          setNodes(entityNodes);
      } else {
          setNodes([]);
      }
    } catch (err) {
      console.error("ImportModal Fetch Error:", err);
      setError(t('evidenceMap.importModal.error', 'Dështoi ngarkimi i të dhënave nga AI.'));
    } finally {
      setIsLoading(false);
    }
  }, [caseId, t]);

  useEffect(() => {
    if (isOpen) {
        fetchGraphData();
    }
  }, [isOpen, fetchGraphData]);

  const handleForceReprocess = async () => {
    if (!user || user.role !== 'ADMIN') return;
    setReprocessStatus(t('reprocess.starting', 'Duke filluar...'));
    
    try {
        await apiService.reprocessCaseDocuments(caseId);
        setReprocessStatus(t('reprocess.success', 'U nis me sukses.'));
        setTimeout(() => {
            setReprocessStatus(null);
            fetchGraphData();
        }, 3000);
    } catch (e) {
        setReprocessStatus(t('reprocess.error', 'Gabim gjatë procesimit.'));
        setTimeout(() => setReprocessStatus(null), 3000);
    }
  };

  const handleToggleSelect = (nodeName: string) => {
    setSelected(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeName)) newSet.delete(nodeName);
      else newSet.add(nodeName);
      return newSet;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
      <div className="glass-high w-full max-w-lg h-[70vh] flex flex-col p-6 rounded-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex-shrink-0 flex justify-between items-center mb-4">
          <h3 className="flex items-center gap-2 text-xl font-bold text-white">
            <BrainCircuit className="text-primary-start" />
            {t('evidenceMap.importModal.title', 'Importo nga Analiza e AI')}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"><X size={24} /></button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2 mb-4 border-t border-b border-white/10 py-6">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Loader2 className="animate-spin h-10 w-10 text-primary-start" />
                <p className="text-text-muted text-sm animate-pulse">{t('general.loading', 'Duke kërkuar për të dhëna të reja...')}</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-4 p-4 text-center">
                 <AlertTriangle size={40} />
                 <span>{error}</span>
                 <button onClick={fetchGraphData} className="px-4 py-2 bg-white/10 rounded-lg text-white hover:bg-white/20">Prova Përsëri</button>
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-text-muted space-y-6 p-4">
                <div className="bg-white/5 p-6 rounded-full">
                    <BrainCircuit size={48} className="opacity-20" />
                </div>
                <div className="text-center space-y-2">
                    <p className="text-white font-medium">{t('evidenceMap.importModal.noEntities', 'AI nuk ka gjetur entitete ende.')}</p>
                    <p className="text-xs px-8 text-gray-500">Kjo ndodh nëse dokumentet nuk janë analizuar ende ose nuk përmbajnë emra personash apo organizatash.</p>
                </div>
                {user?.role === 'ADMIN' && (
                    <button 
                        onClick={handleForceReprocess} 
                        disabled={!!reprocessStatus}
                        className="flex items-center gap-2 px-6 py-2.5 bg-primary-start/20 text-primary-start border border-primary-start/50 rounded-xl hover:bg-primary-start/30 transition-all font-bold"
                    >
                        <RefreshCw size={18} className={reprocessStatus ? 'animate-spin' : ''} /> 
                        {reprocessStatus || "Ri-analizo Dokumentet (Admin)"}
                    </button>
                )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {nodes.map(node => (
                <div
                  key={node.id}
                  onClick={() => handleToggleSelect(node.name)}
                  className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border ${selected.has(node.name) ? 'bg-primary-start/20 border-primary-start/50' : 'bg-white/5 border-transparent hover:bg-white/10'}`}
                >
                  <div className="flex flex-col">
                    <span className="font-semibold text-text-main">{node.name}</span>
                    <span className="text-[10px] text-text-muted uppercase tracking-widest">{node.group}</span>
                  </div>
                  {selected.has(node.name) ? (
                      <div className="bg-primary-start p-1 rounded-full"><Check size={14} className="text-white" /></div>
                  ) : (
                      <div className="w-6 h-6 rounded-full border border-white/10" />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex-shrink-0 flex justify-between items-center pt-2">
            <button 
                onClick={() => setSelected(selected.size === nodes.length ? new Set() : new Set(nodes.map(n => n.name)))} 
                className="px-4 py-2 text-xs text-gray-400 hover:text-white font-medium transition-colors"
            >
                {selected.size === nodes.length ? t('general.deselectAll') : t('general.selectAll')}
            </button>
            <button
                onClick={() => { onImport(Array.from(selected)); onClose(); }}
                disabled={selected.size === 0}
                className="px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed"
            >
                {t('evidenceMap.importModal.importBtn', { count: selected.size })}
            </button>
        </div>
      </div>
    </div>
  );
};

export default ImportModal;