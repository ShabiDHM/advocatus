// src/drafting/utils/promptConstructor.ts
import { TFunction } from 'i18next';
import { TemplateType } from '../types';
import { getDocumentStructureInstructions } from './templateHelpers';

export const constructSmartPrompt = (userText: string, template: TemplateType, _t: TFunction): string => {
  // Domain detection for legal scope
  let domainInstruction = "Refer to Kosovo statutory law only. Do not cite foreign laws.";
  const lowerText = userText.toLowerCase();
  if (['familje', 'martes', 'shkurorëzim', 'alimentacion', 'femij'].some(k => lowerText.includes(k))) {
    domainInstruction = "DOMAIN: FAMILY LAW (Kosovo). Primary law: Ligji për Familjen i Kosovës. Be cautious with article numbers; if unsure, omit or use placeholders.";
  } else if (['shpk', 'aksion', 'biznes', 'ortak', 'partneritet', 'shareholder'].some(k => lowerText.includes(k))) {
    domainInstruction = "DOMAIN: CORPORATE LAW (Kosovo). Primary law: Ligji Nr. 06/L-016 për Shoqëritë Tregtare. Only cite articles you are absolutely certain exist.";
  } else if (['qira', 'pronë', 'patundshmëri'].some(k => lowerText.includes(k))) {
    domainInstruction = "DOMAIN: PROPERTY LAW (Kosovo). Relevant laws include Ligji për Pronësinë dhe të Drejta Tjera Sendore. Avoid inventing article numbers.";
  }

  // Role based on template
  let roleInstruction = "SENIOR KOSOVO ATTORNEY (Avokat i Specializuar).";
  if (template === 'pergjigje') {
    roleInstruction = "DEFENSE ATTORNEY (Avokati i të Paditurit).";
  } else if (template === 'padi') {
    roleInstruction = "PLAINTIFF'S ATTORNEY (Avokati i Paditësit).";
  }

  // Anti-hallucination header with placeholder instruction
  const antiHallucination = `
CRITICAL INSTRUCTION:
- **DO NOT HALLUCINATE.** Never invent Kosovo laws, article numbers, or legal provisions.
- If you are uncertain about a specific citation, use a placeholder like "[Neni i aplikueshëm i Ligjit ...]" or omit the citation entirely.
- If any required information is missing from the user input, insert clear placeholders like [_____] or [Emri i palës] to indicate missing data. Do not assume or invent facts.
- Only use your knowledge of actual Kosovo legislation. If the user input lacks sufficient detail, state that certain clauses may need further specification.
- Base your response strictly on the user input and your training data regarding Kosovo law.
  `;

  const structureInstructions = getDocumentStructureInstructions(template);

  return `
[SYSTEM MANDATE]
ROLE: ${roleInstruction}
GOAL: Draft a professional, accurate legal document in Albanian according to the user's request.
LEGAL SCOPE: ${domainInstruction}
${antiHallucination}
[/SYSTEM MANDATE]

${structureInstructions}

[USER INPUT DATA]
${userText}

Now, draft the document following all instructions above. Use markdown for headings (### for sections) and bold for emphasis where appropriate. Do not include any meta-commentary or explanations outside the document.
  `;
};