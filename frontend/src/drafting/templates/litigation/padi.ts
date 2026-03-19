// src/drafting/templates/litigation/padi.ts
import { TemplateConfig } from '../../types';

export const padiTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Standard Kosovo court pleading structure.
MANDATORY SECTIONS:
- Court name (e.g., "GJYKATA THEMELORE NË PRISHTINË") centered, bold.
- "PALËT:" listing Paditësi (Plaintiff) and I Padituri (Defendant) with details.
- "OBJEKTI:" stating the subject of the lawsuit.
- "BAZA LIGJORE:" citing only actual Kosovo laws (e.g., Ligji për Procedurën Kontestimore, Ligji për Familjen, Ligji për Shoqëritë Tregtare). **Never invent article numbers.** If you are unsure, use a placeholder like "[Neni i aplikueshëm i Ligjit ...]".
- "ARSYETIMI:" a reasoned argument based on the user input.
- "PETITUMI / PËRFUNDIMI:" the specific requests to the court.
- "NËNSHKRIMI:" with placeholders for date and lawyer name.

IMPORTANT: This is a court document, not a contract. Do not include commercial agreement sections.
  `,
  placeholder: "Shembull: Klienti im, Agim Krasniqi, ka një mosmarrëveshje me fqinjin për kufirin e pronës. Fqinji ka ndërtuar gardh 50 cm në tokën tonë. Dëshiroj të parashtroj një padi për cënim të pronës.",
  label: "Padi",
};