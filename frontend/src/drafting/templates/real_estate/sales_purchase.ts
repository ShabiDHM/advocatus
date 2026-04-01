// FILE: src/drafting/templates/real_estate/sales_purchase.ts
// ARCHITECTURE: KOSOVO PROPERTY TRANSFER & CADASTRAL COMPLIANCE – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const salesPurchaseTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kontratë Shitblerje (Sale & Purchase Agreement) për Patundshmëri sipas Ligjit për Pronësinë dhe të Drejtat Tjera Sendore dhe Ligjit për Detyrimet të Republikës së Kosovës.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# KONTRATË SHITBLERJE PËR PATUNDSHMËRI

## 1. Palët Kontraktuese
- Shitësi: [EMRI_MBIEMRI_SHITËSIT], nr. personal [NR_PERSONAL_SHITËSIT], me adresë [ADRESA_SHITËSIT].
- Blerësi: [EMRI_MBIEMRI_BLERËSIT], nr. personal [NR_PERSONAL_BLERËSIT], me adresë [ADRESA_BLERËSIT].

## 2. Përshkrimi i Patundshmërisë
- **KLAUZOLË E DETYRUESHME:** Identifikimi i plotë sipas fletës poseduese dhe kadastrit:
  - Zona Kadastrale: [ZK_ZONA_KADASTRALE]
  - Nr. i Parcelës: [NR_PARCELËS]
  - Nr. i Fletës Poseduese: [NR_FLETA_POSEDUESE]
  - Sipërfaqja: [SIPËRFAQJA_M2] m²
  - Përshkrimi i pronës: [PËRSHKRIMI_I_PRONËS] (p.sh., banesë, lokal, tokë bujqësore, etj.)

## 3. Çmimi dhe Mënyra e Pagesës
- Çmimi total i shitjes: [SHUMA_EURO] €.
- Mënyra e pagesës: [PAGESA_NJËHERËSH / ME_KËSTE].
  - Nëse me këste, detajet: [KËSTI_I_PARË] € më [DATA_KËSTIT_1], [KËSTI_I_DYTË] € më [DATA_KËSTIT_2].
- Shitësi konfirmon se ka marrë pagesën (ose se pagesa do të kryhet sipas planit). Pas pagesës së plotë, Blerësi merr pronësinë e plotë.

## 4. Garantimi i Pronësisë (Eviksioni)
- Shitësi garanton se:
  - Është pronar i vetëm i patundshmërisë dhe ka të drejtën e plotë për ta shitur.
  - Patundshmëria është e lirë nga barrët, hipotekat, qiratë ose të drejta të tjera të palëve të treta, përveç atyre të shprehura në këtë kontratë.
- Në rast se ndonjë palë e tretë pretendon të drejta mbi pronën, Shitësi do të mbrojë Blerësin sipas dispozitave të Ligjit për Detyrimet (Ligji Nr. 2004/31) neni 127 (Garancia kundër eviksionit).

## 5. Transferi i Pronësisë dhe Dorëzimi
- Dorëzimi i posedimit të patundshmërisë do të bëhet më [DATA_DORËZIMIT].
- Shitësi merr përsipër të transferojë titullin e pronësisë në librat kadastralë në emër të Blerësit, brenda [NUMRI_DITËVE] ditëve pas noterizimit të kësaj kontrate.
- Shpenzimet e transferit në kadastër i paguan [SHITËSI / BLERËSI / NDAHEN_PËRGJYSMË].

## 6. Baza Ligjore
- Kjo kontratë rregullohet nga:
  - Ligji për Pronësinë dhe të Drejtat Tjera Sendore (Ligji Nr. 2004/33), nenet [cakto nenet për transferin e pronësisë, p.sh. 66–72].
  - Ligji për Detyrimet (Ligji Nr. 2004/31), nenet 120–127 (Kontrata e shitjes), neni 128 (Dëmshpërblimi), dhe dispozitat e tjera të zbatueshme.

## 7. Noterizimi dhe Taksat
- Kjo kontratë do të vërtetohet (noterizohet) nga një noter publik i licencuar në Republikën e Kosovës, në përputhje me Ligjin për Noterinë ([LIGJI_PËR_NOTERINË]).
- Taksat e noterit dhe taksat e transferit të pronësisë paguhen nga: [SHITËSI / BLERËSI / NDAHEN_PËRGJYSMË] në pajtim me marrëveshjen e palëve.

## 8. Nënshkrimet
- Shitësi: [EMRI_MBIEMRI_SHITËSIT], nënshkrimi, data [DATA].
- Blerësi: [EMRI_MBIEMRI_BLERËSIT], nënshkrimi, data [DATA].
- (Hapësirë për vërtetimin noterial)

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "KONTRATË SHITBLERJE PËR PATUNDSHMËRI" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_MBIEMRI_SHITËSIT]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Baza ligjore përfshin Ligjin për Pronësinë dhe Ligjin për Detyrimet. Mos përfshi ligje që nuk lidhen me shitblerjen e patundshmërisë.
- Identifikimi i patundshmërisë duhet të jetë sa më i detajuar për të siguruar vlefshmërinë dhe regjistrimin në kadastër.
  `,
  placeholder: "Shembull: Shitësi Ilir Shala shet banesën (ZK Prishtina, parcela 123/4, FP 555) për 100,000 euro blerësit Agim Krasniqi. Pagesa bëhet përmes bankës brenda 5 ditësh. Prona është pa barrë hipotekore.",
  label: "Kontratë Shitblerje",
};