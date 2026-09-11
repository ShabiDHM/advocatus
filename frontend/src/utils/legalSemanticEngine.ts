// FILE: src/utils/legalSemanticEngine.ts
// PHOENIX PROTOCOL - PURE JURIDICAL SEMANTIC ENGINE V4.1 (ZERO WARNINGS • CLEAN TYPES)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS

export interface SemanticIntentRule {
  id: string;
  priority: number;
  intent: string;
  plainLanguageSummary: string;
  keywords: string[];
  suggestedArticles: {
    lawPattern?: string;
    articles: string[];
    explanation: string;
  }[];
}

export const SEMANTIC_INTENT_MATRIX: SemanticIntentRule[] = [
  {
    id: 'interest_rate',
    priority: 100,
    intent: 'Kamatëvonesa Ligjore Vjetore (8% në Vit)',
    plainLanguageSummary: 'Pala debitore që vonon pagesën e borxhit detyrohet të paguajë kamatëvonesë ligjore prej 8% në vit sipas LMD-së.',
    keywords: [
      'kamatevonesa',
      'kamatevonese',
      'kamata ligjore',
      'kamate 8%',
      '8% ne vit',
      'interesi vjetor',
      'kamata ndeshkuese',
      'kamatevonesa ligjore 8% ne vit',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LMD',
        articles: ['382', '383', '384'],
        explanation: 'LMD Neni 382: Debitori që vonon me përmbushjen e detyrimit në të holla ka për borxh të paguajë kamatëvonesën ligjore prej tetë përqind (8%) në vit.',
      },
    ],
  },
  {
    id: 'lsht_fiduciary',
    priority: 95,
    intent: 'Detyra e Besnikërisë, Mos-Konkurrimi dhe Përgjegjësia Solidare e Ortakut (LSHT)',
    plainLanguageSummary: 'Ortaku ose drejtori që shkel besnikërinë, përvetëson kontrata biznesi apo konkurron shoqërinë, përgjigjet solidarisht me të gjithë pasurinë e tij.',
    keywords: [
      'detyra e besnikerise',
      'konkurrenca e palejuar',
      'mos konkurrimi',
      'perjashtimi i ortakut',
      'pergjegjesia e drejtorit',
      'vjedhja e biznesit',
      'vjedhja e kontratave',
      'pervetesimi i mundesive afariste',
      'solidare',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LSHT',
        articles: ['258', '259'],
        explanation: 'LSHT (Ligji Nr. 06/L-016) Nenet 258 dhe 259: Ndalohet përvetësimi i mundësive afariste dhe konkurrimi i padrejtë i shoqërisë.',
      },
    ],
  },
  {
    id: 'unjust_enrichment',
    priority: 90,
    intent: 'Pasurimi pa Bazë Ligjore dhe Kthimi i Dobisë Pasurore',
    plainLanguageSummary: 'Kushdo që ka përfituar pasuri ose të drejta pa bazë ligjore detyrohet t’ia kthejë menjëherë personit të dëmtuar.',
    keywords: [
      'pasurimi pa baze',
      'pasurimi pa baze ligjore',
      'pasurim i pabaze',
      'kthimi i perfitimit',
      'kthimi i dobise pasurore',
      'marrja e padrejte e parave',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LMD',
        articles: ['194', '195', '196', '197'],
        explanation: 'LMD (Ligji Nr. 04/L-077) Neni 194: Secili person që pasurohet pa bazë ligjore në dëm të tjetrit, është i detyruar të kthejë atë që ka marrë.',
      },
    ],
  },
  {
    id: 'material_damages',
    priority: 85,
    intent: 'Shpërblimi i Dëmit Material dhe Përgjegjësia Civile',
    plainLanguageSummary: 'Personi që i shkakton tjetrit dëm material ose moral detyrohet ta kompensojë në tërësi dëmin e pësuar dhe fitimin e humbur.',
    keywords: [
      'demshperblimi material',
      'demshperblim',
      'demi material',
      'kompensimi i demit',
      'shkaktimi i demit',
      'pergjegjesia per dem',
      'demi i shkaktuar',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LMD',
        articles: ['136', '137', '171', '172', '177'],
        explanation: 'LMD Neni 136: Kush i shkakton tjetrit dëm ka për detyrë ta kompensojë, në qoftë se nuk provon se dëmi ka lindur pa fajin e tij.',
      },
    ],
  },
  {
    id: 'security_measure_freeze',
    priority: 80,
    intent: 'Masa e Sigurimit dhe Bllokimi i Xhirollogarive Bankare',
    plainLanguageSummary: 'Gjykata urdhëron caktimin e masës së sigurimit për garantimin e kërkesëpadisë sipas LPK-së.',
    keywords: [
      'bllokimi i xhirollogarive',
      'bllokimi i bankave',
      'bllokim llogarie',
      'ngrirja e pasurise',
      'masa e sigurimit',
      'masa e perkohshme',
      'rreziku i tjetersimit',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['297', '298', '304', '304.3', '305'],
        explanation: 'LPK Nenet 297, 298 dhe 304.3: Rregullojnë masën e sigurimit të kërkesëpadisë dhe bllokimin e mjeteve.',
      },
    ],
  },
  {
    id: 'fee_waiver',
    priority: 75,
    intent: 'Lirimi nga Pagesa e Taksave Gjyqësore',
    plainLanguageSummary: 'Gjykata liron palën nga pagimi i shpenzimeve të procedurës kur ajo nuk ka mundësi financiare sipas kushteve ligjore.',
    keywords: [
      'lirimi nga taksa',
      'lirimi nga taksa gjyqesore',
      'lirimi nga shpenzimet',
      'pamundesi financiare',
      'ndihme juridike falas',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['468', '469', '470', '471'],
        explanation: 'LPK Neni 468 dhe 469: Lirimi nga shpenzimet e procedurës për shkak të gjendjes së vështirë ekonomike.',
      },
    ],
  },
  {
    id: 'representation_rule',
    priority: 70,
    intent: 'Përfaqësimi dhe Vlefshmëria e Autorizimit',
    plainLanguageSummary: 'Veprimet procedurale të kryera nga personi pa autorizim me shkrim rregullohen nga dispozitat e LPK-së.',
    keywords: [
      'avokati pa autorizim',
      'avokati pa prokure',
      'mungesa e prokures',
      'perfaqesimi pa autorizim',
      'revokimi i prokures',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['78', '78.4', '91', '92', '93'],
        explanation: 'LPK Nenet 78.4 dhe 91-93 rregullojnë përfaqësimin procedural dhe mungesën e autorizimit.',
      },
    ],
  },
  {
    id: 'deadlines_rule',
    priority: 60,
    intent: 'Afatet Procedurale dhe Kthimi në Gjendjen e Mëparshme',
    plainLanguageSummary: 'Rregullat mbi llogaritjen e afateve prekluzive dhe kërkesën për kthim në gjendjen e mëparshme (Restitutio in Integrum).',
    keywords: [
      'skadimi i afatit',
      'humbja e afatit',
      'afati prekluziv',
      'kthimi ne gjendjen e meparshme',
      'justifikimi i voneses',
      'afatet procedurale',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['108', '109', '110', '129', '130', '131', '132'],
        explanation: 'LPK Nenet 108-110 dhe 129-132: Trajtojnë llogaritjen e afateve dhe kërkesën për kthim në gjendjen e mëparshme.',
      },
    ],
  },
];

export function sanitizeSearchText(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ë/g, 'e')
    .replace(/ç/g, 'c')
    .trim();
}

export function performSemanticSearch(
  articles: string[],
  query: string,
  _lawTitle?: string,
  _legacyCategory?: string
): {
  filteredArticles: string[];
  matchedIntent: SemanticIntentRule | null;
  highlightWords: string[];
} {
  const cleanQuery = sanitizeSearchText(query);
  const queryTokens = cleanQuery.split(/\s+/).filter((t) => t.length > 1);

  if (!cleanQuery) {
    return {
      filteredArticles: articles,
      matchedIntent: null,
      highlightWords: [],
    };
  }

  const directNumMatch = cleanQuery.match(/\d+(\.\d+)?/);
  if (directNumMatch && (cleanQuery.startsWith('neni') || cleanQuery.replace(/\D+/g, '') === cleanQuery)) {
    const targetNum = directNumMatch[0];
    const exactMatches = articles.filter((art) => {
      const cleanArt = art.replace(/^neni\s*/i, '').replace(/\.$/, '').trim();
      return cleanArt === targetNum || cleanArt.startsWith(`${targetNum}.`) || cleanArt.startsWith(targetNum);
    });

    if (exactMatches.length > 0) {
      return {
        filteredArticles: exactMatches,
        matchedIntent: null,
        highlightWords: [targetNum],
      };
    }
  }

  const sortedMatrix = [...SEMANTIC_INTENT_MATRIX].sort((a, b) => b.priority - a.priority);

  let bestIntent: SemanticIntentRule | null = null;
  let intentSuggestedArticles: string[] = [];

  for (const rule of sortedMatrix) {
    const isMatched = rule.keywords.some((kw) => {
      const sanitizedKw = sanitizeSearchText(kw);
      return cleanQuery.includes(sanitizedKw) || sanitizedKw.includes(cleanQuery);
    });

    if (isMatched) {
      bestIntent = rule;
      for (const suggestion of rule.suggestedArticles) {
        intentSuggestedArticles.push(...suggestion.articles);
      }
      break;
    }
  }

  if (bestIntent && intentSuggestedArticles.length > 0) {
    const matchedInLaw = articles.filter((art) => {
      const artNum = art.replace(/^neni\s*/i, '').replace(/\.$/, '').trim();
      return intentSuggestedArticles.some((target) => {
        return artNum === target || artNum.startsWith(`${target}.`) || artNum.startsWith(target);
      });
    });

    if (matchedInLaw.length > 0) {
      return {
        filteredArticles: matchedInLaw,
        matchedIntent: bestIntent,
        highlightWords: queryTokens,
      };
    }
  }

  const tokenMatches = articles.filter((art) => {
    const sanitizedArt = sanitizeSearchText(art);
    return queryTokens.every((token) => sanitizedArt.includes(token));
  });

  return {
    filteredArticles: tokenMatches.length > 0 ? tokenMatches : articles.filter((art) => sanitizeSearchText(art).includes(cleanQuery)),
    matchedIntent: null,
    highlightWords: queryTokens,
  };
}