// FILE: src/drafting/templates/litigation/ankese.ts
// ARCHITECTURE: KOSOVO APPELLATE LITIGATION ENGINE (LCP COMPLIANCE)

import { TemplateConfig } from '../../types';

export const ankeseTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Ankesë kundër aktgjykimit/vendimit të shkallës së parë.
GJUHA: Shqip (Formale, procedurale, juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA E APELIT NË PRISHTINË

## 1. Palët në Procedurë (PALËT)
- Paditësi: [EMRI_I_PADITËSIT], me adresë: [ADRESA].
- I Padituri: [EMRI_I_PADITURIT], me adresë: [ADRESA].

## 2. VENDIMI I ANKUAR
- Përdor tabelë për të listuar:
  | Përshkrimi | Detajet |
  | :--- | :--- |
  | Gjykata e Shkallës së Parë | [EMRI_I_GJYKATËS] |
  | Numri i Lëndës | [NR_I_LËNDËS] |
  | Data e Vendimit | [DATA_E_VENDIMIT] |

## 3. BAZA E ANKESËS (LCP - Neni 187)
- Përcakto qartë bazën (zgjidh një ose më shumë):
  - Shkelje thelbësore e dispozitave të procedurës kontestimore.
  - Vërtetim i gabuar apo jo i plotë i gjendjes faktike.
  - Zbatim i gabuar i së drejtës materiale.

## 4. ARSYETIMI
- Paraqitja kronologjike e fakteve dhe kundërshtimi i argumenteve të gjykatës së shkallës së parë. Analizo ku ka gabuar gjyqtari në vlerësimin e provave.

## 5. KËRKESË-PËRFUNDIMI (PETITUMI)
- Kërkesë specifike: "I propozojmë Gjykatës së Apelit që ankesën ta aprovojë si të bazuar, ta ndryshojë aktgjykimin e shkallës së parë ose ta kthejë lëndën në rigjykim."

## 6. NËNSHKRIMI
- Përfaqësuesi i autorizuar: [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM: Përdor terminologji strikte të 'Ligjit për Procedurën Kontestimore'. Mos përdor gjuhë emocionale.
  `,
  placeholder: "Shembull: Gjykata Themelore në Prishtinë ka marrë vendim për borxhin. Klienti im pretendon se prova e shkresës së borxhit është e falsifikuar dhe se gjyqtari ka injoruar dëshminë e ekspertit grafolog. Kërkojmë anulimin e vendimit.",
  label: "Ankesë",
};