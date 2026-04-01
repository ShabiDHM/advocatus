// FILE: src/drafting/templates/real_estate/lease_agreement.ts
// ARCHITECTURE: KOSOVO PROPERTY LAW & UTILITY COMPLIANCE (LIGJI PËR DETYRIMET NR. 2004/31) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const leaseAgreementTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kontratë Qiraje (Residential/Commercial) sipas Ligjit për Detyrimet të Republikës së Kosovës.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# KONTRATË QIRAJE

## 1. Palët Kontraktuese
- Qiradhënësi: [EMRI_I_QIRADHËNËSIT], me adresë [ADRESA_E_QIRADHËNËSIT], nr. personal [NR_PERSONAL_QIRADHËNËSIT].
- Qiramarrësi: [EMRI_I_QIRAMARRËSIT], me adresë [ADRESA_E_QIRAMARRËSIT], nr. personal [NR_PERSONAL_QIRAMARRËSIT].

## 2. Objekti i Qiradhënies
- Prona e dhënë me qira: [PËRSHKRIMI_I_PRONËS] (p.sh., banesë, zyrë, lokal).
- Lokacioni: [ADRESA_E_PRONËS].
- Sipërfaqja: [SIPËRFAQJA] m².

## 3. Qiraja dhe Mënyra e Pagesës
- Qiraja mujore (bruto/neto): [SHUMA_E_QIRASË] €.
- Data e pagesës: Çdo muaj deri më datën [DATA_E_PAGESËS] për muajin vijues.
- Mënyra e pagesës: [PAGESA_NË_DORË / TRANSFER_BANKAR] në llogarinë [NUMRI_LLOGARISË].

## 4. Shpenzimet e Shërbimeve (Utility Bills)
- Shpenzimet që paguan QIRAMARRËSI: [LISTA_E_SHËRBIMEVE_QIRAMARRËS] (p.sh., rryma, uji, mbeturinat, ngrohja).
- Shpenzimet që paguan QIRADHËNËSI: [LISTA_E_SHËRBIMEVE_QIRADHËNËS] (p.sh., taksa e pronës, mirëmbajtja e ndërtesës).

## 5. Depozita e Sigurisë
- Shuma e depozitës: [SHUMA_DEPOZITËS] € (zakonisht një qira mujore).
- Depozita kthehet Qiramarrësit brenda [NUMRI_DITËVE] ditëve pas përfundimit të kontratës, duke zbritur dëmet e shkaktuara përtej konsumit normal.

## 6. Detyrimet dhe Mirëmbajtja
- Qiramarrësi do ta përdorë pronën me kujdesin e një prindi të mirë familjeje (boni pater familias) dhe do të kryejë riparime të vogla.
- Qiradhënësi do të kryejë riparimet e mëdha strukturore (sipas Ligjit për Detyrimet neni [cakto nenin e zbatueshëm, p.sh. 525]).
- Nëse kontrata ka karakter komercial, palët mund të bien dakord për ndarje të ndryshme të mirëmbajtjes.

## 7. Kohëzgjatja dhe Ndërprerja
- Kohëzgjatja: [KOHËZGIATJA] (p.sh., 12 muaj, nga [DATA_FILLIMIT] deri më [DATA_MBARIMIT]).
- Pas skadimit, kontrata mund të zgjatet me marrëveshje të palëve ose konsiderohet e lidhur për afat të pacaktuar.
- Ndërprerja para afatit: paralajmërimi me shkrim prej [NUMRI_DITËVE_PARALAJMËRIM] ditësh, sipas nenit [cakto nenin e LMD për ndërprerjen e qirasë].

## 8. Baza Ligjore
- Kjo kontratë rregullohet nga Ligji për Detyrimet i Republikës së Kosovës (Ligji Nr. 2004/31), nenet 514–548 (qiraja e pasurisë së paluajtshme), dhe dispozitat e tjera të zbatueshme.

## 9. Inventari i Pronës
- Tabela e pajisjeve dhe mobiljeve që gjenden në pronë (bashkëngjitur si aneks ose e listuar më poshtë):

| Përshkrimi | Gjendja |
|------------|---------|
| [PAJISJA_1] | [GJENDJA_1] |
| [PAJISJA_2] | [GJENDJA_2] |

## 10. Nënshkrimet
- Qiradhënësi: [EMRI_MBIEMRI_QIRADHËNËSIT], nënshkrimi, data [DATA].
- Qiramarrësi: [EMRI_MBIEMRI_QIRAMARRËSIT], nënshkrimi, data [DATA].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "KONTRATË QIRAJE" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_QIRADHËNËSIT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë kontratë, baza ligjore është Ligji për Detyrimet (Ligji Nr. 2004/31). Mos përfshi ligje që nuk lidhen me detyrimet kontraktuale (p.sh., Ligji i Familjes ose LCP).
- Sigurohu që shpenzimet e shërbimeve të jenë të specifikuara qartë për të shmangur mosmarrëveshjet.
  `,
  placeholder: "Shembull: Qiradhënës Ilir Shala. Qiramarrës: [EMRI]. Objekti: Banesë në Prishtinë, rruga 'Bill Clinton'. Qiraja 300 euro. Depozita 300 euro. Qiramarrësi paguan rrymën, ujin dhe mbeturinat.",
  label: "Kontratë Qiraje",
};