// FILE: frontend/src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V70.0 (UNIVERSAL STATUTE & SUPREME PRECEDENT 1-CLICK LINKER)

interface StatuteDefinition {
  regex: RegExp;
  cleanName: string;
}

const STATUTES_REGISTRY: StatuteDefinition[] = [
  {
    regex: /(?:Kodi\s+i\s+Procedurës\s+Penale(?:\s+të\s+Republikës\s+së\s+Kosovës)?|KPPRK|KPP|Ligj(?:it|i)?\s+Nr\.?\s*08\/L-032)/i,
    cleanName: 'KPPRK'
  },
  {
    regex: /(?:Kodi\s+Penal(?:\s+i\s+Republikës\s+së\s+Kosovës)?|KPRK|KPK|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-074)/i,
    cleanName: 'KPRK'
  },
  {
    regex: /(?:Ligji\s+për\s+Procedurën\s+Kontestimore|LPK|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-006)/i,
    cleanName: 'LPK'
  },
  {
    regex: /(?:Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve|LMD|Ligj(?:it|i)?\s+Nr\.?\s*04\/L-077)/i,
    cleanName: 'LMD'
  },
  {
    regex: /(?:Ligji\s+për\s+Familjen(?:\s+i\s+Kosovës)?|LFK|LF|Ligj(?:it|i)?\s+Nr\.?\s*2004\/32)/i,
    cleanName: 'Ligji për Familjen'
  },
  {
    regex: /(?:Kushtetut(?:ës|a|ën)?(?:\s+së\s+Republikës\s+së\s+Kosovës)?)/i,
    cleanName: 'Kushtetuta e Republikës së Kosovës'
  },
  {
    regex: /(?:Ligj(?:it|i)?\s+Nr\.?\s*(?:08\/L-168|03\/L-121|03\/L-052)(?:\s+për\s+Prokurorinë\s+Speciale)?|PSRK)/i,
    cleanName: 'Ligji për Prokurorinë Speciale'
  },
  {
    regex: /(?:Kodi\s+i\s+Drejtësisë\s+për\s+të\s+Mitur|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-006|KDPM)/i,
    cleanName: 'Kodi i Drejtësisë për të Mitur'
  },
  {
    regex: /(?:Konvent(?:ës|a)?\s+Evropiane\s+për\s+të\s+Drejtat\s+e\s+Njeriut|KEDNJ|GJEDNJ)/i,
    cleanName: 'KEDNJ'
  },
  {
    regex: /(?:Konvent(?:ës|a)?(?:\s+së\s+Kombeve\s+të\s+Bashkuara|\s+së\s+OKB-së)?\s+për\s+të\s+Drejtat\s+e\s+Fëmijës|KEDF)/i,
    cleanName: 'Konventa për të Drejtat e Fëmijës'
  },
  {
    regex: /(?:Ligji\s+për\s+Procedurën\s+Përmbarimore|LPP|Ligj(?:it|i)?\s+Nr\.?\s*04\/L-139)/i,
    cleanName: 'Ligji për Procedurën Përmbarimore'
  },
  {
    regex: /(?:Ligji\s+për\s+Parandalimin\s+dhe\s+Mbrojtjen\s+nga\s+Dhuna\s+në\s+Familje|LMDHF|Ligj(?:it|i)?\s+Nr\.?\s*08\/L-185|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-182)/i,
    cleanName: 'Ligji për Mbrojtjen nga Dhuna në Familje'
  },
  {
    regex: /(?:Ligji\s+për\s+Shoqëritë\s+Tregtare|LSHT|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-016)/i,
    cleanName: 'Ligji për Shoqëritë Tregtare'
  },
  {
    regex: /(?:Ligji\s+i\s+Punës|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-212)/i,
    cleanName: 'Ligji i Punës'
  },
  {
    regex: /(?:Ligji\s+për\s+Gjykatën\s+Komerciale|Ligj(?:it|i)?\s+Nr\.?\s*08\/L-015)/i,
    cleanName: 'Ligji për Gjykatën Komerciale'
  },
  {
    regex: /(?:Ligji\s+për\s+Pronësinë|LPTS|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-154)/i,
    cleanName: 'Ligji për Pronësinë dhe të Drejtat Tjera Sendore'
  }
];

export const resolveStatuteName = (rawLawString: string): string => {
  if (!rawLawString) return '';
  for (const item of STATUTES_REGISTRY) {
    if (item.regex.test(rawLawString)) {
      return item.cleanName;
    }
  }
  return '';
};

const createLinkedNumbers = (numbersBlock: string, lawName: string, createToken: (link: string) => string): string => {
  if (!numbersBlock || !lawName) return numbersBlock;

  // Lidh intervalet e neneve (p.sh. 31-35 ose 31–35)
  let processed = numbersBlock.replace(/(\b\d+[a-zA-Z]?)\s*[\-–]\s*(\b\d+[a-zA-Z]?)/g, (_m, n1, n2) => {
    const url1 = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(n1)}`;
    const url2 = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(n2)}`;
    const t1 = createToken(`[Neni ${n1}](${url1})`);
    const t2 = createToken(`[Neni ${n2}](${url2})`);
    return `${t1}–${t2}`;
  });

  // Lidh çdo numër të veçantë në listë (p.sh. 31, 32, 81, 93)
  processed = processed.replace(/\b\d+[a-zA-Z]?\b/g, (num) => {
    const url = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(num)}`;
    return createToken(`[Neni ${num}](${url})`);
  });

  return processed;
};

const stripFakeSignatures = (rawText: string): string => {
  if (!rawText) return '';
  let cleaned = rawText;
  cleaned = cleaned.replace(/\[\s*NËN[ËE]SHKRIMI[^\n\]]*\][\s\S]*?(?=(?:---\s*)?(?:⚖️\s*)?\*?\*?KLAUZOLË|\n\nSugjerime|$)/gi, '');
  cleaned = cleaned.replace(/(?:J\.D\.|\[Emri\s+i\s+Gjyqtarit[^\]]*\]|Kolegji\s+(?:Penal|Civil|i\s+Gjyqtarëve)\s+i\s+Gjykatës\s+Supreme[^\n]*|⚖️\s*Nënshkruar\s+nga[^\n]*)[\s\S]*?(?=(?:---\s*)?(?:⚖️\s*)?\*?\*?KLAUZOLË|\n\nSugjerime|$)/gi, '');
  return cleaned.trim();
};

export const autoLinkLegalCitations = (text: any): string => {
  if (!text || typeof text !== 'string') return '';

  const savedTokens: string[] = [];

  const createToken = (markdownLink: string): string => {
    savedTokens.push(markdownLink);
    return `___LAW_TOKEN_${savedTokens.length - 1}___`;
  };

  // Mbroj lidhjet ekzistuese të markdown-it
  let processed = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (fullMatch) => {
    return createToken(fullMatch);
  });

  const lines = processed.split('\n');
  let activeSectionLaw = 'KPRK';

  const processedLines = lines.map((line) => {
    let lineProcessed = line;

    // PASS 0: PRECEDENTËT E GJYKATËS SUPREME (p.sh. PML.Nr.85/2025, Rev.Nr.142/2022, AC.nr.12/24)
    const supremePrecedentRegex = /\b(PML|Rev|AC|CA|PKR|AP|AGJ)\.?\s*(?:Nr\.?|nr\.?)\s*(\d+\/\d{2,4})\b/gi;
    lineProcessed = lineProcessed.replace(supremePrecedentRegex, (fullMatch, prefix, numPair) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
      const cleanCaseNo = `${prefix.toUpperCase()}.Nr.${numPair}`;
      const url = `/laws/library?q=${encodeURIComponent(cleanCaseNo)}`;
      return createToken(`[${cleanCaseNo}](${url})`);
    });

    // Përcakto ligjin aktiv nga konteksti i rreshtit ose titullit
    for (const statute of STATUTES_REGISTRY) {
      if (statute.regex.test(lineProcessed)) {
        activeSectionLaw = statute.cleanName;
        break;
      }
    }

    // PASS 1: Ligji PARA listës së neneve (p.sh. "Kodi Penal (KPRK Nr. 06/L-074): Nenet 31, 32, 81...")
    const lawBeforeListRegex = /([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,120}?)(?:\s*\([^\)]*\))?:\s*(?:Nenet?|Nenit|Neni|Nenin)?\s*([\d\s,.\-–e(dhe)]+)/gi;
    lineProcessed = lineProcessed.replace(lawBeforeListRegex, (fullMatch, lawCandidate, numbersBlock) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
      const matchedLaw = resolveStatuteName(lawCandidate);
      if (!matchedLaw || !/\d/.test(numbersBlock)) return fullMatch;

      const linkedNums = createLinkedNumbers(numbersBlock, matchedLaw, createToken);
      return `${lawCandidate}: ${linkedNums}`;
    });

    // PASS 2: Nenet me ligj PAS tyre (p.sh. "Nenet 31, 32 dhe 93 të KPRK-së")
    const explicitLawRegex = /\b(Nenet?|Nenit|Nenin|Neni)\s+([\d\s,.\-–e(dhe)]+)\s*(?:i|e|të|së)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,120}?)(?=[.,;\n\r\)]|$)/gi;
    lineProcessed = lineProcessed.replace(explicitLawRegex, (fullMatch, _prefix, numbersBlock, lawCandidate) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
      const matchedLaw = resolveStatuteName(lawCandidate);
      if (!matchedLaw || !/\d/.test(numbersBlock)) return fullMatch;

      const linkedNums = createLinkedNumbers(numbersBlock, matchedLaw, createToken);
      return `${linkedNums} të ${lawCandidate.trim()}`;
    });

    // PASS 3: Nenet e vetmuara (p.sh. "Neni 93" ose "Nenet 188 dhe 221")
    const standaloneArticleRegex = /\b(Nenet?|Nenit|Nenin|Neni)\s+([\d\s,.\-–e(dhe)]+)(?:\s*\(([^)]+)\))?/gi;
    lineProcessed = lineProcessed.replace(standaloneArticleRegex, (fullMatch, _prefix, numbersBlock, parenText) => {
      if (fullMatch.includes('___LAW_TOKEN_') || !/\d/.test(numbersBlock)) return fullMatch;

      const detectedLawFromParen = parenText ? resolveStatuteName(parenText) : '';
      const lawToUse = detectedLawFromParen || activeSectionLaw || 'KPRK';

      const linkedNums = createLinkedNumbers(numbersBlock, lawToUse, createToken);
      return parenText ? `${linkedNums} (${parenText})` : linkedNums;
    });

    return lineProcessed;
  });

  processed = processedLines.join('\n');

  // Rikthe të gjithë tokenët e ruajtur
  let restored = processed;
  for (let i = savedTokens.length - 1; i >= 0; i--) {
    restored = restored.replace(new RegExp(`___LAW_TOKEN_${i}___`, 'g'), savedTokens[i]);
  }

  return restored;
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  let disclaimerBlock = '';
  const disclaimerRegex = /(?:---\s*)?(?:⚖️\s*)?\*?\*?KLAUZOLË\s+E\s+PËRGJEGJËSISË\s+LIGJORE\*?\*?:?[\s\S]*$/i;
  const disclaimerMatch = text.match(disclaimerRegex);

  let textWithoutDisclaimer = text;
  if (disclaimerMatch) {
    disclaimerBlock = disclaimerMatch[0].trim();
    textWithoutDisclaimer = text.substring(0, disclaimerMatch.index).trim();
  }

  textWithoutDisclaimer = stripFakeSignatures(textWithoutDisclaimer);

  const markerRegex = /(?:\n|^)(?:#{1,4}\s*)?(?:Sugjerime(?:\s+për\s+hapat\s+e\s+ardhshëm)?|Pyetje\s+sugjeruese|Pyetje\s+&?\s*Veprime\s+Taktike|Pyetje\s+për\s+hapat\s+e\s+ardhshëm|Hapat\s+e\s+Ardhshëm\s+të\s+Sugjeruar|🎯\s*\*\*Hapat\s+e\s+Sugjeruar)\s*:?/i;
  const match = textWithoutDisclaimer.match(markerRegex);

  let cleanText = textWithoutDisclaimer;
  let questions: string[] = [];

  if (match && match.index !== undefined) {
    cleanText = textWithoutDisclaimer.substring(0, match.index).trim();
    const suggestionsPart = textWithoutDisclaimer.substring(match.index + match[0].length).trim();

    questions = suggestionsPart
      .split(/\n+/)
      .map((line) => {
        return line
          .replace(/^\[PILL:\s*/i, '')
          .replace(/\]$/, '')
          .replace(/^\d+[\.\)\-]\s*/, '')
          .replace(/^[-*•💡📝⚔️🔬💶]\s*/, '')
          .trim();
      })
      .filter((q) => q.length > 5 && !q.startsWith('---') && !q.startsWith('*') && !q.includes('KLAUZOLË'))
      .slice(0, 4);
  }

  if (disclaimerBlock) {
    cleanText = `${cleanText}\n\n${disclaimerBlock}`;
  }

  return { cleanText, questions };
};