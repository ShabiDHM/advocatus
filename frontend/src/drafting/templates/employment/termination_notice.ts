// FILE: src/drafting/templates/employment/termination_notice.ts
// ARCHITECTURE: KOSOVO LABOR LAW COMPLIANCE - TERMINATION (RISK MITIGATION)

import { TemplateConfig } from '../../types';

export const terminationNoticeTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Vendim për Ndërprerje të Marrëdhënies së Punës (Termination Notice).
GJUHA: Shqip (Formale, Juridike, Teknike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# VENDIM PËR NDËRPRERJE TË MARRËDHËNIES SË PUNËS

## 1. Të Dhënat e Punëmarrësit
- Emri, Mbiemri dhe Pozita që mban aktualisht.

## 2. Baza Ligjore
- Cito shprehimisht 'Ligjin e Punës (Nr. 03/L-212)'.
- Cito nenin përkatës (psh. Neni 70/71/72) që justifikon shkëputjen (psh. shkelje e detyrave, performancë, ose nevoja ekonomike).

## 3. Arsyetimi i Vendimit
- Përshkrimi faktik dhe objektiv i arsyeve të ndërprerjes. (Detyruese: duhet të jetë i qartë dhe i provueshëm).

## 4. Afati i Njoftimit (Notice Period)
- Data e fundit e punës dhe përshkrimi i periudhës së njoftimit (nëse punonjësi duhet të punojë gjatë kësaj kohe ose shkëputje e menjëhershme).

## 5. Llogaritja e Pushimeve dhe Kompensimeve
- Kompensimi për pushimin vjetor të pashfrytëzuar dhe pagat e pashlyera deri në datën e ndërprerjes.

## 6. E Drejta e Ankesës (KLAUZOLË E DETYRUESHME)
- Punonjësi ka të drejtë të parashtrojë ankesë pranë komisionit disiplinor të Punëdhënësit ose drejtpërdrejt në Gjykatën Themelore brenda afateve ligjore.

## 7. Dorëzimi i Mjeteve të Punës
- Detyrimi i punonjësit për dorëzimin e laptopit, çelësave, ID-së apo pasurive tjera të shoqërisë.

## 8. Nënshkrimi
- Nënshkrimi i Punëdhënësit / Përfaqësuesit të autorizuar.
  `,
  placeholder: "Shembull: Punonjësi 'Artan Hoxha' ka dështuar të përmbushë detyrat e tij për 3 muaj me radhë, përkundër vërejtjeve me shkrim. Kontrata do të ndërpritet pas 30 ditësh njoftim, siç kërkohet me ligj.",
  label: "Vendim për Ndërprerje",
};