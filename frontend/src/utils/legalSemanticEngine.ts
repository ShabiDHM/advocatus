// FILE: src/utils/legalSemanticEngine.ts
// PHOENIX PROTOCOL - KOSOVA LEGAL SEMANTIC & LAYMAN-FRIENDLY INTENT ENGINE V2.0

export interface LegalCategory {
  id: string;
  label: string;
  icon: string;
  description: string;
  articleRanges?: {
    lpk?: string[];
    lmd?: string[];
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
  intent: string;
  plainLanguageSummary: string; // Shpjegim popullor për njerëzit pa njohuri ligjore/IT
  keywords: string[];
  suggestedArticles: {
    lawPattern?: string;
    articles: string[];
    explanation: string;
  }[];
}

// BUTONAT E NDARË ME 1-KLIKIM PËR PËRDORUESIT E THJESHTË (QUICK HELP PILLS)
export const QUICK_HELP_CHIPS: QuickHelpChip[] = [
  { label: "S'kam para për taksa gjyqi", query: "lirimi nga taksa", icon: "💰" },
  { label: "Bllokimi i llogarisë / bankës", query: "bllokimi i bankave", icon: "🔒" },
  { label: "Avokati pa autorizim", query: "avokati pa autorizim", icon: "⚖️" },
  { label: "Humbja e afatit për ankesë", query: "skadimi i afatit", icon: "⏱️" },
  { label: "Kthimi i dëmit & pasurimi", query: "pasurimi i pabaze", icon: "💥" },
  { label: "Prishja e kontratës", query: "zgjidhja e kontrates", icon: "📑" },
];

// 1. KATEGORITË KRYESORE LIGJORE (CATEGORY PILLS)
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
    id: 'representation',
    label: 'Avokatët & Prokura',
    icon: '⚖️',
    description: 'Rregullat kur avokati vepron pa autorizim ose tejkalon lejen',
    articleRanges: {
      lpk: ['78-95'],
    },
  },
  {
    id: 'deadlines',
    label: 'Afatet & Vonesat',
    icon: '⏱️',
    description: 'Çfarë ndodh kur humbni afatin dhe si kthehet procedura',
    articleRanges: {
      lpk: ['108-142'],
    },
  },
  {
    id: 'appeals',
    label: 'Ankesat në Gjykata',
    icon: '📜',
    description: 'Kundërshtimi i vendimeve të gjyqtarit dhe shkallët e larta',
    articleRanges: {
      lpk: ['175-243'],
      lmd: ['100-140'],
    },
  },
  {
    id: 'damages',
    label: 'Dëmet & Paratë',
    icon: '💥',
    description: 'Kthimi i pasurisë së marrë padrejtësisht dhe kompensimi i dëmit',
    articleRanges: {
      lmd: ['136-200'],
    },
  },
];

// 2. MATRICA SEMANTIKE ME GJUHË TË THJESHTË POPULLORE + JURIDIKE
export const SEMANTIC_INTENT_MATRIX: SemanticIntentRule[] = [
  {
    intent: 'Lirimi nga Shpenzimet dhe Taksat Gjyqësore',
    plainLanguageSummary: 'Ky nen ju mundëson të mos paguani taksa gjyqësore nëse keni gjendje të rëndë ekonomike.',
    keywords: [
      'lirimi nga taksa',
      'lirimi nga shpenzimet',
      'nuk kam para',
      'skam para',
      'nuk kam pare',
      'skam pare',
      'pa para per gjyq',
      'ndihme juridike falas',
      'taksat gjyqesore',
      'pamundesi financiare',
      'varferia',
      'pagesa e takses',
      'shpenzimet e procedures',
      'mbulimi i shpenzimeve',
      'falas',
      'ndihme sociale',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['468', '469', '470', '471', '450'],
        explanation: 'LPK Neni 468 dhe 469: Gjykata e liron palën nga pagimi i shpenzimeve kur ajo nuk ka mundësi t’i përballojë pa rrezikuar jetesën e familjes.',
      },
    ],
  },

  {
    intent: 'Masat e Sigurimit dhe Bllokimi i Pasurisë/Llogarive',
    plainLanguageSummary: 'Këto nene përdoren për të bllokuar llogarinë bankare të debitorit që të mos i fshehë paratë.',
    keywords: [
      'bllokimi i bankave',
      'bllokim llogarie',
      'ngrirja e pasurise',
      'bllokimi i parave',
      'ma bllokun llogarine',
      'rreziku i tjetersimit',
      'masa e sigurimit',
      'masa e perkohshme',
      'pengimi i permbarimit',
      'shitja e fshehte e pasurise',
      'sigurimi i kerkesepadise',
      'ndalim tjetersimi',
      'me ik me pare',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['297', '298', '299', '300', '304', '304.3', '305'],
        explanation: 'LPK Nenet 297-304: Gjykata mund të urdhërojë menjëherë bllokimin e llogarive rrjedhëse ose ndalimin e shitjes së pronës.',
      },
    ],
  },

  {
    intent: 'Prokura dhe Veprimet pa Autorizim të Avokatit',
    plainLanguageSummary: 'Këto nene tregojnë çfarë ndodh kur avokati vepron pa autorizim të nënshkruar nga ju.',
    keywords: [
      'avokati pa autorizim',
      'avokati pa prokure',
      'mungesa e prokures',
      'perfaqesimi pa autorizim',
      'tejkalimi i autorizimit',
      'avokati pa leter',
      'ska nenshkrim',
      'prokura e posacme',
      'prokura e pergjithshme',
      'revokimi i prokures',
      'heqja e avokatit',
      'shkarkimi i avokatit',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['78', '78.4', '91', '92', '93', '93.3', '94'],
        explanation: 'LPK Nenet 78.4 dhe 91-93: Veprimet e kryera nga personi pa prokurë mbeten të pavlefshme nëse pala nuk i aprovon më vonë.',
      },
    ],
  },

  {
    intent: 'Afatet Ligjore dhe Humbja e Afatit (Prekluzioni)',
    plainLanguageSummary: 'Këto nene ju shpjegojnë si llogariten ditët për ankesë dhe si kërkohet falja e vonesës me arsye shëndetësore.',
    keywords: [
      'skadimi i afatit',
      'humbja e afatit',
      'afati prekluziv',
      'me kaloi afati',
      'kam qene semure',
      'kthimi ne gjendjen e meparshme',
      'justifikimi i voneses',
      'llogaritja e afateve',
      'afati ditor',
      'dite pushimi afati',
      'vonesa',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LPK',
        articles: ['108', '109', '110', '129', '130', '131', '132'],
        explanation: 'LPK Nenet 108-110 dhe 129-132: Nëse keni humbur afatin për shkaqe të arsyeshme, keni të drejtë të kërkoni Kthimin në Gjendjen e Mëparshme.',
      },
    ],
  },

  {
    intent: 'Pasurimi i Pabazë dhe Shpërblimi i Dëmit',
    plainLanguageSummary: 'Këto nene detyrojnë personin që ka përfituar padrejtësisht nga ju t’jua kthejë paratë ose pronën mbrapsht.',
    keywords: [
      'pasurimi i pabaze',
      'pasurimi pa baze juridike',
      'vjedhja e bizneseve',
      'kthimi i dobisë pasurore',
      'kthimi i perfitimit',
      'me mori parate',
      'demi material',
      'demi jomaterial',
      'shperblimi i demit',
      'pergjegjesia per dem',
      'pagese e gabuar',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LMD',
        articles: ['136', '137', '194', '195', '196', '197'],
        explanation: 'LMD Nenet 136 dhe 194: Kushdo që është pasuruar pa bazë ligjore në kurriz të tjetrit, detyrohet ta kthejë atë vlerë.',
      },
    ],
  },

  {
    intent: 'Zgjidhja e Kontratës dhe Mosrespektimi i Marrëveshjes',
    plainLanguageSummary: 'Këto nene rregullojnë mënyrën se si mund të shkëputni një kontratë kur pala tjetër nuk i plotëson detyrimet.',
    keywords: [
      'zgjidhja e kontrates',
      'shkeputja e kontrates',
      'mospermbushja e detyrimit',
      'shkelja e kontrates',
      'nuk po i permbahet kontrates',
      'vonesa e debitorit',
      'kapari',
      'klauzola penale',
    ],
    suggestedArticles: [
      {
        lawPattern: 'LMD',
        articles: ['112', '113', '114', '115', '116', '117', '118'],
        explanation: 'LMD Nenet 112-118: Pala besnike ka të drejtë të kërkojë përmbushjen ose prishjen e menjëhershme të kontratës me dëmshpërblim.',
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

  const ranges = isLpk
    ? category.articleRanges.lpk
    : isLmd
    ? category.articleRanges.lmd
    : category.articleRanges.general || category.articleRanges.lpk;

  if (!ranges || ranges.length === 0) return true;

  return ranges.some((range) => isArticleInRange(articleStr, range));
}

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
  if (directNumMatch) {
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

  // 2. Kërkim semantik dhe në gjuhë të përditshme (Intent Matching)
  let bestIntent: SemanticIntentRule | null = null;
  let intentSuggestedArticles: string[] = [];

  for (const rule of SEMANTIC_INTENT_MATRIX) {
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

  // 3. Fallback: Kërkim i pjesshëm
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