// FILE: src/drafting/templates/generic.ts
// ARCHITECTURE: INTELLIGENT DOCUMENT CLASSIFICATION & STRUCTURE

import { TemplateConfig } from '../types';

export const genericTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Dokument ligjor profesional në gjuhën shqipe (Gjuhë zyrtare).
DETYRA: Analizo inputin e përdoruesit dhe zgjidh strukturën më të përshtatshme.

UDHËZIMET E KLASIFIKIMIT:
1. KONFLIKT/MOSMARRËVESHJE: Përdor formatin e SHKRESËS SË GJYKATËS.
   - Seksionet: # GJYKATA THEMELORE, ## PALËT, ## OBJEKTI, ## ARSYETIMI, ## KËRKESË-PËRFUNDIMI, ## NËNSHKRIMI.
2. MARRËVESHJE/BIZNES: Përdor formatin e KONTRATËS.
   - Seksionet: # TITULLI I KONTRATËS, ## PALËT, ## OBJEKTI, ## DETYRIMET, ## ZGJIDHJA E KONTESTEVE, ## NËNSHKRIMET.
3. KËRKESË INFORMACIONI/LAVDËRIMI: Përdor formatin e KËRKESËS FORMALE.

UDHËZIME TË PËRGJITHSHME (ZERO HALLUCINATION):
- **CILËSIMET LIGJORE**: Nëse përmend ligje, përdor vetëm placeholderët: [LIGJI_PËRKATËS_I_REPUBLIKËS_SË_KOSOVËS]. **MOS SHPIK NUMRA LIGJESH.**
- **PLACEHOLDERS**: Përdor formatin [EMRI_MBIEMRI], [DATA], [SHUMA_E_PAGESËS], [ADRESA]. Kjo është e detyrueshme për çdo të dhënë që nuk është dhënë nga përdoruesi.
- **TONI**: Formal, objektiv, i prerë.
- **NDALOJNË PARATHËNIET**: Fillo direkt me titullin e dokumentit.
  `,
  placeholder: "Përshkruani situatën tuaj: p.sh. 'Kam një problem me qiradhënësin sepse nuk po më kthen depozitën' ose 'Dua të bëj një marrëveshje me një partner për të shitur produkte'.",
  label: "Dokument i Përgjithshëm (Generic)",
};