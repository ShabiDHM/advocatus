// FILE: src/drafting/templates/litigation/pergjigje.ts
// ARCHITECTURE: KOSOVO DEFENSE LITIGATION (LCP – NENI 154) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const pergjigjeTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Përgjigje në Padi (Response to Lawsuit) sipas Ligjit për Procedurën Kontestimore (LCP).
GJUHA: Shqip (Formale, Mbrojtëse, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI I PËRGJITHSHËM / EKONOMIK

## 1. PALËT
- Paditësi: [EMRI_I_PADITËSIT], me adresë [ADRESA_E_PADITËSIT], nr. personal [NR_PERSONAL_PADITËSIT].
- I Padituri: [EMRI_I_PALËS_SË_PËRFAQËSUAR], me adresë [ADRESA_E_TË_PADITURIT], nr. personal [NR_PERSONAL_TË_PADITURIT].

## 2. OBJEKTI
- Përgjigje në padi kundër padisë së Paditësit me numër të lëndës [NR_I_LËNDËS].

## 3. PËRGJIGJA NË FAKTE
- Paraqit kundërshtimin ndaj pretendimeve të Paditësit. Për çdo fakt të deklaruar nga Paditësi, jep përgjigje: pranohet, kundërshtohet, ose nuk ka njohuri.
- Nëse i Padituri kundërshton, shpjego arsyet faktike.

## 4. BAZA LIGJORE
**RREGULL I DETYRUESHËM:** Baza ligjore duhet të përbëhet nga nene specifike të ligjeve materiale të Republikës së Kosovës që rregullojnë çështjen në fjalë. Nuk lejohet përdorimi i shprehjeve të përgjithshme si "Neni përkatës i Ligjit...".

Përcakto llojin e çështjes nga fakti i padisë dhe përdor këto referenca:

- **Çështjet familjare (ndarje pasurie, alimentacion, divorc):**
  - Ligji për Familjen (Ligji Nr. 2004/32) i ndryshuar, neni [cakto nenin për çështjen përkatëse].
  - Për procedurën: Ligji për Procedurën Kontestimore (LCP) neni 154 (përgjigjja në padi) dhe nenet e tjera të zbatueshme.

- **Çështjet kontraktuale (borxh, dëmshpërblim):**
  - Ligji për Detyrimet (Ligji Nr. 2004/31), nenet përkatëse (psh. neni 128 për dëmshpërblimin, neni 93 për borxhin).
  - Për procedurën: LCP neni 154.

- **Çështjet pronësore (konfirmim pronësie, servitute):**
  - Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (Ligji Nr. 2004/33), nenet përkatëse.
  - Për procedurën: LCP neni 154.

- **Çështjet tjera:** Cakto ligjin material specifik që lidhet me faktet.

**Baza procedurale:** Gjithmonë përmend Ligjin për Procedurën Kontestimore (LCP) neni 154 si bazë për paraqitjen e përgjigjes.

## 5. ARSYETIMI LIGJOR
- Analizo pse padia e Paditësit është e pabazuar duke iu referuar neneve të cituara në BAZËN LIGJORE.
- Përmend provat që demantojnë pretendimet e Paditësit.

## 6. PROVAT MBROJTËSE
- Listo provat që i Padituri do të paraqesë (p.sh., dokumente, dëshmi, ekspertiza). Nëse nuk ka prova të specifikuara, shkruaj: "I propozoj gjykatës të marrë si provë: [dokumentet që do të paraqiten]".

## 7. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesa 1: Padia e Paditësit të refuzohet në tërësi si e pabazuar.
- Kërkesa 2: Të obligohet Paditësi t'i kompensojë të gjitha shpenzimet e procedurës (taksat gjyqësore dhe shpenzimet e avokatit).

## 8. NËNSHKRIMI
- I Padituri / Përfaqësuesi i autorizuar (Avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM SHTESË:
- Dokumenti fillon direkt me "GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_GJYKATËS]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Shmang çdo përmbajtje që nuk lidhet me procedurën kontestimore të Kosovës.
  `,
  placeholder: "Shembull: Agim Krasniqi është paditur për cënim të pronës. Ne do të argumentojmë se gardhi është ndërtuar brenda vijave kufitare të ligjshme të konfirmuara me matje gjeodezike të vjetra, dhe se paditësi nuk ka ofruar asnjë provë të vlefshme që dëshmon ndërhyrjen.",
  label: "Përgjigje në Padi",
};