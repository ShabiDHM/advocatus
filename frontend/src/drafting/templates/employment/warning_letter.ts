// src/drafting/templates/employment/warning_letter.ts
import { TemplateConfig } from '../../types';

export const warningLetterTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Written warning (Vërejtje me Shkrim) to an employee.
MANDATORY SECTIONS:
- Employee name.
- Description of the issue.
- Previous discussions.
- Consequences if not corrected.
- Signature of issuer.

CITE Kosovo Labor Law (Ligji Nr. 03/L-212 i Punës) where appropriate.
  `,
  placeholder: "Shembull: Punonjësi vazhdimisht vonohet në punë dhe nuk përmbush detyrat.",
  label: "Vërejtje me Shkrim",
};