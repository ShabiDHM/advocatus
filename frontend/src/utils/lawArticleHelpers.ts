// FILE: src/utils/lawArticleHelpers.ts
// PHOENIX PROTOCOL - LAW ARTICLE HELPERS V38.0 (UNICODE WHITESPACE COLLAPSE FIX)

export const normalizeText = (raw: string, _articleNum?: string): string => {
  if (!raw) return '';

  let cleaned = raw;

  // 1. Convert all non-breaking spaces and Unicode wide spaces to standard ASCII spaces
  cleaned = cleaned.replace(/[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]/g, ' ');

  // Strip OCR page markers & headers
  cleaned = cleaned.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');
  cleaned = cleaned.replace(/GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/FLETORJA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+SHQIPËRISË.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/==Start of OCR for page \d+==/gi, '');
  cleaned = cleaned.replace(/==End of OCR for page \d+==/gi, '');
  cleaned = cleaned.replace(/==Screenshot for page \d+==/gi, '');
  cleaned = cleaned.replace(/^\s*\d{1,3}\s*$/gm, '');

  // Remove redundant "Neni X"
  const cleanNumStr = (_articleNum || '').replace(/\.$/, '').trim();
  if (cleanNumStr) {
    const redundantNeniRegex = new RegExp(`^\\s*(?:Neni|NENI)\\s+${cleanNumStr}\\b[:\\.\\-]*\\s*`, 'i');
    cleaned = cleaned.replace(redundantNeniRegex, '');
  }

  // Unwrap mid-sentence hard line breaks
  const lines = cleaned.split('\n');
  const mergedLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const currentLine = lines[i].replace(/[ \t]{2,}/g, ' ').trim();
    if (!currentLine) {
      mergedLines.push('');
      continue;
    }

    if (mergedLines.length > 0 && mergedLines[mergedLines.length - 1] !== '') {
      const lastIdx = mergedLines.length - 1;
      const previousLine = mergedLines[lastIdx];
      const endsWithPunctuation = /[.:;?!]$/.test(previousLine);
      const isNumberedItem = /^\d+\.|\(\d+\)|^[a-z]\)/i.test(currentLine);

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

  // 2. Collapse all multiple spaces inside paragraphs
  const paragraphs = cleaned.split(/\n\n+/);
  return paragraphs
    .map((p) => p.replace(/[\s\u00A0]+/g, ' ').trim())
    .filter((p) => p.length > 0)
    .join('\n\n');
};

export const generateFallbackChunkId = (lawTitle: string, articleNumber: string): string => {
  const cleanTitle = lawTitle.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 80);
  const cleanArticle = articleNumber.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
  return `chunk_${cleanTitle}_${cleanArticle}`;
};