// FILE: src/components/evidence-map/ImportModal.tsx (FINAL CLEANUP)
// PHOENIX PROTOCOL - FIX V6.0 (TRANSLATION COUNT FIX)
// 1. FIX: Corrected the import button's translation usage to pass 'count' variable correctly.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../../services/api';
import { X, BrainCircuit, Check, Loader2 } from 'lucide-react';

// Define the shape of a node from the Neo4j graph service
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
  const [nodes, setNodes] = useState<KnowledgeGraphNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const fetchGraphData = async () => {
        setIsLoading(true);
        setError(null);
        try {
          // Reuses your existing AI graph endpoint (getCaseGraph)
          const response = await apiService.getCaseGraph(caseId);
          const entityNodes = response.nodes.filter((n: KnowledgeGraphNode) => n.group !== 'DOCUMENT');
          setNodes(entityNodes as KnowledgeGraphNode[]);
          // Reset selection on new open
          setSelected(new Set());
        } catch (err) {
          setError(t('evidenceMap.importModal.error', 'Dështoi ngarkimi i të dhënave nga AI.'));
        } finally {
          setIsLoading(false);
        }
      };
      fetchGraphData();
    }
  }, [isOpen, caseId, t]);

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
            <div className="flex items-center justify-center h-full text-red-400">{error}</div>
          ) : nodes.length === 0 ? (
            <div className="flex items-center justify-center h-full text-text-muted">{t('evidenceMap.importModal.noEntities', 'AI nuk ka gjetur entitete në dokumente.')}</div>
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
                {/* PHOENIX FIX: Correctly pass the count variable to the i18n function */}
                {t('evidenceMap.importModal.importBtn', { count: selected.size })}
            </button>
        </div>
      </div>
    </div>
  );
};

export default ImportModal;