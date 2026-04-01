// FILE: src/drafting/templates/litigation/padi.ts
// ARCHITECTURE: KOSOVO COURT FILING (LCP) – DETERMINISTIC LEGAL BASIS

import { TemplateConfig } from '../../types';

export const padiTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Padi (Lawsuit) sipas Ligjit për Procedurën Kontestimore (LCP).
GJUHA: Shqip (Formale, procedurale, juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI I PËRGJITHSHËM / EKONOMIK

## 1. PALËT
- Paditësi: [EMRI_MBIEMRI], me adresë [ADRESA], nr. personal [NR_PERSONAL].
- I Padituri: [EMRI_I_PALËS_TJETER], me adresë [ADRESA].

## 2. OBJEKTI I PADISË
- Përshkrimi i shkurtër i kërkesëpadisë (psh. Ndarja e pasurisë së përbashkët, pagesa e alimentacionit, konfirmim pronësie, borxh, dëmshpërblim).

## 3. BAZA LIGJORE
**RREGULL I DETYRUESHËM:** Në këtë seksion duhet të citohen nene specifike të ligjeve materiale të Republikës së Kosovës që rregullojnë çështjen. Nuk lejohet përdorimi i shprehjeve të përgjithshme si "Neni përkatës i Ligjit..." ose "Ligji për Procedurën Kontestimore (LCP)" pa nenin konkret.

Përcakto llojin e çështjes nga faktet e dhëna dhe përdor këto referenca bazë:

- **Çështjet familjare (ndarje pasurie, alimentacion, divorc):**
  - Ligji për Familjen (Ligji Nr. 2004/32) i ndryshuar, neni [cakto nenin për pasurinë e përbashkët] dhe neni [cakto nenin për alimentacionin].
  - Për procedurën: Ligji për Procedurën Kontestimore (Ligji Nr. 03/L-006) neni 83 e në vijim.

- **Çështjet kontraktuale (borxh, dëmshpërblim):**
  - Ligji për Detyrimet (Ligji Nr. 2004/31), nenet përkatëse (psh. neni 128 për dëmshpërblimin, neni 93 për borxhin).

- **Çështjet pronësore (konfirmim pronësie, shpronësim, servitute):**
  - Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (Ligji Nr. 2004/33), nenet përkatëse.

- **Çështjet tjera:** Cakto ligjin material specifik që lidhet me faktet.

**Baza procedurale:** Gjithmonë përmend Ligjin për Procedurën Kontestimore (LCP) me nenin që parasheh llojin e padisë (zakonisht neni 83).

## 4. ARSYETIMI I PADISË
- Paraqitja faktike: Përshkruaj kronologjikisht ngjarjen dhe dëmin e shkaktuar, duke u bazuar vetëm në faktet e dhëna nga klienti.
- Argumentimi ligjor: Lidh faktet me obligimet ligjore të të Paditurit, duke iu referuar neneve të cituara në BAZËN LIGJORE.

## 5. PROVAT
- Listo të gjitha provat që përmenden në faktet e klientit. Nëse nuk ka prova të specifikuara, shkruaj: "I propozoj gjykatës të marrë si provë: [dokumentet që do të paraqiten]". Mos përdor vija të zbrazëta.

## 6. PETITUMI (Kërkesë-Padia)
- Kërkesa 1: Të konfirmohet se [PËRSHKRIMI_I_TË_DREJTËS].
- Kërkesa 2: Të obligohet i Padituri që [VEPRIMI_I_KËRKUAR_OSE_SHUMA].
- Kërkesa 3: Të obligohet i Padituri që t'i kompensojë shpenzimet e procedurës (taksat gjyqësore dhe shpenzimet e avokatit).

## 7. NËNSHKRIMI
- Paditësi / Përfaqësuesi i autorizuar (Avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM SHTESË: Dokumenti duhet të fillojë direkt me kokën "GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]" pa ndonjë parathënie. Shmang çdo përmbajtje që nuk lidhet me procedurën kontestimore të Kosovës (p.sh., kontrata korporative, marrëveshje ndërkombëtare që nuk aplikohen).
  `,
  placeholder: "Shembull: Agim Krasniqi kërkon që fqinji i tij të largojë gardhin e ndërtuar 50cm në pronën e tij. Fqinji refuzon, pavarësisht matjeve gjeodezike. Agimi ka në dorë planin gjeodezik si provë kryesore.",
  label: "Padi",
};