// FILE: src/drafting/utils/promptConstructor.ts
// PHOENIX PROTOCOL - USER CONTEXT PARSER V2 (DE-DUPLICATED)

import { TemplateType } from '../types';
import { getDocumentStructureInstructions } from './templateHelpers';

export const constructSmartPrompt = (userText: string, template: TemplateType): string => {
  // NOTE: The conflicting LEGAL_WHITELIST has been intentionally removed from here.
  // The strict Kosovo statute mapping and System Directives are now securely handled 
  // by the Zero-Hallucination Protocol in DraftingPage.tsx.

  return `
[FAKTET DHE KËRKESA E KLIENTIT]
Të dhënat e ofruara nga përdoruesi për këtë rast:
"""
${userText}
"""

[UDHËZIME SHTESË PËR KËTË DRAFT]
1. Ndërto dokumentin duke u bazuar KREJTËSISHT te faktet e mësipërme.
2. Për çdo të dhënë që klienti nuk e ka ofruar në tekstin e mësipërm, NDALOHET përdorimi i vijave të zbrazëta (si p.sh. "_____").
3. TI DUHET të përdorësh emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë. 
   Shembuj të saktë: [NUMRI_PERSONAL_I_PADITËSIT], [DATA_E_LIDHJES_SË_KONTRATËS], [SHUMA_E_DETYRIMIT], [ADRESA_E_TË_PADITURIT].

[STRUKTURA SPECIFIKE E DOKUMENTIT TË ZGJEDHUR]
${getDocumentStructureInstructions(template)}
  `.trim();
};