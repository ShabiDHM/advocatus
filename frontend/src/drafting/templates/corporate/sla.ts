// FILE: src/drafting/templates/corporate/sla.ts
// ARCHITECTURE: KOSOVO SERVICE LEVEL PERFORMANCE & PENALTY ENFORCEMENT

import { TemplateConfig } from '../../types';

export const slaTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Marrëveshje e Nivelit të Shërbimit (SLA - Service Level Agreement).
GJUHA: Shqip (Formale, Komerciale, Teknike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MARRËVESHJE E NIVELIT TË SHËRBIMIT (SLA)

## 1. Palët
- Ofruesi i Shërbimit ([EMRI_I_KOMPANISË_SË_IT]) dhe Klienti ([EMRI_I_KLIENTIT]).

## 2. Përshkrimi i Shërbimeve
- Detajimi i saktë i shërbimeve të kontraktuara (psh. mirëmbajtje serveri, zhvillim softueri, mbështetje teknike).

## 3. Matrikset e Performancës (KPIs)
- Përdor tabelë për të listuar: Shërbimin, Kohën e Përgjigjes (psh. 4 orë), dhe Disponueshmërinë (psh. 99.9%).

## 4. Detyrimet e Palëve
- Çfarë pritet nga Ofruesi dhe çfarë bashkëpunimi kërkohet nga Klienti.

## 5. Sanksionet për Mos-përmbushje (Penalitetet)
- Përcakto zbritjen e çmimit ose kompensimin nëse shërbimi bie nën nivelin e kontraktuar. Cito përputhshmërinë me 'Ligjin për Marrëdhëniet e Detyrimeve (LMD)' për dëmet kontraktuale.

## 6. Matrica e Përshkallëzimit (Escalation)
- Hapat që ndiqen në rast të problemeve të vazhdueshme (nga mbështetja teknike te menaxhmenti).

## 7. Kohëzgjatja dhe Përfundimi
- Afati i vlefshmërisë dhe kushtet për shkëputje të njëanshme.

## 8. Ligji i Zbatueshëm dhe Gjykata
- Ligjet e Republikës së Kosovës. Zgjidhja në Gjykatën Themelore në Prishtinë.

## 9. Nënshkrimet
- Nënshkrimi i palëve.

UDHËZIM: Përdor ton profesional dhe teknik. Nëse nuk ka të dhëna specifike për përqindjet e disponueshmërisë, përdor [PËRQINDJA_%].
  `,
  placeholder: "Shembull: Kompania ime ofron mirëmbajtje IT për një bankë. Duhet të përgjigjemi brenda 2 orëve për probleme kritike dhe brenda 24 orëve për probleme të thjeshta. Nëse dështojmë, kemi një penalitet financiar.",
  label: "Marrëveshje e Nivelit të Shërbimit (SLA)",
};