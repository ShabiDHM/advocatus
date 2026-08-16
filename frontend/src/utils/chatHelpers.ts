// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V38.0 (CASE-INSENSITIVE UNIVERSAL SUGGESTION EXTRACTOR)

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  // 1. Protect existing markdown links (documents & laws) by placeholders
  const savedLinks: string[] = [];
  let protectedText = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    savedLinks.push(fullMatch);
    return `__MD_LINK_TOKEN_${savedLinks.length - 1}__`;
  });

  // 2. Clean stray brackets around plain law citations like [neni 123] or [neni 145 i LPK]
  protectedText = protectedText.replace(/\[\s*(neni\s+\d+[^\]]*)\s*\]/gi, '$1');

  // 3. Strict Regex for Kosovo statutory citations
  const lawPattern = /\b(?:(Ligji|Kodi)\s+Nr\.\s*[\d\/L\-]+[^\n,.:;()]*|\b(Neni|neni|NENI)\s+(\d+)\s*(?:i|e|të)?\s*(Ligjit\s+të\s+Punës|LPK|LMD|KPRK|KPPRK|LFK|LSHT|Kodi\s+Penal|Kodi\s+Civil|Ligji\s+për\s+Procedurën\s+Kontestimore|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve)?)\b/gi;

  try {
    protectedText = protectedText.replace(lawPattern, (match, lawPrefix, _neniWord, artNum, lawTitle) => {
      let finalLaw = '';
      let finalArticle = '';

      if (lawPrefix) {
        finalLaw = match.trim();
        finalArticle = '1';
      } else if (artNum) {
        finalArticle = artNum.trim();
        finalLaw = (lawTitle || 'Ligji përkatës').trim();
      }

      if (!finalLaw && !finalArticle) return match;

      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(finalLaw)}&articleNumber=${encodeURIComponent(finalArticle || '1')}`;
      return `[${match.trim()}](${targetUrl})`;
    });
  } catch (err) {
    console.error('Law citation autolinking error:', err);
  }

  // 4. Restore protected links
  const restoredText = protectedText.replace(/__MD_LINK_TOKEN_(\d+)__/g, (_, idx) => {
    return savedLinks[Number(idx)] || '';
  });

  return restoredText;
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  // Case-insensitive regex to capture any suggestion header
  const regex = /(?:###?\s*)?(?:sugjerime[^\n:]*|pyetje\s+sugjeruese[^\n:]*|pyetje\s+të\s+sugjeruara[^\n:]*):\s*/i;
  const match = text.match(regex);

  if (match && match.index !== undefined) {
    const markerIndex = match.index;
    const cleanText = text.substring(0, markerIndex).trim();
    let suggestionsPart = text.substring(markerIndex + match[0].length).trim();

    // Strip bottom disclaimer if attached
    const disclaimerIdx = suggestionsPart.search(/(?:---\s*\n)?\s*\*?Kjo analizë ligjore/i);
    if (disclaimerIdx !== -1) {
      suggestionsPart = suggestionsPart.substring(0, disclaimerIdx).trim();
    }

    const questions = suggestionsPart
      .split(/\n+/)
      .map((line) => {
        return line
          .replace(/^\[PILL:\s*/i, '')
          .replace(/\]$/, '')
          .replace(/^\d+[\.\)\-]\s*/, '')
          .replace(/^[-*•]\s*/, '')
          .trim();
      })
      .filter((q) => q.length > 6 && !q.startsWith('---') && !q.startsWith('*'))
      .slice(0, 3);

    return { cleanText, questions };
  }

  return { cleanText: text, questions: [] };
};