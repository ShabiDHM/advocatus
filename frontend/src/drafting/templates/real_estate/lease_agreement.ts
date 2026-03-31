// FILE: src/drafting/templates/real_estate/lease_agreement.ts
// ARCHITECTURE: KOSOVO PROPERTY LAW & UTILITY COMPLIANCE (LMD)

import { TemplateConfig } from '../../types';

export const leaseAgreementTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kontratë Qiraje (Residential/Commercial).
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# KONTRATË QIRAJE

## 1. Palët Kontraktuese
- Qiradhënësi: [EMRI_I_QIRADHËNËSIT], me adresë [ADRESA].
- Qiramarrësi: [EMRI_I_QIRAMARRËSIT], me adresë [ADRESA].

## 2. Objekti i Qiradhënies
- Përshkrimi i detajuar i pronës (banesë, zyre, lokal), lokacioni dhe sipërfaqja.

## 3. Qiraja dhe Mënyra e Pagesës
- Shuma e qirasë (Bruto/Neto).
- Data e pagesës (psh. deri më datën 5 të muajit për muajin vijues).
- Mënyra e pagesës (Transfer bankar ose para në dorë).

## 4. Shpenzimet e Shërbimeve (Utility Bills)
- Specifikimi: Kush paguan për rrymën, ujin, mbeturinat, ngrohjen dhe mirëmbajtjen e hyrjes.

## 5. Depozita e Sigurisë
- Shuma e depozitës (psh. një qira mujore) dhe kushtet e kthimit të saj pas përfundimit të kontratës.

## 6. Detyrimet dhe Mirëmbajtja
- Qiramarrësi obligohet ta ruajë pronën si "boni pater familias".
- Qiradhënësi obligohet për riparimet e mëdha strukturore (sipas LMD).

## 7. Kohëzgjatja dhe Ndërprerja
- Afati i kontratës.
- Kushtet e shkëputjes (psh. paralajmërimi 30 ditë më parë).

## 8. Baza Ligjore
- Cito: "Ligji për Marrëdhëniet e Detyrimeve (Nr. 04/L-077) i Republikës së Kosovës".

## 9. Inventari i Pronës (Shto tabelë)
- Listo mobiljet dhe gjendjen e pajisjeve (psh. frigorifer, kondicioner, etj.).

## 10. Nënshkrimet
- Nënshkrimi i Qiradhënësit dhe Qiramarrësit.
  `,
  placeholder: "Shembull: Qiradhënës Ilir Shala. Qiramarrës: [EMRI]. Objekti: Banesë në Prishtinë, rruga 'Bill Clinton'. Qiraja 300 euro. Depozita 300 euro. Qiramarrësi paguan rrymën, ujin dhe mbeturinat.",
  label: "Kontratë Qiraje",
};