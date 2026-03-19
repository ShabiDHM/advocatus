// src/drafting/templates/real_estate/lease_agreement.ts
import { TemplateConfig } from '../../types';

export const leaseAgreementTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Residential or commercial lease agreement (Kontratë Qiraje) under Kosovo law.
MANDATORY SECTIONS:
- Parties (landlord and tenant).
- Property description.
- Rent amount and payment terms.
- Duration of lease.
- Deposit (if any).
- Obligations of parties (maintenance, utilities).
- Termination conditions.
- Signatures.

CITE Kosovo Law on Obligations (Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve) where appropriate.
  `,
  placeholder: "Shembull: Marr me qira një banesë në Prishtinë, te rruga 'Bill Clinton'. Qiradhënësi: Ilir Shala. Qiraja mujore 300 euro.",
  label: "Kontratë Qiraje",
};