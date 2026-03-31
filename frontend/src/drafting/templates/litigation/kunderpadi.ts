// FILE: src/drafting/templates/litigation/kunderpadi.ts
// ARCHITECTURE: KOSOVO PROCEDURAL LITIGATION (LCP - NENI 160)

import { TemplateConfig } from '../../types';

export const kunderpadiTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Parashtresë për Kundërpadi (Counterclaim).
GJUHA: Shqip (Formale, procedurale, juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI I PËRGJITHSHËM / EKONOMIK

## 1. PALËT
- Paditësi (në padinë kryesore) / I Padituri (në kundërpadi): [EMRI_I_PALËS_A]
- I Padituri (në padinë kryesore) / Kundërpaditësi: [EMRI_I_PALËS_B]

## 2. OBJEKTI I KUNDËRPADISË
- Përshkrimi i shkurtër i kërkesës (psh. dëmshpërblim, konfirmim pronësie, kompensim).

## 3. LIDHSHMËRIA (KLAUZOLË E DETYRUESHME)
- Shpjego lidhjen juridike ndërmjet padisë kryesore dhe kundërpadisë (sipas nenit 160 të LCP-së), përse këto duhet të gjykohen së bashku.

## 4. BAZA LIGJORE
- Cito dispozitat materiale të 'Ligjit për Marrëdhëniet e Detyrimeve' ose ligjit tjetër përkatës që mbështesin kërkesën tuaj.

## 5. ARSYETIMI I KUNDËRPADISË
- Paraqitja e fakteve: Përse kërkesa e palës kundërshtare është e pabazuar dhe përse kërkesa juaj është e bazuar. 
- Analizo provat që do t'i paraqisni.

## 6. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesa 1: Të refuzohet padia kryesore e Paditësit si e pabazuar.
- Kërkesa 2: Të aprovohet kundërpadia jonë si e bazuar dhe të obligohet Pala kundërshtare të [PËRSHKRIMI_I_VEPRIMIT].
- Kërkesa 3: Shpenzimet e procedurës të paguhen nga pala humbëse.

## 7. NËNSHKRIMI
- I Padituri / Kundërpaditësi (përfaqësuar nga avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM: Kundërpadia duhet të jetë në përputhje me dispozitat e 'Ligjit për Procedurën Kontestimore' (LCP). Shkruaj në gjuhë të pastër juridike.
  `,
  placeholder: "Shembull: Paditësi më ka paditur për 'dëmtim të pronës'. Në realitet, ai ka uzurpuar 2 metra të tokës sime. Unë po parashtroj kundërpadi për ta detyruar atë të kthejë tokën në gjendjen e mëparshme dhe për të paguar dëmin e shkaktuar nga ndërtimi i paligjshëm.",
  label: "Kundërpadi",
};