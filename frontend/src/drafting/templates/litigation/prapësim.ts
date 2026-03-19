// src/drafting/templates/litigation/prapësim.ts
import { TemplateConfig } from '../../types';

export const prapesimTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Standard Kosovo court pleading structure for an objection (Prapësim).
MANDATORY SECTIONS:
- Court name.
- "PALËT:" listing parties.
- "OBJEKTI:" subject of the objection.
- "BAZA LIGJORE:" legal basis.
- "ARSYETIMI:" reasons for objection.
- "KËRKESAT / PËRFUNDIMI:" specific request.
- "NËNSHKRIMI:" with placeholders.

IMPORTANT: This is a court document. It is used to object to a procedural action or evidence.
  `,
  placeholder: "Shembull: Dëshiroj të kundërshtoj provën e paraqitur nga pala tjetër për shkak se është e parregullt.",
  label: "Prapësim",
};