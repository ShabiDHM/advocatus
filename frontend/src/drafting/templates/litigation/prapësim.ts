// FILE: src/drafting/templates/litigation/prapesim.ts
// ARCHITECTURE: KOSOVO LITIGATION - PROCEDURAL OBJECTION & EXECUTION DEFENSE

import { TemplateConfig } from '../../types';

export const prapesimTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Prapësim (Objection/Opposition) kundër Urdhëresës/Vendimit ose Provës.
GJUHA: Shqip (Formale, Procedurale).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI PËR ÇËSHTJE EKONOMIKE / TË PËRGJITHSHME

## 1. PALËT
- Pala kundërshtuese (Debitori): [EMRI_MBIEMRI]
- Pala përballë (Kreditori): [EMRI_MBIEMRI]

## 2. OBJEKTI
- Prapësim kundër [PËRSHKRIMI_I_VEPRIMIT_PROCEDURAL] (psh. Urdhrit Përmbarimor, Vendimit për caktimin e masës, apo Provës së paraqitur).

## 3. AFATI LIGJOR
- "Prapësimi është parashtruar brenda afatit ligjor prej [NR_DITËSH] ditësh nga dita e pranimit të vendimit/urdhëresës."

## 4. BAZA LIGJORE
- Cito dispozitat përkatëse të 'Ligjit për Procedurën Kontestimore (LCP)' ose 'Ligjit për Procedurën Përmbarimore (LPP)'.
- Argumento përse veprimi i palës tjetër ose i gjykatës është në kundërshtim me këto dispozita.

## 5. ARSYETIMI (Shkaqet e Prapësimit)
- Detajimi i shkeljeve:
  - Nëse është kundër provës: "Provë e marrë në mënyrë të paligjshme / e parëndësishme."
  - Nëse është kundër urdhrit përmbarimor: "Borxhi është shlyer / Obligimi nuk ekziston / Parashkrimi i borxhit."

## 6. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesë: "I propozojmë Gjykatës që prapësimin ta aprovojë si të bazuar dhe ta anulojë [VEPRIMIN_PROCEDURAL_OSE_URDHËRESËN]."

## 7. NËNSHKRIMI
- I Padituri / Debitori (përfaqësuar nga avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM: Përdor ton të prerë dhe procedural. Ky dokument është për të ndalur një veprim të paligjshëm ose të pasaktë procedural.
  `,
  placeholder: "Shembull: Kundërshtoj Urdhrin Përmbarimor të datës 10.03.2024. Borxhi për të cilin jam paditur është shlyer plotësisht më 05.02.2024, siç dëshmohet me vërtetimin e pagesës në aneksin e kësaj shkrese.",
  label: "Prapësim",
};