// FILE: src/components/chat/CommandPaletteGrid.tsx
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
      badge: clientPosition === 'DEFENDANT' ? 'MBROJTJA & ARGUMENTET' : 'SULMI & PRETEGIMET',
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
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-2 sm:p-4 gap-3 sm:gap-4">
      <div className="space-y-1.5 max-w-lg">
        <h3 className="text-xs sm:text-base font-black uppercase text-text-primary tracking-tight">
          Unë jam Agjenti i rastit tuaj, {userSalutation}
        </h3>
        <p className="text-[10px] sm:text-xs text-text-secondary leading-relaxed font-medium">
          {clientPosition === 'DEFENDANT'
            ? 'Asistenti juaj ligjor me AI për ndërtimin e mbrojtjes strategjike, rrëzimin e padisë dhe analizën e thellë të dokumenteve të lëndës.'
            : 'Asistenti juaj ligjor me AI për vërtetimin e kërkesëpadisë, provimin e përgjegjësisë dhe argumentimin e të drejtave të klientit.'}
        </p>

        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-surface border border-main rounded-lg text-[9px] sm:text-[10px] text-text-muted font-medium mt-1">
          <Info size={11} className="text-primary-start shrink-0" />
          <span>Përgjigjet e AI shërbejnë për referencë dhe verifikohen nga avokati.</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3 w-full max-w-xl text-left mt-1">
        {cards.map((card, idx) => {
          const IconComponent = card.icon;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSendMessage(card.prompt)}
              className="group p-3 sm:p-3.5 bg-surface hover:bg-hover border border-main hover:border-primary-start/60 rounded-2xl text-left transition-all duration-200 shadow-sm flex flex-col justify-between gap-1.5 active:scale-[0.98] cursor-pointer"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[8px] sm:text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-primary-start/10 text-primary-start border border-primary-start/20 tracking-wider">
                  {card.badge}
                </span>
                <ChevronRight size={13} className="text-text-muted group-hover:text-primary-start transition-colors" />
              </div>

              <div className="flex items-center gap-2 mt-0.5">
                <IconComponent size={14} className="text-primary-start shrink-0" />
                <h4 className="text-[11px] sm:text-xs font-black uppercase text-text-primary tracking-wide group-hover:text-primary-start transition-colors">
                  {card.title}
                </h4>
              </div>

              <p className="text-[10px] sm:text-[11px] text-text-secondary leading-relaxed font-normal line-clamp-2">
                {card.prompt}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};