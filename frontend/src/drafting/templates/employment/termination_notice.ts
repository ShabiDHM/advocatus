// src/drafting/templates/employment/termination_notice.ts
import { TemplateConfig } from '../../types';

export const terminationNoticeTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Termination notice (Lajmërim për Ndërprerje të Marrëdhënies së Punës).
MANDATORY SECTIONS:
- Employee name and position.
- Date of termination.
- Reason for termination.
- Notice period and final settlement.
- Reference to Kosovo Labor Law.
- Signature of employer.

CITE Kosovo Labor Law (Ligji Nr. 03/L-212 i Punës) where appropriate.
  `,
  placeholder: "Shembull: Punonjësi ka shkelur rregullat e brendshme dhe duhet të ndërpresim kontratën me të.",
  label: "Lajmërim për Ndërprerje",
};