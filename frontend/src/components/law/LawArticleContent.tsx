// FILE: src/components/law/LawArticleContent.tsx
import React from 'react';
import { GraduationCap, BookOpen, FileText, ExternalLink, Scale, ChevronLeft, ChevronRight, ShieldCheck } from 'lucide-react';
import { ArticleData, SourceInfo } from './lawArticleTypes';
import { TFunction } from 'i18next';

interface LawArticleContentProps {
  article: ArticleData;
  sourceInfo: SourceInfo | null;
  isAcademicDoc: boolean;
  rawArtNum: string;
  prevArticleNum: string | null;
  nextArticleNum: string | null;
  onNavigateToArticle: (num: string) => void;
  onOpenPdf: () => void;
  t: TFunction;
}

export const LawArticleContent: React.FC<LawArticleContentProps> = ({
  article,
  sourceInfo,
  isAcademicDoc,
  rawArtNum,
  prevArticleNum,
  nextArticleNum,
  onNavigateToArticle,
  onOpenPdf,
  t,
}) => {
  return (
    <div className="p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-2xl">
      <div className="bg-canvas px-6 sm:px-8 py-8 border-b border-main relative overflow-hidden">
        <div className="relative z-10 flex flex-col gap-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
              {isAcademicDoc ? <GraduationCap size={14} /> : <BookOpen size={14} />}
              <span className="text-[10px] font-black uppercase tracking-wider">
                {isAcademicDoc ? 'UDHËZUES I AKADEMISË SË DREJTËSISË' : t('lawArticle.lawTitle', 'LIGJI ZYRTAR')}
              </span>
            </div>

            <button
              type="button"
              onClick={onOpenPdf}
              className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3 py-1 rounded-lg transition-all hover-lift cursor-pointer focus:outline-none"
              title="Shiko dokumentin PDF të plotë zyrtar"
            >
              <FileText size={14} />
              <span className="text-[10px] font-bold uppercase tracking-wider truncate max-w-[200px] sm:max-w-[300px]">
                {article.source}
              </span>
              <ExternalLink size={12} className="opacity-80 shrink-0" />
            </button>
          </div>

          <h1 className="text-xl sm:text-2xl font-black text-text-primary leading-tight tracking-tight">{article.law_title}</h1>
          <div className="flex items-center justify-between border-t border-main/50 pt-4 mt-1">
            <div className="flex items-center gap-3">
              <Scale size={20} className="text-primary-start" />
              <p className="text-base font-black text-primary-start uppercase tracking-wider">
                {(() => {
                  const cleanNum = rawArtNum;
                  const isPreamble = cleanNum === '0' || cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja';
                  return isPreamble ? 'Preambula' : `${t('lawArticle.article', 'Neni')} ${cleanNum}`;
                })()}
              </p>
            </div>

            <div className="flex items-center gap-2">
              {prevArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => onNavigateToArticle(prevArticleNum)}
                  className="p-2 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start transition-colors cursor-pointer"
                  title="Neni i Mëparshëm"
                >
                  <ChevronLeft size={16} />
                </button>
              )}
              {nextArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => onNavigateToArticle(nextArticleNum)}
                  className="p-2 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start transition-colors cursor-pointer"
                  title="Neni i Ardhshëm"
                >
                  <ChevronRight size={16} />
                </button>
              )}
            </div>
          </div>

          {sourceInfo && (
            <div className="mt-2 p-4 rounded-2xl bg-surface border border-main shadow-sm font-mono text-xs text-text-primary">
              <div className="flex flex-wrap items-center justify-between pb-2.5 mb-2.5 border-b border-main/70 gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-base">{sourceInfo.confidence?.icon || '📜'}</span>
                  <span className="font-black text-xs uppercase tracking-wider text-emerald-500 dark:text-emerald-400">
                    {sourceInfo.confidence?.label || 'Tekst Zyrtar i Verifikuar'}
                  </span>
                </div>
                <span className="text-xs font-mono font-black px-2.5 py-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-inner">
                  100% verifikuar
                </span>
              </div>

              <div className="font-bold text-xs sm:text-sm text-text-primary leading-relaxed mb-1 font-sans">
                {sourceInfo.matched_law || article.law_title}
              </div>

              <div className="text-xs font-bold text-primary-start mb-2">
                Neni {sourceInfo.matched_article || article.article_number}
              </div>

              <div className="text-xs font-medium border-t border-main/50 pt-2.5 mt-2 flex items-center gap-1.5 font-sans text-emerald-500">
                <ShieldCheck size={15} className="shrink-0 text-emerald-500" />
                <span>{sourceInfo.verification_hint || 'Ky nen është verifikuar nga Kodi Zyrtar i Kosovës.'}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-canvas/50 px-2 sm:px-10 py-12 flex justify-center">
        <div className="w-full max-w-[95ch] bg-surface border border-main rounded-2xl sm:rounded-r-3xl sm:rounded-l-lg shadow-2xl p-8 sm:p-16 relative overflow-hidden transition-all duration-300">
          <div className="absolute top-0 bottom-0 left-0 w-4 bg-gradient-to-r from-black/20 via-primary-start/1 to-transparent pointer-events-none border-r border-main/40 hidden sm:block" />
          <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-8 bg-gradient-to-r from-transparent via-black/5 to-transparent pointer-events-none hidden sm:block" />

          <div className="text-center pb-6 mb-8 border-b border-main/60 relative z-10">
            <h2 className="text-2xl sm:text-3xl font-black text-text-primary uppercase tracking-tight font-serif">
              {(() => {
                const cleanNum = rawArtNum;
                const isPreamble = cleanNum === '0' || cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja';
                return isPreamble ? 'Preambula' : `Neni ${cleanNum}`;
              })()}
            </h2>
          </div>

          <div className="text-[15px] sm:text-[17px] text-text-primary leading-[1.75] font-normal whitespace-pre-wrap text-justify font-serif selection:bg-primary-start/20 relative z-10 px-0 sm:px-6">
            {article.text}
          </div>

          <div className="mt-14 pt-6 border-t border-main/40 flex justify-between items-center text-xs sm:text-sm font-mono relative z-10">
            <span className="text-text-muted">Kodi Juridik i Republikës së Kosovës</span>
            <span className="text-text-muted">§</span>
            <span className="font-bold flex items-center gap-1.5 text-emerald-500">✅ Burim Zyrtar i Verifikuar</span>
          </div>
        </div>
      </div>
    </div>
  );
};