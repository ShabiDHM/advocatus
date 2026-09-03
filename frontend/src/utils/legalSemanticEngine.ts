// FILE: src/utils/legalSemanticEngine.ts
// PHOENIX PROTOCOL - KOSOVA LEGAL MASTER MATRIX (7 GOLDEN TEST CASES INCLUDED) V3.0

export interface LegalCategory {
  id: string;
  label: string;
  icon: string;
  description: string;
  articleRanges?: {
    lpk?: string[];
    lmd?: string[];
    lsht?: string[];
    kprk?: string[];
    general?: string[];
  };
}

export interface QuickHelpChip {
  label: string;
  query: string;
  icon: string;
}

export interface SemanticIntentRule {
  id: string;
  priority: number; // Numër më i lartë = Prioritet më i lartë
  intent: string;
  plainLanguageSummary: string;
  keywords: string[];
  suggestedArticles: {
    lawPattern?: string; // 'LPK', 'LMD', 'LSHT', 'KPK'
    articles: string[];
    explanation: string;
  }[];
}

// BUTONAT E NDARË ME 1-KLIKIM
export const QUICK_HELP_CHIPS: QuickHelpChip[] = [
  { label: "S'kam para për taksa gjyqi", query: "lirimi nga taksa", icon: "💰" },
  { label: "Bllokimi i llogarisë / bankës", query: "bllokimi i xhirollogarive bankare", icon: "🔒" },
  { label: "Kamatëvonesa ligjore 8%", query: "kamatëvonesa ligjore 8% në vit", icon: "📈" },
  { label: "Dëmi & Pasurimi pa bazë", query: "pasurimi pa baze ligjore", icon: "💥" },
  { label: "Konkurrenca e ortakut (LSHT)", query: "konkurrenca e palejuar e ortakut dhe detyra e besnikerise", icon: "🏢" },
  { label: "Avokati pa autorizim", query: "avokati pa autorizim", icon: "⚖️" },
];

// KATEGORITË KRYESORE LIGJORE
export const LEGAL_CATEGORIES: LegalCategory[] = [
  {
    id: 'all',
    label: 'Të Gjitha',
    icon: '🔍',
    description: 'Shfaq të gjitha nenet me radhë',
  },
  {
    id: 'expenses',
    label: 'Taksat & Ndihma Falas',
    icon: '💰',
    description: 'Lirimi nga shpenzimet kur nuk keni mundësi financiare',
    articleRanges: {
      lpk: ['448-473'],
    },
  },
  {
    id: 'security_measures',
    label: 'Masat & Bllokimet',
    icon: '🔒',
    description: 'Bllokimi i parave në bankë dhe mbrojtja e pasurisë para gjykimit',
    articleRanges: {
      lpk: ['297-317'],
    },
  },
  {
    id: 'commercial',
    label: 'Shoqëritë Tregtare & Ortakët',
    icon: '🏢',
    description: 'Detyrat e ortakëve, besnikëria, konkurrenca dhe përjashtimi (LSHT)',
    articleRanges: {
      lsht: ['250-270'],
    },
  },
  {
    id: 'damages',
    label: 'Dëmet & Kamata',
    icon: '💥',
    description: 'Kthimi i pasurisë pa bazë, kompensimi i dëmit dhe kamata 8%',
    articleRanges: {
      lmd: ['136-200', '382-385'],
    },
  },
  {
    id: 'appeals',
    label: 'Ankesat & Afatet',
    icon: '📜',
    description: 'Kundërshtimi i vendimeve të gjyqtarit dhe kthimi i afatit',
    articleRanges: {
      lpk: ['108-142', '175-243'],
    },
  },
];

// MATRICA E 7 TEST-CASES ME PRIORITET TË LARTË (WEIGHTED MASTER MATRIX)
export const SEMANTIC_INTENT_MATRIX: SemanticIntentRule[] = [
  // 1. TEST-CASE 3: KAMATËVONESA LIGJORE 8%
  {
    id: 'interest_rate',
    priority: 100,
    intent: 'Kamatëvonesa Ligjore Vjetore (8% në Vit)',
    plainLanguageSummary: 'Pala debitore që vonon pagesën e borxhit detyrohet të paguajë kamatëvonesë ligjore prej 8% në vit.',
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

  // 2. TEST-CASE 4 & 5: DETYRA E BESNIKËRISË, KONKURRENCA E PALEJUAR DHE PËRJASHTIMI I ORTAKUT (LSHT)
  {
    id: 'lsht_fiduciary',
    priority: 95,
    intent: 'Detyra e Besnikërisë, Mos-Konkurrimi dhe Përgjegjësia Solidare e Ortakut (LSHT)',
    plainLanguageSummary: 'Ortaku ose drejtori që shkel besnikërinë, përvetëson kontrata biznesi apo konkurron shoqërinë, përgjigjet solidarisht me të gjithë pasurinë dhe detyrohet të kthejë çdo fitim personal.',
    keywords: [
      'detyra e besnikerise',
      'konkurrenca e palejuar',
      'mos konkurrimi',
      'perjashtimi i ortakut',
      'pergjegjesia e drejtorit',
      'vjedhja e biznesit',
      'vjedhja e kontratave',
      'pervetesimi i mundesive afariste',
      'shkelje te renda te ortakut',
      'solidare',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LSHT',
        articles: ['258', '259'],
        explanation: 'LSHT (Ligji Nr. 06/L-016) Nenet 258 dhe 259: Ndalohet përvetësimi i mundësive afariste dhe konkurrimi. Ortakët e korruptuar përgjigjen solidarisht me kthimin e plotë të fitimit personal dhe dëmshpërblim.',
      },
    ],
  },

  // 3. TEST-CASE 2: PASURIMI PA BAZË LIGJORE
  {
    id: 'unjust_enrichment',
    priority: 90,
    intent: 'Pasurimi pa Bazë Ligjore dhe Kthimi i Dobisë Pasurore',
    plainLanguageSummary: 'Kushdo që ka përfituar pasuri ose të drejta pa bazë ligjore detyrohet t’ia kthejë menjëherë personit të dëmtuar me kamatë.',
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
        explanation: 'LMD (Ligji Nr. 04/L-077) Neni 194: Secili person që pasurohet pa bazë ligjore në dëm të tjetrit, është i detyruar të kthejë atë që ka marrë dhe të shpërblejë vlerën e dobisë së realizuar.',
      },
    ],
  },

  // 4. TEST-CASE 1: DËMSHPËRBLIMI MATERIAL DHE MORAL
  {
    id: 'material_damages',
    priority: 85,
    intent: 'Shpërblimi i Dëmit Material dhe Përgjegjësia Civile',
    plainLanguageSummary: 'Personi që i shkakton tjetrit dëm material detyrohet ta kompensojë në tërësi dëmin e pësuar dhe fitimin e humbur.',
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

  // 5. TEST-CASE 6: MASAT E SIGURIMIT & BLLOKIMI I XHIROLLOGARIVE
  {
    id: 'security_measure_freeze',
    priority: 80,
    intent: 'Masa e Sigurimit dhe Bllokimi i Xhirollogarive Bankare',
    plainLanguageSummary: 'Gjykata urdhëron menjëherë bllokimin e llogarive bankare të debitorit kur ekziston rreziku i fshehjes së parave.',
    keywords: [
      'bllokimi i xhirollogarive',
      'bllokimi i bankave',
      'bllokim llogarie',
      'ngrirja e pasurise',
      'masa e sigurimit',
      'masa e perkohshme',
      'rreziku i tjetersimit',
      'bllokimi i parave',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['297', '298', '304', '304.3', '305'],
        explanation: 'LPK Nenet 297, 298 dhe 304.3: Gjykata cakton masën e sigurimit duke urdhëruar bankat të bllokojnë fondet e debitorit me qëllim garantimin e kërkesëpadisë.',
      },
    ],
  },

  // 6. TEST-CASE 7: LIRIMI NGA TAKSAT GJYQËSORE DHE SHPENZIMET
  {
    id: 'fee_waiver',
    priority: 75,
    intent: 'Lirimi nga Pagesa e Taksave Gjyqësore për Shkak të Gjendjes Ekonomike',
    plainLanguageSummary: 'Gjykata liron palën nga pagesa e taksave gjyqësore dhe shpenzimeve të procedurës kur ajo nuk ka mundësi financiare.',
    keywords: [
      'lirimi nga taksa',
      'lirimi nga taksa gjyqesore',
      'lirimi nga shpenzimet',
      'pamundesi financiare',
      'skam para',
      'skam pare',
      'varferia',
      'ndihme juridike falas',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['468', '469', '470', '471', '450'],
        explanation: 'LPK Neni 468 dhe 469 (Kapitulli XXV): Gjykata e liron palën nga pagimi i shpenzimeve të procedurës përfshirë shpenzimet dhe taksat gjyqësore.',
      },
    ],
  },

  // 7. PROKURA & PËRFAQËSIMI
  {
    id: 'representation_rule',
    priority: 70,
    intent: 'Përfaqësimi dhe Mungesa e Autorizimit të Avokatit',
    plainLanguageSummary: 'Veprimet procedurale të avokatit pa autorizim me shkrim janë juridikisht të pavlefshme.',
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
        articles: ['78', '78.4', '91', '92', '93', '93.3'],
        explanation: 'LPK Nenet 78.4 dhe 91-93 rregullojnë vlefshmërinë e veprimeve procedurale dhe mungesën e prokurës.',
      },
    ],
  },

  // 8. AFATET DHE KTHIMI I AFATIT (PREKLUZIONI)
  {
    id: 'deadlines_rule',
    priority: 60,
    intent: 'Afatet Procedurale dhe Kthimi në Gjendjen e Mëparshme',
    plainLanguageSummary: 'Këto nene rregullojnë llogaritjen e ditëve për ankesë dhe justifikimin e vonesës (Restitutio in Integrum).',
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
        explanation: 'LPK Nenet 108-110 dhe 129-132: Trajtojnë afatet prekluzive dhe procedurën e kthimit në gjendjen e mëparshme.',
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

export function isArticleInRange(articleStr: string, rangeStr: string): boolean {
  const artNum = parseInt(articleStr.replace(/\D+/g, ''), 10);
  if (isNaN(artNum)) return false;

  if (rangeStr.includes('-')) {
    const [start, end] = rangeStr.split('-').map((n) => parseInt(n.trim(), 10));
    return artNum >= start && artNum <= end;
  }

  return artNum === parseInt(rangeStr, 10);
}

export function matchArticleToCategory(articleStr: string, categoryId: string, lawTitle: string): boolean {
  if (categoryId === 'all') return true;

  const category = LEGAL_CATEGORIES.find((c) => c.id === categoryId);
  if (!category || !category.articleRanges) return true;

  const normalizedTitle = sanitizeSearchText(lawTitle);
  const isLpk = normalizedTitle.includes('lpk') || normalizedTitle.includes('kontestimore');
  const isLmd = normalizedTitle.includes('lmd') || normalizedTitle.includes('detyrimeve');
  const isLsht = normalizedTitle.includes('lsht') || normalizedTitle.includes('tregtare');

  const ranges = isLpk
    ? category.articleRanges.lpk
    : isLmd
    ? category.articleRanges.lmd
    : isLsht
    ? category.articleRanges.lsht
    : category.articleRanges.general || category.articleRanges.lpk;

  if (!ranges || ranges.length === 0) return true;

  return ranges.some((range) => isArticleInRange(articleStr, range));
}

// ALGORITMI I KËRKIMIT SEMANTIK ME PRIORITET TË PESHUAR
export function performSemanticSearch(
  articles: string[],
  query: string,
  lawTitle: string,
  activeCategoryId: string = 'all'
): {
  filteredArticles: string[];
  matchedIntent: SemanticIntentRule | null;
  highlightWords: string[];
} {
  const cleanQuery = sanitizeSearchText(query);
  const queryTokens = cleanQuery.split(/\s+/).filter((t) => t.length > 1);

  let candidateArticles = articles;
  if (activeCategoryId !== 'all') {
    candidateArticles = articles.filter((art) => matchArticleToCategory(art, activeCategoryId, lawTitle));
  }

  if (!cleanQuery) {
    return {
      filteredArticles: candidateArticles,
      matchedIntent: null,
      highlightWords: [],
    };
  }

  // 1. Kërkim i drejtpërdrejtë me numër neni
  const directNumMatch = cleanQuery.match(/\d+(\.\d+)?/);
  if (directNumMatch && (cleanQuery.startsWith('neni') || cleanQuery.replace(/\D+/g, '') === cleanQuery)) {
    const targetNum = directNumMatch[0];
    const exactMatches = candidateArticles.filter((art) => {
      const cleanArt = art.replace(/^neni\s*/i, '').trim();
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

  // 2. Kërkim sipas matricës së prioriteteve (Sorted by Priority Descending)
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
    const matchedInLaw = candidateArticles.filter((art) => {
      const artNum = art.replace(/^neni\s*/i, '').trim();
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

  // 3. Fallback: Kërkim tekstual i lirë
  const tokenMatches = candidateArticles.filter((art) => {
    const sanitizedArt = sanitizeSearchText(art);
    return queryTokens.every((token) => sanitizedArt.includes(token));
  });

  return {
    filteredArticles: tokenMatches.length > 0 ? tokenMatches : candidateArticles.filter((art) => sanitizeSearchText(art).includes(cleanQuery)),
    matchedIntent: null,
    highlightWords: queryTokens,
  };
}