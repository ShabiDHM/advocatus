// FILE: src/components/evidence-map/ImportModal.tsx
// PHOENIX PROTOCOL - FIX V8.0 (SMART POLLING)
// 1. ADDED: Auto-polling mechanism (checks every 3s after reprocessing starts).
// 2. FIXED: Automatically populates the list when data arrives—no refresh needed.
// 3. UX: Improved status messages to reflect real-time activity.

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../../services/api'; 
import { X, BrainCircuit, Check, Loader2, RefreshCw, AlertCircle } from 'lucide-react';
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
  
  // Data States
  const [nodes, setNodes] = useState<KnowledgeGraphNode[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  
  // UI States
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Polling/Reprocess States
  const [isPolling, setIsPolling] = useState(false);
  const [reprocessStatus, setReprocessStatus] = useState<string | null>(null);
  const pollCount = useRef(0);
  const MAX_POLLS = 30; // 30 * 2s = 60 seconds max wait time

  // Function to fetch data (used by initial load and polling)
  const fetchGraphData = useCallback(async (isBackgroundCheck = false) => {
    if (!isBackgroundCheck) setIsLoading(true);
    setError(null);
    
    try {
      const graphResponse = await apiService.getCaseGraph(caseId);
      
      if (graphResponse && Array.isArray(graphResponse.nodes)) {
          const entityNodes = graphResponse.nodes.filter((n: KnowledgeGraphNode) => n.group !== 'DOCUMENT');
          
          if (entityNodes.length > 0) {
            setNodes(entityNodes);
            // If we found nodes, we can stop polling/loading
            setIsPolling(false);
            setReprocessStatus(null); 
            setIsLoading(false);
            return true; // Success signal
          }
      }
      // If we are here, we found no nodes yet.
      if (!isBackgroundCheck) setNodes([]);
      
    } catch (err) {
      console.error(err);
      if (!isBackgroundCheck) setError(t('evidenceMap.importModal.error', 'Dështoi ngarkimi i të dhënave nga AI.'));
    } finally {
      if (!isBackgroundCheck) setIsLoading(false);
    }
    return false; // No data found yet signal
  }, [caseId, t]);

  // Initial Load
  useEffect(() => {
    if (isOpen) {
        setNodes([]);
        setReprocessStatus(null);
        setIsPolling(false);
        fetchGraphData();
    }
  }, [isOpen, fetchGraphData]);

  // POLLING LOGIC: The Heart of the Fix
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (isPolling) {
        pollCount.current = 0; // Reset counter
        
        intervalId = setInterval(async () => {
            pollCount.current += 1;
            
            // Check for data
            const foundData = await fetchGraphData(true);
            
            if (foundData) {
                // Data found! Stop loop.
                clearInterval(intervalId);
                setIsPolling(false);
            } else if (pollCount.current >= MAX_POLLS) {
                // Timeout reached
                clearInterval(intervalId);
                setIsPolling(false);
                setReprocessStatus(null);
                setError(t('reprocess.timeout', 'Procesimi po zgjat më shumë se zakonisht. Ju lutem provoni të rifreskoni pas pak.'));
            }
        }, 2000); // Check every 2 seconds
    }

    return () => {
        if (intervalId) clearInterval(intervalId);
    };
  }, [isPolling, fetchGraphData, t]);

  const handleForceReprocess = async () => {
    if (!user || user.role !== 'ADMIN') return;
    
    setReprocessStatus(t('reprocess.starting', 'Duke iniciuar motorin AI...'));
    setIsPolling(true); // START THE POLLING LOOP
    
    try {
        const response = await apiService.reprocessCaseDocuments(caseId);
        setReprocessStatus(t('reprocess.processing', `AI po analizon ${response.count} dokumente...`));
    } catch (e) {
        setIsPolling(false);
        setReprocessStatus(null);
        setError(t('reprocess.error', 'Dështoi nisja e ri-procesimit.'));
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
            <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-4 px-4 text-center">
                 <AlertCircle size={32} />
                 <span>{error}</span>
                 {isAdmin && (
                    <button onClick={handleForceReprocess} className="mt-2 px-4 py-2 bg-red-600/20 rounded-lg text-sm text-red-400 border border-red-500/50 hover:bg-red-600/40 transition-colors">
                        {t('reprocess.tryAgain', 'Provo Përsëri')}
                    </button>
                 )}
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-text-muted space-y-6 px-4">
                {!isPolling ? (
                    <>
                        <p className="text-center text-lg">{t('evidenceMap.importModal.noEntities', 'AI nuk ka gjetur entitete në dokumente.')}</p>
                        {isAdmin && (
                            <button 
                                onClick={handleForceReprocess} 
                                className="flex items-center gap-2 px-6 py-3 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/50 rounded-xl transition-all hover:scale-105 active:scale-95"
                            >
                                <RefreshCw size={18} /> 
                                {t('reprocess.forceAll', 'Ri-proceso Të Gjitha Dokumentet')}
                            </button>
                        )}
                    </>
                ) : (
                    <div className="flex flex-col items-center animate-pulse space-y-4">
                        <div className="relative">
                            <div className="absolute inset-0 bg-primary-start blur-xl opacity-20 animate-pulse"></div>
                            <RefreshCw size={48} className="text-primary-start animate-spin duration-1000" />
                        </div>
                        <p className="text-primary-start font-medium text-center max-w-xs">{reprocessStatus}</p>
                    </div>
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
            <button onClick={handleSelectAll} disabled={nodes.length === 0} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                {selected.size === nodes.length && nodes.length > 0 ? t('general.deselectAll', 'Çseleto të Gjitha') : t('general.selectAll', 'Selekto të Gjitha')}
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