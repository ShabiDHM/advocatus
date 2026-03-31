// FILE: src/drafting/templates/corporate/mou.ts
// ARCHITECTURE: KOSOVO CORPORATE INTENT & GOOD FAITH NEGOTIATION

import { TemplateConfig } from '../../types';

export const mouTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Memorandum Bashkëpunimi (Memorandum of Understanding - MoU).
GJUHA: Shqip (Formale, Komerciale).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MEMORANDUM BASHKËPUNIMI

## 1. Palët Kontraktuese
- Identifikimi i plotë i palëve: [EMRI_I_KOMPANISË_A] dhe [EMRI_I_KOMPANISË_B], përfshirë personat e autorizuar për përfaqësim.

## 2. Qëllimi dhe Objekti i Bashkëpunimit
- Përshkrimi i qartë i qëllimit strategjik, fushëveprimi i bashkëpunimit dhe rezultatet e pritshme.

## 3. Parimet e Bashkëpunimit
- Theksimi i parimit të "Mirëbesimit" (Good Faith) në përputhje me dispozitat e 'Ligjit për Marrëdhëniet e Detyrimeve (LMD)'.

## 4. Natyra Ligjore (Binding vs. Non-binding)
- Sqarimi i qartë se cilat seksione janë obligative (psh. Konfidencialiteti, Pronësia Intelektuale) dhe cilat janë vetëm shprehje e qëllimit (të palidhshme ligjërisht).

## 5. Konfidencialiteti
- Detyrimi për ruajtjen e sekretit afarist të palëve gjatë fazës së negociatave.

## 6. Kohëzgjatja dhe Përfundimi
- Afati kohor i vlefshmërisë së këtij Memorandumi dhe mënyra e shkëputjes.

## 7. Ligji i Zbatueshëm dhe Zgjidhja e Mosmarrëveshjeve
- Zbatimi i ligjeve të Republikës së Kosovës.

## 8. Nënshkrimet
- Hapësira për nënshkrimin dhe vulën e përfaqësuesve të palëve:
  PËR PALËN A: _________________
  PËR PALËN B: _________________
  `,
  placeholder: "Shembull: Kompania ime 'Tech-Prishtina' dëshiron të bashkëpunojë me një kompani logjistike 'Logjistika-Express' për të zhvilluar një sistem shpërndarjeje automatike në Kosovë. Duam të definojmë hapat e parë për 6 muaj.",
  label: "Memorandum Bashkëpunimi (MoU)",
};