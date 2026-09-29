// FILE: src/utils/legalSemanticEngine.ts
// PHOENIX PROTOCOL - LEGAL FILTER ENGINE V5.0
//
// V5.0: HEQUR HARDCODING MASIV (Opsion C).
//   - HEQUR SEMANTIC_INTENT_MATRIX (8 rregulla ligjore hardcoded)
//   - HEQUR pretendimet specifike: 8% kamatëvonesa, LMD 382-384, etj.
//   - HEQUR prioritar hardcoded
//   - FSHIRË hardcoding i përmbajtjes juridike
//
//   Ky file tani është thjeshtë NJË FILTER për numra nenesh + substring.
//   Për semantikë të vërtetë, përdorni /laws/ai-semantic-search (backend RAG).
//
//   Arkitektura e re:
//     - performSemanticSearch() → filtron numra nenesh ose substring
//     - NUK pretendon semantikë
//     - NUK përmban përmbajtje juridike
//
// V4.1: Versioni i vjetër me SEMANTIC_INTENT_MATRIX hardcoded.

// ═══════════════════════════════════════════════════════════════════════════
// RESULT TYPE
// ═══════════════════════════════════════════════════════════════════════════

export interface SemanticSearchResult {
  filteredArticles: string[];
  highlightWords: string[];
  matchedIntent: null;   // V5.0: gjithmonë null (nuk ka më rregulla hardcoded)
}

// ═══════════════════════════════════════════════════════════════════════════
// SANITIZE
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Normalizon tekstin për matching: lowercase + heq diakritikat (ë→e, ç→c).
 * V5.0: hequr rreshtat dead-code (regex NFD tashmë heq diakritikat).
 */
export function sanitizeSearchText(text: string): string {
  if (!text) return '';
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

// ═══════════════════════════════════════════════════════════════════════════
// FILTER ENGINE — V5.0
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Filtron një listë artikujsh (numra nenesh) bazuar në një query.
 *
 * V5.0: Ky funksion NUK bën semantikë. Është thjeshtë:
 *   1. Nëse query është numër neni ("neni 5", "5") → filtron artikujt me atë numër
 *   2. Nëse query është tekst → filtron artikujt që përmbajnë atë substring
 *
 * Për semantikë të vërtetë (p.sh. "marrja e deklaratës së fëmijës") → përdorni
 * `/laws/ai-semantic-search` (backend RAG me DeepSeek).
 *
 * @param articles Lista e numrave të neneve (p.sh. ["1", "2", "5", "5.1"])
 * @param query Kërkimi i userit
 * @returns Filtrim + highlight words
 */
export function performSemanticSearch(
  articles: string[],
  query: string,
): SemanticSearchResult {
  const cleanQuery = sanitizeSearchText(query);

  // Nuk ka query → kthen të gjithë
  if (!cleanQuery) {
    return {
      filteredArticles: articles,
      highlightWords: [],
      matchedIntent: null,
    };
  }

  const queryTokens = cleanQuery.split(/\s+/).filter((t) => t.length > 1);

  // ═══ RASTI 1: Query është numër neni ("neni 5", "5", "5.1") ═══
  const directNumMatch = cleanQuery.match(/\d+(\.\d+)?/);
  const isNumberQuery =
    directNumMatch !== null &&
    (cleanQuery.startsWith('neni') || cleanQuery.replace(/\D+/g, '') === cleanQuery);

  if (isNumberQuery && directNumMatch) {
    const targetNum = directNumMatch[0];
    const exactMatches = articles.filter((art) => {
      const cleanArt = art
        .replace(/^neni\s*/i, '')
        .replace(/\.$/, '')
        .trim();
      return (
        cleanArt === targetNum ||
        cleanArt.startsWith(`${targetNum}.`) ||
        cleanArt.startsWith(targetNum)
      );
    });

    if (exactMatches.length > 0) {
      return {
        filteredArticles: exactMatches,
        highlightWords: [targetNum],
        matchedIntent: null,
      };
    }
  }

  // ═══ RASTI 2: Query është tekst → filtrim substring ═══
  // Kërko nëse numri i nenit përmban token-at (jo semantikë reale)
  const tokenMatches = articles.filter((art) => {
    const sanitizedArt = sanitizeSearchText(art);
    return queryTokens.every((token) => sanitizedArt.includes(token));
  });

  if (tokenMatches.length > 0) {
    return {
      filteredArticles: tokenMatches,
      highlightWords: queryTokens,
      matchedIntent: null,
    };
  }

  // ═══ RASTI 3: Fallback — substring i plotë ═══
  const substringMatches = articles.filter((art) =>
    sanitizeSearchText(art).includes(cleanQuery),
  );

  return {
    filteredArticles: substringMatches,
    highlightWords: queryTokens,
    matchedIntent: null,
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORTS — Larguar SEMANTIC_INTENT_MATRIX
// ═══════════════════════════════════════════════════════════════════════════