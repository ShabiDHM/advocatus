// FILE: src/utils/lawArticleHelpers.ts
// PHOENIX PROTOCOL - LAW ARTICLE HELPERS V39.0
//
// V39.0: FIX H1-H7 (auditim i plotë).
//   - H1: HEQUR `generateFallbackChunkId` (krijonte ID fake që nuk ekziston në DB)
//   - H3: Hequr prefiks `_` nga `articleNum` (parametri PËRDORET realisht)
//   - H4: Zgjeruar punctuation detection (thonjëza, kllapa, guillemets)
//   - H5: Zgjeruar numbered item detection (Neni X, Artikulli Y, romake)
//   - H6: Ruajtur `\n{3,}` collapse — OK
//   - H7: Kufizuar heqjen e numrave standalone (vetëm 1-3 shifra, jo 4+)
//
// V38.0: Versioni i vjetër me generateFallbackChunkId.

// ═══════════════════════════════════════════════════════════════════════════
// NORMALIZE TEXT
// ═══════════════════════════════════════════════════════════════════════════

export const normalizeText = (raw: string, articleNum?: string): string => {
  if (!raw) return '';

  let cleaned = raw;

  // 1. Normalizo hapësirat Unicode në ASCII
  cleaned = cleaned.replace(
    /[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]/g,
    ' ',
  );

  // 2. Heq OCR page markers & headers
  cleaned = cleaned.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');
  cleaned = cleaned.replace(
    /GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*?(?=\n|$)/gi,
    '',
  );
  cleaned = cleaned.replace(
    /FLETORJA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+SHQIPËRISË.*?(?=\n|$)/gi,
    '',
  );
  cleaned = cleaned.replace(/==Start of OCR for page \d+==/gi, '');
  cleaned = cleaned.replace(/==End of OCR for page \d+==/gi, '');
  cleaned = cleaned.replace(/==Screenshot for page \d+==/gi, '');

  // V39.0 (H7): Heq vetëm numrat standalone 1-3 shifra (numrat e faqeve OCR),
  // NUK 4+ shifra (mund të jenë numra nenesh ose referenca).
  cleaned = cleaned.replace(/^\s*\d{1,3}\s*$/gm, '');

  // 3. Heq "Neni X" redundant në fillim
  const cleanNumStr = (articleNum || '').replace(/\.$/, '').trim();
  if (cleanNumStr) {
    const redundantNeniRegex = new RegExp(
      `^\\s*(?:Neni|NENI)\\s+${cleanNumStr}\\b[:\\.\\-]*\\s*`,
      'i',
    );
    cleaned = cleaned.replace(redundantNeniRegex, '');
  }

  // 4. Bashko linjat e ndara në mes të fjalisë
  const lines = cleaned.split('\n');
  const mergedLines: string[] = [];

  // V39.0 (H4): punctuation e plotë — pika, dy pika, pikëpresje, pikëpyetje,
  // pikëçuditëse, thonjëza, kllapa mbyllëse, guillemets
  const ENDS_WITH_PUNCT = /[.:;?!)\]}"'»""'']$/;

  // V39.0 (H5): numbered item detection e zgjeruar
  const IS_NUMBERED_ITEM =
    /^(?:\d+[.)]|\(\d+\)|\([a-z]\)|^[a-z][.)]|[IVX]+[.)]|Neni\s+\d+|Artikulli\s+\d+|NENI\s+\d+)/i;

  for (let i = 0; i < lines.length; i++) {
    const currentLine = lines[i].replace(/[ \t]{2,}/g, ' ').trim();
    if (!currentLine) {
      mergedLines.push('');
      continue;
    }

    if (mergedLines.length > 0 && mergedLines[mergedLines.length - 1] !== '') {
      const lastIdx = mergedLines.length - 1;
      const previousLine = mergedLines[lastIdx];
      const endsWithPunctuation = ENDS_WITH_PUNCT.test(previousLine);
      const isNumberedItem = IS_NUMBERED_ITEM.test(currentLine);

      if (!endsWithPunctuation && !isNumberedItem) {
        mergedLines[lastIdx] = previousLine + ' ' + currentLine;
      } else {
        mergedLines.push(currentLine);
      }
    } else {
      mergedLines.push(currentLine);
    }
  }

  cleaned = mergedLines.join('\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  // 5. Collapse hapësirat e shumta brenda paragrafëve
  const paragraphs = cleaned.split(/\n\n+/);
  return paragraphs
    .map((p) => p.replace(/[\s\u00A0]+/g, ' ').trim())
    .filter((p) => p.length > 0)
    .join('\n\n');
};

// ═══════════════════════════════════════════════════════════════════════════
// H1 FIX: generateFallbackChunkId ËSHTË HEQUR
// ═══════════════════════════════════════════════════════════════════════════
//
// Arsyeja: funksioni krijonte ID "fake" (p.sh. `chunk_KODI_PENAL_5`) që nuk
// ekzistonte në DB. Përdorej si `article_id` në audit-chat, por backend e
// injoron këtë fushë (V3.0). Ishte dead code + potenciale për bug kur URL
// navigohej me këtë ID.
//
// Nëse një ID fallback është i nevojshëm për ndonjë arsye, krijoje me UUID
// të vërtetë nga `crypto.randomUUID()` — por NUK duhet të përdoret si
// zëvendësim i `chunk_id` nga DB.