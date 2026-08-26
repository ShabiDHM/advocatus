// FILE: src/components/chat/CommandPaletteGrid.tsx
// PHOENIX PROTOCOL - COMMAND PALETTE GRID V39.0 (DYNAMIC SCOPE-AWARE LEGAL CITATION VERIFIER)

import React, { useMemo } from 'react';
import { ShieldCheck, Scale, Gavel, FileText, Info, ChevronRight, Swords, Shield } from 'lucide-react';
import { Document } from '../../data/types';

interface CommandPaletteGridProps {
  userSalutation: string;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL' | string;
  selectedDocumentIds?: string[];
  documents?: Document[];
  onSendMessage: (prompt: string) => void;
}

export const CommandPaletteGrid: React.FC<CommandPaletteGridProps> = ({
  userSalutation,
  clientPosition = 'DEFENDANT',
  selectedDocumentIds = [],
  documents = [],
  onSendMessage,
}) => {
  const normalizedPosition = String(clientPosition || 'DEFENDANT').toUpperCase();

  // Determine active document context
  const isSingleDoc = selectedDocumentIds.length === 1;
  const activeDoc = isSingleDoc ? documents.find(d => String(d.id) === String(selectedDocumentIds[0])) : null;
  const activeDocName = activeDoc?.file_name || 'këtë dokument';

  // Dynamic Prompt for Legal Verification
  const verificationPrompt = useMemo(() => {
    if (isSingleDoc) {
      return `Duke u bazuar në dokumentin e zgjedhur "${activeDocName}", analizo dhe lidh të gjitha nenet, paragrafët dhe bazën përkatëse ligjore (KPRK, KPPRK, LPK, LMD, Kushtetutë, Konventa) për verifikim të drejtpërdrejtë, pa ndryshuar asnjë fakt apo emër të fashikullit.`;
    }
    return `Duke u bazuar në të gjithë fashikullin e lëndës, ndërto matricën e plotë të verifikimit ligjor duke lidhur të gjitha provat, veprimet dhe shkeljet me nenet dhe ligjet përkatëse të Kosovës (KPRK, KPPRK, Kushtetutë, Konventa), të grupuara qartë sipas secilit dokument të administruar.`;
  }, [isSingleDoc, activeDocName]);

  const cards = useMemo(() => {
    // 1. ROLI: PADITËS / KALLËZUES
    if (normalizedPosition === 'PLAINTIFF') {
      return [
        {
          title: 'STRATEGJIA E PADISË / KALLËZIMIT',
          badge: 'PRETENDIMET',
          badgeColor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
          icon: Swords,
          prompt: isSingleDoc 
            ? `Identifiko shtyllat kryesore dhe provat vendimtare nga dokumenti "${activeDocName}".`
            : 'Identifiko 3 shtyllat kryesore ku mbështetet kërkesëpadia/kallëzimi ynë dhe provat vendimtare që ngarkojnë të paditurin/denoncuarin.',
        },
        {
          title: 'VERIFIKIMI I NENEVE DHE LIGJEVE',
          badge: 'BAZA LIGJORE',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: Scale,
          prompt: verificationPrompt,
        },
        {
          title: 'PYETËSORI I BALLAFAQIMIT',
          badge: 'MARRJA NË PYETJE',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: Gavel,
          prompt: 'Gjenero pyetjet taktike për të ballafaquar palën kundërshtare dhe dëshmitarët e saj në seancë.',
        },
        {
          title: 'DËMI DHE MASAT EMERGJENTE',
          badge: 'MEMORANDUM',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: FileText,
          prompt: 'Analizo kërkesat për masë emergjente mbrojtëse, llogarit dëmet e kërkuara dhe përgatit përmbledhjen ekzekutive.',
        },
      ];
    }

    // 2. ROLI: NEUTRAL (Auditim / Gjykata)
    if (normalizedPosition === 'NEUTRAL') {
      return [
        {
          title: 'GJENDJA DHE SHKRESAT',
          badge: 'AUDITIMI I LËNDËS',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          icon: Scale,
          prompt: isSingleDoc
            ? `Analizo objektivisht dokumentin "${activeDocName}" dhe vlerën provuese të tij.`
            : 'Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara.',
        },
        {
          title: 'VERIFIKIMI I NENEVE DHE LIGJEVE',
          badge: 'BAZA LIGJORE',
          badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
          icon: ShieldCheck,
          prompt: verificationPrompt,
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

    // 3. ROLI: I PADITUR / I DENONCUAR (Mbrojtje)
    return [
      {
        title: 'STRATEGJIA E MBROJTJES',
        badge: 'PRAPËSIMET',
        badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
        icon: Shield,
        prompt: isSingleDoc
          ? `Analizo faktet shfajësuese dhe prapësimet e mundshme nga dokumenti "${activeDocName}".`
          : 'Analizo 3 prapësimet kryesore të mbrojtjes, mungesën e provave të paditësit dhe faktet shfajësuese në fashikull.',
      },
      {
        title: 'VERIFIKIMI I NENEVE DHE LIGJEVE',
        badge: 'BAZA LIGJORE',
        badgeColor: 'bg-primary-start/10 text-primary-start border-primary-start/30',
        icon: Scale,
        prompt: verificationPrompt,
      },
      {
        title: 'KUNDËR-PYETJET PËR PADITËSIN',
        badge: 'MARRJA NË PYETJE',
        badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
        icon: Gavel,
        prompt: 'Gjenero kundër-pyetjet taktike për të zbuluar kontradiktat e palës kundërshtare dhe dëshmitarëve të saj në seancë.',
      },
      {
        title: 'RREZIQET DHE RAPORTI PËR KLIENTIN',
        badge: 'MEMORANDUM',
        badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
        icon: FileText,
        prompt: 'Përgatit përmbledhjen ekzekutive mbi rreziqet ligjore, shanset e mbrojtjes dhe hapat e mëtejshëm.',
      },
    ];
  }, [normalizedPosition, isSingleDoc, activeDocName, verificationPrompt]);

  return (
    <div className="flex-1 my-auto flex flex-col items-center justify-center text-center p-3 sm:p-6 gap-4 sm:gap-5 max-w-3xl mx-auto w-full">
      <div className="space-y-2 max-w-xl mx-auto">
        <h3 className="text-sm sm:text-base md:text-lg font-bold text-text-primary tracking-tight">
          Unë jam <span className="font-black text-primary-start">SOKRATI</span> Agjenti i rastit tuaj, {userSalutation}
        </h3>

        <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium px-2">
          {isSingleDoc 
            ? `Fokusuar te dokumenti: ${activeDocName}`
            : 'Asistenti juaj inteligjent për analizën e thellë të provave, strategjinë procedurale dhe zbatimin e ligjeve të Kosovës.'
          }
        </p>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-main rounded-xl text-[10px] sm:text-xs text-text-muted font-medium shadow-sm">
          <Info size={13} className="text-primary-start shrink-0" />
          <span>
            {isSingleDoc 
              ? `Auditim aktiv i dokumentit [${activeDocName}]`
              : 'Përgjigjet bazohen në të gjithë fashikullin dhe duhet të verifikohen'
            }
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 w-full text-left mt-1">
        {cards.map((card, idx) => {
          const IconComponent = card.icon;
          return (
            <button
              key={`${normalizedPosition}_${isSingleDoc ? activeDocName : 'all'}_${idx}`}
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