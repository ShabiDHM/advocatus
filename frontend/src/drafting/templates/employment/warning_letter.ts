// FILE: src/drafting/templates/employment/warning_letter.ts
// ARCHITECTURE: KOSOVO LABOR LAW COMPLIANCE - DISCIPLINARY RECORD

import { TemplateConfig } from '../../types';

export const warningLetterTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Vërejtje me Shkrim (Warning Letter).
GJUHA: Shqip (Formale, Disiplinore).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# VËREJTJE ME SHKRIM (MASË DISIPLINORE)

## 1. Të Dhënat e Punëmarrësit
- Emri, Mbiemri dhe Pozita e Punës.

## 2. Përshkrimi i Shkeljes
- Detajimi faktik i shkeljes (psh. vonesat, mosrespektimi i detyrave, sjellja jo-profesionale).
- Referenca në Rregulloren e Brendshme të Punës ose 'Ligjin e Punës (Nr. 03/L-212)'.

## 3. Përmirësimi i Kërkuar
- Çfarë pritet nga punonjësi për të korrigjuar sjelljen dhe afati kohor për përmirësim.

## 4. Diskutimet e Mëparshme
- Përmendja e vërejtjeve verbale ose takimeve të mëparshme ku është diskutuar kjo çështje.

## 5. Pasojat e Vazhdimit të Shkeljes
- KLAUZOLË E DETYRUESHME: "Nëse sjellja/performanca nuk përmirësohet brenda afatit të caktuar, Punëdhënësi rezervon të drejtën e ndërprerjes së marrëdhënies së punës sipas nenit përkatës të Ligjit të Punës."

## 6. E Drejta për Përgjigje
- Punonjësi ka të drejtë të japë deklaratën e tij/saj në lidhje me këtë vërejtje brenda një afati të arsyeshëm (psh. 3 ditë).

## 7. Nënshkrimet
- Nënshkrimi i Punëdhënësit dhe hapësira për nënshkrimin e Punonjësit (si dëshmi e pranimit të vërejtjes).
  `,
  placeholder: "Shembull: Artan Hoxha vjen me vonesë 30 minuta çdo mëngjes prej 2 javësh, pavarësisht vërejtjeve verbale të menaxherit më 10 dhe 15 mars. Kjo është shkelje e rregullores së brendshme të punës.",
  label: "Vërejtje me Shkrim",
};