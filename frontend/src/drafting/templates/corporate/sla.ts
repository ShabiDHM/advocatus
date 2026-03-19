// src/drafting/templates/corporate/sla.ts
import { TemplateConfig } from '../../types';

export const slaTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Service Level Agreement (Marrëveshje e Nivelit të Shërbimit).
MANDATORY SECTIONS:
- Parties.
- Services to be provided.
- Performance metrics and service levels.
- Remedies for breach.
- Responsibilities of each party.
- Term and termination.
- Signatures.

CITATIONS: If Kosovo law applies, reference it with placeholders.
  `,
  placeholder: "Shembull: Një kompani IT do të ofrojë shërbime të mirëmbajtjes për klientin, me kohë përgjigjeje dhe sanksione.",
  label: "Marrëveshje e Nivelit të Shërbimit (SLA)",
};