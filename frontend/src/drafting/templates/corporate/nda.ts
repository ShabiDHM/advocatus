// FILE: src/drafting/templates/corporate/nda.ts
// ARCHITECTURE: KOSOVO TRADE SECRET & COMMERCIAL LIABILITY PROTECTION

import { TemplateConfig } from '../../types';

export const ndaTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Marrëveshje për Moszbulim të Informacionit (NDA - Non-Disclosure Agreement).
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MARRËVESHJE PËR MOSZBULIMIN E INFORMACIONIT (NDA)

## 1. Palët e Marrëveshjes
- Pala Zbuluese ([EMRI_I_KOMPANISË_A]) dhe Pala Pranuese ([EMRI_I_KOMPANISË_B]).

## 2. Përkufizimi i Informacionit Konfidencial
- Defino informacionin si çdo informacion teknik, financiar, komercial, ose strategjik. Cito mbrojtjen si "Sekret Tregtar" sipas 'Ligjit Nr. 06/L-016 për Shoqëritë Tregtare'.

## 3. Detyrimet e Palës Pranuese
- Detyrimi për moszbulim, moskopjim dhe mos-përdorim për qëllime të tjera përveç qëllimit të miratuar.

## 4. Standardi i Kujdesit
- Pala Pranuese duhet ta mbrojë informacionin me të njëjtin nivel kujdesi siç mbron informacionin e vet, por jo më pak se një nivel i arsyeshëm profesional.

## 5. Përjashtimet (Informacionet Publike)
- Informacionet që janë bërë publike pa fajin e Palës Pranuese ose që ekzistonin përpara marrëveshjes.

## 6. Kohëzgjatja (Termi)
- Specifiko sa vjet (psh. [NUMRI] vjet) pas përfundimit të bashkëpunimit mbetet në fuqi detyrimi për konfidencialitet.

## 7. Pasojat e Shkeljes dhe Dëmshpërblimi
- Pala Pranuese është përgjegjëse për shkeljen e këtyre detyrimeve sipas dispozitave për dëmet në 'Ligjin për Marrëdhëniet e Detyrimeve (LMD)'.

## 8. Ligji i Zbatueshëm dhe Gjykata Kompetente
- Zbatimi i ligjeve të Republikës së Kosovës. Çdo mosmarrëveshje do të zgjidhet në Gjykatën Themelore në Prishtinë.

## 9. Nënshkrimet
- Nënshkrimi i përfaqësuesve të autorizuar të të dyja palëve.
  `,
  placeholder: "Shembull: Kompania ime po ndan të dhëna teknike të një softueri të ri me një bashkëpunëtor të jashtëm. Dua të sigurohem që ata nuk do t'i kopjojnë kodin apo klientët tanë për 3 vitet e ardhshme.",
  label: "Marrëveshje Konfidencialiteti (NDA)",
};