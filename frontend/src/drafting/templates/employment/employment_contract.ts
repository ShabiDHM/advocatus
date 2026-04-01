// FILE: src/drafting/templates/employment/employment_contract.ts
// ARCHITECTURE: KOSOVO LABOR LAW COMPLIANCE (LIGJI I PUNËS NR. 03/L-212) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const employmentContractTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kontratë Pune (Employment Contract) sipas Ligjit të Punës të Republikës së Kosovës.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# KONTRATË PUNE

## 1. Palët Kontraktuese
- Punëdhënësi: [EMRI_I_KOMPANISË_OSE_PRONARIT], me seli në [ADRESA_E_PUNËDHËNËSIT], nr. regjistrimi [NR_REGJISTRIMIT].
- Punëmarrësi: [EMRI_I_PUNONJËSIT], me adresë [ADRESA_E_PUNONJËSIT], nr. personal [NR_PERSONAL].

## 2. Pozita dhe Detyrat e Punës
- Pozita: [TITULLI_I_POZITËS].
- Vendndodhja: [VENI_I_PUNËS].
- Përshkrimi i detyrave: [PËRSHKRIMI_I_DETYRAVE].

## 3. Kohëzgjatja dhe Periudha e Provës
- Data e fillimit: [DATA_FILLIMIT].
- Kohëzgjatja: [KOHË_E_CAKTUAR / E_PACAKTUAR]. Nëse e caktuar, deri më [DATA_MBARIMIT].
- Periudha e provës: [NUMRI_MUAJVE] muaj (maksimumi 6 muaj sipas Ligjit të Punës neni 15).
- Baza ligjore: Ligji i Punës (Ligji Nr. 03/L-212) neni 15 (periudha e provës), neni 17 (kontrata me kohë të caktuar).

## 4. Orari i Punës dhe Pushimet
- Orari javor: [NUMRI_ORËVE] orë në javë (maksimumi 40 orë sipas ligjit).
- Pushimi ditor: [KOHËZGIATJA_E_PUSHIMIT_DITOR] (sipas nenit 49).
- Pushimi vjetor: minimumi [NUMRI_DITËVE] ditë pune (sipas nenit 50, minimumi 20 ditë).
- Baza ligjore: Ligji i Punës nenet 48-51 (koha e punës dhe pushimet).

## 5. Paga dhe Benefitet
| Përshkrimi | Shuma |
|------------|-------|
| Paga bruto mujore | [SHUMA_BRUTO] € |
| Paga neto (pas tatimit dhe kontributeve) | [SHUMA_NETO] € |
| Mënyra e pagesës | Transfertë bankare në llogarinë [NUMRI_LLOGARISË] jo më vonë se data [DATA_PAGESËS] e çdo muaji |
| Kontributet pensionale (Trusti) | Në përputhje me Ligjin Nr. 04/L-101 (sipas nenit 8) |
| Tatimi në të ardhura personale (TAP) | Në përputhje me Ligjin Nr. 06/L-016 |

## 6. Detyrimet dhe Përgjegjësitë
- Punëmarrësi do të respektojë rregulloret e brendshme të punës, sigurinë në punë, dhe do të kryejë detyrat me kujdes profesional.
- Punëdhënësi do të sigurojë kushte të sigurta pune dhe do të paguajë pagën në kohë.

## 7. Ndërprerja e Kontratës
- Afati i njoftimit për ndërprerje nga secila palë: [NUMRI_DITËVE] ditë (sipas Ligjit të Punës neni 73).
- Rastet e shkëputjes së menjëhershme: sipas nenit 74 (shkelje e rëndë e detyrimeve).
- Në rast të ndërprerjes nga punëdhënësi pa arsye, punëmarrësi ka të drejtë në kompensim sipas nenit 75.

## 8. Zgjidhja e Kontesteve
- Çdo mosmarrëveshje që rrjedh nga kjo kontratë do të zgjidhet në Gjykatën Themelore kompetente, në pajtim me Ligjin për Procedurën Kontestimore.
- Para se të fillojë procedura gjyqësore, palët mund të provojnë ndërmjetësimin vullnetar.

## 9. Nënshkrimet
- Punëdhënësi: [EMRI_MBIEMRI_PUNËDHËNËSIT], [POZITA], nënshkrimi, data [DATA].
- Punëmarrësi: [EMRI_MBIEMRI_PUNËMARRËSIT], nënshkrimi, data [DATA].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "KONTRATË PUNE" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_KOMPANISË_OSE_PRONARIT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë kontratë, baza ligjore është Ligji i Punës (Ligji Nr. 03/L-212) dhe ligjet e tjera të zbatueshme (Trusti, TAP). Mos përfshi ligje që nuk lidhen me marrëdhëniet e punës (p.sh., Ligji për Shoqëritë Tregtare ose LCP).
  `,
  placeholder: "Shembull: Blerta Rexhepi do të punësohet si Asistente Administrative në 'Prishtina-Consulting Sh.P.K.'. Paga bruto 500 EUR, kontratë me kohë të pacaktuar, me 3 muaj periudhë prove. Fillon me 1 prill.",
  label: "Kontratë Pune",
};