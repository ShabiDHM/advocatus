// src/drafting/templates/corporate/shareholders.ts
import { TemplateConfig } from '../../types';

export const shareholdersTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Standard commercial agreement structure.
- Title centered: e.g., "MARRËVESHJE E ORTAKËVE".
- Introduction: "Kjo marrëveshje lidhet sot, më [data], ndërmjet:" followed by party details.
- Recitals (preamble) beginning with "DUKE PASUR PARASYSH:".
- Definitions (if needed).
- Substantive clauses (numbered articles).
- Signatures.

This is a Shareholders' Agreement (Marrëveshje e Ortakëve) governed by the Kosovo Law on Business Organizations (Ligji Nr. 06/L-016 për Shoqëritë Tregtare). Include:
- Parties (shareholders), company name, registered office.
- Share capital, share classes, rights and obligations of shareholders.
- Management structure, decision-making, dividend policy.
- Transfer of shares, dispute resolution, duration.
- Signature blocks.

CITE only actual articles from Ligji Nr. 06/L-016 if you are certain. Otherwise use placeholders.

**Do not use court styling (no "GJYKATA", "PADITËSI", "PETITUMI").**
  `,
  placeholder: "Shembull: Dua të krijoj një marrëveshje ortakërie për një biznes të ri me dy partnerë: unë, Fatmir Berisha, dhe shoku im Labinot Gashi. Do të kemi 50% secili, dhe dua të përcaktojmë menaxhimin dhe ndarjen e fitimit.",
  label: "Marrëveshje e Ortakëve",
};