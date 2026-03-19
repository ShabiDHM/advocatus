// src/drafting/templates/employment/employment_contract.ts
import { TemplateConfig } from '../../types';

export const employmentContractTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Professional employment contract (Kontratë Pune).
MANDATORY SECTIONS:
- Parties (employer and employee).
- Start date.
- Job description.
- Salary and payment terms.
- Working hours, leave.
- Termination conditions.
- Signatures.

CITE Kosovo Labor Law (Ligji Nr. 03/L-212 i Punës) where appropriate, but only actual articles you are sure of.
  `,
  placeholder: "Shembull: Punësoj një punonjës, Blerta Rexhepi, si asistente administrative. Paga mujore 500 euro, fillon më 1 prill.",
  label: "Kontratë Pune",
};