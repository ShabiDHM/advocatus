// FILE: src/drafting/templates/litigation/pergjigje.ts
// ARCHITECTURE: KOSOVO DEFENSE LITIGATION (LCP - NENI 154)

import { TemplateConfig } from '../../types';

export const pergjigjeTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Përgjigje në Padi (Response to Lawsuit) sipas Ligjit për Procedurën Kontestimore (LCP).
GJUHA: Shqip (Formale, Mbrojtëse, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI I PËRGJITHSHËM / EKONOMIK

## 1. PALËT
- Paditësi: [EMRI_I_PADITËSIT]
- I Padituri: [EMRI_I_PALËS_SË_PËRFAQËSUAR]

## 2. OBJEKTI
- Përgjigje në padi kundër padisë së Paditësit [NR_I_LËNDËS].

## 3. PËRGJIGJA NË FAKTE
- Kundërshtimi i pikave të padisë: "I Padituri i kundërshton në tërësi pretendimet e Paditësit sepse...". 
- Adresimi i çdo akuaze kryesore të Paditësit me argumente faktike.

## 4. BAZA LIGJORE
- Cito dispozitat ligjore që mbrojnë të drejtën e të Paditurit (psh. LMD, Kodi Civil, ose Ligji për Pronësinë).
- Baza procedurale: 'Ligji për Procedurën Kontestimore (LCP)'.

## 5. ARSYETIMI LIGJOR
- Analiza ligjore: Përse padia e Paditësit është e pabazuar. (Përmend provat që demantojnë padinë).

## 6. PROVAT MBROJTËSE
- Listo provat e të Paditurit (psh. dëshmitë, shkresat, ekspertizat). "I propozoj gjykatës të marrë si provë: [LISTA_E_PROVAVE]".

## 7. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesa 1: Padia e Paditësit të refuzohet në tërësi si e pabazuar.
- Kërkesa 2: Të obligohet Paditësi t'i kompensojë të gjitha shpenzimet e procedurës (taksat dhe shpenzimet e avokatit).

## 8. NËNSHKRIMI
- I Padituri / Përfaqësuesi i autorizuar (Avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM: Dokumenti duhet të jetë mbrojtës dhe bindës. Përdor terminologji procedurale si "të pabazuar", "të paprovuar", dhe "e pabazuar në ligj".
  `,
  placeholder: "Shembull: Agim Krasniqi është paditur për cënim të pronës. Ne do të argumentojmë se gardhi është ndërtuar brenda vijave kufitare të ligjshme të konfirmuara me matje gjeodezike të vjetra, dhe se paditësi nuk ka ofruar asnjë provë të vlefshme që dëshmon ndërhyrjen.",
  label: "Përgjigje në Padi",
};