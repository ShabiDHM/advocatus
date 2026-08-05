// FILE: src/components/graph/EvidenceInspector.tsx
import React from 'react';
import { X, FileCheck, Euro, AlertTriangle, MessageCircle, Languages } from 'lucide-react';
import { OntologyNode, OntologyEdge, ENTITY_CONFIG } from './graphTypes';
import { translateToAlbanian, formatRelationText } from '../../utils/albanianLegalTranslator';
import { LawCitationText } from '../LawCitationText';

interface EvidenceInspectorProps {
  selectedNode: OntologyNode | null;
  selectedEdge: OntologyEdge | null;
  onClose: () => void;
  nodeMap: Map<string, OntologyNode>;
  financialTotals: { inEur: number; outEur: number; netEur: number };
  connectedEdges: OntologyEdge[];
  onSelectEdge: (e: OntologyEdge) => void;
  onOpenEntityChat: (node: OntologyNode) => void;
}

export const EvidenceInspector: React.FC<EvidenceInspectorProps> = ({
  selectedNode,
  selectedEdge,
  onClose,
  nodeMap,
  financialTotals,
  connectedEdges,
  onSelectEdge,
  onOpenEntityChat,
}) => {
  if (!selectedNode && !selectedEdge) return null;

  return (
    <div className="w-96 bg-surface border-l border-main p-5 flex flex-col gap-4 z-20 shadow-2xl shrink-0 overflow-y-auto font-sans">
      <div className="flex items-center justify-between border-b border-main pb-3">
        <span className="text-xs font-black text-primary-start uppercase tracking-widest flex items-center gap-2">
          <FileCheck size={16} /> {selectedNode ? 'Doshja e Entitetit' : 'Detajet e Lidhjes'}
        </span>
        <button type="button" onClick={onClose}>
          <X className="w-5 h-5 text-text-muted" />
        </button>
      </div>

      {selectedNode && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-canvas border border-main rounded-2xl">
            <div
              className="p-3 rounded-2xl text-white shrink-0 border border-white/20 shadow-md"
              style={{ backgroundColor: ENTITY_CONFIG[selectedNode.type].bg }}
            >
              {React.createElement(ENTITY_CONFIG[selectedNode.type].icon, { className: 'w-6 h-6 text-white' })}
            </div>
            <div className="min-w-0 flex-1">
              <h4 className="font-black text-base text-text-primary leading-snug">{translateToAlbanian(selectedNode.label)}</h4>
              <span
                className="inline-block mt-1 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase text-white tracking-wider"
                style={{ backgroundColor: ENTITY_CONFIG[selectedNode.type].bg }}
              >
                {ENTITY_CONFIG[selectedNode.type].albanianLabel}
              </span>
            </div>
          </div>

          {(financialTotals.inEur > 0 || financialTotals.outEur > 0) && (
            <div className="bg-canvas p-4 rounded-2xl border border-main space-y-2">
              <span className="text-[10px] font-black text-primary-start uppercase tracking-widest flex items-center gap-1.5">
                <Euro size={14} /> Balanca e Transaksioneve
              </span>
              <div className="flex justify-between text-xs font-bold text-emerald-400">
                <span>Të Pranuara:</span>
                <span>+€{financialTotals.inEur.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-xs font-bold text-rose-400">
                <span>Të Paguara:</span>
                <span>-€{financialTotals.outEur.toLocaleString()}</span>
              </div>
              <div className="border-t border-main pt-2 flex justify-between font-black text-sm text-text-primary">
                <span>Bilanci Neto:</span>
                <span>€{financialTotals.netEur.toLocaleString()}</span>
              </div>
            </div>
          )}

          {selectedNode.description && (
            <div className="bg-canvas p-4 rounded-2xl border border-main space-y-2">
              <span className="text-[10px] font-black text-text-muted uppercase tracking-widest block">Roli / Përshkrimi i Plotë</span>
              <div className="text-xs text-text-secondary leading-relaxed font-medium">
                <LawCitationText text={translateToAlbanian(selectedNode.description)} />
              </div>
            </div>
          )}

          <div className="space-y-2">
            <span className="text-[10px] font-black text-text-muted uppercase tracking-widest block">
              Veprimet & Lidhjet Ligjore ({connectedEdges.length})
            </span>
            <div className="space-y-2 max-h-60 overflow-y-auto custom-finance-scroll pr-1">
              {connectedEdges.map((e) => {
                const otherNodeId = e.source === selectedNode.id ? e.target : e.source;
                const otherNode = nodeMap.get(otherNodeId);
                const isContradiction = e.relation.includes('CONTRADICT') || e.relation.includes('KUNDËR');

                return (
                  <div
                    key={e.id}
                    onClick={() => onSelectEdge(e)}
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
                          {translateToAlbanian(otherNode.label)}
                        </span>
                      )}
                    </div>
                    {e.evidence_text && (
                      <div className="text-[11px] text-text-secondary italic line-clamp-2 mt-1">
                        &quot;<LawCitationText text={translateToAlbanian(e.evidence_text)} />&quot;
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            onClick={() => onOpenEntityChat(selectedNode)}
            className="w-full py-3 bg-primary-start hover:bg-opacity-95 text-white rounded-xl text-xs font-black uppercase flex items-center justify-center gap-2 shadow-lg"
          >
            <MessageCircle size={16} /> Pyet AI për këtë entitet
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
            <div className="bg-surface p-3.5 rounded-xl border border-main text-xs text-text-secondary leading-relaxed space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-text-muted uppercase block">Dëshmia nga Dokumentet Origjinale</span>
                <span className="text-[9px] font-black uppercase text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 flex items-center gap-1">
                  <Languages size={10} /> 🇦🇱 Përkthyer në Shqip
                </span>
              </div>
              <div className="italic text-text-primary font-medium text-xs leading-relaxed">
                &quot;<LawCitationText text={translateToAlbanian(selectedEdge.evidence_text)} />&quot;
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};