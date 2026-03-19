// src/drafting/templates/corporate/nda.ts
import { TemplateConfig } from '../../types';

export const ndaTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Non-Disclosure Agreement (Marrëveshje për Konfidencialitet) under Kosovo law.
MANDATORY SECTIONS:
- Parties (disclosing and receiving parties).
- Definition of confidential information.
- Obligations of receiving party (non-disclosure, non-use).
- Exclusions from confidential information.
- Term and termination.
- Governing law (Kosovo).
- Signatures.

CITATIONS: Only reference actual Kosovo laws (e.g., Ligji Nr. 06/L-016 për Shoqëritë Tregtare) if certain. Otherwise use placeholders.
  `,
  placeholder: "Shembull: Dua të mbroj informacionin tim konfidencial kur diskutoj një partneritet të mundshëm me një kompani tjetër.",
  label: "Marrëveshje Konfidencialiteti (NDA)",
};