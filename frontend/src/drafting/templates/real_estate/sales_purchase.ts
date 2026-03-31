// FILE: src/drafting/templates/real_estate/sales_purchase.ts
// ARCHITECTURE: KOSOVO PROPERTY TRANSFER & CADASTRAL COMPLIANCE

import { TemplateConfig } from '../../types';

export const salesPurchaseTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kontratë Shitblerje (Sale & Purchase Agreement) për Patundshmëri.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# KONTRATË SHITBLERJE PËR PATUNDSHMËRI

## 1. Palët Kontraktuese
- Shitësi: [EMRI_MBIEMRI], nr. personal [NR_PERSONAL], me adresë [ADRESA].
- Blerësi: [EMRI_MBIEMRI], nr. personal [NR_PERSONAL], me adresë [ADRESA].

## 2. Përshkrimi i Patundshmërisë
- KLAUZOLË E DETYRUESHME: Identifikimi i plotë nga Fleta Poseduese:
  - Zona Kadastrale: [ZK_ZONA_KADASTRALE]
  - Nr. i Parcelës: [NR_PARCELËS]
  - Nr. i Fletës Poseduese: [NR_FLETA_POSEDUESE]
  - Sipërfaqja: [SIPËRFAQJA_M2]

## 3. Çmimi dhe Mënyra e Pagesës
- Çmimi total: [SHUMA_EURO].
- Mënyra e pagesës (transfer bankar/transaksion noterësor).
- Konfirmimi se Shitësi ka pranuar pagesën në tërësi (ose planin e pagesës).

## 4. Garantimi i Pronësisë (Eviksioni)
- Shitësi garanton se prona është e lirë nga barrët (hipoteka, shënime kadastrale, ose të drejta të palëve të treta).

## 5. Transferi i Pronësisë dhe Dorëzimi
- Dorëzimi i pronës në posedim të Blerësit. 
- Obligimi për bartjen e pronësisë në librat kadastralë pas notarizimit.

## 6. Baza Ligjore (Detyruese)
- Cito: "Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat Tjera Sendore" dhe "Ligji për Marrëdhëniet e Detyrimeve (LMD)".

## 7. Noterizimi dhe Taksat
- Kontrata duhet të noterizohet. Taksat e transferit dhe shpenzimet e noterit ndahen sipas marrëveshjes (psh. secila palë paguan pjesën e saj).

## 8. Nënshkrimet
- Nënshkrimi i Shitësit dhe Blerësit para Noterit publik.
  `,
  placeholder: "Shembull: Shitësi Ilir Shala shet banesën (ZK Prishtina, parcela 123/4, FP 555) për 100,000 euro blerësit Agim Krasniqi. Pagesa bëhet përmes bankës brenda 5 ditësh. Prona është pa barrë hipotekore.",
  label: "Kontratë Shitblerje",
};