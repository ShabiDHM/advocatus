// FILE: src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V47.0 (BULLETPROOF COMMONMARK LAW LINK SYNTAX & ZERO-FAIL CITATIONS)

interface StatuteDefinition {
  regex: RegExp;
  cleanName: string;
}

const STATUTES_REGISTRY: StatuteDefinition[] = [
  {
    regex: /(?:Ligj(?:it|i)?\s+Nr\.?\s*(?:08\/L-168|03\/L-121|03\/L-052)(?:\s+për\s+Prokurorinë\s+Speciale)?|PSRK)/i,
    cleanName: 'Ligji Nr. 03/L-121 për Prokurorinë Speciale'
  },
  {
    regex: /(?:Kushtetut(?:ës|a|ën)?(?:\s+së\s+Republikës\s+së\s+Kosovës)?)/i,
    cleanName: 'Kushtetuta e Republikës së Kosovës'
  },
  {
    regex: /(?:Konvent(?:ës|a)?\s+Evropiane\s+për\s+të\s+Drejtat\s+e\s+Njeriut|KEDNJ)/i,
    cleanName: 'KEDNJ'
  },
  {
    regex: /(?:Konvent(?:ës|a)?(?:\s+së\s+Kombeve\s+të\s+Bashkuara|\s+së\s+OKB-së)?\s+për\s+të\s+Drejtat\s+e\s+Fëmijës|KEDF)/i,
    cleanName: 'Konventa për të Drejtat e Fëmijës'
  },
  {
    regex: /(?:KPPRK|KPP|Kodi\s+i\s+Procedurës\s+Penale(?:\s+të\s+Republikës\s+së\s+Kosovës)?)/i,
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
    regex: /(?:LMDHF|Ligji\s+për\s+Mbrojtjen?\s+nga\s+Dhuna\s+në\s+Familje)/i,
    cleanName: 'Ligji për Mbrojtjen nga Dhuna në Familje'
  },
  {
    regex: /(?:LMD|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve)/i,
    cleanName: 'LMD'
  },
  {
    regex: /(?:LFK|LF|Ligji\s+për\s+Familjen)/i,
    cleanName: 'Ligji për Familjen'
  },
  {
    regex: /(?:LSHT|Ligji\s+për\s+Shoqëritë\s+Tregtare)/i,
    cleanName: 'Ligji për Shoqëritë Tregtare'
  },
  {
    regex: /(?:Ligj(?:it|i)?\s+të\s+Punës)/i,
    cleanName: 'Ligji i Punës'
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

  // 1. Mbrojmë linket ekzistuese Markdown
  let processed = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    return createToken(fullMatch);
  });

  // 2. Skanimi rresht për rresht me Context-Aware Law Memory
  const lines = processed.split('\n');
  let activeSectionLaw = 'KPRK';

  const processedLines = lines.map((line) => {
    // A. Përditësojmë ligjin aktiv të seksionit nëse hasim një titull ligji
    for (const statute of STATUTES_REGISTRY) {
      if (statute.regex.test(line)) {
        activeSectionLaw = statute.cleanName;
        break;
      }
    }

    let lineProcessed = line;

    // B. PASS 1: Nenet me ligj të shprehur në të njëjtin rresht (p.sh. "Nenet 31 dhe 32 të KPRK-së", "Neni 6 KEDNJ", "Neni 31 Kushtetutës")
    const explicitLawRegex = /\b(Nenet?)\s+([\d\s,.\-(dhe)(e)]+)\s*(?:i|e|të)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,40}?)(?=[.,;\n\r\)]|$)/gi;
    try {
      lineProcessed = lineProcessed.replace(explicitLawRegex, (fullMatch, prefix, numbersBlock, lawCandidate) => {
        if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
        const matchedLaw = resolveStatuteName(lawCandidate);
        if (!matchedLaw) return fullMatch;

        const rawNumbers = numbersBlock.match(/\b\d+\b/g);
        if (!rawNumbers || rawNumbers.length === 0) return fullMatch;

        const linkedParts = rawNumbers.map((num: string) => {
          const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(matchedLaw)}&articleNumber=${encodeURIComponent(num)}`;
          return createToken(`[Neni ${num}](${targetUrl})`);
        });

        return `${prefix} ${linkedParts.join(', ')} të ${matchedLaw}`;
      });
    } catch (e) {
      console.warn('Explicit law link error:', e);
    }

    // C. PASS 2: Nenet e vetmuara (p.sh. "Neni 424 (Ushtrimi i ndikimit)", "Neni 425", "Neni 103")
    // Këtu vendosim vetëm numrin brenda kllapave katrore për të mos thyer sintaksën e Markdown!
    const standaloneArticleRegex = /\b(Neni\s+(\d+[a-zA-Z]?))(?:\s*\(([^)]+)\))?/gi;
    try {
      lineProcessed = lineProcessed.replace(standaloneArticleRegex, (fullMatch, _p1, artNum, parenText) => {
        if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;

        const detectedLawFromParen = parenText ? resolveStatuteName(parenText) : '';
        const lawToUse = detectedLawFromParen || activeSectionLaw || 'KPRK';

        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawToUse)}&articleNumber=${encodeURIComponent(artNum)}`;
        const token = createToken(`[Neni ${artNum}](${targetUrl})`);

        return parenText ? `${token} (${parenText})` : token;
      });
    } catch (e) {
      console.warn('Standalone article link error:', e);
    }

    return lineProcessed;
  });

  processed = processedLines.join('\n');

  // 3. Rikthimi i tokenave të mbrojtur
  let restored = processed;
  for (let i = savedTokens.length - 1; i >= 0; i--) {
    restored = restored.replace(new RegExp(`___LAW_TOKEN_${i}___`, 'g'), savedTokens[i]);
  }

  return restored;
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  const markerRegex = /(?:\n|^)(?:#{1,4}\s*)?(?:Sugjerime(?:\s+për\s+hapat\s+e\s+ardhshëm)?|Pyetje\s+sugjeruese|Pyetje\s+për\s+hapat\s+e\s+ardhshëm|Hapat\s+e\s+Ardhshëm\s+të\s+Sugjeruar)\s*:?/i;

  const match = text.match(markerRegex);

  if (match && match.index !== undefined) {
    const markerIndex = match.index;
    const cleanText = text.substring(0, markerIndex).trim();
    let suggestionsPart = text.substring(markerIndex + match[0].length).trim();

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