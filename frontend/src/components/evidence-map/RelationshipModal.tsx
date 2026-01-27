// FILE: src/components/evidence-map/RelationshipModal.tsx
// PHOENIX PROTOCOL - PHASE 2: RELATIONSHIP DIALOG
// 1. PURPOSE: Allows user to define a new connection's type and strength.
// 2. LOGIC: Replaces the automatic edge creation in EvidenceMapPage.tsx.

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Check, TrendingUp, TrendingDown, Users } from 'lucide-react';
import { Edge } from '@xyflow/react';

export type RelationshipType = 'supports' | 'contradicts' | 'related';

interface RelationshipModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (type: RelationshipType, strength: number, label: string) => void;
  tempEdge: Edge | null;
}

const RelationshipModal: React.FC<RelationshipModalProps> = ({ isOpen, onClose, onSave, tempEdge }) => {
  const { t } = useTranslation();
  const [type, setType] = useState<RelationshipType>('supports');
  const [strength, setStrength] = useState(3);
  const [label, setLabel] = useState('');

  // Reset state when opening a new connection
  React.useEffect(() => {
    if (isOpen) {
      setType('supports');
      setStrength(3);
      setLabel('');
    }
  }, [isOpen]);

  const handleSave = () => {
    onSave(type, strength, label);
    onClose();
  };

  if (!isOpen || !tempEdge) return null;

  const relationshipOptions: { type: RelationshipType; label: string; icon: JSX.Element; color: string; }[] = [
    { type: 'supports', label: t('relationship.supports', 'Mbështet'), icon: <TrendingUp size={20} />, color: 'text-green-500 border-green-500' },
    { type: 'contradicts', label: t('relationship.contradicts', 'Kundërthotë'), icon: <TrendingDown size={20} />, color: 'text-red-500 border-red-500' },
    { type: 'related', label: t('relationship.related', 'I Lidhura'), icon: <Users size={20} />, color: 'text-gray-500 border-gray-500' },
  ];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
      <div className="glass-high w-full max-w-lg p-6 rounded-2xl flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div className="flex-shrink-0 flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-white">{t('relationship.defineTitle', 'Përcakto Lidhjen')}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"><X size={24} /></button>
        </div>

        <div className="space-y-6 flex-1 overflow-y-auto custom-scrollbar pr-2">
            {/* Source/Target Info */}
            <div className="text-sm text-text-secondary border-b border-white/10 pb-4">
                <p>Nga: <span className="font-semibold text-white">{tempEdge.source}</span></p>
                <p>Tek: <span className="font-semibold text-white">{tempEdge.target}</span></p>
            </div>

            {/* Type Selection */}
            <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">{t('relationship.typeLabel', 'Tipi i Lidhjes')}</label>
                <div className="grid grid-cols-3 gap-3">
                    {relationshipOptions.map(option => (
                        <button
                            key={option.type}
                            onClick={() => setType(option.type)}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all duration-200 ${type === option.type ? `${option.color} bg-white/5 shadow-lg` : 'border-gray-700 text-gray-400 hover:border-gray-500'}`}
                        >
                            {option.icon}
                            <span className="text-xs font-medium mt-1">{option.label}</span>
                        </button>
                    ))}
                </div>
            </div>
            
            {/* Strength/Weight Selection */}
            <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">{t('relationship.strengthLabel', 'Forca (1-5)')}: <span className="text-white font-bold">{strength}</span></label>
                <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={strength}
                    onChange={(e) => setStrength(Number(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer range-lg transition-colors"
                    style={{ accentColor: type === 'contradicts' ? '#ef4444' : type === 'supports' ? '#10b981' : '#6b7280' }}
                />
            </div>
            
            {/* Label/Note */}
            <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">{t('relationship.labelNote', 'Etiketë / Shënim (Opsionale)')}</label>
                <input
                    type="text"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    placeholder={t('relationship.placeholder', 'P.sh: Lidhje e Konfirmuar në Dokument...')}
                    className="glass-input w-full rounded-xl px-4 py-2"
                />
            </div>

        </div>

        <div className="flex-shrink-0 flex justify-end gap-3 mt-6">
          <button type="button" onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white font-medium transition-colors">
            {t('general.cancel', 'Anulo')}
          </button>
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95"
          >
            <Check size={20} />
            {t('general.save', 'Ruaj')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RelationshipModal;