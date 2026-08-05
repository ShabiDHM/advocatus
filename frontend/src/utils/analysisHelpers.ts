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

export const cleanSummaryHeadings = (raw: string): string => {
  if (!raw) return '';
  let clean = raw;
  clean = clean.replace(
    /###\s*[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]?\s*(UDHËZUESI|ANALIZA|PËRMBLEDHJA|KËSHILLIM|STRATEGJIA|OPINIONI|KËSHILLË).*?(?=\r?\n|$)/giu,
    ''
  );
  clean = clean.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
  return clean.trim();
};

export const cleanLegalText = (text: any): string => {
  const clean = safeString(text);
  return cleanSummaryHeadings(clean);
};

export const splitExecutiveSummary = (text: any): { citizenText: string; lawyerText: string } => {
  if (!text) return { citizenText: '', lawyerText: '' };

  if (typeof text === 'object') {
    const citizen = safeString(text.citizenText || text.citizen_summary || text.summary || text.text || '');
    const lawyer = safeString(text.lawyerText || text.lawyer_summary || text.professional || '');
    if (citizen || lawyer) {
      return { citizenText: cleanSummaryHeadings(citizen), lawyerText: cleanSummaryHeadings(lawyer) };
    }
    return { citizenText: cleanSummaryHeadings(safeString(text)), lawyerText: '' };
  }

  const strText = safeString(text);
  const marker = '### ⚖️ ANALIZA PROFESIONALE';
  const markerIndex = strText.indexOf(marker);
  if (markerIndex !== -1) {
    const citizenText = strText.substring(0, markerIndex).trim();
    const lawyerText = strText.substring(markerIndex + marker.length).trim();
    return {
      citizenText: cleanSummaryHeadings(citizenText),
      lawyerText: cleanSummaryHeadings(lawyerText),
    };
  }
  return { citizenText: cleanSummaryHeadings(strText), lawyerText: '' };
};

export const parseLawTitleAndArticle = (titleStr: string, articleStr: string) => {
  const lawTitle = titleStr || 'Ligj i Paidentifikuar';
  let articleNum: string | null = null;

  const artMatchInArticle = articleStr ? articleStr.match(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)?\s*(\d+)/) : null;
  if (artMatchInArticle) {
    articleNum = artMatchInArticle[1];
  }

  if (!articleNum && titleStr) {
    const artMatchInTitle = titleStr.match(/(?:Neni|neni|NENI|nenit|Nenit|nenin|Nenin)\s*(\d+)/i) || titleStr.match(/\b(\d+)\b/);
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