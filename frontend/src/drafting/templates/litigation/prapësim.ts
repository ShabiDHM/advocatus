// FILE: src/drafting/templates/litigation/prapesim.ts
// ARCHITECTURE: KOSOVO LITIGATION – PROCEDURAL OBJECTION & EXECUTION DEFENSE – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const prapesimTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Prapësim (Objection/Opposition) kundër Urdhëresës/Vendimit ose Provës, sipas Ligjit për Procedurën Kontestimore (LCP) ose Ligjit për Procedurën Përmbarimore (LPP).
GJUHA: Shqip (Formale, Procedurale).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI PËR ÇËSHTJE EKONOMIKE / TË PËRGJITHSHME

## 1. PALËT
- Pala kundërshtuese (Debitori): [EMRI_MBIEMRI], me adresë [ADRESA], nr. personal [NR_PERSONAL].
- Pala përballë (Kreditori): [EMRI_MBIEMRI], me adresë [ADRESA], nr. personal [NR_PERSONAL].

## 2. OBJEKTI
- Prapësim kundër [PËRSHKRIMI_I_VEPRIMIT_PROCEDURAL] (psh. Urdhrit Përmbarimor, Vendimit për caktimin e masës, ose Provës së paraqitur).

## 3. AFATI LIGJOR
- "Prapësimi është parashtruar brenda afatit ligjor prej [NR_DITËSH] ditësh nga dita e pranimit të vendimit/urdhëresës."

## 4. BAZA LIGJORE
**RREGULL I DETYRUESHËM:** Cito nene specifike të Ligjit për Procedurën Kontestimore (LCP) ose Ligjit për Procedurën Përmbarimore (LPP). Nuk lejohet përdorimi i shprehjeve të përgjithshme si "Neni përkatës i Ligjit...".

Përcakto llojin e prapësimit dhe përdor këto referenca:

- **Prapësim kundër provës (LCP):**
  - LCP neni 169 (kundërshtimi i provave) dhe neni 174 (kundërshtimi i ekspertizës), në varësi të rrethanave.

- **Prapësim kundër urdhrit përmbarimor (LPP):**
  - Ligji për Procedurën Përmbarimore (Ligji Nr. 08/L-024), neni 48 (prapësimi kundër urdhrit përmbarimor) dhe nenet e tjera përkatëse.

- **Prapësim kundër vendimit tjetër procedural (LCP):**
  - LCP neni 147 (prapësimi kundër vendimit gjyqësor) ose neni 148 (prapësimi kundër vendimit të gjyqtarit të procedurës paraprake).

**Baza materiale:** Nëse prapësimi lidhet me thelbin e detyrimit (p.sh., parashkrimi, shlyerja), cito edhe dispozitat përkatëse të Ligjit për Detyrimet (Ligji Nr. 2004/31).

## 5. ARSYETIMI (Shkaqet e Prapësimit)
- Detajimi i shkeljeve:
  - Nëse është kundër provës: "Provë e marrë në mënyrë të paligjshme / e parëndësishme."
  - Nëse është kundër urdhrit përmbarimor: "Borxhi është shlyer / Obligimi nuk ekziston / Parashkrimi i borxhit."
  - Nëse është kundër vendimit tjetër: specifiko shkeljen procedurale.

## 6. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesë: "I propozojmë Gjykatës që prapësimin ta aprovojë si të bazuar dhe ta anulojë [VEPRIMIN_PROCEDURAL_OSE_URDHËRESËN]."

## 7. NËNSHKRIMI
- I Padituri / Debitori (përfaqësuar nga avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM SHTESË:
- Dokumenti fillon direkt me "GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_GJYKATËS]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Shmang çdo përmbajtje që nuk lidhet me procedurën kontestimore ose përmbarimore të Kosovës.
  `,
  placeholder: "Shembull: Kundërshtoj Urdhrin Përmbarimor të datës 10.03.2024. Borxhi për të cilin jam paditur është shlyer plotësisht më 05.02.2024, siç dëshmohet me vërtetimin e pagesës në aneksin e kësaj shkrese.",
  label: "Prapësim",
};