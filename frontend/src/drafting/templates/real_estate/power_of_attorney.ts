// FILE: src/drafting/templates/real_estate/power_of_attorney.ts
// ARCHITECTURE: KOSOVO NOTARIAL COMPLIANCE (LIGJI PËR NOTERINË & LIGJI PËR DETYRIMET) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const powerOfAttorneyTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Autorizim / Prokurë (Power of Attorney) sipas Ligjit për Detyrimet dhe Ligjit për Noterinë të Republikës së Kosovës.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# AUTORIZIM (PROKURË)

## 1. Dhënësi i Autorizimit (Pali)
- Emri, mbiemri: [EMRI_MBIEMRI_DHËNËSIT]
- Nr. personal: [NR_PERSONAL_DHËNËSIT]
- Adresa e banimit: [ADRESA_DHËNËSIT]
- Data e lindjes: [DATA_LINDJES_DHËNËSIT]

## 2. Pranuesi i Autorizimit (I Autorizuari)
- Emri, mbiemri: [EMRI_MBIEMRI_PRANUESIT]
- Nr. personal: [NR_PERSONAL_PRANUESIT]
- Adresa e banimit: [ADRESA_PRANUESIT]

## 3. Qëllimi dhe Fusha e Autorizimit
- Ky autorizim jepet për veprimet e mëposhtme (përshkrimi i saktë):
  [LISTA_E_VEPRIMEVE_TË_AUTORIZUARA]
- (Shembull: Të nënshkruajë kontratën e shitjes për pronën me nr. parcele [NR_PARCELËS], të dorëzojë dokumentet pranë noterit, të marrë çmimin e shitjes në xhirollogarinë e dhënësit, etj.)
- I autorizuari nuk ka të drejtë të kryejë veprime jashtë këtij qëllimi, përveç nëse autorizohet shprehimisht.

## 4. Kohëzgjatja
- Data e fillimit: [DATA_FILLIMIT]
- Data e skadimit: [DATA_SKADIMIT] ose "deri në përfundim të punës" / "deri në revokim".

## 5. Kufizimet dhe Revokimi
- Dhënësi i autorizimit mund ta revokojë (shfuqizojë) këtë autorizim në çdo kohë, duke njoftuar me shkrim të autorizuarin dhe palët e treta të përfshira.
- Autorizimi pushon automatikisht me vdekjen ose humbjen e aftësisë për të vepruar të dhënësit, nëse ligji nuk parashikon ndryshe.

## 6. Baza Ligjore
- Ky autorizim rregullohet nga Ligji për Detyrimet i Republikës së Kosovës (Ligji Nr. 2004/31), neni 139 (Autorizimi), neni 140 (Vlefshmëria), neni 141 (Përfundimi), dhe dispozitat e tjera të zbatueshme për përfaqësimin vullnetar.

## 7. Noterizimi (KLAUZOLË E DETYRUESHME)
- Ky autorizim do të jetë i vlefshëm vetëm pasi të vërtetohet (noterizohet) nga një noter publik i licencuar në Republikën e Kosovës, në përputhje me Ligjin për Noterinë ([LIGJI_PËR_NOTERINË]). Dhënësi i autorizimit duhet të paraqitet personalisht para noterit për të konfirmuar vullnetin e tij.

## 8. Nënshkrimi
- Dhënësi i autorizimit: [EMRI_MBIEMRI_DHËNËSIT], nënshkrimi, data [DATA].
- (Hapësirë për vërtetimin noterial)

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "AUTORIZIM (PROKURË)" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_MBIEMRI_DHËNËSIT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë autorizim, baza ligjore është Ligji për Detyrimet (LMD) dhe Ligji për Noterinë. Mos përfshi ligje që nuk lidhen (p.sh., LCP, Ligji i Familjes).
- Qëllimi dhe fusha duhet të jenë sa më të detajuara për të shmangur keqkuptimet dhe për të garantuar vlefshmërinë para noterit.
  `,
  placeholder: "Shembull: Unë, [EMRI], autorizoj avokatin [EMRI_AVOKATIT] që në emrin tim të shesë banesën në Prishtinë, të nënshkruajë para noterit dhe të pranojë çmimin e shitjes në xhirollogarinë time.",
  label: "Autorizim / Prokurë",
};