// FILE: src/utils/chatHelpers.ts

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  const universalLawRegex = /(?:((?:Ligji|Ligjit|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.:;]*?)(?:,?\s*(?:Neni|neni|NENI)\s+(\d+))?)|(?:(?:Neni|neni|NENI)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)[^\n,.:;]*|LPK|LMD|LIDK|Kodi Penal|Kodi Civil)?)/gi;

  try {
    return text.replace(universalLawRegex, (match, fullLawTitle, art1, art2, shortLawTitle) => {
      if (match.startsWith('[') && match.includes('](')) return match;

      let lawTitle = '';
      let articleNum = '';

      if (fullLawTitle) {
        lawTitle = fullLawTitle.trim();
        articleNum = art1 ? art1.trim() : '1';
      } else if (art2) {
        articleNum = art2.trim();
        lawTitle = shortLawTitle ? shortLawTitle.trim() : 'Ligji përkatës';
      }

      if (!lawTitle) return match;

      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;
      return `[${match.trim()}](${targetUrl})`;
    });
  } catch (err) {
    console.error('Universal law linking failed:', err);
    return String(text);
  }
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  const marker = 'Sugjerime:';
  const markerIndex = text.lastIndexOf(marker);
  if (markerIndex !== -1) {
    const cleanText = text.substring(0, markerIndex).trim();
    const suggestionsPart = text.substring(markerIndex + marker.length);
    const questions = suggestionsPart
      .split(/\n/)
      .map((line) => line.replace(/^\d+[\.\)\-]\s*/, '').trim())
      .filter((q) => q.length > 5 && q.endsWith('?'))
      .slice(0, 3);
    return { cleanText, questions };
  }
  return { cleanText: text, questions: [] };
};