// FILE: frontend/src/utils/chatHelpers.ts
// PHOENIX PROTOCOL - CHAT HELPERS V48.0 (UNIVERSAL 100% LAW LINKING & GUARANTEED DISCLAIMER PRESERVATION)

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
    regex: /(?:Kodi\s+i\s+Drejtësisë\s+për\s+të\s+Mitur|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-006|KDPM)/i,
    cleanName: 'Kodi i Drejtësisë për të Mitur'
  },
  {
    regex: /(?:Kushtetut(?:ës|a|ën)?(?:\s+së\s+Republikës\s+së\s+Kosovës)?)/i,
    cleanName: 'Kushtetuta e Republikës së Kosovës'
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
    regex: /(?:KPPRK|KPP|Kodi\s+i\s+Procedurës\s+Penale(?:\s+të\s+Republikës\s+së\s+Kosovës)?|Ligj(?:it|i)?\s+Nr\.?\s*08\/L-032)/i,
    cleanName: 'KPPRK'
  },
  {
    regex: /(?:KPRK|KPK|Kodi\s+Penal(?:\s+i\s+Republikës\s+së\s+Kosovës)?|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-074)/i,
    cleanName: 'KPRK'
  },
  {
    regex: /(?:LPK|Ligji\s+për\s+Procedurën\s+Kontestimore|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-006)/i,
    cleanName: 'LPK'
  },
  {
    regex: /(?:LMDHF|Ligji\s+për\s+Mbrojtjen?\s+nga\s+Dhuna\s+në\s+Familje|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-182|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-015)/i,
    cleanName: 'Ligji për Mbrojtjen nga Dhuna në Familje'
  },
  {
    regex: /(?:LMD|Ligji\s+për\s+Marrëdhëniet\s+e\s+Detyrimeve|Ligj(?:it|i)?\s+Nr\.?\s*04\/L-077)/i,
    cleanName: 'LMD'
  },
  {
    regex: /(?:LFK|LF|Ligji\s+për\s+Familjen|Ligj(?:it|i)?\s+Nr\.?\s*2004\/32)/i,
    cleanName: 'Ligji për Familjen'
  },
  {
    regex: /(?:LSHT|Ligji\s+për\s+Shoqëritë\s+Tregtare|Ligj(?:it|i)?\s+Nr\.?\s*06\/L-016)/i,
    cleanName: 'Ligji për Shoqëritë Tregtare'
  },
  {
    regex: /(?:Ligj(?:it|i)?\s+të\s+Punës|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-212)/i,
    cleanName: 'Ligji i Punës'
  },
  {
    regex: /(?:Ligji\s+për\s+Gjykatën\s+Komerciale|Ligj(?:it|i)?\s+Nr\.?\s*08\/L-015)/i,
    cleanName: 'Ligji për Gjykatën Komerciale'
  },
  {
    regex: /(?:Ligji\s+për\s+Pronësinë|LPTS|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-154)/i,
    cleanName: 'Ligji për Pronësinë dhe të Drejtat Tjera Sendore'
  },
  {
    regex: /(?:Ligji\s+për\s+Konfliktet\s+Administrative|LKA|Ligj(?:it|i)?\s+Nr\.?\s*03\/L-202)/i,
    cleanName: 'Ligji për Konfliktet Administrative'
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

// Funksion ndihmës për të nxjerrë dhe linkuar çdo numër neni nga një bllok (p.sh. "78, 80, 81, 133-134, 243–249")
const createLinkedNumbers = (numbersBlock: string, lawName: string, createToken: (link: string) => string): string => {
  if (!numbersBlock || !lawName) return numbersBlock;

  // Zëvendësojmë diapazonet (p.sh. 133-134 ose 243–249)
  let processed = numbersBlock.replace(/(\b\d+[a-zA-Z]?)\s*[\-–]\s*(\b\d+[a-zA-Z]?)/g, (_m, n1, n2) => {
    const url1 = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(n1)}`;
    const url2 = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(n2)}`;
    const t1 = createToken(`[Neni ${n1}](${url1})`);
    const t2 = createToken(`[Neni ${n2}](${url2})`);
    return `${t1}–${t2}`;
  });

  // Zëvendësojmë numrat individualë që kanë mbetur pa u linkuar
  processed = processed.replace(/\b\d+[a-zA-Z]?\b/g, (num) => {
    const url = `/laws/article?lawTitle=${encodeURIComponent(lawName)}&articleNumber=${encodeURIComponent(num)}`;
    return createToken(`[Neni ${num}](${url})`);
  });

  return processed;
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

  const lines = processed.split('\n');
  let activeSectionLaw = 'KPRK';

  const processedLines = lines.map((line) => {
    for (const statute of STATUTES_REGISTRY) {
      if (statute.regex.test(line)) {
        activeSectionLaw = statute.cleanName;
        break;
      }
    }

    let lineProcessed = line;

    // A. PASS 1: Ligji PARA listës së neneve (p.sh. "KPPRK (Ligji Nr. 08/L-032): Nenet 78, 80, 81, 103, 110, 120, 128, 133, 134, 144, 145, 212, 213, 462")
    const lawBeforeListRegex = /([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,40}?)(?:\s*\([^\)]+\))?:\s*(Nenet?)\s*([\d\s,.\-–(dhe)(e)]+)/gi;
    lineProcessed = lineProcessed.replace(lawBeforeListRegex, (fullMatch, lawCandidate, prefix, numbersBlock) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
      const matchedLaw = resolveStatuteName(lawCandidate);
      if (!matchedLaw) return fullMatch;

      const linkedNums = createLinkedNumbers(numbersBlock, matchedLaw, createToken);
      return `${lawCandidate}: ${prefix} ${linkedNums}`;
    });

    // B. PASS 2: Nenet me ligj PAS tyre (p.sh. "Nenet 31, 32 të KPRK-së", "Neni 10 i Ligjit Nr. 08/L-168", "Neni 6 KEDNJ", "Neni 31 i Kushtetutës")
    const explicitLawRegex = /\b(Nenet?|Nenit|Neni)\s+([\d\s,.\-–(dhe)(e)]+)\s*(?:i|e|të|së)?\s*([A-Za-z0-9\/\-ëçËÇ\s\(\)\.]{2,40}?)(?=[.,;\n\r\)]|$)/gi;
    lineProcessed = lineProcessed.replace(explicitLawRegex, (fullMatch, prefix, numbersBlock, lawCandidate) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;
      const matchedLaw = resolveStatuteName(lawCandidate);
      if (!matchedLaw) return fullMatch;

      const linkedNums = createLinkedNumbers(numbersBlock, matchedLaw, createToken);
      return `${prefix} ${linkedNums} të ${lawCandidate.trim()}`;
    });

    // C. PASS 3: Nenet e vetmuara në tekst (p.sh. "Neni 424", "Neni 103", "Neni 96")
    const standaloneArticleRegex = /\b(Neni\s+(\d+[a-zA-Z]?))(?:\s*\(([^)]+)\))?/gi;
    lineProcessed = lineProcessed.replace(standaloneArticleRegex, (fullMatch, _p1, artNum, parenText) => {
      if (fullMatch.includes('___LAW_TOKEN_')) return fullMatch;

      const detectedLawFromParen = parenText ? resolveStatuteName(parenText) : '';
      const lawToUse = detectedLawFromParen || activeSectionLaw || 'KPRK';

      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawToUse)}&articleNumber=${encodeURIComponent(artNum)}`;
      const token = createToken(`[Neni ${artNum}](${targetUrl})`);

      return parenText ? `${token} (${parenText})` : token;
    });

    return lineProcessed;
  });

  processed = processedLines.join('\n');

  // Rikthimi i të gjithë tokenave të mbrojtur
  let restored = processed;
  for (let i = savedTokens.length - 1; i >= 0; i--) {
    restored = restored.replace(new RegExp(`___LAW_TOKEN_${i}___`, 'g'), savedTokens[i]);
  }

  return restored;
};

export const extractFollowUpQuestions = (text: any): { cleanText: string; questions: string[] } => {
  if (!text || typeof text !== 'string') return { cleanText: '', questions: [] };

  // Nxjerrim Klauzolën e Përgjegjësisë Ligjore nëse ndodhet kudo në tekst
  let disclaimerBlock = '';
  const disclaimerRegex = /(?:---\s*)?(?:⚖️\s*)?\*?\*?KLAUZOLË\s+E\s+PËRGJEGJËSISË\s+LIGJORE\*?\*?:?[\s\S]*$/i;
  const disclaimerMatch = text.match(disclaimerRegex);

  let textWithoutDisclaimer = text;
  if (disclaimerMatch) {
    disclaimerBlock = disclaimerMatch[0].trim();
    textWithoutDisclaimer = text.substring(0, disclaimerMatch.index).trim();
  }

  const markerRegex = /(?:\n|^)(?:#{1,4}\s*)?(?:Sugjerime(?:\s+për\s+hapat\s+e\s+ardhshëm)?|Pyetje\s+sugjeruese|Pyetje\s+për\s+hapat\s+e\s+ardhshëm|Hapat\s+e\s+Ardhshëm\s+të\s+Sugjeruar)\s*:?/i;
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
          .replace(/^[-*•]\s*/, '')
          .trim();
      })
      .filter((q) => q.length > 5 && !q.startsWith('---') && !q.startsWith('*') && !q.includes('KLAUZOLË'))
      .slice(0, 4);
  }

  // Bashkangjisim gjithmonë Disclaimer-in në fund të tekstit të pastër që të shfaqet në çdo mesazh
  if (disclaimerBlock) {
    cleanText = `${cleanText}\n\n${disclaimerBlock}`;
  } else {
    cleanText = `${cleanText}\n\n---\n⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Sokrati (Juristi AI) për qëllime informative, kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*`;
  }

  return { cleanText, questions };
};