// FILE: src/components/law/LawArticleContent.tsx
// PHOENIX PROTOCOL - LAW ARTICLE CONTENT V31.0
//
// V31.0: FIX repeals + highlight boundary + i18n + clipboard fallback.
//   - T20: Shtuar warning shfuqizimi në krye të kartës
//   - T21: "Preambula" dhe "Paragrafi" përmes t()
//   - T22: Highlight regex me \b në TË DYJA anët
//   - T23: Hequr startsWith (vetëm === match exact)
//   - T24: Clipboard fallback për kontekst jo-secure
//
// V30.0: Versioni i vjetër.

import React, { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileText, ExternalLink, Copy, Check, AlertTriangle } from 'lucide-react';
import type { ArticleData } from './lawArticleTypes';
import type { TFunction } from 'i18next';
import { sanitizeSearchText } from '../../utils/legalSemanticEngine';

interface LawArticleContentProps {
  article: ArticleData;
  rawArtNum: string;
  onOpenPdf: () => void;
  t: TFunction;
}

export const LawArticleContent: React.FC<LawArticleContentProps> = ({
  article,
  rawArtNum,
  onOpenPdf,
  t,
}) => {
  const [searchParams] = useSearchParams();
  const highlightQuery = searchParams.get('highlight') || '';
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const isPreamble =
    rawArtNum === '0' ||
    rawArtNum.toLowerCase() === 'preambula' ||
    rawArtNum.toLowerCase() === 'hyrja';

  const articleHeading = isPreamble
    ? t('lawArticle.preamble', 'Preambula')
    : `${t('lawArticle.article', 'Neni')} ${rawArtNum}`;

  const highlightWords = useMemo(() => {
    if (!highlightQuery.trim()) return [];
    return sanitizeSearchText(highlightQuery)
      .split(/\s+/)
      .filter((w) => w.length >= 3 && !['nga', 'per', 'dhe', 'ose', 'tek'].includes(w));
  }, [highlightQuery]);

  const paragraphs = useMemo(() => {
    if (!article.text) return [];
    return article.text
      .split(/\n+/)
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
  }, [article.text]);

  const renderHighlightedText = (text: string) => {
    if (highlightWords.length === 0) return text;

    const escapedTokens = highlightWords.map((token) =>
      token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
    );
    // V31.0: word boundary në TË DYJA anët
    const regex = new RegExp(`\\b(${escapedTokens.join('|')})\\b`, 'gi');

    const parts = text.split(regex);

    return parts.map((part, i) => {
      const isMatch = highlightWords.some(
        (hw) => sanitizeSearchText(part) === hw,
      );
      if (isMatch) {
        return (
          <mark
            key={i}
            className="bg-amber-400/30 text-amber-900 dark:text-amber-200 border-b border-amber-500 font-semibold px-1 py-0.5 rounded transition-all"
          >
            {part}
          </mark>
        );
      }
      return part;
    });
  };

  const handleCopyParagraph = async (text: string, index: number) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback për kontekst jo-secure
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Kopjimi dështoi:', err);
    }
  };

  return (
    <div className="flex flex-col overflow-hidden shadow-sm border border-main rounded-2xl bg-canvas">
      {article.is_repealed && (
        <div className="px-4 sm:px-8 py-3 bg-warning-start/10 border-b-2 border-warning-start/40 flex items-center gap-2">
          <AlertTriangle size={16} className="text-warning-start shrink-0" />
          <span className="text-xs font-bold text-warning-start uppercase tracking-wider">
            {t('lawArticle.repealedBanner', 'Ky nen i përket një ligji të shfuqizuar')}
          </span>
        </div>
      )}

      <div className="px-4 sm:px-8 py-4 sm:py-6 border-b border-main bg-surface/50">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={onOpenPdf}
              className="h-8 sm:h-9 px-3 sm:px-3.5 flex items-center gap-1.5 sm:gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 rounded-xl text-[11px] sm:text-xs font-semibold transition-all hover-lift cursor-pointer"
              title={t('lawArticle.openPdf', 'Shiko dokumentin PDF të plotë')}
            >
              <FileText size={13} />
              <span>{t('lawArticle.pdfDocument', 'Dokumenti PDF')}</span>
              <ExternalLink size={11} className="opacity-80 shrink-0" />
            </button>
          </div>

          <h1 className="text-base sm:text-xl md:text-2xl font-black text-text-primary leading-snug tracking-tight">
            {article.law_title}
          </h1>
        </div>
      </div>

      <div className="px-2 sm:px-6 md:px-8 py-4 sm:py-10 flex justify-center bg-canvas">
        <div className="w-full max-w-[85ch] bg-surface border border-main rounded-2xl shadow-md p-4 sm:p-10 md:p-12 relative">
          <div className="text-center pb-4 sm:pb-5 mb-5 sm:mb-7 border-b border-main">
            <h2 className="text-xl sm:text-2xl md:text-3xl font-black text-text-primary uppercase tracking-wide font-serif">
              {articleHeading}
            </h2>
          </div>

          <div className="space-y-6">
            {paragraphs.map((paragraph, index) => {
              const isCopied = copiedIndex === index;
              return (
                <div
                  key={index}
                  className="group relative p-3 sm:p-4 rounded-xl hover:bg-canvas/60 border border-transparent hover:border-main transition-all duration-200"
                >
                  <p className="text-[14px] sm:text-[16px] md:text-[17px] text-text-primary leading-[1.75] sm:leading-[1.85] font-normal text-justify font-serif tracking-normal selection:bg-primary-start/20">
                    {renderHighlightedText(paragraph)}
                  </p>

                  <div className="mt-3 pt-2 border-t border-main/40 flex items-center justify-between flex-wrap gap-2 text-xs">
                    <span className="text-[10px] font-mono font-bold text-text-muted uppercase">
                      {t('lawArticle.paragraph', 'Paragrafi')} {index + 1}
                    </span>

                    <div className="opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        type="button"
                        onClick={() => handleCopyParagraph(paragraph, index)}
                        className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                          isCopied
                            ? 'bg-emerald-500 text-white border-emerald-500'
                            : 'bg-canvas hover:bg-surface border-main text-text-secondary hover:text-text-primary'
                        }`}
                        title={t('lawArticle.copyParagraphTitle', 'Kopjo tekstin e këtij paragrafi')}
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                        <span>
                          {isCopied
                            ? t('lawArticle.copied', 'U kopjua!')
                            : t('lawArticle.copyParagraph', 'Kopjo Paragrafin')}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LawArticleContent;