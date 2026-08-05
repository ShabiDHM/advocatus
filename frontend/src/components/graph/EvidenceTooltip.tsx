// FILE: src/components/graph/EvidenceTooltip.tsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link2, Languages } from 'lucide-react';
import { OntologyEdge, OntologyNode } from './graphTypes';
import { translateToAlbanian, formatRelationText } from '../../utils/albanianLegalTranslator';
import { LawCitationText } from '../LawCitationText';

interface EvidenceTooltipProps {
  hoveredEdge: OntologyEdge | null;
  tooltipPos: { x: number; y: number };
  nodeMap: Map<string, OntologyNode>;
}

export const EvidenceTooltip: React.FC<EvidenceTooltipProps> = ({ hoveredEdge, tooltipPos, nodeMap }) => {
  return (
    <AnimatePresence>
      {hoveredEdge && (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.1 }}
          style={{
            position: 'absolute',
            left: Math.min(window.innerWidth - 480, tooltipPos.x + 20),
            top: Math.max(20, tooltipPos.y - 40),
            pointerEvents: 'none',
          }}
          className="z-[999] w-[440px] p-5 bg-[#0a0f1d] border-2 border-blue-500/70 rounded-2xl shadow-[0_25px_60px_rgba(0,0,0,0.95)] space-y-3.5 font-sans"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="px-3 py-1 rounded-full text-xs font-black uppercase bg-blue-500/20 text-blue-300 border border-blue-500/40">
              {formatRelationText(hoveredEdge.relation)}
            </span>
            {hoveredEdge.amount_eur && (
              <span className="text-xs font-mono font-black text-emerald-400 bg-emerald-500/20 px-2.5 py-1 rounded border border-emerald-500/30">
                €{hoveredEdge.amount_eur.toLocaleString()}
              </span>
            )}
          </div>

          <div className="flex items-center justify-between text-xs font-bold text-slate-200 bg-[#111827] p-3 rounded-xl border border-slate-800">
            <span className="text-white font-black text-sm">
              {translateToAlbanian(nodeMap.get(hoveredEdge.source)?.label) || 'Burimi'}
            </span>
            <Link2 size={14} className="text-blue-400 shrink-0 mx-2" />
            <span className="text-white font-black text-sm">
              {translateToAlbanian(nodeMap.get(hoveredEdge.target)?.label) || 'Caku'}
            </span>
          </div>

          {hoveredEdge.evidence_text && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest block">
                  Dëshmia nga Shkresa:
                </span>
                <span className="text-[9px] font-black uppercase text-blue-400 bg-blue-500/20 px-2 py-0.5 rounded border border-blue-500/30 flex items-center gap-1">
                  <Languages size={10} /> 🇦🇱 Përkthyer në Shqip
                </span>
              </div>
              <p className="text-xs text-white leading-relaxed bg-[#111827] p-3.5 rounded-xl border border-slate-800 font-medium leading-relaxed">
                &quot;<LawCitationText text={translateToAlbanian(hoveredEdge.evidence_text)} />&quot;
              </p>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};