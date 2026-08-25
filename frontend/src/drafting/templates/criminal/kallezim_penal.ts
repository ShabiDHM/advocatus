// FILE: src/drafting/templates/criminal/kallezim_penal.ts
// ARCHITECTURE: KOSOVO CRIMINAL PROCEDURE COMPLIANT TEMPLATE (KPPRK & KPRK)

import { TemplateConfig } from '../../types';

export const kallezimPenalTemplate: TemplateConfig = {
  label: 'Kallëzim Penal',
  placeholder: 'Përshkruani ngjarjen, personin e denoncuar (ose person i panjohur NN), kohën dhe vendin e kryerjes së veprës, veprën penale të dyshuar, si dhe provat konkrete (dëshmitarë, dokumente, xhirime, etj.)...',
  structureInstructions: `
STRUKTURA E DETYRUESHME E KALLËZIMIT PENAL (Sipas Kodit të Procedurës Penale të Kosovës - KPPRK Nr. 08/L-032):

1. TITULLI & MARRËSI:
   - PROKURORISË THEMELORE NË [EMRI_I_QYTETIT] - DEPARTAMENTI PËRKATËS (Krimet e Rënda / Departamenti i Përgjithshëm / Departamenti për të Mitur).

2. PALËT:
   - KALLËZUESI (I DËMTUARI): [EMRI_MBIEMRI], Numri Personal: [NUMRI_PERSONAL], Vendbanimi: [ADRESA], Përfaqësuar nga: [EMRI_I_AVOKATIT/PËRFAQËSUESIT].
   - KUNDËR TË DENONCUARIT (TË DYSHUARIT): [EMRI_MBIEMRI_OSE_KOMPANIA] ose [PERSON I PANJOHUR - NN], me të dhënat e njohura [ADRESA/FUNKSIONI].

3. CILËSIMI JURIDIK I VEPRËS PENALE:
   - Për shkak të dyshimit të bazuar se ka kryer veprën penale: [EMËRTIMI_I_VEPRËS_PENALE], nga Neni [NENI] i Kodit Penal të Republikës së Kosovës (KPRK Nr. 06/L-074).

4. PËRSHKRIMI FAKTIK I NGJARJES (ELEMENTET E VEPRËS):
   - Kronologjia e qartë dhe e detajuar: Kur, ku dhe si është kryer vepra penale.
   - Përshkrimi i veprimeve të drejtpërdrejta inkriminuese, dashjes (qëllimit) dhe pasojës së shkaktuar (dëmi material/jo-material).

5. PROVAT DHE DËSHMITË MATERIALE:
   - Numërimi i saktë dhe i renditur i provave (Prova 1: Kontrata, Prova 2: Komunikimet, Prova 3: Dëshmitarët me emër e mbiemër, etj.).

6. KËRKESA DHE PROPOZIMI DREJTUAR PROKURORIT TË SHTETIT:
   - Fillimi i hetimeve ndaj të dyshuarit.
   - Ndërmarrja e veprimeve të nevojshme procedurale hetimore.
   - Ngritja e Aktakuzës pranë Gjykatës kompetente.
   - Rezervimi i kërkesës pasurore-juridike për kompensimin e dëmit.
`.trim()
};