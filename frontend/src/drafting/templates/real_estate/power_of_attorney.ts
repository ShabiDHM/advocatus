// src/drafting/templates/real_estate/power_of_attorney.ts
import { TemplateConfig } from '../../types';

export const powerOfAttorneyTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Power of attorney (Autorizim / Prokurë) authorizing a person to act on behalf of another.
MANDATORY SECTIONS:
- Principal and agent.
- Scope of authority.
- Duration.
- Notarization requirements.
- Signatures.

CITE Kosovo law on representation (Ligji për Marrëdhëniet e Detyrimeve) where appropriate.
  `,
  placeholder: "Shembull: Dua të autorizoj avokatin tim për të përfaqësuar mua në shitjen e pronës time.",
  label: "Autorizim / Prokurë",
};