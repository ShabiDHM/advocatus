// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V38.0 (100% REAL-TIME DYNAMIC ROLE-SWITCHING)

import React, { useMemo } from 'react';
import { ShieldCheck, Scale, Gavel, FileText, Info, ChevronRight, Swords, Shield } from 'lucide-react';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL' | string;
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
  clientPosition = 'DEFENDANT',
  onSendMessage,
}) => {
  const normalizedPosition = String(clientPosition || 'DEFENDANT').toUpperCase();

  const cards = useMemo(() => {
    // 1. ROLI: PADITËS (Sulm / Kërkesëpadi / Përgjegjësi)
    if (normalizedPosition === 'PLAINTIFF') {
      return [
        {
          title: 'STRATEGJIA E PADISË',
          badge: 'KËRKESËPADIA',
          badgeColor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
          icon: Swords,
          prompt: 'Identifiko 3 shtyllat kryesore ku mbështetet kërkesëpadia jonë dhe provat vendimtare që ngarkojnë të paditurin.',
        },
        {
          title: 'BAZA STATUTORE DHE DETYRIMI',
          badge: 'BAZA LIGJORE',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: Scale,
          prompt: 'Analizo bazën ligjore të kërkesëpadisë, afatet procedurale dhe nenet përkatëse të ligjeve të Kosovës.',
        },
        {
          title: 'PYETËSORI PËR TË PADITURIN',
          badge: 'MARRJA NË PYETJE',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: Gavel,
          prompt: 'Gjenero pyetjet taktike për të ballafaquar të paditurin dhe dëshmitarët e tij në seancë.',
        },
        {
          title: 'DËMI DHE RAPORTI PËR KLIENTIN',
          badge: 'LLOGARITJA E DËMIT',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: FileText,
          prompt: 'Llogarit dëmet e kërkuara sipas ligjit dhe përgatit përmbledhjen ekzekutive mbi ecurinë e padisë.',
        },
      ];
    }

    // 2. ROLI: NEUTRAL (Auditim / Gjykata / Paanshmëri)
    if (normalizedPosition === 'NEUTRAL') {
      return [
        {
          title: 'GJENDJA DHE SHKRESAT',
          badge: 'AUDITIMI I LËNDËS',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: Scale,
          prompt: 'Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara.',
        },
        {
          title: 'LIGJSHMËRIA DHE STATUTI',
          badge: 'BARRA E PROVËS',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: ShieldCheck,
          prompt: 'Vlerëso ligjshmërinë e pretendimeve të të dyja palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit.',
        },
        {
          title: 'PYETJET PËR ZBARDHJEN E TË VËRTETËS',
          badge: 'SQARIM FAKTESH',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: Gavel,
          prompt: 'Identifiko mospërputhjet thelbësore dhe gjenero pyetje neutrale sqaruese për vërtetimin e fakteve.',
        },
        {
          title: 'MEMORANDUMI PËRFUNDIMTAR',
          badge: 'SINTEZA OBJEKTIVE',
          badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
          icon: FileText,
          prompt: 'Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme.',
        },
      ];
    }

    // 3. ROLI: I PADITUR (Mbrojtje / Prapësime / Shfajësim)
    return [
      {
        title: 'STRATEGJIA E MBROJTJES',
        badge: 'PRAPËSIMET',
        badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
        icon: Shield,
        prompt: 'Analizo 3 prapësimet kryesore të mbrojtjes, mungesën e provave të paditësit dhe faktet shfajësuese në fashikull.',
      },
      {
        title: 'BAZA PROCEDURALE E MBROJTJES',
        badge: 'BAZA LIGJORE',
        badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
        icon: Scale,
        prompt: 'Analizo bazën ligjore të prapësimeve, parashkrimin e afateve dhe nenet përkatëse për rrëzimin e padisë.',
      },
      {
        title: 'KUNDËR-PYETJET PËR PADITËSIN',
        badge: 'MARRJA NË PYETJE',
        badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
        icon: Gavel,
        prompt: 'Gjenero kundër-pyetjet taktike për të zbuluar kontradiktat e paditësit dhe dëshmitarëve të tij në seancë.',
      },
      {
        title: 'RREZIQET DHE RAPORTI PËR KLIENTIN',
        badge: 'MEMORANDUM',
        badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
        icon: FileText,
        prompt: 'Përgatit përmbledhjen ekzekutive mbi rreziqet ligjore, shanset e mbrojtjes dhe hapat e mëtejshëm.',
      },
    ];
  }, [normalizedPosition]);

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
              key={`${normalizedPosition}_${idx}`}
              type="button"
              onClick={() => onSendMessage(card.prompt)}
              className="group p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/60 rounded-2xl text-left transition-all duration-200 shadow-sm flex flex-col justify-between gap-2.5 active:scale-[0.98] cursor-pointer"
            >
              <div className="flex items-center justify-between gap-2">
                <span className={`text-[9px] sm:text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-md border tracking-wider ${card.badgeColor}`}>
                  {card.badge}
                </span>
                <ChevronRight size={14} className="text-text-muted group-hover:text-primary-start transition-colors" />
              </div>

              <div className="flex items-center gap-2 mt-0.5">
                <IconComponent size={16} className="text-primary-start shrink-0" />
                <h4 className="text-xs sm:text-sm font-bold uppercase text-text-primary tracking-wide group-hover:text-primary-start transition-colors">
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