// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V39.0 (MULTI-ARTICLE AWARE LAW LINKER)

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  // 1. Protect existing markdown links (documents & laws) by placeholders
  const savedLinks: string[] = [];
  let protectedText = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    savedLinks.push(fullMatch);
    return `__MD_LINK_TOKEN_${savedLinks.length - 1}__`;
  });

  // 2. Clean stray brackets around plain law citations
  protectedText = protectedText.replace(/\[\s*(neni\s+\d+[^\]]*)\s*\]/gi, '$1');

  // 3. Strict Regex for Single and Multi-Article Kosovo statutory citations
  // Kap shembuj si: "Neni 12 i LPK", "Nenet 424 dhe 427 të KPRK", "Neni 30, 31 dhe 32 të LMD"
  const lawPattern = /\b(?:(Nen(?:i|et))\s+(\d+(?:\s*(?:,|dhe|e)\s*\d+)*)\s*(?:i|e|të)?\s*(Ligjit\s+të\s+Punës|LPK|LMD|KPRK|KPPRK|LFK|LSHT|Kodi\s+Penal|Kodi\s+Civil|Ligji\s+për\s+Procedurën\s+Kontestimore|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve)?)\b/gi;

  try {
    protectedText = protectedText.replace(lawPattern, (match, prefix, numbersStr, lawTitle) => {
      const finalLaw = (lawTitle || 'Ligji përkatës').trim();
      
      // Split the numbers string to link them individually (e.g. "424 dhe 427" -> ["424", "427"])
      const individualNumbers = numbersStr.split(/(?:,|dhe|e)/i).map((n: string) => n.trim()).filter(Boolean);
      
      if (individualNumbers.length === 0) return match;

      let linkedText = prefix + ' ';
      individualNumbers.forEach((artNum: string, idx: number) => {
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(finalLaw)}&articleNumber=${encodeURIComponent(artNum)}`;
        linkedText += `[${artNum}](${targetUrl})`;
        
        // Restore formatting (commas or "dhe")
        if (idx < individualNumbers.length - 2) {
          linkedText += ', ';
        } else if (idx === individualNumbers.length - 2) {
          linkedText += ' dhe ';
        }
      });

      if (lawTitle) {
        linkedText += ` të ${lawTitle}`;
      }

      return linkedText;
    });
  } catch (err) {
    console.error('Law citation autolinking error:', err);
  }

  // 4. Fallback for "Ligji Nr. 03/L-..."
  const fullLawPattern = /\b((?:Ligji|Kodi)\s+Nr\.\s*[\d\/L\-]+[^\n,.:;()]*)\b/gi;
  try {
    protectedText = protectedText.replace(fullLawPattern, (match, fullLawTitle) => {
      if (match.includes('__MD_LINK_TOKEN_')) return match;
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(fullLawTitle.trim())}&articleNumber=1`;
      return `[${match.trim()}](${targetUrl})`;
    });
  } catch (err) {
    console.error('Full Law citation error:', err);
  }

  // 5. Restore protected links
  const restoredText = protectedText.replace(/__MD_LINK_TOKEN_(\d+)__/g, (_, idx) => {
    return savedLinks[Number(idx)] || '';
  });

  return restoredText;
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  const markers = [
    'Sugjerime:',
    'Sugjerimet:',
    '### Sugjerime:',
    '### Sugjerimet:',
    'Sugjerime për hapat e ardhshëm:',
    'PYETJE SUGJERUESE:',
    'Pyetje Sugjeruese',
  ];

  let markerIndex = -1;
  let chosenMarkerLength = 0;

  for (const marker of markers) {
    const idx = text.lastIndexOf(marker);
    if (idx !== -1 && idx > markerIndex) {
      markerIndex = idx;
      chosenMarkerLength = marker.length;
    }
  }

  if (markerIndex !== -1) {
    const cleanText = text.substring(0, markerIndex).trim();
    let suggestionsPart = text.substring(markerIndex + chosenMarkerLength).trim();

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
      .slice(0, 4); // Lejon deri në 4 sugjerime

    return { cleanText, questions };
  }

  return { cleanText: text, questions: [] };
};