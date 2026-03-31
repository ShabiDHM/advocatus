// FILE: src/drafting/utils/promptConstructor.ts
import { TemplateType } from '../types';
import { getDocumentStructureInstructions } from './templateHelpers';

// STRICT REGISTRY: Maps templates to specific Kosovo Legislation.
const LEGAL_WHITELIST: Record<string, { law: string; focus: string }> = {
  padi: { law: "Ligji i Familjes së Kosovës (Nr. 2004/25) dhe Ligji për Procedurën Kontestimore", focus: "Family Law & Civil Procedure" },
  pergjigje: { law: "Ligji i Familjes së Kosovës (Nr. 2004/25) dhe Ligji për Procedurën Kontestimore", focus: "Family Law Defense" },
  kunderpadi: { law: "Ligji i Familjes së Kosovës (Nr. 2004/25)", focus: "Family Law Counter-claim" },
  nda: { law: "Ligji Nr. 06/L-016 për Shoqëritë Tregtare dhe Kodi Civil", focus: "Corporate Confidentiality" },
  employment_contract: { law: "Ligji i Punës Nr. 03/L-212", focus: "Employment Rights" },
  generic: { law: "Kodi Civil i Republikës së Kosovës", focus: "General Civil Obligations" }
};

export const constructSmartPrompt = (userText: string, template: TemplateType): string => {
  const meta = LEGAL_WHITELIST[template] || LEGAL_WHITELIST['generic'];

  return `
[SYSTEM ROLE]
You are a senior attorney in the Republic of Kosovo. 
TASK: Draft a professional legal document based on the input.

[STRICT LEGAL CONSTRAINTS]
1. CITATION SOURCE: You are restricted to using: ${meta.law}.
2. PROHIBITION: DO NOT cite the 'Ligji për Marrëdhëniet e Detyrimeve' if the case is Family Law.
3. OUTPUT FORMAT: Begin immediately with the court header. No conversational filler.
4. PLACEHOLDERS: Use [_____] for any information not provided by the user. Do not invent facts.

[DOCUMENT STRUCTURE]
${getDocumentStructureInstructions(template)}

[USER INPUT]
${userText}

[DRAFTING INSTRUCTIONS]
- Use the structure defined above.
- Apply formal Albanian legal terminology.
- Maintain professional tone.
  `;
};