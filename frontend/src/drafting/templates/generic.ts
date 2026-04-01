// FILE: src/drafting/templates/generic.ts
// ARCHITECTURE: INTELLIGENT DOCUMENT CLASSIFICATION & STRUCTURE – DETERMINISTIC

import { TemplateConfig } from '../types';

export const genericTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Dokument ligjor profesional në gjuhën shqipe (Gjuhë zyrtare).
DETYRA: Analizo inputin e përdoruesit dhe zgjidh strukturën më të përshtatshme sipas klasifikimit më poshtë.

UDHËZIMET E KLASIFIKIMIT:

**1. KONFLIKT / MOSMARRËVESHJE (p.sh., padi, ankesë, përgjigje)**
   - Struktura e SHKRESËS SË GJYKATËS:
     # GJYKATA THEMELORE NË [EMRI_I_GJYKATËS]
     ## 1. PALËT
     ## 2. OBJEKTI
     ## 3. BAZA LIGJORE (përdor [LIGJI_PËRKATËS_I_REPUBLIKËS_SË_KOSOVËS] dhe [NENI_PËRKATËS])
     ## 4. ARSYETIMI
     ## 5. PROVAT
     ## 6. KËRKESË-PËRFUNDIMI (PETITUMI)
     ## 7. NËNSHKRIMI

**2. MARRËVESHJE / BIZNES (p.sh., kontratë, NDA, SLA)**
   - Struktura e KONTRATËS:
     # [TITULLI_I_KONTRATËS]
     ## 1. PALËT
     ## 2. OBJEKTI / PËRSHKRIMI I SHËRBIMEVE
     ## 3. DETYRIMET E PALËVE
     ## 4. ÇMIMI DHE PAGESA
     ## 5. KOHËZGJATJA DHE NDËRPRERJA
     ## 6. LIGJI I ZBATUESHËM (përdor [LIGJI_PËRKATËS_I_REPUBLIKËS_SË_KOSOVËS])
     ## 7. ZGJIDHJA E KONTESTEVE
     ## 8. NËNSHKRIMET

**3. KËRKESË FORMALE / INFORMIM (p.sh., kërkesë për informim, lajmërim)**
   - Struktura e KËRKESËS FORMALE:
     # [TITULLI]
     ## 1. PALËT
     ## 2. BAZA LIGJORE (nëse ka)
     ## 3. KËRKESA / ARSYETIMI
     ## 4. NËNSHKRIMI

UDHËZIME TË PËRGJITHSHME (ZERO HALLUCINATION):

- **BAZA LIGJORE**: Për çdo referencë ligjore, përdor placeholderët:
  - [LIGJI_PËRKATËS_I_REPUBLIKËS_SË_KOSOVËS] për emrin e ligjit.
  - [NENI_PËRKATËS] për numrin e nenit.
  - **MOS SHPIK NUMRA LIGJESH OSE NENESH**. Nëse nuk jeni i sigurt për ligjin, përdor këta placeholderë.

- **PLACEHOLDERS**: Për të dhënat që mungojnë, përdor formatin [PËRSHKRIMI_I_TË_DHËNËS]. Shembuj:
  - [EMRI_MBIEMRI_PADITËSIT], [DATA_E_NGRARJES], [SHUMA_E_PAGESËS], [ADRESA_E_PRONËS].
  - **NDALOHET** përdorimi i vijave të zbrazëta (_____) apo placeholder-it “[_____]”.

- **NDALO PARATHËNIET**: Fillo direkt me titullin e dokumentit (p.sh., # GJYKATA THEMELORE ose # KONTRATË...).

- **NDALO HALLUCINIMIN E FUSHËS**: Nëse fakti i përdoruesit lidhet me familje, mos përfshi kontrata korporative. Nëse lidhet me pronësi, mos përfshi procedurë penale. Qëndro brenda kontekstit të fakteve.

- **TONI**: Formal, objektiv, i prerë. Përdor gjuhë juridike standarde.

- **STRUKTURA**: Zgjedh strukturën bazuar në llojin e çështjes. Nëse nuk mund të klasifikohet, përdor strukturën e kërkesës formale.
  `,
  placeholder: "Përshkruani situatën tuaj: p.sh. 'Kam një problem me qiradhënësin sepse nuk po më kthen depozitën' ose 'Dua të bëj një marrëveshje me një partner për të shitur produkte'.",
  label: "Dokument i Përgjithshëm (Generic)",
};