// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V47.0 (ONLY ANALIZO RASTIN)

import React from 'react';
import { FileSearch, ChevronRight, Info } from 'lucide-react';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL' | string;
  selectedDocumentIds?: string[];
  documents?: any[];
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
  onSendMessage,
}) => {
  return (
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-3 sm:p-6 gap-4 sm:gap-5 max-w-3xl mx-auto w-full">
      <div className="space-y-2 max-w-xl mx-auto">
        <h3 className="text-sm sm:text-base md:text-lg font-bold text-text-primary tracking-tight">
          Unë jam <span className="font-black text-primary-start">SOKRATI</span> Agjenti i rastit tuaj, {userSalutation}
        </h3>

        <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium px-2">
          Asistenti juaj inteligjent për analizën e thellë të provave, strategjinë procedurale dhe zbatimin e vendimeve parimore të Gjykatës Supreme të Kosovës.
        </p>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-main rounded-xl text-[10px] sm:text-xs text-text-muted font-medium shadow-sm">
          <Info size={13} className="text-primary-start shrink-0" />
          <span>Kliko "Analizo Rastin" për raportin e plotë forenzik me 10 seksione</span>
        </div>
      </div>

      <div className="w-full max-w-md text-left">
        <button
          type="button"
          onClick={() => onSendMessage("ANALIZO RASTIN — Gjenero raportin e plotë forenzik me 10 seksione: përmbledhja ekzekutive, kronologjia, shkeljet me nene, matrica e provave, aktorët, baza statutore, opinioni supremit, dëmet, plani i veprimit dhe rekomandimet.")}
          className="group w-full p-5 bg-amber-500/5 hover:bg-amber-500/10 border-2 border-amber-500/40 hover:border-amber-500/70 rounded-2xl text-left transition-all duration-200 shadow-sm flex items-center justify-between gap-3 active:scale-[0.98] cursor-pointer"
        >
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="p-3 rounded-xl bg-gradient-to-br from-amber-500 to-primary-start text-white shadow-md shrink-0">
              <FileSearch size={22} />
            </div>
            <div className="min-w-0">
              <span className="text-[9px] font-bold uppercase px-2.5 py-0.5 rounded-md border bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30 tracking-wider">
                RAPORTI I PLOTË
              </span>
              <h4 className="text-sm sm:text-base font-bold uppercase text-text-primary tracking-wide mt-1">
                ⚖️ Analizo Rastin
              </h4>
              <p className="text-xs text-text-secondary leading-relaxed font-normal mt-0.5">
                10 seksione: shkeljet, provat, nenet, dëmet, plani i veprimit.
              </p>
            </div>
          </div>
          <ChevronRight size={20} className="text-amber-500 group-hover:translate-x-1 transition-transform shrink-0" />
        </button>
      </div>
    </div>
  );
};

export default CommandPaletteGrid;