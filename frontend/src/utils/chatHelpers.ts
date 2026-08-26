// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V43.0 (CLEAN REGEX MATCHER & ZERO SUBSTRING CORRUPTION)

interface StatuteDefinition {
  regex: RegExp;
  cleanName: string;
}

const STATUTES_REGISTRY: StatuteDefinition[] = [
  {
    regex: /(?:Ligj(?:it|i)?\s+Nr\.?\s*03\/L-052(?:\s+për\s+Prokurorinë\s+Speciale(?:\s+të\s+Republikës\s+së\s+Kosovës)?)?|PSRK)/i,
    cleanName: 'Ligji Nr. 03/L-052 për Prokurorinë Speciale'
  },
  {
    regex: /(?:Kushtetut(?:ës|a)?(?:\s+së\s+Republikës\s+së\s+Kosovës)?)/i,
    cleanName: 'Kushtetuta e Republikës së Kosovës'
  },
  {
    regex: /(?:Konvent(?:ës|a)?\s+Evropiane\s+për\s+të\s+Drejtat\s+e\s+Njeriut|KEDNJ)/i,
    cleanName: 'KEDNJ'
  },
  {
    regex: /(?:Konvent(?:ës|a)?(?:\s+së\s+Kombeve\s+të\s+Bashkuara|\s+së\s+OKB-së)?\s+për\s+të\s+Drejtat\s+e\s+Fëmijës)/i,
    cleanName: 'Konventa për të Drejtat e Fëmijës'
  },
  {
    regex: /(?:KPPRK|Kodi\s+i\s+Procedurës\s+Penale(?:\s+të\s+Republikës\s+së\s+Kosovës)?)/i,
    cleanName: 'KPPRK'
  },
  {
    regex: /(?:KPRK|Kodi\s+Penal(?:\s+i\s+Republikës\s+së\s+Kosovës)?)/i,
    cleanName: 'KPRK'
  },
  {
    regex: /(?:LPK|Ligji\s+për\s+Procedurën\s+Kontestimore)/i,
    cleanName: 'LPK'
  },
  {
    regex: /(?:LMD|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve)/i,
    cleanName: 'LMD'
  },
  {
    regex: /(?:Ligj(?:it|i)?\s+të\s+Punës)/i,
    cleanName: 'Ligji i Punës'
  },
  {
    regex: /(?:LFK|Ligji\s+për\s+Familjen)/i,
    cleanName: 'Ligji për Familjen'
  },
  {
    regex: /(?:LSHT|Ligji\s+për\s+Shoqëritë\s+Tregtare)/i,
    cleanName: 'Ligji për Shoqëritë Tregtare'
  }
];

const resolveStatuteName = (rawLawString: string): string => {
  if (!rawLawString) return 'Ligji përkatës';
  for (const item of STATUTES_REGISTRY) {
    if (item.regex.test(rawLawString)) {
      return item.cleanName;
    }
  }
  return rawLawString.trim() || 'Ligji përkatës';
};

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  // 1. Mbrojmë linket ekzistuese Markdown
  const savedLinks: string[] = [];
  let protectedText = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    savedLinks.push(fullMatch);
    return `__MD_LINK_TOKEN_${savedLinks.length - 1}__`;
  });

  // 2. Pastrojmë kllapat katrore të mbetura gabimisht te nenet
  protectedText = protectedText.replace(/\[\s*(Nen(?:i|et)\s+\d+[^\]]*)\s*\]/gi, '$1');

  // 3. PASS A: Ndarja e grupeve me shumë nene
  // P.sh.: "Nenet 31, 32, 81, 82, 83, 93, 193, 246, 248, 330, 378, 382, 383, 385, 386, 387, 390, 414, 424 dhe 427 të KPRK-së"
  const multiArticleGroupRegex = /\b(Nenet\s+([\d\s,.\-(dhe)(e)]+)\s*(?:i|e|të)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,90}?))(?=[.,;\n\r\)]|$)/gi;

  try {
    protectedText = protectedText.replace(multiArticleGroupRegex, (fullMatch, _p1, numbersBlock, lawCandidate) => {
      const lawName = resolveStatuteName(lawCandidate || fullMatch);
      const rawNumbers = numbersBlock.match(/\b\d+\b/g);

      if (!rawNumbers || rawNumbers.length === 0) return fullMatch;

      // Rendisim numrat nga më i gjati te më i shkurtri për të mos prishur nën-vargjet (p.sh. 424 para 4)
      const sortedNumbers = Array.from(new Set(rawNumbers)).sort((a, b) => b.length - a.length || Number(b) - Number(a));

      let replacedNumbers = numbersBlock;
      for (const num of sortedNumbers) {
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(num)}`;
        const pill = `[Neni ${num}](${targetUrl})`;
        const numRegex = new RegExp(`(?<!\\d)${num}(?!\\d)`, 'g');
        replacedNumbers = replacedNumbers.replace(numRegex, pill);
      }

      return `Nenet ${replacedNumbers} të ${lawName}`;
    });
  } catch (err) {
    console.error('Multi-article parsing error:', err);
  }

  // 4. PASS B: Kapja e Neneve individuale me ose pa paragrafe
  // P.sh.: "Neni 424, paragrafi 1 i KPRK-së", "Neni 9, paragrafi 1 i Ligjit Nr. 03/L-052"
  const singleArticleRegex = /\b(Neni\s+(\d+)(?:,?\s*(?:paragrafi|par\.?)\s*(\d+))?\s*(?:i|e|të)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,80}?))(?=[.,;\n\r\)]|$)/gi;

  try {
    protectedText = protectedText.replace(singleArticleRegex, (fullMatch, _p1, artNum, parNum, lawCandidate) => {
      if (fullMatch.includes('__MD_LINK_TOKEN_') || fullMatch.includes('](')) return fullMatch;

      const lawName = resolveStatuteName(lawCandidate || fullMatch);
      const parLabel = parNum ? `, par. ${parNum}` : '';
      const displayLabel = `Neni ${artNum}${parLabel} (${lawName})`;
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(artNum)}`;

      return `[${displayLabel}](${targetUrl})`;
    });
  } catch (err) {
    console.error('Single article parsing error:', err);
  }

  // 5. PASS C: Kapja e formatit të anasjelltë (p.sh. "KPRK Neni 387")
  const reverseArticleRegex = /\b((?:KPRK|KPPRK|LPK|LMD|Kushtetuta|KEDNJ)\s+Neni\s+(\d+))(?=[.,;\n\r\)\s]|$)/gi;

  try {
    protectedText = protectedText.replace(reverseArticleRegex, (fullMatch, _p1, artNum) => {
      if (fullMatch.includes('__MD_LINK_TOKEN_') || fullMatch.includes('](')) return fullMatch;
      const lawName = resolveStatuteName(fullMatch);
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(artNum)}`;
      return `[${fullMatch}](${targetUrl})`;
    });
  } catch (err) {
    console.error('Reverse article parsing error:', err);
  }

  // 6. Rikthejmë linket e mbrojtura
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