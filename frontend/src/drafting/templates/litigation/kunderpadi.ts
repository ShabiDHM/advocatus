// FILE: src/drafting/templates/litigation/kunderpadi.ts
// ARCHITECTURE: KOSOVO PROCEDURAL LITIGATION (LCP – NENI 160) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const kunderpadiTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Parashtresë për Kundërpadi (Counterclaim) sipas Ligjit për Procedurën Kontestimore (LCP).
GJUHA: Shqip (Formale, procedurale, juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI I PËRGJITHSHËM / EKONOMIK

## 1. PALËT
- Paditësi (në padinë kryesore) / I Padituri (në kundërpadi): [EMRI_I_PALËS_A], me adresë [ADRESA_A], nr. personal [NR_PERSONAL_A].
- I Padituri (në padinë kryesore) / Kundërpaditësi: [EMRI_I_PALËS_B], me adresë [ADRESA_B], nr. personal [NR_PERSONAL_B].

## 2. OBJEKTI I KUNDËRPADISË
- Përshkrimi i shkurtër i kërkesës (psh. dëmshpërblim, konfirmim pronësie, kompensim).

## 3. LIDHSHMËRIA (KLAUZOLË E DETYRUESHME)
- Shpjego lidhjen juridike ndërmjet padisë kryesore dhe kundërpadisë sipas nenit 160 të LCP-së, duke treguar pse këto duhet të gjykohen së bashku.

## 4. BAZA LIGJORE
**RREGULL I DETYRUESHËM:** Në këtë seksion duhet të citohen nene specifike të ligjeve materiale të Republikës së Kosovës që rregullojnë kërkesën e kundërpadisë. Nuk lejohet përdorimi i shprehjeve të përgjithshme si "Neni përkatës i Ligjit...".

Përcakto llojin e çështjes nga fakti i padisë kryesore dhe i kundërpadisë, dhe përdor këto referenca:

- **Çështjet familjare (ndarje pasurie, alimentacion, divorc):**
  - Ligji për Familjen (Ligji Nr. 2004/32) i ndryshuar, neni [cakto nenin për çështjen përkatëse].
  - Për procedurën: Ligji për Procedurën Kontestimore (LCP) neni 160 (kundërpadi).

- **Çështjet kontraktuale (borxh, dëmshpërblim):**
  - Ligji për Detyrimet (Ligji Nr. 2004/31), nenet përkatëse (psh. neni 128 për dëmshpërblimin, neni 93 për borxhin).
  - Për procedurën: LCP neni 160.

- **Çështjet pronësore (konfirmim pronësie, servitute):**
  - Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (Ligji Nr. 2004/33), nenet përkatëse.
  - Për procedurën: LCP neni 160.

- **Çështjet tjera:** Cakto ligjin material specifik që lidhet me faktet.

**Baza procedurale:** Gjithmonë përmend Ligjin për Procedurën Kontestimore (LCP) neni 160 si bazë për paraqitjen e kundërpadisë.

## 5. ARSYETIMI I KUNDËRPADISË
- Paraqitja e fakteve: Pse kërkesa e palës kundërshtare është e pabazuar dhe pse kërkesa juaj është e bazuar.
- Analizo provat që do të paraqiten, duke i lidhur me nenet e cituara në BAZËN LIGJORE.

## 6. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesa 1: Të refuzohet padia kryesore e Paditësit si e pabazuar.
- Kërkesa 2: Të aprovohet kundërpadia jonë si e bazuar dhe të obligohet Pala kundërshtare të [PËRSHKRIMI_I_VEPRIMIT].
- Kërkesa 3: Shpenzimet e procedurës të paguhen nga pala humbëse.

## 7. NËNSHKRIMI
- I Padituri / Kundërpaditësi (përfaqësuar nga avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM SHTESË:
- Dokumenti fillon direkt me "GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_GJYKATËS]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Shmang çdo përmbajtje që nuk lidhet me procedurën kontestimore të Kosovës.
  `,
  placeholder: "Shembull: Paditësi më ka paditur për 'dëmtim të pronës'. Në realitet, ai ka uzurpuar 2 metra të tokës sime. Unë po parashtroj kundërpadi për ta detyruar atë të kthejë tokën në gjendjen e mëparshme dhe për të paguar dëmin e shkaktuar nga ndërtimi i paligjshëm.",
  label: "Kundërpadi",
};