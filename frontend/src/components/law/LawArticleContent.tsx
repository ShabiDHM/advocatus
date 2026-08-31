// FILE: src/components/law/LawArticleContent.tsx
// PHOENIX PROTOCOL - CLEAN & MINIMALIST LAW ARTICLE CONTENT (NO REDUNDANT FOOTER)

import React from 'react';
import { FileText, ExternalLink } from 'lucide-react';
import { ArticleData } from './lawArticleTypes';
import { TFunction } from 'i18next';

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
  const isPreamble =
    rawArtNum === '0' ||
    rawArtNum.toLowerCase() === 'preambula' ||
    rawArtNum.toLowerCase() === 'hyrja';

  const articleHeading = isPreamble ? 'Preambula' : `${t('lawArticle.article', 'Neni')} ${rawArtNum}`;

  return (
    <div className="flex flex-col overflow-hidden shadow-sm border border-main rounded-2xl bg-canvas">
      {/* Header i Pastër i Ligjit */}
      <div className="px-6 sm:px-8 py-6 border-b border-main bg-surface/50">
        <div className="flex flex-col gap-4">
          <div className="flex items-center">
            {/* Butoni Dokumenti PDF majtas */}
            <button
              type="button"
              onClick={onOpenPdf}
              className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3.5 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all hover-lift cursor-pointer"
              title="Shiko dokumentin PDF të plotë"
            >
              <FileText size={14} />
              <span>Dokumenti PDF</span>
              <ExternalLink size={12} className="opacity-80 shrink-0" />
            </button>
          </div>

          {/* Titulli Kryesor i Ligjit */}
          <h1 className="text-lg sm:text-xl md:text-2xl font-black text-text-primary leading-tight tracking-tight">
            {article.law_title}
          </h1>
        </div>
      </div>

      {/* Trupi i Dokumentit / Neni (pa footer të panevojshëm) */}
      <div className="px-3 sm:px-8 py-8 sm:py-12 flex justify-center bg-canvas">
        <div className="w-full max-w-[90ch] bg-surface border border-main rounded-2xl shadow-lg p-6 sm:p-12 md:p-14 relative">
          
          {/* Titulli i Nenit */}
          <div className="text-center pb-6 mb-8 border-b border-main">
            <h2 className="text-2xl sm:text-3xl font-black text-text-primary uppercase tracking-wide font-serif">
              {articleHeading}
            </h2>
          </div>

          {/* Përmbajtja e Nenit */}
          <div className="text-[15px] sm:text-[16px] md:text-[17px] text-text-primary leading-[1.85] font-normal whitespace-pre-line text-left font-serif tracking-normal selection:bg-primary-start/20">
            {article.text}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LawArticleContent;