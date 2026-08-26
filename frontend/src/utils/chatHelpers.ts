// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V44.0 (COLLISION-IMMUNE TOKEN REGISTRY & PERFECT INLINE CITATION LINKING)

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
    regex: /(?:KPRK|KPK|Kodi\s+Penal(?:\s+i\s+Republikës\s+së\s+Kosovës)?)/i,
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

  const savedTokens: string[] = [];

  const createToken = (markdownLink: string): string => {
    savedTokens.push(markdownLink);
    return `__LAW_TOKEN_${savedTokens.length - 1}__`;
  };

  // 1. Mbrojmë linket ekzistuese Markdown
  let processed = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    return createToken(fullMatch);
  });

  // 2. Pastrojmë kllapat katrore të mbetura gabimisht te nenet
  processed = processed.replace(/\[\s*(Nen(?:i|et)\s+\d+[^\]]*)\s*\]/gi, '$1');

  // 3. PASS A: Grupet me shumë nene të njëpasnjëshme (p.sh. "Nenet 31, 32, 81 dhe 427 të KPRK-së")
  const multiArticleRegex = /\b(Nenet\s+([\d\s,.\-(dhe)(e)]+)\s*(?:i|e|të)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,80}?))(?=[.,;\n\r\)]|$)/gi;

  try {
    processed = processed.replace(multiArticleRegex, (fullMatch, _p1, numbersBlock, lawCandidate) => {
      if (fullMatch.includes('__LAW_TOKEN_')) return fullMatch;

      const lawName = resolveStatuteName(lawCandidate || fullMatch);
      const rawNumbers = numbersBlock.match(/\b\d+\b/g);

      if (!rawNumbers || rawNumbers.length === 0) return fullMatch;

      const uniqueNumbers: string[] = Array.from(new Set<string>(rawNumbers));
      const sortedNumbers: string[] = uniqueNumbers.sort((a: string, b: string) => b.length - a.length || Number(b) - Number(a));

      let replacedNumbers = numbersBlock;
      for (const num of sortedNumbers) {
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(num)}`;
        const token = createToken(`[Neni ${num}](${targetUrl})`);
        const numRegex = new RegExp(`(?<!\\d)${num}(?!\\d)`, 'g');
        replacedNumbers = replacedNumbers.replace(numRegex, token);
      }

      return `Nenet ${replacedNumbers} të ${lawName}`;
    });
  } catch (err) {
    console.error('Multi-article parsing error:', err);
  }

  // 4. PASS B: Nenet individuale me ose pa paragrafe (p.sh. "Neni 424, paragrafi 1 i KPRK-së", "Neni 383 (KPRK)")
  const singleArticleRegex = /\b(Neni\s+(\d+)(?:,?\s*(?:paragrafi|par\.?)\s*(\d+))?(?:\s*\(([^)]+)\))?\s*(?:i|e|të)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,70}?))(?=[.,;\n\r\)]|$)/gi;

  try {
    processed = processed.replace(singleArticleRegex, (fullMatch, _p1, artNum, parNum, parenContent, lawCandidate) => {
      if (fullMatch.includes('__LAW_TOKEN_')) return fullMatch;

      const detectedRaw = lawCandidate || parenContent || fullMatch;
      const lawName = resolveStatuteName(detectedRaw);
      const parLabel = parNum ? `, par. ${parNum}` : '';
      const displayLabel = `Neni ${artNum}${parLabel} (${lawName})`;
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(artNum)}`;

      return createToken(`[${displayLabel}](${targetUrl})`);
    });
  } catch (err) {
    console.error('Single article parsing error:', err);
  }

  // 5. PASS C: Formati i anasjelltë (p.sh. "KPRK Neni 387")
  const reverseArticleRegex = /\b((?:KPRK|KPPRK|LPK|LMD|Kushtetuta|KEDNJ)\s+Neni\s+(\d+))(?=[.,;\n\r\)\s]|$)/gi;

  try {
    processed = processed.replace(reverseArticleRegex, (fullMatch, _p1, artNum) => {
      if (fullMatch.includes('__LAW_TOKEN_')) return fullMatch;
      const lawName = resolveStatuteName(fullMatch);
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(artNum)}`;
      return createToken(`[${fullMatch}](${targetUrl})`);
    });
  } catch (err) {
    console.error('Reverse article parsing error:', err);
  }

  // 6. RIKTHIMI I TOKENAVE TË IZOLUAR (Zero Përplasje & Zero Korruptim Teksti)
  let restored = processed;
  for (let i = savedTokens.length - 1; i >= 0; i--) {
    restored = restored.replace(new RegExp(`__LAW_TOKEN_${i}__`, 'g'), savedTokens[i]);
  }

  return restored;
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