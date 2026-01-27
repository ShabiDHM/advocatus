// FILE: src/components/evidence-map/NodeEditModal.tsx (COMPLETE REPLACEMENT)
// PHOENIX PROTOCOL - FIX V5.4.2 (CLEANUP)
// 1. FIX: Removed unused imports (useMemo, CheckCircle, XCircle).

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Save, Gavel, FileText, Info } from 'lucide-react'; // PHOENIX: Cleaned imports
import { Node } from '@xyflow/react';
import { MapNodeData } from './Nodes';

interface NodeEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  node: Node<MapNodeData> | null;
  onSave: (nodeId: string, newContent: Partial<MapNodeData>) => void;
}

const NodeEditModal: React.FC<NodeEditModalProps> = ({ isOpen, onClose, node, onSave }) => {
  const { t } = useTranslation();
  const [localData, setLocalData] = useState<Partial<MapNodeData>>({});
  const [isSaving, setIsSaving] = useState(false);

  // Initialize local state from prop node
  useEffect(() => {
    if (node) {
      // PHOENIX: Exclude the transient UI properties 'stats', 'isHighlighted', 'editing' from the local state
      const { stats, isHighlighted, editing, ...dataToEdit } = node.data;
      setLocalData(dataToEdit);
    }
  }, [node]);

  const isClaim = node?.type === 'claimNode';
  const headerIcon = isClaim ? <Gavel className="text-green-500" /> : <FileText className="text-blue-500" />;
  const headerText = isClaim ? t('nodeEdit.claimTitle', 'Redakto Pretendimin') : t('nodeEdit.evidenceTitle', 'Redakto Provën');
  
  const handleSave = () => {
    if (!node) return;
    setIsSaving(true);
    
    // PHOENIX: No need to explicitly delete UI properties if we only pass the localData state
    onSave(node.id, localData);
    
    // Simulate save time for UX
    setTimeout(() => {
      setIsSaving(false);
      onClose();
    }, 200);
  };
  
  const handleChange = (field: keyof MapNodeData, value: any) => {
    setLocalData(prev => ({ ...prev, [field]: value }));
  };

  if (!isOpen || !node) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
      <div className="glass-high w-full max-w-xl p-8 rounded-2xl flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div className="flex-shrink-0 flex justify-between items-center mb-6 border-b border-white/10 pb-4">
          <h3 className="flex items-center gap-3 text-2xl font-bold text-white">
            {headerIcon}
            <span>{headerText}</span>
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"><X size={24} /></button>
        </div>

        <div className="space-y-6 flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2">
            {/* Title/Label Edit */}
            <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">{t('nodeEdit.label', 'Titulli')}</label>
                <input 
                    type="text" 
                    value={localData.label || ''} 
                    onChange={(e) => handleChange('label', e.target.value)}
                    className="glass-input w-full rounded-xl px-4 py-2 text-lg font-semibold" 
                />
            </div>
            
            {/* Content Edit */}
            <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">{t('nodeEdit.content', 'Përmbajtja / Përshkrimi')}</label>
                <textarea 
                    value={localData.content || ''} 
                    onChange={(e) => handleChange('content', e.target.value)}
                    rows={4}
                    className="glass-input w-full rounded-xl px-4 py-2 resize-none" 
                    placeholder={t('nodeEdit.contentPlaceholder', 'Shkruaj detajet e pretendimit ose citimin e provës...')}
                />
            </div>

            {/* PHOENIX PHASE 5: METADATA SECTION */}
            <div className="pt-4 border-t border-white/10">
                <h4 className="flex items-center gap-2 text-base font-semibold text-text-primary mb-4">
                    <Info size={18} className="text-primary-start" />
                    {t('nodeEdit.metadataTitle', 'Metadata Ligjore')}
                </h4>
                
                {/* EVIDENCE FIELDS */}
                {!isClaim && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1">{t('nodeEdit.exhibitNumber', 'Nr. i Ekspozitës / Burimi')}</label>
                            <input 
                                type="text" 
                                value={localData.exhibitNumber || ''} 
                                onChange={(e) => handleChange('exhibitNumber', e.target.value)}
                                className="glass-input w-full rounded-xl px-4 py-2" 
                                placeholder="P.sh: Ex. A-1 / Dëshmia e J. Smith"
                            />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                            {/* Authentication Status */}
                            <label className="flex items-center justify-between text-sm text-text-secondary">
                                <span>{t('nodeEdit.isAuthenticated', 'Autentikuar')}</span>
                                <input 
                                    type="checkbox" 
                                    checked={!!localData.isAuthenticated}
                                    onChange={(e) => handleChange('isAuthenticated', e.target.checked)}
                                    className="h-4 w-4 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start"
                                />
                            </label>

                            {/* Admission Status */}
                            <div className="text-sm">
                                <label className="block font-medium text-text-secondary mb-1">{t('nodeEdit.isAdmitted', 'Pranim Mbi Provën')}</label>
                                <select
                                    value={localData.isAdmitted || ''}
                                    onChange={(e) => handleChange('isAdmitted', e.target.value || null)}
                                    className="w-full bg-background-dark border border-white/10 rounded-md px-3 py-1.5 text-sm text-text-main focus:ring-2 focus:ring-primary-start focus:outline-none"
                                >
                                    <option value="">{t('general.pending', 'Në Pritje')}</option>
                                    <option value="Admitted">{t('general.admitted', 'Pranuar')}</option>
                                    <option value="Stricken">{t('general.stricken', 'Hequr')}</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                {/* CLAIM FIELD */}
                {isClaim && (
                    <div className="text-sm">
                        <label className="flex items-center justify-between text-text-secondary">
                            <span>{t('nodeEdit.isProven', 'Pretendimi i Vërtetuar')}</span>
                            <input 
                                type="checkbox" 
                                checked={!!localData.isProven}
                                onChange={(e) => handleChange('isProven', e.target.checked)}
                                className="h-4 w-4 rounded bg-background-dark border-white/20 text-green-500 focus:ring-green-500"
                            />
                        </label>
                    </div>
                )}
            </div>

        </div>

        <div className="flex-shrink-0 flex justify-end gap-3 mt-8 pt-4 border-t border-white/10">
          <button type="button" onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white font-medium transition-colors">
            {t('general.cancel', 'Anulo')}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-50"
          >
            <Save size={20} />
            {isSaving ? t('general.saving', 'Duke ruajtur...') : t('general.save', 'Ruaj')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NodeEditModal;