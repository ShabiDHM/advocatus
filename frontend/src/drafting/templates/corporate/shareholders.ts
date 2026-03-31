// FILE: src/drafting/templates/corporate/shareholders.ts
// ARCHITECTURE: KOSOVO CORPORATE GOVERNANCE & SHAREHOLDER PROTECTION

import { TemplateConfig } from '../../types';

export const shareholdersTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Marrëveshje e Ortakëve (Shareholders' Agreement) për Sh.P.K.
GJUHA: Shqip (Formale, Juridike, Komerciale).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MARRËVESHJE E ORTAKËVE

## 1. Hyrje dhe Palët
- "Kjo marrëveshje lidhet sot, më [DATA], ndërmjet: [EMRI_I_ORTAKUT_A]... dhe [EMRI_I_ORTAKUT_B]... në cilësinë e themeluesve të shoqërisë [EMRI_I_SHOQËRISË]."

## 2. Përkufizime dhe Interpretimi
- Defino kapitalin themeltar, pjesët e kapitalit (aksionet), dhe organet e shoqërisë.

## 3. Menaxhimi dhe Vendimmarrja
- Përcakto kompetencat e Kuvendit të Ortakëve dhe Drejtorit. Cito se si merren vendimet (shumicë e thjeshtë vs. shumicë e kualifikuar).

## 4. Transferimi i Pjesëve të Kapitalit
- Klauzolat "Right of First Refusal" (E drejta e parablerjes). 
- KLAUZOLË E DETYRUESHME: "Drag-Along" (Detyrimi për shitje) dhe "Tag-Along" (E drejta për të shitur bashkërisht).

## 5. Ndarja e Fitimit dhe Politika e Dividendit
- Mënyra dhe afatet e ndarjes së fitimit pas shlyerjes së obligimeve tatimore.

## 6. Zgjidhja e Ngërçit (Deadlock)
- Procedura për zgjidhjen e situatave ku ortakët nuk pajtohen (psh. shitja, likuidimi ose ndërmjetësimi).

## 7. Ligji i Zbatueshëm dhe Gjykata Kompetente
- Baza Ligjore: 'Ligji Nr. 06/L-016 për Shoqëritë Tregtare' i Republikës së Kosovës.
- Gjykata: Gjykata Themelore në Prishtinë - Departamenti për Çështje Ekonomike.

## 8. Nënshkrimet
- Nënshkrimi i të gjithë ortakëve, dëshmitarëve (nëse ka), dhe vula e shoqërisë.

UDHËZIM: Mos përdor gjuhë procesuale gjyqësore (nuk është padi). Përqendrohu në qeverisjen korporative.
  `,
  placeholder: "Shembull: Fatmir Berisha dhe Labinot Gashi do të themelojnë 'Tech-Solutions Sh.P.K.'. Fatmiri do të kontribuojë me kapital në para, ndërsa Labinoti me ekspertizë teknike. Duam të dimë si ndahet fitimi dhe çfarë ndodh nëse njëri do të largohet nga biznesi.",
  label: "Marrëveshje e Ortakëve",
};