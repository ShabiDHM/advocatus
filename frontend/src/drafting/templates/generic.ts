// src/drafting/templates/generic.ts
import { TemplateConfig } from '../types';

export const genericTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Professional legal document in Albanian, appropriate to the context provided by the user.
Use clear headings (### for sections).
If the user describes a dispute, use court pleading style.
If they describe a business arrangement, use contract style.
**Do not invent Kosovo laws or article numbers.** Use placeholders like "[Neni përkatës i Ligjit ...]" if you are uncertain.
  `,
  placeholder: "Përshkruani situatën tuaj ligjore...",
  label: "Generic",
};