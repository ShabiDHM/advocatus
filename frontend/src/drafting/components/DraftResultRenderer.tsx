// FILE: src/drafting/components/DraftResultRenderer.tsx
// PHOENIX PROTOCOL - DRAFT RESULT RENDERER V3.3 (CITATION PUNCTUATION FIX)

import React from 'react';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Link } from 'react-router-dom';
import { Scale, Eye } from 'lucide-react';

const highlightPlaceholders = (text: string) => {
  if (!text) return text;
  const parts = text.split(/(\[[^\]]+\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('[') && part.endsWith(']')) {
      const cleanText = part.slice(1, -1);
      return (
        <span 
          key={i} 
          className="inline-block border-b border-dashed border-gray-400 text-gray-500 font-bold px-1 mx-0.5 tracking-wider uppercase text-[10px] sm:text-xs"
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

  // Match legal citations: (Ligjit|Ligji|Kodi|Kodin) Nr. XX/L-XXX, Neni YYY
  const citationRegex = /(?:Në\s+bazë\s+të\s+)?(Ligjit|Ligji|Kodi|Kodin)\s+(Nr\.\s*[\d\/L\-]+[^\n,]*?),\s*(?:Neni|neni)\s+(\d+)/gi;

  const segments: Array<{ type: 'text' | 'citation'; value: string; url?: string }> = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.substring(lastIndex, match.index) });
    }

    const fullMatch = match[0];
    const lawPrefix = match[1];
    
    // PHOENIX FIX: Aggressively strip trailing parenthesis, commas, or periods from the extracted titles
    let lawTitle = match[2].trim().replace(/[\),.;]+$/, '');
    let articleNum = match[3].trim().replace(/[\),.;]+$/, '');
    
    const fullLawName = `${lawPrefix} ${lawTitle}`;
    const targetUrl = `/laws/article?lawTitle=${encodeURIComponent(fullLawName)}&articleNumber=${encodeURIComponent(articleNum)}`;

    segments.push({
      type: 'citation',
      value: fullMatch,
      url: targetUrl
    });

    lastIndex = citationRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.substring(lastIndex) });
  }

  return segments.map((seg, idx) => {
    if (seg.type === 'citation' && seg.url) {
      return (
        <Link
          key={`cit-${idx}`}
          to={seg.url}
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] sm:text-xs font-black bg-indigo-50 text-indigo-800 border border-indigo-200 hover:bg-indigo-100 transition-all mx-1 align-middle no-underline shadow-sm font-sans tracking-widest"
          title={`Hap ${seg.value}`}
        >
          <Scale size={11} className="text-indigo-600 shrink-0" />
          <span>{seg.value}</span>
          <Eye size={11} className="text-indigo-500 ml-0.5 opacity-80 shrink-0" />
        </Link>
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
              li: ({ node, children, ...props }) => (
                <li {...props} className="leading-[1.8] pl-2 break-words text-sm sm:text-[15px]">
                  {React.Children.map(children, child => {
                    if (typeof child === 'string') {
                      return processContent(child);
                    }
                    return child;
                  })}
                </li>
              ),
              
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