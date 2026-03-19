// src/drafting/templates/real_estate/sales_purchase.ts
import { TemplateConfig } from '../../types';

export const salesPurchaseTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Sale and purchase agreement (Kontratë Shitblerje) for immovable property.
MANDATORY SECTIONS:
- Parties (seller and buyer).
- Property description.
- Price and payment terms.
- Transfer of ownership.
- Warranties.
- Signatures.

CITE Kosovo Law on Property (Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat Tjera Sendore) and Law on Obligations as appropriate.
  `,
  placeholder: "Shembull: Dua të shes një shtëpi në Prishtinë për 100,000 euro. Blerësi është Agim Krasniqi.",
  label: "Kontratë Shitblerje",
};