// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V46.0 (ANALIZO RASTIN + FORENSIKA DOKUMENTI + HARTIMI)

import React, { useMemo } from 'react';
import { ShieldCheck, Scale, Gavel, FileText, Info, ChevronRight, Swords, Shield, FileSearch } from 'lucide-react';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL' | string;
  selectedDocumentIds?: string[];
  documents?: any[];
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
  clientPosition = 'DEFENDANT',
  onSendMessage,
}) => {
  const normalizedPosition = String(clientPosition || 'DEFENDANT').toUpperCase();

  const cards = useMemo(() => {
    const baseCards = [
      {
        title: '⚖️ ANALIZO RASTIN',
        badge: 'RAPORTI I PLOTË',
        badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
        icon: FileSearch,
        prompt: 'ANALIZO RASTIN — Gjenero raportin e plotë forenzik me 10 seksione: përmbledhja ekzekutive, kronologjia, shkeljet me nene, matrica e provave, aktorët, baza statutore, opinioni supremit, dëmet, plani i veprimit dhe rekomandimet.',
      },
      {
        title: '🔍 FORENZIKA E DOKUMENTIT',
        badge: 'AUDITIM 1-KLIK',
        badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
        icon: Scale,
        prompt: 'Audito dokumentin e zgjedhur: verifiko nenet, zbulon prapadatimet, lapsuset procedurale dhe jep opinionin e Gjyqtarit Suprem.',
      },
    ];

    // Shto kartelat specifike sipas rolit
    let roleCards = [];

    if (normalizedPosition === 'PLAINTIFF') {
      roleCards = [
        {
          title: 'STRATEGJIA E PADISË',
          badge: 'SULMI',
          badgeColor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
          icon: Swords,
          prompt: 'Duke u bazuar në fashikull, ndërto shtyllat strategjike të kërkesëpadisë me provat vendimtare.',
        },
        {
          title: 'BAZA STATUTORE',
          badge: 'LIGJET',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: ShieldCheck,
          prompt: 'Nxirr bazën e plotë ligjore dhe audito lapsuset me precedentët e Gjykatës Supreme.',
        },
      ];
    } else if (normalizedPosition === 'NEUTRAL') {
      roleCards = [
        {
          title: 'AUDITIMI OBJEKTIV',
          badge: 'PAANSHMËRI',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: ShieldCheck,
          prompt: 'Analizo me paanshmëri të plotë të gjitha provat dhe vendimet sipas standardit suprem.',
        },
        {
          title: 'MEMORANDUMI DOKTRINAR',
          badge: 'SINTEZA',
          badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
          icon: FileText,
          prompt: 'Përgatit memorandumin përfundimtar doktrinar mbi çështjen.',
        },
      ];
    } else {
      // DEFENDANT
      roleCards = [
        {
          title: 'MBROJTJA DHE PRAPËSIMET',
          badge: 'PRAPËSIMET',
          badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
          icon: Shield,
          prompt: 'Analizo prapësimet e mbrojtjes dhe faktet shfajësuese sipas precedentëve suprem.',
        },
        {
          title: 'KUNDËR-PYETJET',
          badge: 'BALLAFAQIM',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: Gavel,
          prompt: 'Gjenero kundër-pyetjet taktike për të ballafaquar paditësin në seancë.',
        },
      ];
    }

    return [...baseCards, ...roleCards];
  }, [normalizedPosition]);

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
          <span>Përgjigjet bazohen në fashikull dhe precedentët e Gjykatës Supreme</span>
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

              <p className="text-xs text-text-secondary leading-relaxed font-normal line-clamp-2">
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