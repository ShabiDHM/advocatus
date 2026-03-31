// FILE: src/drafting/templates/employment/employment_contract.ts
// ARCHITECTURE: KOSOVO LABOR LAW COMPLIANCE (LIGJI I PUNËS)

import { TemplateConfig } from '../../types';

export const employmentContractTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kontratë Pune (Employment Contract).
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# KONTRATË PUNE

## 1. Palët Kontraktuese
- Punëdhënësi ([EMRI_I_KOMPANISË_OSE_PRONARIT]) dhe Punëmarrësi ([EMRI_I_PUNONJËSIT]).

## 2. Pozita dhe Detyrat e Punës
- Përshkrimi i detajuar i pozitës dhe vendit të punës.

## 3. Kohëzgjatja dhe Periudha e Provës
- Data e fillimit dhe kohëzgjatja (kohë e caktuar ose e pacaktuar).
- KLAUZOLË E DETYRUESHME: Periudha e provës (psh. 6 muaj) sipas 'Ligjit të Punës së Kosovës'.

## 4. Orari i Punës dhe Pushimet
- Orari javor (psh. 40 orë), pushimi ditor, javor dhe vjetor (min. 20 ditë pune sipas ligjit).

## 5. Paga dhe Benefitet (Shto tabelë)
- Paga bruto, neto, mënyra e pagesës.
- Kontributet pensionale (Trusti) dhe tatimi në të ardhurat personale (TAP) sipas legjislacionit të Kosovës.

## 6. Detyrimet dhe Përgjegjësitë
- Respektimi i rregulloreve të brendshme dhe masave të sigurisë në punë.

## 7. Ndërprerja e Kontratës
- Kushtet për ndërprerje, afatet e njoftimit (sipas Ligjit të Punës) dhe rastet e shkëputjes së menjëhershme.

## 8. Zgjidhja e Kontesteve
- Zgjidhja e mosmarrëveshjeve në Gjykatën Themelore (Departamenti i Përgjithshëm/Çështje Ekonomike).

## 9. Nënshkrimet
- Nënshkrimi i Punëdhënësit dhe Punëmarrësit.

BAZA LIGJORE: Çdo dispozitë duhet të jetë në përputhje me "Ligjin e Punës (Nr. 03/L-212) të Republikës së Kosovës".
  `,
  placeholder: "Shembull: Blerta Rexhepi do të punësohet si Asistente Administrative në 'Prishtina-Consulting Sh.P.K.'. Paga bruto 500 EUR, kontratë me kohë të pacaktuar, me 3 muaj periudhë prove. Fillon me 1 prill.",
  label: "Kontratë Pune",
};