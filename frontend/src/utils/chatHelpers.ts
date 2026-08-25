// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V40.0 (SEAMLESS INLINE LAW MATCHER)

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  // 1. Mbrojmë linket ekzistuese Markdown që vijnë nga backend (p.sh. Dokumentet)
  const savedLinks: string[] = [];
  let protectedText = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    savedLinks.push(fullMatch);
    return `__MD_LINK_TOKEN_${savedLinks.length - 1}__`;
  });

  // 2. Heqim kllapat katrore te neneve të mbetura gabimisht (p.sh. [Neni 424])
  protectedText = protectedText.replace(/\[\s*(Neni\s+\d+[^\]]*)\s*\]/gi, '$1');

  // 3. Kapja Inteligjente e Neneve (p.sh. "Neni 244 par. 1 i KPPRK", "Nenet 424 dhe 427 të KPRK")
  // Ky regex kap të gjithë bllokun si një fjali të vetme.
  const lawPattern = /\b((?:Nen(?:i|et))\s+[\d\.,\s(dhe)(e)(par)(paragrafi)\-]+\s*(?:i|e|të)?\s*(?:Ligjit\s+të\s+Punës|LPK|LMD|KPRK|KPPRK|LFK|LSHT|Kodi\s+Penal|Kodi\s+Civil|Ligji\s+për\s+Procedurën\s+Kontestimore|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve)?)\b/gi;

  try {
    protectedText = protectedText.replace(lawPattern, (match) => {
      const cleanMatch = match.replace(/[\n\r]+/g, ' ').trim();
      
      // Ekstraktojmë numrin e parë që gjejmë për ta dërguar te linku
      const firstNumMatch = cleanMatch.match(/\d+/);
      const articleNumber = firstNumMatch ? firstNumMatch[0] : '1';
      
      // Ekstraktojmë emrin e ligjit (p.sh. "KPRK", "LPK", "LMD")
      let lawTitle = 'Ligji përkatës';
      const knownLaws = ['LPK', 'KPRK', 'KPPRK', 'LMD', 'LFK', 'LSHT', 'Kodi Penal', 'Kodi Civil'];
      for (const kl of knownLaws) {
        if (cleanMatch.toUpperCase().includes(kl.toUpperCase())) {
          lawTitle = kl;
          break;
        }
      }

      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNumber)}`;
      return `[${cleanMatch}](${targetUrl})`;
    });
  } catch (err) {
    console.error('Law citation autolinking error:', err);
  }

  // 4. Rikthejmë linket e mbrojtura të dokumenteve
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
      .slice(0, 4);

    return { cleanText, questions };
  }

  return { cleanText: text, questions: [] };
};