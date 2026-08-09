// FILE: src/utils/analysisHelpers.ts

export const safeString = (val: any): string => {
  if (!val) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'object') {
    try {
      return (
        val.citizenText ||
        val.lawyerText ||
        val.summary ||
        val.text ||
        val.opponent_strategy ||
        val.strategy ||
        JSON.stringify(val)
      );
    } catch {
      return String(val);
    }
  }
  return String(val);
};

export const cleanActionStepText = (raw: any): string => {
  const text = safeString(raw);
  return text
    .replace(/^(HAPAT\s+PËR\s+QYTETARIN|HAPAT\s+PËR\s+AVOKATIN|KËSHILLA\s+PËR\s+QYTETARIN|KËSHILLA\s+PËR\s+AVOKATIN)\s*:\s*/gi, '')
    .trim();
};

export const cleanSummaryHeadings = (raw: string): string => {
  if (!raw) return '';
  let clean = raw;
  // Strip markdown headers like ### 🧑‍💼 UDHËZUESI PËR QYTETARIN... or ### ⚖️ ANALIZA...
  clean = clean.replace(
    /###\s*(?:[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]|\S+)?\s*(UDHËZUESI|ANALIZA|PËRMBLEDHJA|KËSHILLIM|STRATEGJIA|OPINIONI|KËSHILLË)[^\n]*/giu,
    ''
  );
  // Strip any remaining standalone Markdown ### headers
  clean = clean.replace(/^###\s+.*$/gm, '');
  clean = clean.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
  return clean.trim();
};

export const cleanLegalText = (text: any): string => {
  const clean = safeString(text);
  return cleanSummaryHeadings(clean);
};

export const splitExecutiveSummary = (text: any): { citizenText: string; lawyerText: string; unifiedText: string } => {
  if (!text) return { citizenText: '', lawyerText: '', unifiedText: '' };

  let citizenText = '';
  let lawyerText = '';

  if (typeof text === 'object') {
    citizenText = safeString(text.citizenText || text.citizen_summary || text.summary || text.text || '');
    lawyerText = safeString(text.lawyerText || text.lawyer_summary || text.professional || '');
  } else {
    const strText = safeString(text);
    const marker = '### ⚖️ ANALIZA PROFESIONALE';
    const markerIndex = strText.indexOf(marker);
    if (markerIndex !== -1) {
      citizenText = strText.substring(0, markerIndex).trim();
      lawyerText = strText.substring(markerIndex + marker.length).trim();
    } else {
      citizenText = strText;
    }
  }

  const cleanCitizen = cleanSummaryHeadings(citizenText);
  const cleanLawyer = cleanSummaryHeadings(lawyerText);

  const unifiedParts: string[] = [];
  if (cleanCitizen) unifiedParts.push(cleanCitizen);
  if (cleanLawyer && cleanLawyer !== cleanCitizen) unifiedParts.push(cleanLawyer);

  return {
    citizenText: cleanCitizen,
    lawyerText: cleanLawyer,
    unifiedText: unifiedParts.join('\n\n') || cleanSummaryHeadings(safeString(text)),
  };
};

export const parseLawTitleAndArticle = (titleStr: string, articleStr: string) => {
  const lawTitle = titleStr || 'Ligj i Paidentifikuar';
  let articleNum: string | null = null;

  const artMatchInArticle = articleStr ? articleStr.match(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)?\s*(\d+)/) : null;
  if (artMatchInArticle) {
    articleNum = artMatchInArticle[1];
  }

  if (!articleNum && titleStr) {
    const artMatchInTitle = titleStr.match(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)\s*\d+/i) || titleStr.match(/\b(\d+)\b/);
    if (artMatchInTitle) {
      articleNum = artMatchInTitle[1];
    }
  }

  let cleanLawTitle = lawTitle
    .replace(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)\s*\d+/gi, '')
    .replace(/^[,\s\-\–]+|[,\s\-\–]+$/g, '')
    .trim();

  if (!cleanLawTitle) cleanLawTitle = lawTitle;

  const targetUrl = articleNum
    ? `/laws/article?lawTitle=${encodeURIComponent(cleanLawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`
    : `/laws/overview?lawTitle=${encodeURIComponent(cleanLawTitle)}`;

  return { cleanLawTitle, articleNum, targetUrl };
};