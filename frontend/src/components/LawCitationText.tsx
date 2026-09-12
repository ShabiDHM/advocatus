// FILE: src/components/LawCitationText.tsx
// PHOENIX PROTOCOL - UNIFIED STATUTE & SUPREME PRECEDENT TEXT PARSER V2.0
// 100% COMPLETE CODE • ZERO "LIGJI I PËRGJITHSHËM" FAKES • SUPREME PRECEDENT AWARE • ZERO TS WARNINGS

import React from 'react';
import { LawCitationLink } from './LawCitationLink';
import { PrecedentCitationLink } from './PrecedentCitationLink';
import { resolveStatuteName } from '../utils/chatHelpers';

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

interface TokenMatch {
  index: number;
  length: number;
  component: React.ReactNode;
}

export const LawCitationText: React.FC<LawCitationTextProps> = ({ text, className = '' }) => {
  if (!text) return null;

  const clean = cleanSummaryHeadings(text);
  const tokenMatches: TokenMatch[] = [];

  // =========================================================================
  // 1. ZBULIMI I PRECEDENTËVE TË GJYKATËS SUPREME (Rev, PML, KMLP, A.NR, PZR)
  // =========================================================================
  const supremeRegex = /\b(PML|Rev|REV|KMLP|ANR|A\.NR|PZR)\.?\s*(?:Nr\.?|nr\.?)?\s*(\d+[\w\/\.\-]*\/\d{2,4})\b/gi;
  let sMatch: RegExpExecArray | null;

  while ((sMatch = supremeRegex.exec(clean)) !== null) {
    const prefix = sMatch[1].toUpperCase().replace(/\.$/, '');
    const numPair = sMatch[2];
    const cleanCaseNo = `${prefix}.Nr.${numPair}`;

    tokenMatches.push({
      index: sMatch.index,
      length: sMatch[0].length,
      component: (
        <PrecedentCitationLink
          key={`prec-${sMatch.index}-${cleanCaseNo}`}
          caseNumber={cleanCaseNo}
        />
      ),
    });
  }

  // =========================================================================
  // 2. ZBULIMI I NENEVE DHE LIGJEVE TË KOSOVËS (ZERO "LIGJI I PËRGJITHSHËM")
  // =========================================================================
  const statuteRegex = /(?:(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,.]*?)\s*,?\s*(?:Neni|neni|NENI)\s+(\d+))|(?:(?:Neni|neni|NENI)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.]*|[A-Z][a-zçëA-ZÇË\s\d\/L\-]{3,35})?)/gi;
  let stMatch: RegExpExecArray | null;

  while ((stMatch = statuteRegex.exec(clean)) !== null) {
    const startIndex = stMatch.index;
    const matchLength = stMatch[0].length;

    // Shmang përplasjen me precedentët supremë të zbuluar më sipër
    const overlaps = tokenMatches.some(
      (tm) => startIndex < tm.index + tm.length && startIndex + matchLength > tm.index
    );
    if (overlaps) continue;

    let lawTitle = "";
    let articleNum = "";

    if (stMatch[1] && stMatch[3]) {
      // Modeli 1: Ligji Nr. 04/L-077, Neni 12
      const lawPrefix = stMatch[1];
      const lawNumber = stMatch[2].trim();
      const rawTitle = `${lawPrefix} ${lawNumber}`;
      lawTitle = resolveStatuteName(rawTitle) || rawTitle;
      articleNum = stMatch[3].trim();
    } else if (stMatch[4]) {
      // Modeli 2 ose 3: Neni 182 [i LPK-së / Kodit Penal]
      articleNum = stMatch[4].trim();
      const candidate = stMatch[5] ? stMatch[5].trim() : "";
      
      // Zgjidhje inteligjente: nëse nuk përmendet ligji, merret LPK (Kodi Procedural i Kosovës)
      // dhe ASNJËHERË termi imagjinar "Ligji i Përgjithshëm"
      lawTitle = resolveStatuteName(candidate) || candidate || "LPK";
    }

    if (!articleNum) continue;

    const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;

    tokenMatches.push({
      index: startIndex,
      length: matchLength,
      component: (
        <LawCitationLink
          key={`stat-${startIndex}-${articleNum}`}
          lawTitle={lawTitle}
          articleNum={articleNum}
          fullMatch={stMatch[0]}
          targetUrl={targetUrl}
        />
      ),
    });
  }

  // Nëse nuk u gjet asnjë citim, kthe tekstin e pastruar
  if (tokenMatches.length === 0) {
    return <span className={className}>{clean}</span>;
  }

  // Rendit të gjitha lidhjet sipas pozicionit të tyre në tekst
  tokenMatches.sort((a, b) => a.index - b.index);

  // Ndërto rezultatin e ndërthurur (Tekst + Pulla Interaktive)
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;

  tokenMatches.forEach((m) => {
    if (m.index > lastIndex) {
      elements.push(clean.substring(lastIndex, m.index));
    }
    elements.push(m.component);
    lastIndex = m.index + m.length;
  });

  if (lastIndex < clean.length) {
    elements.push(clean.substring(lastIndex));
  }

  return <span className={className}>{elements}</span>;
};

export default LawCitationText;