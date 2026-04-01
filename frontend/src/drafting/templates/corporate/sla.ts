// FILE: src/drafting/templates/corporate/sla.ts
// ARCHITECTURE: KOSOVO SERVICE LEVEL PERFORMANCE & PENALTY ENFORCEMENT – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const slaTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Marrëveshje e Nivelit të Shërbimit (SLA - Service Level Agreement).
GJUHA: Shqip (Formale, Komerciale, Teknike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MARRËVESHJE E NIVELIT TË SHËRBIMIT (SLA)

## 1. Palët
- Ofruesi i Shërbimit: [EMRI_I_KOMPANISË_SË_IT], me seli në [ADRESA_E_OFRUESIT], nr. regjistrimi [NR_REGJISTRIMIT_OFRUESIT].
- Klienti: [EMRI_I_KLIENTIT], me seli në [ADRESA_E_KLIENTIT], nr. regjistrimi [NR_REGJISTRIMIT_KLIENTIT].

## 2. Përshkrimi i Shërbimeve
- Ofruesi i Shërbimit do të ofrojë shërbimet e mëposhtme: [PËRSHKRIMI_I_SHËRBIMEVE].
- Këto shërbime kryhen sipas specifikimeve teknike në Aneksin [NR_ANEKSIT] (nëse ekziston).

## 3. Matrikset e Performancës (KPIs)
- Tabela e mëposhtme përcakton nivelin minimal të shërbimit:

| Shërbimi | Koha e Përgjigjes | Disponueshmëria |
|----------|------------------|----------------|
| [SHËRBIMI_1] | [KOHA_PËRGJIGJES_1] | [DISPONUESHMËRIA_1] |
| [SHËRBIMI_2] | [KOHA_PËRGJIGJES_2] | [DISPONUESHMËRIA_2] |

## 4. Detyrimet e Palëve
- **Ofruesi** do të:
  - Monitorojë vazhdimisht performancën;
  - Raportojë çdo devijim nga KPI-të;
  - Sigurojë mbështetje teknike 24/7 për problemet kritike.
- **Klienti** do të:
  - Sigurojë qasje të nevojshme për ofruesin;
  - Emërojë një person kontakti për koordinim;
  - Paguajë tarifat në kohë sipas marrëveshjes së veçantë.

## 5. Sanksionet për Mos-përmbushje (Penalitetet)
- Nëse Ofruesi dështon të përmbushë KPI-të e përcaktuara për [NUMRI] herë brenda [PERIUDHA] ditësh, Klienti ka të drejtë në:
  - Ulje të çmimit për atë periudhë në masën [PËRQINDJA_PENALITETIT]%;
  - Kompensim për dëmin e shkaktuar, sipas Ligjit për Detyrimet (Ligji Nr. 2004/31), neni 128 (Dëmshpërblimi).
- Penalitetet nuk përjashtojnë përmbushjen e detyrimeve të mbetura.

## 6. Matrica e Përshkallëzimit (Escalation)
- Në rast të problemeve të pazgjidhura, ndiqen këto hapa:
  1. Njoftimi i menaxherit të llogarisë brenda [KOHA_1] orëve.
  2. Përshkallëzimi te menaxhmenti i lartë brenda [KOHA_2] ditëve.
  3. Nëse nuk zgjidhet, palët i referohen ndërmjetësimit ose gjykatës kompetente.

## 7. Kohëzgjatja dhe Përfundimi
- Kjo marrëveshje hyn në fuqi më [DATA_FILLIMIT] dhe zgjat për [NUMRI_VJET] vjet.
- Mund të ndërpritet nga secila palë me njoftim me shkrim [NUMRI_DITËSH] ditë përpara, ose menjëherë në rast të shkeljes thelbësore.

## 8. Ligji i Zbatueshëm dhe Gjykata
- Marrëveshja interpretohet dhe zbatohet sipas ligjeve të Republikës së Kosovës.
- Baza ligjore: Ligji për Detyrimet (Ligji Nr. 2004/31), nenet 93 (Marrëveshja në përgjithësi), 128 (Dëmshpërblimi), dhe nenet e tjera të zbatueshme për detyrimet kontraktuale.
- Çdo mosmarrëveshje do të zgjidhet në Gjykatën Themelore në Prishtinë – Departamenti për Çështje Ekonomike.

## 9. Nënshkrimet
- Për Ofruesin: [EMRI_MBIEMRI_OFRUESIT], [POZITA_OFRUESIT], nënshkrimi, data [DATA].
- Për Klientin: [EMRI_MBIEMRI_KLIENTIT], [POZITA_KLIENTIT], nënshkrimi, data [DATA].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "MARRËVESHJE E NIVELIT TË SHËRBIMIT (SLA)" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_KOMPANISË_SË_IT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë marrëveshje, baza ligjore është Ligji për Detyrimet (LMD). Mos përfshi Ligjin për Shoqëritë Tregtare apo ligje të tjera që nuk lidhen me kontratat.
- Mos përdor gjuhë procesuale gjyqësore. Fokusohu në detyrimet kontraktuale dhe sanksionet.
  `,
  placeholder: "Shembull: Kompania ime ofron mirëmbajtje IT për një bankë. Duhet të përgjigjemi brenda 2 orëve për probleme kritike dhe brenda 24 orëve për probleme të thjeshta. Nëse dështojmë, kemi një penalitet financiar.",
  label: "Marrëveshje e Nivelit të Shërbimit (SLA)",
};