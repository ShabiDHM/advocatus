// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V41.0 (INDIVIDUAL LAW ARTICLE SPLITTER & EXHAUSTIVE STATUTE RECOGNITION)

const KNOWN_STATUTES = [
  { pattern: /(?:Ligj(?:it|i)?\s+Nr\.?\s*03\/L-052(?:\s+për\s+Prokurorinë\s+Speciale(?:\s+të\s+Republikës\s+së\s+Kosovës)?)?|PSRK)/i, name: 'Ligji Nr. 03/L-052 për Prokurorinë Speciale' },
  { pattern: /(?:Kushtetut(?:ës|a)?(?:\s+së\s+Republikës\s+së\s+Kosovës)?)/i, name: 'Kushtetuta e Republikës së Kosovës' },
  { pattern: /(?:Konvent(?:ës|a)?\s+Evropiane\s+për\s+të\s+Drejtat\s+e\s+Njeriut|KEDNJ)/i, name: 'KEDNJ' },
  { pattern: /(?:Konvent(?:ës|a)?(?:\s+së\s+Kombeve\s+të\s+Bashkuara|\s+së\s+OKB-së)?\s+për\s+të\s+Drejtat\s+e\s+Fëmijës)/i, name: 'Konventa për të Drejtat e Fëmijës' },
  { pattern: /(?:KPPRK|Kodi\s+i\s+Procedurës\s+Penale)/i, name: 'KPPRK' },
  { pattern: /(?:KPRK|Kodi\s+Penal)/i, name: 'KPRK' },
  { pattern: /(?:LPK|Ligji\s+për\s+Procedurën\s+Kontestimore)/i, name: 'LPK' },
  { pattern: /(?:LMD|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve)/i, name: 'LMD' },
  { pattern: /(?:Ligj(?:it|i)?\s+të\s+Punës)/i, name: 'Ligji i Punës' },
  { pattern: /(?:LFK|Ligji\s+për\s+Familjen)/i, name: 'Ligji për Familjen' },
  { pattern: /(?:LSHT|Ligji\s+për\s+Shoqëritë\s+Tregtare)/i, name: 'Ligji për Shoqëritë Tregtare' }
];

const detectLawTitle = (contextSnippet: string): string => {
  for (const stat of KNOWN_STATUTES) {
    if (stat.pattern.test(contextSnippet)) {
      return stat.name;
    }
  }
  return 'Ligji përkatës';
};

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  // 1. Mbrojmë linket ekzistuese Markdown
  const savedLinks: string[] = [];
  let protectedText = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    savedLinks.push(fullMatch);
    return `__MD_LINK_TOKEN_${savedLinks.length - 1}__`;
  });

  // 2. Pastrojmë kllapat katrore të mbetura gabimisht
  protectedText = protectedText.replace(/\[\s*(Nen(?:i|et)\s+\d+[^\]]*)\s*\]/gi, '$1');

  // 3. RAPORT I PLOTË I NENEVE DHE LIGJEVE (Kapje Inteligjente dhe Ndarje Individuale)
  // Shembuj: "Nenet 31, 32, 81 dhe 427 të KPRK-së", "Neni 424, paragrafi 1 i KPRK-së", "Neni 9, paragrafi 1 i Ligjit Nr. 03/L-052"
  const multiArticlePattern = /\b((?:Nenet|Neni)\s+([\d\s,.\-(dhe)(e)(par)(paragrafi)]+)\s*(?:i|e|të)?\s*([A-Za-z0-9\/\-ëçËÇ\s]{2,80}?))(?=[.,;\n\r\)\s]|$)/gi;

  try {
    protectedText = protectedText.replace(multiArticlePattern, (fullMatch, _p1, numbersBlock, trailingLaw) => {
      // Gjejmë ligjin
      const lawTitle = detectLawTitle(`${fullMatch} ${trailingLaw}`);
      
      // Nxirr të gjithë numrat e neneve
      const numbers = numbersBlock.match(/\b\d+\b/g);
      if (!numbers || numbers.length === 0) {
        return fullMatch;
      }

      // Nëse është një nen i vetëm (p.sh. "Neni 424, par. 1 i KPRK-së")
      if (numbers.length === 1) {
        const artNum = numbers[0];
        const cleanDisplay = fullMatch.replace(/\s+/g, ' ').trim();
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(artNum)}`;
        return `[${cleanDisplay}](${targetUrl})`;
      }

      // Nëse ka shumë nene të listuara (p.sh. "Nenet 31, 32, 81, 82, 83... dhe 427 të KPRK-së")
      // I ndajmë në butona individualë të veçantë që të mos dalin kurrë jashtë kutisë!
      let replacedNumbersBlock = numbersBlock;
      for (const num of numbers) {
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(num)}`;
        const singlePill = `[Neni ${num}](${targetUrl})`;
        const regexForNum = new RegExp(`\\b${num}\\b`, 'g');
        replacedNumbersBlock = replacedNumbersBlock.replace(regexForNum, singlePill);
      }

      return `Nenet ${replacedNumbersBlock} ${trailingLaw ? trailingLaw.trim() : ''}`.replace(/\s+/g, ' ');
    });
  } catch (err) {
    console.error('Law citation autolinking error:', err);
  }

  // 4. Rikthejmë linket e mbrojtura
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