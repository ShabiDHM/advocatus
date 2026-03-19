// src/drafting/templates/litigation/ankese.ts
import { TemplateConfig } from '../../types';

export const ankeseTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Standard Kosovo court pleading structure for an appeal (Ankesë).
MANDATORY SECTIONS:
- Court name (the appellate court).
- "PALËT:" listing appellant and respondent.
- "VENDIMI I ANKUAR:" reference to the decision being appealed.
- "BAZA LIGJORE:" grounds for appeal (e.g., errors of law, procedural violations).
- "ARSYETIMI:" detailed argument.
- "KËRKESAT / PËRFUNDIMI:" specific request (e.g., annulment, modification).
- "NËNSHKRIMI:" with placeholders.

IMPORTANT: This is a court document. Follow procedural rules for appeals.
  `,
  placeholder: "Shembull: Klienti im ka marrë një vendim të padrejtë nga Gjykata Themelore në Prishtinë dhe dëshiron të apelojë.",
  label: "Ankesë",
};