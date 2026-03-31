// FILE: src/drafting/templates/litigation/padi.ts
// ARCHITECTURE: KOSOVO COURT FILING (LCP - NENI 83)

import { TemplateConfig } from '../../types';

export const padiTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Padi (Lawsuit) sipas Ligjit për Procedurën Kontestimore (LCP).
GJUHA: Shqip (Formale, procedurale, juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
## DEPARTAMENTI I PËRGJITHSHËM / EKONOMIK

## 1. PALËT
- Paditësi: [EMRI_MBIEMRI], me adresë [ADRESA], nr. personal [NR_PERSONAL].
- I Padituri: [EMRI_I_PALËS_TJETER], me adresë [ADRESA].

## 2. OBJEKTI I PADISË
- Përshkrimi i shkurtër i kërkesëpadisë (psh. Konfirmim pronësie, Borxh, Dëmshpërblim).

## 3. BAZA LIGJORE
- Cito dispozitat materiale të aplikueshme në Republikën e Kosovës.
- Baza procedurale: 'Ligji për Procedurën Kontestimore (LCP)'.
- Përdor placeholder nëse neni nuk është i sigurt: "[Neni përkatës i Ligjit...]".

## 4. ARSYETIMI I PADISË
- Paraqitja faktike: Përshkruaj kronologjikisht ngjarjen dhe dëmin e shkaktuar.
- Argumentimi ligjor: Lidh faktet me obligimet ligjore të të Paditurit.

## 5. PROVAT
- Listo të gjitha provat: (psh. Kontratat, dëshmitë, ekspertiza, fletëkthesat). "I propozoj gjykatës të marrë si provë: [LISTA_E_PROVAVE]".

## 6. PETITUMI (Kërkesë-Padia)
- Kërkesa 1: Të konfirmohet se [PËRSHKRIMI_I_TË_DREJTËS].
- Kërkesa 2: Të obligohet i Padituri që [VEPRIMI_I_KËRKUAR_OSE_SHUMA].
- Kërkesa 3: Të obligohet i Padituri që t'i kompensojë shpenzimet e procedurës (taksat gjyqësore dhe shpenzimet e avokatit).

## 7. NËNSHKRIMI
- Paditësi / Përfaqësuesi i autorizuar (Avokati): [EMRI_MBIEMRI_AVOKATIT]
- Vula dhe nënshkrimi.

UDHËZIM: Strukturoje dokumentin si një padi zyrtare drejtuar gjykatës. Shmang gjuhën emotive. Fokusohu në fakte, prova dhe dispozita ligjore.
  `,
  placeholder: "Shembull: Agim Krasniqi kërkon që fqinji i tij të largojë gardhin e ndërtuar 50cm në pronën e tij. Fqinji refuzon, pavarësisht matjeve gjeodezike. Agimi ka në dorë planin gjeodezik si provë kryesore.",
  label: "Padi",
};