// src/drafting/templates/compliance/privacy_policy.ts
import { TemplateConfig } from '../../types';

export const privacyPolicyTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Privacy Policy (Politika e Privatësisë) for a website.
MANDATORY SECTIONS:
- Introduction.
- Types of data collected.
- Purposes of processing.
- Data sharing with third parties.
- User rights.
- Security measures.
- Changes to policy.
- Contact information.

CITE the Kosovo Law on Personal Data Protection (Ligji Nr. 06/L-082) where appropriate.
  `,
  placeholder: "Shembull: Krijo një politikë privatësie për faqen time të internetit që shet produkte.",
  label: "Politika e Privatësisë",
};