// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V45.0 (ROBUST CITATION LINKER & UNIVERSAL CLICKABLE SUGGESTIONS PARSER)

interface StatuteDefinition {
  regex: RegExp;
  cleanName: string;
}

const STATUTES_REGISTRY: StatuteDefinition[] = [
  {
    regex: /(?:Ligj(?:it|i)?\s+Nr\.?\s*03\/L-121(?:\s+për\s+Prokurorinë\s+Speciale(?:\s+të\s+Republikës\s+së\s+Kosovës)?)?|PSRK)/i,
    cleanName: 'Ligji Nr. 03/L-121 për Prokurorinë Speciale'
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
  if (!rawLawString) return '';
  for (const item of STATUTES_REGISTRY) {
    if (item.regex.test(rawLawString)) {
      return item.cleanName;
    }
  }
  return '';
};

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  const savedTokens: string[] = [];

  const createToken = (markdownLink: string): string => {
    savedTokens.push(markdownLink);
    return `___LAW_TOKEN_${savedTokens.length - 1}___`;
  };

  // 1. Mbrojmë linket ekzistuese Markdown dhe bllokun e kodeve
  let processed = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    return createToken(fullMatch);
  });

  // 2. PASS A: Nenet me ligje eksplicite (p.sh. "Neni 390 i KPRK-së", "Neni 424 të KPRK", "Nenet 31 dhe 32 të KPRK-së")
  const articleWithLawRegex = /\b(Nenet?)\s+([\d\s,.\-(dhe)(e)]+)\s*(?:i|e|të)?\s*(KPRK|KPPRK|LPK|LMD|LFK|LSHT|Kushtetutës|KEDNJ|Ligjit\s+Nr\.\s*03\/L-121)/gi;

  try {
    processed = processed.replace(articleWithLawRegex, (fullMatch, prefix, numbersBlock, lawAbbr) => {
      const lawName = resolveStatuteName(lawAbbr);
      if (!lawName) return fullMatch;

      const rawNumbers = numbersBlock.match(/\b\d+\b/g);
      if (!rawNumbers || rawNumbers.length === 0) return fullMatch;

      const linkedParts = rawNumbers.map((num: string) => {
        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(num)}`;
        return `[Neni ${num}](${targetUrl})`;
      });

      return `${prefix} ${linkedParts.join(', ')} të ${lawName}`;
    });
  } catch (err) {
    console.error('Article with Law parsing error:', err);
  }

  // 3. PASS B: Format i thjeshtë me kllapa (p.sh. "Neni 424 (Ushtrimi i ndikimit)") pa prishur kllapat
  const simpleArticleRegex = /\bNeni\s+(\d+)\s*\(([^)]+)\)/gi;

  try {
    processed = processed.replace(simpleArticleRegex, (fullMatch, artNum, titleInsideParen) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
      const detectedLaw = resolveStatuteName(titleInsideParen);
      const lawTitle = detectedLaw || 'KPRK';
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(artNum)}`;
      return `[Neni ${artNum} (${titleInsideParen})](${targetUrl})`;
    });
  } catch (err) {
    console.error('Simple article parsing error:', err);
  }

  // 4. RIKTHIMI I TOKENAVE TË MBROJTUR
  let restored = processed;
  for (let i = savedTokens.length - 1; i >= 0; i--) {
    restored = restored.replace(new RegExp(`___LAW_TOKEN_${i}___`, 'g'), savedTokens[i]);
  }

  return restored;
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  // Case-Insensitive Universal Marker Regex
  const markerRegex = /(?:\n|^)(?:#{1,4}\s*)?(?:Sugjerime(?:\s+për\s+hapat\s+e\s+ardhshëm)?|Pyetje\s+sugjeruese|Pyetje\s+për\s+hapat\s+e\s+ardhshëm)\s*:?/i;

  const match = text.match(markerRegex);

  if (match && match.index !== undefined) {
    const markerIndex = match.index;
    const cleanText = text.substring(0, markerIndex).trim();
    let suggestionsPart = text.substring(markerIndex + match[0].length).trim();

    // Pastrojmë disclaimer-in ligjor nga fundi nëse ekziston
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
      .filter((q) => q.length > 5 && !q.startsWith('---') && !q.startsWith('*'))
      .slice(0, 4);

    return { cleanText, questions };
  }

  return { cleanText: text, questions: [] };
};