// src/drafting/templates/litigation/kunderpadi.ts
import { TemplateConfig } from '../../types';

export const kunderpadiTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Standard Kosovo court pleading structure for a counterclaim (Kundërpadi).
MANDATORY SECTIONS:
- Court name centered.
- "PALËT:" listing Paditësi and I Padituri (including counterclaim parties).
- "OBJEKTI:" subject of the counterclaim.
- "BAZA LIGJORE:" citing relevant laws.
- "ARSYETIMI:" facts and arguments supporting the counterclaim.
- "KËRKESAT / PËRFUNDIMI:" specific requests.
- "NËNSHKRIMI:" with placeholders.

IMPORTANT: This is a court document. It should be filed as part of the same lawsuit but may include additional claims.
  `,
  placeholder: "Shembull: Pasi fqinji më paditi për cënim të pronës, unë dua të parashtroj kundërpadi për shpifje dhe ngacmim.",
  label: "Kundërpadi",
};