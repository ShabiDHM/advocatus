// src/drafting/templates/litigation/pergjigje.ts
import { TemplateConfig } from '../../types';

export const pergjigjeTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Standard Kosovo court pleading structure for a response (Përgjigje në Padi).
MANDATORY SECTIONS:
- Court name centered.
- "PALËT:" listing Paditësi and I Padituri.
- "OBJEKTI:" brief subject.
- "BAZA LIGJORE:" citing relevant laws.
- "ARSYETIMI:" arguments against the claim.
- "KËRKESAT / PËRFUNDIMI:" specific requests (e.g., dismissal of lawsuit).
- "NËNSHKRIMI:" with placeholders.

IMPORTANT: This is a court document. Do not use commercial agreement language.
  `,
  placeholder: "Shembull: Klienti im, Agim Krasniqi, është paditur nga fqinji për cënim të pronës. Ne pretendojmë se gardhi është në tokën tonë dhe kërkojmë rrëzimin e padisë.",
  label: "Përgjigje në Padi",
};