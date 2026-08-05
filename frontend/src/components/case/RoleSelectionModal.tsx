// FILE: src/components/case/RoleSelectionModal.tsx
import React from 'react';
import { motion } from 'framer-motion';
import { Gavel, Shield, Swords, Scale, X } from 'lucide-react';
import { useLockBodyScroll } from '../../hooks/useLockBodyScroll';

interface RoleSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectRole: (role: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL') => void;
}

export const RoleSelectionModal: React.FC<RoleSelectionModalProps> = ({ isOpen, onClose, onSelectRole }) => {
  useLockBodyScroll(isOpen);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[300] p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        className="glass-panel w-full max-w-lg p-6 sm:p-8 rounded-3xl shadow-2xl border border-main bg-canvas"
      >
        <div className="flex justify-between items-center mb-6 border-b border-main pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
              <Gavel size={20} />
            </div>
            <div>
              <h3 className="text-lg font-black text-text-primary uppercase tracking-tight">Cilin Pozicion po Përfaqësoni?</h3>
              <p className="text-xs text-text-muted font-medium">Zgjidhni rolin e klientit për të përshtatur strategjinë AI</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-text-muted hover:text-text-primary transition-colors focus:outline-none">
            <X size={20} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 mb-6">
          <button
            type="button"
            onClick={() => onSelectRole('DEFENDANT')}
            className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-2xl text-left transition-all hover-lift focus:outline-none flex items-start gap-3.5 shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 group-hover:scale-110 transition-transform">
              <Shield size={22} />
            </div>
            <div>
              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide group-hover:text-primary-start transition-colors">
                🛡️ I Paditur / I Akuzuar (Mbrojtje)
              </h4>
              <p className="text-[11px] text-text-secondary leading-relaxed mt-0.5">
                Mbrojtja e palës që paditet. Strategjia fokusohet në prapësime, gabime procedurale dhe rrëzimin e pretendimeve.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectRole('PLAINTIFF')}
            className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-2xl text-left transition-all hover-lift focus:outline-none flex items-start gap-3.5 shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 group-hover:scale-110 transition-transform">
              <Swords size={22} />
            </div>
            <div>
              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide group-hover:text-primary-start transition-colors">
                ⚔️ Paditësi / I Dëmtuari (Sulm)
              </h4>
              <p className="text-[11px] text-text-secondary leading-relaxed mt-0.5">
                Përfaqësimi i palës që ngre padinë. Strategjia fokusohet në provimin e përgjegjësisë dhe forcat e padisë.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectRole('NEUTRAL')}
            className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start rounded-2xl text-left transition-all hover-lift focus:outline-none flex items-start gap-3.5 shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 group-hover:scale-110 transition-transform">
              <Scale size={22} />
            </div>
            <div>
              <h4 className="text-xs font-black text-text-primary uppercase tracking-wide group-hover:text-primary-start transition-colors">
                ⚖️ Neutral / Analizë Objektive
              </h4>
              <p className="text-[11px] text-text-secondary leading-relaxed mt-0.5">
                Vlerësim i paanshëm ligjor (për Gjyqtarë, Arbitra ose Simuluar të Seancës). Peshon të dyja anët në mënyrë objektive.
              </p>
            </div>
          </button>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="w-full py-3 rounded-xl text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary bg-surface border border-main transition-colors focus:outline-none"
        >
          Anulo
        </button>
      </motion.div>
    </div>
  );
};