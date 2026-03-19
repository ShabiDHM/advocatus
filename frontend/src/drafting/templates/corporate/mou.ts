// src/drafting/templates/corporate/mou.ts
import { TemplateConfig } from '../../types';

export const mouTemplate: TemplateConfig = {
  structureInstructions: `
FORMAT: Memorandum of Understanding (Memorandum Bashkëpunimi).
MANDATORY SECTIONS:
- Parties and intent.
- Key terms and conditions.
- Next steps and timeline.
- Non-binding clause (if applicable).
- Signatures.

CITATIONS: Usually no citations, but if specific laws apply, mention them with placeholders.
  `,
  placeholder: "Shembull: Dy kompanitë tona duan të bashkëpunojnë për një projekt të përbashkët dhe duan të përshkruajnë qëllimet para kontratës finale.",
  label: "Memorandum Bashkëpunimi (MoU)",
};