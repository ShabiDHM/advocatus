// FILE: src/drafting/templates/employment/warning_letter.ts
// ARCHITECTURE: KOSOVO LABOR LAW COMPLIANCE – DISCIPLINARY RECORD – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const warningLetterTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Vërejtje me Shkrim (Warning Letter) sipas Ligjit të Punës të Republikës së Kosovës dhe Rregullores së Brendshme të Punës.
GJUHA: Shqip (Formale, Disiplinore).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# VËREJTJE ME SHKRIM (MASË DISIPLINORE)

## 1. Të Dhënat e Punëmarrësit
- Emri dhe mbiemri: [EMRI_MBIEMRI_PUNËMARRËSIT]
- Pozita: [POZITA_E_PUNËMARRËSIT]

## 2. Përshkrimi i Shkeljes
- Data(et) e shkeljes: [DATA_E_SHKELEJES]
- Përshkrimi faktik: [PËRSHKRIMI_I_SHKELEJES] (p.sh., vonesa të përsëritura, moskryerje e detyrave, sjellje joprofesionale).
- Baza në rregulloren e brendshme: [RREGULLORJA_E_BRENDSHME] – neni [NR_NENIT] (ose nëse nuk ekziston, referenca në Ligjin e Punës).

## 3. Përmirësimi i Kërkuar
- Veprimet që priten nga punëmarrësi: [VEPRIMET_E_KËRKUARA] (p.sh., ardhja në kohë, kryerja e detyrave sipas përshkrimit).
- Afati për përmirësim: [AFATI_PËR_PËRMIRËSIM] (p.sh., 7 ditë pune).

## 4. Diskutimet e Mëparshme
- Vërejtjet verbale ose takimet e mëparshme: [PËRSHKRIMI_I_DISKUTIMEVE_TË_MËPARSHEME] (p.sh., “Më 10 mars dhe 15 mars menaxheri ka dhënë vërejtje verbale për vonesat”).

## 5. Pasojat e Vazhdimit të Shkeljes
- **KLAUZOLË E DETYRUESHME:** "Nëse sjellja / performanca nuk përmirësohet brenda afatit të caktuar, Punëdhënësi rezervon të drejtën të fillojë procedurën e ndërprerjes së marrëdhënies së punës në pajtim me nenin 72 (shkelje e detyrimeve) të Ligjit të Punës (Nr. 03/L-212)."

## 6. E Drejta për Përgjigje
- Punëmarrësi ka të drejtë të japë deklaratën e tij/saj me shkrim në lidhje me këtë vërejtje brenda [AFATI_PËR_PËRGJIGJE] ditëve pune nga marrja e kësaj vërejtjeje.

## 7. Nënshkrimet
- Punëdhënësi / Përfaqësuesi i autorizuar: [EMRI_MBIEMRI_PUNËDHËNËSIT], [POZITA], nënshkrimi, data [DATA_LËSHIMIT].
- Punëmarrësi (vërtetim i pranimit): nënshkrimi, data [DATA_PRONIMIT].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "VËREJTJE ME SHKRIM (MASË DISIPLINORE)" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_MBIEMRI_PUNËMARRËSIT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë vërejtje, baza ligjore është Ligji i Punës (Ligji Nr. 03/L-212) dhe rregullorja e brendshme e punëdhënësit. Mos përfshi ligje që nuk lidhen me marrëdhëniet e punës.
- Vërejtja me shkrim është masë paraprake disiplinore dhe duhet të jetë objektive, e qartë dhe e provueshme për të shërbyer si provë në rast të ndërprerjes së mëvonshme.
  `,
  placeholder: "Shembull: Artan Hoxha vjen me vonesë 30 minuta çdo mëngjes prej 2 javësh, pavarësisht vërejtjeve verbale të menaxherit më 10 dhe 15 mars. Kjo është shkelje e rregullores së brendshme të punës.",
  label: "Vërejtje me Shkrim",
};