// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V44.0 (SUPREME COURT JURISPRUDENCE & FULL CASE FORENSICS)

import React, { useMemo } from 'react';
import { ShieldCheck, Scale, Gavel, FileText, Info, ChevronRight, Swords, Shield } from 'lucide-react';

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
    // 1. ROLI: PADITËS / KALLËZUES (Sulm Procedural & Standarti Suprem)
    if (normalizedPosition === 'PLAINTIFF') {
      return [
        {
          title: 'STRATEGJIA DHE PROVAT E PADISË',
          badge: 'KËRKESËPADIA',
          badgeColor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
          icon: Swords,
          prompt: 'Duke u bazuar në të gjithë fashikullin e lëndës dhe në vendimet parimore të Gjykatës Supreme të Kosovës, identifiko 3 shtyllat kryesore ku mbështetet kërkesëpadia/kallëzimi ynë, provat vendimtare që ngarkojnë palën kundërshtare dhe jep vlerësimin doktrinar të Gjyqtarit Suprem mbi qëndrueshmërinë e lëndës.',
        },
        {
          title: 'BAZA STATUTORE DHE JURISPRUDENCA',
          badge: 'BAZA LIGJORE',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: Scale,
          prompt: 'Analizo të gjithë fashikullin e lëndës: nxirr bazën e plotë ligjore (nenet, ligjet, Kushtetutën dhe Konventat), audito me saktësi nëse ka lapsuse në shkresa dhe lidhe çdo shkelje me precedentët dhe qëndrimet e Gjykatës Supreme të Kosovës.',
        },
        {
          title: 'PYETËSORI TAKTIK PËR SEANCË',
          badge: 'MARRJA NË PYETJE',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: Gavel,
          prompt: 'Duke u bazuar në kontradiktat e shkresave të fashikullit dhe standardin e vlerësimit të dëshmive të Gjykatës Supreme, gjenero pyetësorin taktik të ballafaqimit për të zbuluar të pavërtetat e palës kundërshtare dhe dëshmitarëve të saj në seancë.',
        },
        {
          title: 'LLOGARITJA E DËMIT DHE MASAT EMERGJENTE',
          badge: 'LLOGARITJA E DËMIT',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: FileText,
          prompt: 'Analizo të gjithë fashikullin: llogarit dëmet materiale e jomateriale sipas LMD-së bashkë me kamatën ligjore vonesore 8%, arsyeto masat emergjente mbrojtëse / sigurimin e kërkesëpadisë dhe përgatit përmbledhjen ekzekutive për klientin.',
        },
      ];
    }

    // 2. ROLI: NEUTRAL (Auditim Gjyqësor & Paanshmëri Supreme)
    if (normalizedPosition === 'NEUTRAL') {
      return [
        {
          title: 'AUDITIMI FORENZIK I FASHIKULLIT',
          badge: 'AUDITIMI I LËNDËS',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: Scale,
          prompt: 'Duke u bazuar në të gjithë fashikullin e lëndës, analizo me paanshmëri të plotë të gjitha provat e administruara, vendimet gjyqësore të marra dhe jep vlerësimin e Kolegjit të Gjykatës Supreme mbi ligjshmërinë e procesit.',
        },
        {
          title: 'BARRA E PROVËS DHE LIGJSHMËRIA',
          badge: 'STANDARD SUPREM',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: ShieldCheck,
          prompt: 'Vlerëso ligjshmërinë e pretendimeve të të dyja palëve në bazë të dispozitave ligjore dhe vendimeve parimore të Gjykatës Supreme mbi barrën e provës dhe vlefshmërinë procedurale.',
        },
        {
          title: 'PYETJET PËR ZBARDHJEN E TË VËRTETËS',
          badge: 'SQARIM FAKTESH',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: Gavel,
          prompt: 'Identifiko mospërputhjet thelbësore midis shkresave të fashikullit dhe formulo pyetje të thella neutrale për vërtetimin e plotë të gjendjes faktike.',
        },
        {
          title: 'MEMORANDUMI DOKTRINAR PËRFUNDIMTAR',
          badge: 'SINTEZA SUPREME',
          badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
          icon: FileText,
          prompt: 'Përgatit memorandumin përfundimtar doktrinar mbi çështjen duke sintetizuar të gjitha provat dhe konkluzionet sipas standardit më të lartë gjyqësor.',
        },
      ];
    }

    // 3. ROLI: I PADITUR / I DENONCUAR (Mbrojtje & Prapësime Supreme)
    return [
      {
        title: 'STRATEGJIA E MBROJTJES DHE PRAPËSIMET',
        badge: 'PRAPËSIMET',
        badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
        icon: Shield,
        prompt: 'Duke u bazuar në të gjithë fashikullin e lëndës dhe precedentët e Gjykatës Supreme të Kosovës, identifiko 3 prapësimet kryesore të mbrojtjes, mungesën e provave të paditësit, faktet shfajësuese dhe jep vlerësimin doktrinar të Gjyqtarit Suprem mbi rrëzimin e padisë/akuzës.',
      },
      {
        title: 'BAZA PROCEDURALE DHE PRECEDENTËT',
        badge: 'BAZA LIGJORE',
        badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
        icon: Scale,
        prompt: 'Analizo bazën procedurale të mbrojtjes në të gjithë fashikullin: parashkrimin e afateve prekluzive, shkeljet thelbësore procedurale, lapsuset e neneve dhe lidhjen me Aktgjykimet e Gjykatës Supreme të Kosovës.',
      },
      {
        title: 'KUNDËR-PYETJET PËR PALËN KUNDËRSHTARE',
        badge: 'MARRJA NË PYETJE',
        badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
        icon: Gavel,
        prompt: 'Duke u bazuar në kontradiktat e shkresave të fashikullit, gjenero kundër-pyetjet taktike për të ballafaquar paditësin dhe dëshmitarët e tij në seancë, duke shfrytëzuar të pavërtetat dhe mungesën e bazës materiale.',
      },
      {
        title: 'RREZIQET DHE RAPORTI PËR KLIENTIN',
        badge: 'MEMORANDUM',
        badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
        icon: FileText,
        prompt: 'Përgatit memorandumin ekzekutiv për klientin: analizo shanset e fitores së mbrojtjes, rreziqet e mundshme, hapat e mëtejshëm proceduralë dhe strategjinë para gjykatës.',
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