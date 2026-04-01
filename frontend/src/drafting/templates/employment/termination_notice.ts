// FILE: src/drafting/templates/employment/termination_notice.ts
// ARCHITECTURE: KOSOVO LABOR LAW COMPLIANCE – TERMINATION NOTICE (RISK MITIGATION) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const terminationNoticeTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Vendim për Ndërprerje të Marrëdhënies së Punës (Termination Notice) sipas Ligjit të Punës të Republikës së Kosovës.
GJUHA: Shqip (Formale, Juridike, Teknike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# VENDIM PËR NDËRPRERJE TË MARRËDHËNIES SË PUNËS

## 1. Të Dhënat e Punëmarrësit
- Emri dhe mbiemri: [EMRI_MBIEMRI_PUNËMARRËSIT]
- Pozita: [POZITA_E_PUNËMARRËSIT]
- Data e fillimit të punës: [DATA_FILLIMIT]

## 2. Baza Ligjore
- Kjo vendim bazohet në Ligjin e Punës të Republikës së Kosovës (Ligji Nr. 03/L-212).
- Neni i zbatueshëm: [ZBATONI_NENIN] (zgjidh një nga më poshtë dhe shpjego pse zbatohet):
  - Neni 70 – Ndërprerja nga punëdhënësi për arsye ekonomike, teknike ose organizative.
  - Neni 71 – Ndërprerja për shkak të paaftësisë së punëmarrësit.
  - Neni 72 – Ndërprerja për shkak të sjelljes së punëmarrësit (shkelje e detyrimeve).
  - Neni 73 – Ndërprerja me njoftim nga punëdhënësi (pa shkak të veçantë).

## 3. Arsyetimi i Vendimit
- [PËRSHKRIMI_I_ARSYEVE_FAKTIKE] (duhet të jetë i qartë, i provueshëm dhe në përputhje me nenin e cituar).
- Nëse bazohet në nenin 72, duhet të përshkruhen shkeljet konkrete dhe vërejtjet e mëparshme.

## 4. Afati i Njoftimit (Notice Period)
- Data e fundit e punës: [DATA_MBARIMIT]
- Periudha e njoftimit: [NUMRI_DITËVE] ditë (në përputhje me nenin 73 të Ligjit të Punës).
- Gjatë periudhës së njoftimit, punëmarrësi: [VENDOS_NËSE_PUNON_OSE_LIROHET_NGA_PUNA] (p.sh., "vazhdon punën" ose "lirohet nga puna me pagë të plotë").

## 5. Llogaritja e Pushimeve dhe Kompensimeve
- Paga e pashlyer deri në datën e ndërprerjes: [SHUMA_PAGËS] €.
- Kompensimi për pushim vjetor të pashfrytëzuar: [NUMRI_DITËVE_PUSHIM] ditë, vlera [SHUMA_PUSHIMIT] €.
- Çdo kompensim tjetër (psh. pagesa për periudhën e njoftimit nëse punëmarrësi është liruar): [SHPJEGIMI_DHE_SHUMAT].

## 6. E Drejta e Ankesës (KLAUZOLË E DETYRUESHME)
- Punëmarrësi ka të drejtë të parashtrojë ankesë pranë komisionit disiplinor të Punëdhënësit (nëse ekziston) ose drejtpërdrejt në Gjykatën Themelore kompetente, brenda afatit prej 30 ditësh nga data e pranimit të këtij vendimi, në pajtim me nenin 75 të Ligjit të Punës.

## 7. Dorëzimi i Mjeteve të Punës
- Punëmarrësi është i detyruar të dorëzojë të gjitha mjetet e punës (laptopi, çelësat, ID‑në, dokumentet e tjera) deri më datën [DATA_DORËZIMIT], përndryshe mbahet përgjegjës për dëmin e shkaktuar.

## 8. Nënshkrimi
- Punëdhënësi / Përfaqësuesi i autorizuar: [EMRI_MBIEMRI_PUNËDHËNËSIT], [POZITA], nënshkrimi, data [DATA_LËSHIMIT].
- Punëmarrësi (vërtetim i pranimit): nënshkrimi, data [DATA_PRONIMIT].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "VENDIM PËR NDËRPRERJE TË MARRËDHËNIES SË PUNËS" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_MBIEMRI_PUNËMARRËSIT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë vendim, baza ligjore është Ligji i Punës (Ligji Nr. 03/L-212). Mos përfshi ligje që nuk lidhen me marrëdhëniet e punës.
- Sigurohu që arsyetimi të jetë i qartë dhe në përputhje me nenin e zgjedhur, për të minimizuar rrezikun e kontestimit.
  `,
  placeholder: "Shembull: Punonjësi 'Artan Hoxha' ka dështuar të përmbushë detyrat e tij për 3 muaj me radhë, përkundër vërejtjeve me shkrim. Kontrata do të ndërpritet pas 30 ditësh njoftim, siç kërkohet me ligj.",
  label: "Vendim për Ndërprerje",
};