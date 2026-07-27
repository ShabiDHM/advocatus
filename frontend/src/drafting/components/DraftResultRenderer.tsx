// FILE: src/drafting/components/DraftResultRenderer.tsx
// PHOENIX PROTOCOL - DRAFT RESULT RENDERER V5.0 (UNIVERSAL BLUE LAW CITATION MATCHING)

import React from 'react';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { LawCitationLink } from '../../components/LawCitationLink';

const highlightPlaceholders = (text: string) => {
  if (!text) return text;
  const parts = text.split(/(\[[^\]]+\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('[') && part.endsWith(']')) {
      const cleanText = part.slice(1, -1);
      return (
        <span 
          key={i} 
          className="inline-block border-b border-dashed border-gray-400 text-gray-500 font-bold px-1 mx-0.5 tracking-wider uppercase text-[10px] sm:text-xs font-sans"
          title="Të dhëna që duhet të plotësohen manualisht"
        >
          {cleanText}
        </span>
      );
    }
    return part;
  });
};

const processContent = (text: string) => {
  if (!text) return text;

  // UNIVERSAL CITATION REGEX:
  // Pattern 1: (Ligji|Kodi) Nr. XXX/L-YYY... (with optional Neni ZZZ)
  // Pattern 2: (LPK|LMD|KPK|KPC) Neni ZZZ
  // Pattern 3: Neni ZZZ (i/e/të...)
  const universalCitationRegex = /(?:((?:Ligji|Ligjit|Kodi|Kodin)\s+Nr\.\s*[\d\/L\-]+[^\n,.:;]*?)(?:,?\s*(?:Neni|neni|NENI|nenit|Nenit)\s+(\d+))?)|(?:(LPK|LMD|KPK|KPPK|KPPRK|LPA|KPC)\s+(?:Neni|neni|NENI|nenit|Nenit)\s+(\d+))|(?:(?:Neni|neni|NENI|nenit|Nenit)\s+(\d+)\s*(?:i|e|të)?\s*((?:Ligjit|Ligji|Kodi|Kodin)[^\n,.:;]*|LPK|LMD|LIDK|Kodi Penal|Kodi Civil)?)/gi;

  const segments: Array<{ 
    type: 'text' | 'citation'; 
    value: string; 
    url?: string;
    lawTitle?: string;
    articleNum?: string;
  }> = [];
  let lastIndex = 0;
  let match;

  while ((match = universalCitationRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.substring(lastIndex, match.index) });
    }

    const fullMatch = match[0];
    let lawTitle = "";
    let articleNum = "1";

    if (match[1]) {
      // Pattern 1: Full Law Title with optional Neni
      lawTitle = match[1].trim();
      if (match[2]) articleNum = match[2].trim();
    } else if (match[3] && match[4]) {
      // Pattern 2: LPK Neni 160
      lawTitle = match[3].trim();
      articleNum = match[4].trim();
    } else if (match[5]) {
      // Pattern 3: Neni 258 i/e/të LMD-së
      articleNum = match[5].trim();
      lawTitle = match[6] ? match[6].trim() : `Neni ${articleNum}`;
    }

    if (lawTitle) {
      const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(articleNum)}`;

      segments.push({
        type: 'citation',
        value: fullMatch,
        url: targetUrl,
        lawTitle,
        articleNum
      });
    } else {
      segments.push({ type: 'text', value: fullMatch });
    }

    lastIndex = universalCitationRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.substring(lastIndex) });
  }

  return segments.map((seg, idx) => {
    if (seg.type === 'citation' && seg.url && seg.lawTitle && seg.articleNum) {
      return (
        <LawCitationLink
          key={`cit-${idx}`}
          lawTitle={seg.lawTitle}
          articleNum={seg.articleNum}
          fullMatch={seg.value}
          targetUrl={seg.url}
          className="font-sans font-bold text-blue-600 dark:text-blue-400 hover:underline"
        />
      );
    }
    return highlightPlaceholders(seg.value);
  });
};

export const DraftResultRenderer: React.FC<{ text: string; t: TFunction }> = React.memo(({ text, t }) => {
  const disclaimer = t('drafting.subtitle', 'Kjo shkresë është gjeneruar nga Juristi AI dhe duhet të verifikohet nga avokati përpara dorëzimit në gjykatë.');

  const cleanMarkdownText = text
    .replace(/^```markdown\s*/gi, '')
    .replace(/^```\s*/gi, '')
    .replace(/```$/gi, '')
    .trim();

  return (
    <div className="flex flex-col h-full w-full max-w-full font-serif" style={{ fontFamily: '"Times New Roman", Times, serif' }}>
      <div className="flex-1 w-full overflow-x-auto text-black">
        
        <style>
          {`
            .legal-markdown-body {
              word-wrap: break-word;
              word-break: break-word;
              white-space: normal;
              overflow-wrap: break-word;
              color: #000000;
            }
            .legal-markdown-body p, 
            .legal-markdown-body li, 
            .legal-markdown-body h1, 
            .legal-markdown-body h2, 
            .legal-markdown-body h3 {
              word-wrap: break-word;
              word-break: break-word;
              white-space: normal;
              color: #000000;
            }
            .legal-markdown-body strong {
              color: #000000;
              font-weight: 900;
            }
          `}
        </style>

        <div className="legal-markdown-body w-full max-w-full">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ node, ...props }) => (
                <h1 {...props} className="font-black uppercase text-center mb-8 text-xl sm:text-2xl tracking-widest leading-tight" />
              ),
              h2: ({ node, ...props }) => (
                <h2 {...props} className="font-bold uppercase text-center mt-10 mb-6 text-lg sm:text-xl tracking-wider leading-snug" />
              ),
              h3: ({ node, ...props }) => (
                <h3 {...props} className="font-bold uppercase mt-8 mb-4 text-base sm:text-lg tracking-wide" />
              ),
              
              strong: ({ node, ...props }) => (
                <strong {...props} className="font-black" />
              ),
              
              p: ({ node, children, ...props }) => {
                return (
                  <p {...props} className="mb-5 leading-[1.8] text-justify whitespace-normal break-words text-sm sm:text-[15px]">
                    {React.Children.map(children, child => {
                      if (typeof child === 'string') {
                        return processContent(child);
                      }
                      return child;
                    })}
                  </p>
                );
              },
              
              ul: ({ node, ...props }) => (
                <ul {...props} className="list-disc pl-6 sm:pl-10 mb-5 space-y-2 text-justify break-words text-sm sm:text-[15px]" />
              ),
              ol: ({ node, ...props }) => (
                <ol {...props} className="list-decimal pl-6 sm:pl-10 mb-5 space-y-2 text-justify break-words text-sm sm:text-[15px]" />
              ),
              li: ({ node, children, ...props }) => {
                return (
                  <li {...props} className="leading-[1.8] pl-2 break-words text-sm sm:text-[15px]">
                    {React.Children.map(children, child => {
                      if (typeof child === 'string') {
                        return processContent(child);
                      }
                      return child;
                    })}
                  </li>
                );
              },
              
              blockquote: ({ node, ...props }) => (
                <blockquote {...props} className="border-l-4 border-gray-400 pl-5 py-2 my-6 text-gray-700 italic bg-gray-50/50 break-words text-sm sm:text-[15px]" />
              ),
              
              code: ({ node, inline, ...props }: any) => {
                if (inline) {
                  return <code {...props} className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-800 break-words" />;
                }
                return <code {...props} className="block bg-gray-100 p-4 rounded-xl my-5 font-mono text-xs text-gray-800 overflow-x-auto whitespace-pre-wrap break-words border border-gray-200" />;
              }
            }}
          >
            {cleanMarkdownText}
          </ReactMarkdown>
        </div>
      </div>
      
      {/* Footer Disclaimer */}
      <div className="mt-12 pt-4 border-t border-gray-300 text-center shrink-0 font-sans">
        <p className="text-[9px] sm:text-[10px] uppercase tracking-[0.2em] text-gray-500 font-bold">
          {disclaimer}
        </p>
      </div>
    </div>
  );
});

export default DraftResultRenderer;