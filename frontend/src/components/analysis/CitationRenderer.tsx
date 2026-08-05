// FILE: src/components/analysis/CitationRenderer.tsx
import React from 'react';
import { LawCitationLink } from '../LawCitationLink';
import { cleanLegalText, parseLawTitleAndArticle, safeString } from '../../utils/analysisHelpers';

export const renderTextWithCitations = (text: string): React.ReactNode => {
  if (!text) return null;
  const clean = cleanLegalText(text);

  const citationRegex = /(?:(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,.]*?)\s*,?\s*(?:Neni|neni|NENI|nenit|nenit|Nenit|NENIT|nenin|Nenin|NENIN|nene|Nene|NENE|nenet|Nenet|NENET)\s+(\d+))|(?:(?:Neni|neni|NENI|nenit|nenit|Nenit|NENIT|nenin|Nenin|NENIN|nene|Nene|NENE|nenet|Nenet|NENET)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.]*|[A-Z][a-zçëA-ZÇË\s\d\/L\-]{3,30})?)/gi;

  const matches: Array<{
    fullMatch: string;
    targetUrl: string;
    index: number;
    lawTitle: string;
    articleNum: string;
  }> = [];

  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(clean)) !== null) {
    const fullMatch = match[0];
    let lawTitle = '';
    let articleNum = '';

    if (match[1] && match[3]) {
      const lawPrefix = match[1];
      const lawNumber = match[2].trim();
      lawTitle = `${lawPrefix} ${lawNumber}`;
      articleNum = match[3].trim();
    } else if (match[4]) {
      articleNum = match[4].trim();
      lawTitle = match[5] ? match[5].trim() : 'Ligji i Përgjithshëm';
    }

    if (!articleNum) continue;

    const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;

    matches.push({ fullMatch, targetUrl, index: match.index, lawTitle, articleNum });

    if (match.index === citationRegex.lastIndex) {
      citationRegex.lastIndex++;
    }
  }

  if (matches.length === 0) return clean;

  const elements: React.ReactNode[] = [];
  let lastIndex = 0;

  matches.forEach((m, i) => {
    if (m.index > lastIndex) {
      elements.push(clean.substring(lastIndex, m.index));
    }
    elements.push(
      <LawCitationLink
        key={`cit-${i}-${m.index}`}
        lawTitle={m.lawTitle}
        articleNum={m.articleNum}
        fullMatch={m.fullMatch}
        targetUrl={m.targetUrl}
      />
    );
    lastIndex = m.index + m.fullMatch.length;
  });

  if (lastIndex < clean.length) {
    elements.push(clean.substring(lastIndex));
  }

  return elements;
};

export const RenderCitationItem: React.FC<{ item: any }> = ({ item }) => {
  if (typeof item === 'object' && item !== null && (item.law || item.title)) {
    const rawLawTitle = item.law || item.title || 'Ligj i Paidentifikuar';
    const rawArticle = item.article || item.legal_basis || '';
    const body = item.relevance || item.argument || item.description || '';

    const { cleanLawTitle, articleNum, targetUrl } = parseLawTitleAndArticle(rawLawTitle, rawArticle);

    return (
      <div className="flex flex-col gap-3 w-full">
        <div className="flex flex-wrap items-center gap-2">
          <LawCitationLink
            lawTitle={cleanLawTitle}
            articleNum={articleNum || '1'}
            fullMatch={`${rawLawTitle}${rawArticle ? ` - ${rawArticle}` : ''}`}
            targetUrl={targetUrl}
          />
        </div>
        {body && (
          <div className="text-text-secondary text-[13px] leading-relaxed pl-5 border-l-2 border-main ml-0.5 mt-1">
            <span className="text-primary-start opacity-80 text-[11px] font-black uppercase mr-2 tracking-widest">
              Relevanca:
            </span>
            {renderTextWithCitations(body)}
          </div>
        )}
      </div>
    );
  }

  const rawText = safeString(item);
  return <span className="leading-relaxed text-text-primary">{renderTextWithCitations(rawText)}</span>;
};