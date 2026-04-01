// FILE: src/drafting/templates/corporate/shareholders.ts
// ARCHITECTURE: KOSOVO CORPORATE GOVERNANCE & SHAREHOLDER PROTECTION – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const shareholdersTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Marrëveshje e Ortakëve (Shareholders' Agreement) për Shoqëri me Përgjegjësi të Kufizuar (Sh.P.K.) sipas Ligjit për Shoqëritë Tregtare.
GJUHA: Shqip (Formale, Juridike, Komerciale).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MARRËVESHJE E ORTAKËVE

## 1. Hyrje dhe Palët
- "Kjo marrëveshje lidhet sot, më [DATA], ndërmjet:"
  - Ortaku 1: [EMRI_I_ORTAKUT_A], me adresë [ADRESA_A], nr. personal [NR_PERSONAL_A].
  - Ortaku 2: [EMRI_I_ORTAKUT_B], me adresë [ADRESA_B], nr. personal [NR_PERSONAL_B].
- Ortakët janë themelues të shoqërisë "[EMRI_I_SHOQËRISË]" (në tekstin e mëtejmë: "Shoqëria").

## 2. Përkufizime dhe Interpretimi
- Kapitali themeltar: [SHUMA_NË_EURO] euro, i ndarë në [NUMRI_I_PJESËVE] pjesë kapitali.
- Secila pjesë kapitali jep të drejtën e një vote në Kuvendin e Ortakëve.
- Organet e Shoqërisë: Kuvendi i Ortakëve, Drejtori (ose Bordi i Drejtorëve), sipas Ligjit për Shoqëritë Tregtare (Ligji Nr. 06/L-016).

## 3. Menaxhimi dhe Vendimmarrja
- Kuvendi i Ortakëve mbahet të paktën [NUMRI] herë në vit.
- Vendimet merren me shumicë të thjeshtë, përveç vendimeve themelore që kërkojnë shumicë të kualifikuar (të paktën [PËRQINDJA]% të kapitalit), si:
  - Ndryshimi i kapitalit themeltar (LST neni [cakto nenin]);
  - Miratimi i bilancit vjetor (LST neni [cakto nenin]);
  - Ndryshimi i veprimtarisë kryesore të shoqërisë;
  - Shkrirja, bashkimi ose ndarja e shoqërisë.

## 4. Transferimi i Pjesëve të Kapitalit
- **E drejta e parablerjes (Right of First Refusal):** Një ortak që dëshiron të shesë pjesët e tij, duhet t'ua ofrojë fillimisht ortakëve të tjerë.
- **Klauzola "Drag-Along":** Nëse ortakët që zotërojnë të paktën [PËRQINDJA]% të kapitalit pranojnë të shesin shoqërinë, ata mund të detyrojnë ortakët e tjerë të bashkëshiten në të njëjtat kushte.
- **Klauzola "Tag-Along":** Nëse një ortak shet pjesët e tij, ortakët e tjerë kanë të drejtë të bashkëshiten në të njëjtat kushte.
- Transferimi i pjesëve të kapitalit rregullohet sipas neneve [cakto nenet] të Ligjit për Shoqëritë Tregtare (LST).

## 5. Ndarja e Fitimit dhe Politika e Dividendit
- Fitimi neto pas shlyerjes së obligimeve tatimore ndahet si më poshtë:
  - [PËRQINDJA]% për Ortakun A;
  - [PËRQINDJA]% për Ortakun B.
- Dividenda paguhet jo më vonë se [DATA_E_PAGESËS] e çdo viti, nëse Kuvendi i Ortakëve vendos ndryshe.

## 6. Zgjidhja e Ngërçit (Deadlock)
- Nëse ortakët nuk arrijnë të marrin vendim për një çështje thelbësore për më shumë se [NUMRI_DITËSH] ditë, procedura e zgjidhjes është:
  1. Ndërmjetësim i detyrueshëm nga një ndërmjetës i përbashkët i emëruar nga ortakët.
  2. Nëse ndërmjetësimi dështon, secili ortak ka të drejtë t'i ofrojë tjetrit shitjen e pjesëve të tij me vlerë të përcaktuar nga një vlerësues i pavarur.

## 7. Ligji i Zbatueshëm dhe Gjykata Kompetente
- Marrëveshja interpretohet dhe zbatohet sipas ligjeve të Republikës së Kosovës.
- Baza ligjore: Ligji për Shoqëritë Tregtare (Ligji Nr. 06/L-016), nenet përkatëse për menaxhimin, transferimin e pjesëve, dhe ndarjen e fitimit.
- Çdo mosmarrëveshje do të zgjidhet në Gjykatën Themelore në Prishtinë – Departamenti për Çështje Ekonomike.

## 8. Nënshkrimet
- Ortaku A: [EMRI_MBIEMRI_ORTAKU_A], nënshkrimi, data [DATA].
- Ortaku B: [EMRI_MBIEMRI_ORTAKU_B], nënshkrimi, data [DATA].
- Dëshmitarët (nëse ka): [EMRI_MBIEMRI_DËSHMITAR_1], [EMRI_MBIEMRI_DËSHMITAR_2].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "MARRËVESHJE E ORTAKËVE" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_ORTAKUT_A]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë marrëveshje, baza ligjore është Ligji për Shoqëritë Tregtare (Ligji Nr. 06/L-016). Mos përfshi ligje që nuk lidhen me fushën korporative (p.sh., LCP, Ligji i Familjes).
- Mos përdor gjuhë procesuale gjyqësore (nuk është padi). Fokusohu në qeverisjen korporative dhe marrëveshjet kontraktuale ndërmjet ortakëve.
  `,
  placeholder: "Shembull: Fatmir Berisha dhe Labinot Gashi do të themelojnë 'Tech-Solutions Sh.P.K.'. Fatmiri do të kontribuojë me kapital në para, ndërsa Labinoti me ekspertizë teknike. Duam të dimë si ndahet fitimi dhe çfarë ndodh nëse njëri do të largohet nga biznesi.",
  label: "Marrëveshje e Ortakëve",
};