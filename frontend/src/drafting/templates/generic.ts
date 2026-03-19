// src/drafting/templates/generic.ts
import { TemplateConfig } from '../types';

export const genericTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Professional legal document in Albanian, appropriate to the context provided by the user.
Use clear headings (### for sections).

**GUIDELINES FOR CHOOSING THE CORRECT FORMAT:**
- If the user describes a **dispute, problem, or conflict** regarding a contract (e.g., "problem me kontratë", "mosmarrëveshje"), use a **court pleading** style:
   * Include sections: PALËT, OBJEKTI, BAZA LIGJORE, ARSYETIMI, KËRKESAT / PËRFUNDIMI, NËNSHKRIMI.
   * Do not create a new contract; instead, create a document that addresses the dispute (e.g., a padí, kërkesë, or ankesë).

- If the user describes a **business arrangement, partnership, or new agreement**, use a **contract** style:
   * Include parties, recitals, numbered articles, signatures.

- If the user describes an **employment issue**, but does not explicitly ask for a contract, consider whether it is a dispute or a new agreement.

**CRITICAL INSTRUCTION:**
- **DO NOT CITE ANY SPECIFIC KOSOVO LAWS** unless the user explicitly mentions them.
- If you feel a legal reference is necessary, use ONLY a descriptive placeholder, e.g., "[Ligji përkatës i Republikës së Kosovës]".
- NEVER invent law numbers.
- Base your response on general legal principles and the user's input.
- Use placeholders for all missing specific details.
  `,
  placeholder: "Përshkruani situatën tuaj ligjore...",
  label: "Generic",
};