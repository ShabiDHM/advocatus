// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V37.0 (PRECISION ROLE PROMPTS & NATURAL CASING)

import React from 'react';
import { ShieldCheck, Scale, Gavel, FileText, Info, ChevronRight } from 'lucide-react';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL';
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
  clientPosition = 'DEFENDANT',
  onSendMessage,
}) => {
  const getCards = () => {
    if (clientPosition === 'PLAINTIFF') {
      return [
        {
          title: 'STRATEGJIA E PADISË',
          badge: 'SULMI & PRETENDIMET',
          icon: ShieldCheck,
          prompt: 'Identifiko 3 shtyllat kryesore të kërkesëpadisë, përgjegjësinë e kundërshtarit dhe provat vendimtare në fashikull.',
        },
        {
          title: 'BAZA LIGJORE & PROCEDURA',
          badge: 'LPK & KODET LIGJORE',
          icon: Scale,
          prompt: 'Analizo bazën ligjore procedurale dhe materiale, afatet dhe zbatueshmërinë e neneve të ligjeve përkatëse të Kosovës.',
        },
        {
          title: 'PYETËSORI I SEANCËS',
          badge: 'MARRJA NË PYETJE',
          icon: Gavel,
          prompt: 'Gjenero pyetjet taktike të ballafaqimit për dëgjimin e palëve dhe dëshmitarëve në seancë.',
        },
        {
          title: 'RAPORTI PËR KLIENTIN',
          badge: 'MEMO TEKNIKE',
          icon: FileText,
          prompt: 'Përgatit një përmbledhje ekzekutive mbi rreziqet ligjore, shanset e suksesit dhe hapat e mëtejshëm proceduralë.',
        },
      ];
    }

    if (clientPosition === 'NEUTRAL') {
      return [
        {
          title: 'AUDITIMI I LËNDËS',
          badge: 'ANALIZA OBJEKTIVE',
          icon: Scale,
          prompt: 'Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara.',
        },
        {
          title: 'LIGJSHMËRIA & PROVAT',
          badge: 'BARRA E PROVËS',
          icon: ShieldCheck,
          prompt: 'Vlerëso ligjshmërinë e pretendimeve të palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit në fuqi.',
        },
        {
          title: 'ZBULIMI I MOSPERPUTHJEVE',
          badge: 'KONTROLL PROCEDURAL',
          icon: Gavel,
          prompt: 'Identifiko mospërputhjet thelbësore procedurale dhe mjetet juridike të zbatueshme në këtë fazë të lëndës.',
        },
        {
          title: 'MEMORANDUMI OBJEKTIV',
          badge: 'SINTEZA E ÇËSHTJES',
          icon: FileText,
          prompt: 'Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme.',
        },
      ];
    }

    // DEFENDANT (Default)
    return [
      {
        title: 'STRATEGJIA E MBROJTJES',
        badge: 'MBROJTJA & ARGUMENTET',
        icon: ShieldCheck,
        prompt: 'Analizo 3 prapësimet kryesore të mbrojtjes, kontradiktat e palës kundërshtare dhe provat shfajësuese në fashikull.',
      },
      {
        title: 'BAZA LIGJORE & PROCEDURA',
        badge: 'LPK & KODET LIGJORE',
        icon: Scale,
        prompt: 'Analizo bazën ligjore procedurale dhe materiale, afatet dhe zbatueshmërinë e neneve të ligjeve përkatëse të Kosovës.',
      },
      {
        title: 'PYETËSORI I SEANCËS',
        badge: 'MARRJA NË PYETJE',
        icon: Gavel,
        prompt: 'Gjenero pyetjet taktike dhe kundër-pyetjet për ballafaqimin e dëshmitarëve dhe ekspertëve në seancë.',
      },
      {
        title: 'RAPORTI PËR KLIENTIN',
        badge: 'MEMO TEKNIKE',
        icon: FileText,
        prompt: 'Përgatit një përmbledhje ekzekutive mbi rreziqet ligjore, shanset e suksesit dhe hapat e mëtejshëm proceduralë.',
      },
    ];
  };

  const cards = getCards();

  return (
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-3 sm:p-6 gap-4 sm:gap-5 max-w-3xl mx-auto w-full">
      <div className="space-y-2 max-w-xl mx-auto">
        <h3 className="text-sm sm:text-base md:text-lg font-bold text-text-primary tracking-tight">
          Unë jam <span className="font-black text-primary-start">SOKRATI</span> Agjenti i rastit tuaj, {userSalutation}
        </h3>

        <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium px-2">
          Asistenti juaj inteligjent për analizën e thellë të provave, strategjinë procedurale dhe zbatimin e ligjeve të Kosovës.
        </p>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-main rounded-xl text-[10px] sm:text-xs text-text-muted font-medium shadow-sm">
          <Info size={13} className="text-primary-start shrink-0" />
          <span>Përgjigjet bazohen në fashikull dhe duhet të verifikohen</span>
        </div>
      </div>

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