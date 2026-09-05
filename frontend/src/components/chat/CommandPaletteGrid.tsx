// FILE: frontend/src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V52.0 (PURE MINIMAL JURISTI AI GREETING • ZERO ICONS • ZERO DISTRACTIONS)

import React from 'react';

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
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-4 sm:p-8 max-w-2xl mx-auto w-full select-none">
      <div className="space-y-2.5 max-w-xl mx-auto">
        <h3 className="text-base sm:text-lg md:text-xl font-black text-text-primary tracking-tight">
          Mirësevini te <span className="text-primary-start">Juristi AI</span>, {userSalutation}
        </h3>

        <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium px-4">
          Asistenti juaj inteligjent sokratik për konsultim doktrinar, pyetje procedurale dhe zbatimin e legjislacionit e jurisprudencës së Gjykatës Supreme të Kosovës.
        </p>
      </div>
    </div>
  );
};

export default CommandPaletteGrid;