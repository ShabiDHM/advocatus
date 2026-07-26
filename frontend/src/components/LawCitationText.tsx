// FILE: src/components/LawCitationText.tsx
// PHOENIX PROTOCOL - CENTRALIZED LAW CITATION TEXT PARSER V1.0

import React from 'react';
import { LawCitationLink } from './LawCitationLink';

export interface LawCitationTextProps {
  text: string;
  className?: string;
}

const cleanSummaryHeadings = (raw: string): string => {
    if (!raw) return "";
    let clean = raw;
    clean = clean.replace(/###\s*[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]?\s*(UDHËZUESI|ANALIZA|PËRMBLEDHJA|KËSHILLIM).*?(?=\n|$)/giu, '');
    clean = clean.replace(/###\s*.*?(?=\n|$)/g, '');
    clean = clean.replace(/^["'\s{}]+|["'\s{}]+$/g, '');
    clean = clean.replace(/\[\[?([^\]]+)\]?\]/g, '$1');
    return clean.trim();
};

export const LawCitationText: React.FC<LawCitationTextProps> = ({ text, className = '' }) => {
    if (!text) return null;

    const clean = cleanSummaryHeadings(text);

    // Dynamic flexible multi-pattern regex matching Albanian legal citations:
    // Pattern 1: Ligji/Ligjit/Kodi Nr. XXX, Neni YYY
    // Pattern 2: Neni YYY i/e/të Ligjit/Kodit Nr. XXX (or Kodi Penal)
    // Pattern 3: Standalone Neni YYY
    const citationRegex = /(?:(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,.]*?)\s*,?\s*(?:Neni|neni|NENI)\s+(\d+))|(?:(?:Neni|neni|NENI)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.]*|[A-Z][a-zçëA-ZÇË\s\d\/L\-]{3,30})?)/gi;

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
        let lawTitle = "";
        let articleNum = "";

        if (match[1] && match[3]) {
            // Pattern 1: Ligji Nr. 04/L-006, Neni 423
            const lawPrefix = match[1];
            const lawNumber = match[2].trim();
            lawTitle = `${lawPrefix} ${lawNumber}`;
            articleNum = match[3].trim();
        } else if (match[4]) {
            // Pattern 2 or 3: Neni 423 [i Ligjit Nr. 04/L-006]
            articleNum = match[4].trim();
            lawTitle = match[5] ? match[5].trim() : "Ligji i Përgjithshëm";
        }

        if (!articleNum) continue;

        const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;

        matches.push({ 
            fullMatch, 
            targetUrl, 
            index: match.index,
            lawTitle,
            articleNum
        });

        if (match.index === citationRegex.lastIndex) {
            citationRegex.lastIndex++;
        }
    }

    if (matches.length === 0) {
        return <span className={className}>{clean}</span>;
    }

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

    return <span className={className}>{elements}</span>;
};

export default LawCitationText;