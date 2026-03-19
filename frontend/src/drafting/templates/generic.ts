// src/drafting/templates/generic.ts
import { TemplateConfig } from '../types';

export const genericTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Professional legal document in Albanian, appropriate to the context provided by the user.
Use clear headings (### for sections).
If the user describes a dispute, use court pleading style.
If they describe a business arrangement, use contract style.

**CRITICAL INSTRUCTION FOR GENERIC TEMPLATE:**
- **DO NOT CITE ANY SPECIFIC KOSOVO LAWS** unless the user explicitly mentions them.
- If you feel a legal reference is necessary, use ONLY a descriptive placeholder, e.g., "[Ligji përkatës i Republikës së Kosovës]" or "[Neni përkatës i Kodit Civil]" (but remember Kosovo has no Civil Code – avoid that too).
- NEVER invent law numbers (e.g., "Ligji Nr. 05/L-012").
- Base your response on general legal principles and the user's input.
- Use placeholders for all missing specific details.
  `,
  placeholder: "Përshkruani situatën tuaj ligjore...",
  label: "Generic",
};