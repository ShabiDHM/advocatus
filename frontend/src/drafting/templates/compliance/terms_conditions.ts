// src/drafting/templates/compliance/terms_conditions.ts
import { TemplateConfig } from '../../types';

export const termsConditionsTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Terms and Conditions (Kushtet e Përdorimit) for a website/service.
MANDATORY SECTIONS:
- Acceptance of terms.
- User accounts.
- Payments (if applicable).
- Intellectual property.
- Termination.
- Disclaimers and limitation of liability.
- Governing law (Kosovo).
- Contact information.

CITE relevant Kosovo laws (e.g., Law on Consumer Protection) only if certain; otherwise use general principles.
  `,
  placeholder: "Shembull: Faqja ime e internetit shet produkte online dhe kam nevojë për kushtet e përdorimit.",
  label: "Kushtet e Përdorimit",
};