// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V36.0 (EXACT NATURAL NAME CASING & PROPORTIONAL TITLE)

import React from 'react';
import { ShieldCheck, Scale, Gavel, FileText, Info, ChevronRight } from 'lucide-react';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF';
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
  clientPosition,
  onSendMessage,
}) => {
  const cards = [
    {
      title: clientPosition === 'DEFENDANT' ? 'STRATEGJIA E MBROJTJES' : 'STRATEGJIA E PADISË',
      badge: clientPosition === 'DEFENDANT' ? 'MBROJTJA & ARGUMENTET' : 'SULMI & PRETENDIMET',
      icon: ShieldCheck,
      prompt:
        clientPosition === 'DEFENDANT'
          ? 'Identifiko 3 pikat kryesore të pretendimeve mbrojtëse dhe provat mbështetëse në të gjitha dokumentet e lëndës.'
          : 'Identifiko 3 pikat kryesore ku mbështetet padia jonë dhe provat vendimtare në fashikull.',
    },
    {
      title: 'BAZA LIGJORE & PROCEDURA',
      badge: 'LPK & KODET LIGJORE',
      icon: Scale,
      prompt: 'Analizo përputhshmërinë e veprimeve të palëve me nenet përkatëse të Ligjit për Procedurën Kontestimore (LPK).',
    },
    {
      title: 'PYETËSORI I SEANCËS',
      badge: 'MARRJA NË PYETJE',
      icon: Gavel,
      prompt: 'Gjenero pyetjet kritike dhe kundër-pyetjet taktike për dëgjimin e palëve dhe dëshmitarëve në seancë.',
    },
    {
      title: 'RAPORTI PËR KLIENTIN',
      badge: 'MEMO TEKNIKE',
      icon: FileText,
      prompt: 'Përgatit një përmbledhje ekzekutive të strukturuar mbi rreziqet ligjore dhe hapat e mëtejshëm për informimin e klientit.',
    },
  ];

  return (
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-3 sm:p-6 gap-4 sm:gap-5 max-w-3xl mx-auto w-full">
      <div className="space-y-2 max-w-xl mx-auto">
        {/* Title with exact natural casing */}
        <h3 className="text-sm sm:text-base md:text-lg font-bold text-text-primary tracking-tight">
          Unë jam <span className="font-black text-primary-start">SOKRATI</span> Agjenti i rastit tuaj, {userSalutation}
        </h3>

        {/* Executive Subtitle */}
        <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium px-2">
          Asistenti juaj inteligjent për analizën e thellë të provave, strategjinë procedurale dhe zbatimin e ligjeve të Kosovës.
        </p>

        {/* Disclaimer Pill */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-main rounded-xl text-[10px] sm:text-xs text-text-muted font-medium shadow-sm">
          <Info size={13} className="text-primary-start shrink-0" />
          <span>Përgjigjet bazohen në fashikull dhe duhet të verifikohen</span>
        </div>
      </div>

      {/* Symmetric 2x2 Command Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 w-full text-left mt-1">
        {cards.map((card, idx) => {
          const IconComponent = card.icon;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSendMessage(card.prompt)}
              className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/60 rounded-2xl text-left transition-all duration-200 shadow-sm flex flex-col justify-between gap-2.5 active:scale-[0.98] cursor-pointer"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[9px] sm:text-[10px] font-black uppercase px-2.5 py-0.5 rounded-md bg-primary-start/10 text-primary-start border border-primary-start/20 tracking-wider">
                  {card.badge}
                </span>
                <ChevronRight size={14} className="text-text-muted group-hover:text-primary-start transition-colors" />
              </div>

              <div className="flex items-center gap-2 mt-0.5">
                <IconComponent size={16} className="text-primary-start shrink-0" />
                <h4 className="text-xs sm:text-sm font-black uppercase text-text-primary tracking-wide group-hover:text-primary-start transition-colors">
                  {card.title}
                </h4>
              </div>

              <p className="text-xs text-text-secondary leading-relaxed font-normal">
                {card.prompt}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default CommandPaletteGrid;