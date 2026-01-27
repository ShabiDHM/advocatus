// FILE: src/components/evidence-map/ImportModal.tsx
// PHOENIX PROTOCOL - FIX V7.3 (FINAL)
// 1. VERIFIED: Connects to apiService.reprocessCaseDocuments (bulk).
// 2. FIXED: "No entities found" state now offers a working Admin recovery button.

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../../services/api'; 
import { X, BrainCircuit, Check, Loader2, RefreshCw } from 'lucide-react';
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
      const graphResponse = await apiService.getCaseGraph(caseId);
      
      if (graphResponse && Array.isArray(graphResponse.nodes)) {
          const entityNodes = graphResponse.nodes.filter((n: KnowledgeGraphNode) => n.group !== 'DOCUMENT');
          setNodes(entityNodes);
      } else {
          setNodes([]);
      }
      
    } catch (err) {
      console.error(err);
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
    setReprocessStatus(t('reprocess.starting', 'Duke filluar ri-procesimin...'));
    
    try {
        const response = await apiService.reprocessCaseDocuments(caseId);
        setReprocessStatus(t('reprocess.success', `U nis procesimi për ${response.count} dokumente. Prisni 30s.`));
    } catch (e) {
        setReprocessStatus(t('reprocess.error', 'Dështoi nisja e ri-procesimit. Shiko logs.'));
        console.error(e);
    }
  };

  const handleToggleSelect = (nodeName: string) => {
    setSelected(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeName)) {
        newSet.delete(nodeName);
      } else {
        newSet.add(nodeName);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selected.size === nodes.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(nodes.map(n => n.name)));
    }
  };

  const handleConfirmImport = () => {
    onImport(Array.from(selected));
    onClose();
    setSelected(new Set());
  };

  if (!isOpen) return null;

  const isAdmin = user?.role === 'ADMIN';

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

        <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2 mb-4 border-t border-b border-white/10 py-2">
          {isLoading ? (
            <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-4">
                 <span>{error}</span>
                 {isAdmin && (
                    <button onClick={handleForceReprocess} className="flex items-center gap-2 px-3 py-1.5 bg-red-600/20 rounded-lg text-sm text-red-400 border border-red-500 hover:bg-red-600/40">
                        <RefreshCw size={16} /> {t('reprocess.forceCheck', 'Kontrollo Forcueshëm (Admin)')}
                    </button>
                 )}
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-text-muted space-y-4">
                <p className="text-center">{t('evidenceMap.importModal.noEntities', 'AI nuk ka gjetur entitete në dokumente.')}</p>
                {isAdmin && (
                    <button onClick={handleForceReprocess} disabled={reprocessStatus !== null} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${reprocessStatus ? 'bg-gray-600/20 text-gray-400 cursor-not-allowed' : 'bg-primary-start/20 text-primary-start border border-primary-start/50 hover:bg-primary-start/30'}`}>
                        <RefreshCw size={16} className={reprocessStatus ? 'animate-spin' : ''} /> 
                        {reprocessStatus || t('reprocess.forceAll', 'Ri-proceso Të Gjitha Dokumentet')}
                    </button>
                )}
            </div>
          ) : (
            <div className="space-y-2">
              {nodes.map(node => (
                <div
                  key={node.id}
                  onClick={() => handleToggleSelect(node.name)}
                  className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${selected.has(node.name) ? 'bg-primary-start/20' : 'hover:bg-white/5'}`}
                >
                  <div className="flex flex-col">
                    <span className="font-medium text-text-main">{node.name}</span>
                    <span className="text-xs text-text-muted uppercase">{node.group}</span>
                  </div>
                  {selected.has(node.name) && <Check className="text-primary-start" />}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex-shrink-0 flex justify-between items-center">
            <button onClick={handleSelectAll} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition-colors">
                {selected.size === nodes.length ? t('general.deselectAll', 'Çseleto të Gjitha') : t('general.selectAll', 'Selekto të Gjitha')}
            </button>
            <button
                onClick={handleConfirmImport}
                disabled={selected.size === 0}
                className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {t('evidenceMap.importModal.importBtn', { count: selected.size })}
            </button>
        </div>
      </div>
    </div>
  );
};

export default ImportModal;