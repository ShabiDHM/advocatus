// FILE: frontend/src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V48.0 (MINIMALIST & HIGH-CLASS WELCOME SCREEN)

import React from 'react';
import { Info, Sparkles } from 'lucide-react';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL' | string;
  selectedDocumentIds?: string[];
  documents?: any[];
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
}) => {
  return (
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-4 sm:p-8 gap-4 max-w-2xl mx-auto w-full select-none">
      <div className="space-y-2.5 max-w-xl mx-auto">
        <div className="w-12 h-12 bg-primary-start/10 text-primary-start rounded-2xl flex items-center justify-center mx-auto border border-primary-start/20 shadow-xs mb-3">
          <Sparkles size={22} className="animate-pulse" />
        </div>

        <h3 className="text-base sm:text-lg md:text-xl font-black text-text-primary tracking-tight">
          Unë jam <span className="text-primary-start">SOKRATI</span>, Asistenti Ligjor i rastit tuaj, {userSalutation}
        </h3>

        <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium px-2">
          Asistenti juaj inteligjent për analizën e thellë forenzike të provave, strategjinë procedurale dhe zbatimin e vendimeve parimore të Gjykatës Supreme të Kosovës.
        </p>

        <div className="pt-2">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-surface border border-main rounded-xl text-[11px] sm:text-xs text-text-muted font-medium shadow-xs">
            <Info size={14} className="text-amber-500 shrink-0" />
            <span>Kliko butonin <strong>⚖️ Analizo Rastin</strong> sipër ose shkruaj pyetjen tënde më poshtë</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommandPaletteGrid;