// FILE: src/drafting/templates/real_estate/power_of_attorney.ts
// ARCHITECTURE: KOSOVO NOTARIAL COMPLIANCE (LIGJI PËR NOTERINË)

import { TemplateConfig } from '../../types';

export const powerOfAttorneyTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Autorizim / Prokurë (Power of Attorney).
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# AUTORIZIM (PROKURË)

## 1. Dhënësi i Autorizimit (Pali)
- Emri, Mbiemri, nr. personal, adresa e banimit dhe data e lindjes.

## 2. Pranuesi i Autorizimit (I Autorizuari)
- Emri, Mbiemri, nr. personal, adresa e banimit.

## 3. Qëllimi dhe Fusha e Autorizimit (Seksioni më i rëndësishëm)
- Përshkrimi i saktë i veprimeve (psh. "Të nënshkruajë kontratën e shitjes së paluajtshmërisë me nr. parcele..."). 
- Specifiko nëse ka të drejtë të pranojë pagesa apo vetëm të nënshkruajë.

## 4. Kohëzgjatja
- Data e fillimit dhe data e skadimit (ose klauzola "deri në përfundim të punës").

## 5. Kufizimet dhe Revokimi
- E drejta e dhënësit për të revokuar (shfuqizuar) autorizimin në çdo kohë.

## 6. Baza Ligjore (Detyruese)
- "Ky autorizim bëhet në përputhje me dispozitat e 'Ligjit për Marrëdhëniet e Detyrimeve' dhe 'Kodi Civil' të Republikës së Kosovës."

## 7. Noterizimi (Detyruese)
- KLAUZOLË E DETYRUESHME: "Ky autorizim është i vlefshëm vetëm pasi të jetë vërtetuar (noterizuar) nga Noteri publik në përputhje me 'Ligjin për Noterinë (Nr. 03/L-010)'."

## 8. Nënshkrimi
- Nënshkrimi i Dhënësit të Autorizimit.
  `,
  placeholder: "Shembull: Unë, [EMRI], autorizoj avokatin [EMRI_AVOKATIT] që në emrin tim të shesë banesën në Prishtinë, të nënshkruajë para noterit dhe të pranojë çmimin e shitjes në xhirollogarinë time.",
  label: "Autorizim / Prokurë",
};