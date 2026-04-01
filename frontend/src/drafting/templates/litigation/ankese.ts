// FILE: src/drafting/templates/litigation/ankese.ts
// ARCHITECTURE: KOSOVO APPELLATE LITIGATION ENGINE (LCP COMPLIANCE) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const ankeseTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Ankesë kundër aktgjykimit/vendimit të shkallës së parë.
GJUHA: Shqip (Formale, procedurale, juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA E APELIT NË PRISHTINË

## 1. Palët në Procedurë (PALËT)
- Paditësi: [EMRI_I_PADITËSIT], me adresë: [ADRESA_E_PADITËSIT].
- I Padituri: [EMRI_I_PADITURIT], me adresë: [ADRESA_E_TË_PADITURIT].

## 2. VENDIMI I ANKUAR
| Përshkrimi | Detajet |
| :--- | :--- |
| Gjykata e Shkallës së Parë | [EMRI_I_GJYKATËS] |
| Numri i Lëndës | [NR_I_LËNDËS] |
| Data e Vendimit | [DATA_E_VENDIMIT] |

## 3. BAZA E ANKESËS (LCP – Neni 187)
**RREGULL I DETYRUESHËM:** Baza e ankesës duhet të përcaktohet qartë duke zgjedhur një ose më shumë nga arsyet e përcaktuara në nenin 187 të Ligjit për Procedurën Kontestimore (LCP). Nuk lejohet përdorimi i shprehjeve të përgjithshme si "Neni përkatës i Ligjit..." pa specifikuar bazën.

Baza e ankesës (zgjidh atë që vlen):
- Shkelje thelbësore e dispozitave të procedurës kontestimore (LCP neni 187 par. 1).
- Vërtetim i gabuar apo jo i plotë i gjendjes faktike (LCP neni 187 par. 2).
- Zbatim i gabuar i së drejtës materiale (LCP neni 187 par. 3).

## 4. ARSYETIMI
- Paraqit kronologjikisht faktet dhe kundërshto argumentet e gjykatës së shkallës së parë. Analizo se ku ka gabuar gjykata në vlerësimin e provave ose në zbatimin e ligjit.
- Për çdo bazë të ankesës, lidh faktet me dispozitën përkatëse të LCP.

## 5. KËRKESË-PËRFUNDIMI (PETITUMI)
- "I propozojmë Gjykatës së Apelit që ankesën ta aprovojë si të bazuar, ta ndryshojë aktgjykimin e shkallës së parë ose ta kthejë lëndën në rigjykim."

## 6. NËNSHKRIMI
- Përfaqësuesi i autorizuar: [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM SHTESË:
- Dokumenti fillon direkt me "GJYKATA E APELIT NË PRISHTINË" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_GJYKATËS]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë ankesë, baza ligjore është **vetëm** Ligji për Procedurën Kontestimore (LCP). Mos cito Kodi Civil ose ligje të tjera materiale përveç nëse arsyetimi kërkon shqyrtim të së drejtës materiale.
- Shmang çdo përmbajtje që nuk lidhet me procedurën kontestimore të Kosovës.
  `,
  placeholder: "Shembull: Gjykata Themelore në Prishtinë ka marrë vendim për borxhin. Klienti im pretendon se prova e shkresës së borxhit është e falsifikuar dhe se gjyqtari ka injoruar dëshminë e ekspertit grafolog. Kërkojmë anulimin e vendimit.",
  label: "Ankesë",
};