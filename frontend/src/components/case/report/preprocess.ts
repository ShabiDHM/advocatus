// FILE: frontend/src/components/case/report/preprocess.ts
// PHOENIX PROTOCOL - REPORT PREPROCESS V1.0
// Ekstraktuar nga DraftVerificationModal V3.10.
// Emoji → simbole tipografike për pamje profesionale.

import { STATUS_MARK } from './typography';

// ───────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ───────────────────────────────────────────────────────────────────────────

const WORD_CODE_BG = '#f1f5f9';
const WORD_BLOCKQUOTE_BORDER = '#94a3b8';
const WORD_BLOCKQUOTE_BG = 'transparent';
const WORD_BLOCKQUOTE_TEXT = '#334155';
const WORD_HR_COLOR = '#cbd5e1';
const WORD_HEADING_COLOR = '#0f172a';
const WORD_BODY_COLOR = '#1e293b';

// ───────────────────────────────────────────────────────────────────────────
// PREPROCESS MARKDOWN
// ───────────────────────────────────────────────────────────────────────────

export const preprocessReport = (markdown: string): string => {
  if (!markdown) return '';
  return markdown
    // Marker-t e backend → simbole tipografike
    .replace(/\[OK\]/g, STATUS_MARK.ok)
    .replace(/\[X\]/g, STATUS_MARK.fail)
    .replace(/\[!\]/g, STATUS_MARK.warn)
    .replace(/\[\?\]/g, STATUS_MARK.hint)
    // Emoji → simbole (për raporte të vjetra me emoji)
    .replace(/✅/g, STATUS_MARK.ok)
    .replace(/❌/g, STATUS_MARK.fail)
    .replace(/⚠️/g, STATUS_MARK.warn)
    .replace(/💡/g, STATUS_MARK.hint)
    .replace(/🛑\s*/g, STATUS_MARK.forbid + ' ')
    .replace(/ℹ️\s*/g, '')
    // Heq emoji dekorativë (precedent, sparkles)
    .replace(/⚖️\s*/g, '')
    .replace(/📅\s*/g, '')
    .replace(/📚\s*/g, '')
    .replace(/🧪\s*/g, '')
    .replace(/🔍\s*/g, '')
    .replace(/📌\s*/g, '')
    .replace(/🎯\s*/g, '')
    // Ndryshimet semantike EN → SQ
    .replace(/\*\*File:\*\*/g, '**Dokumenti:**')
    .replace(/\*\*File\*\*/g, '**Dokumenti**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*NEEDS WORK\*\*/g, '**Gatishmëria:** **KËRKON PUNË**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*READY\*\*/g, '**Gatishmëria:** **GATI**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*INCOMPLETE\*\*/g, '**Gatishmëria:** **I PËRPLOTË**')
    .replace(/\*\*Gatishmëria:\*\*\s*\*\*UNKNOWN\*\*/g, '**Gatishmëria:** **I PANJOHUR**')
    .replace(/\bNEEDS WORK\b/g, 'KËRKON PUNË')
    .replace(/\bINCOMPLETE\b/g, 'I PËRPLOTË')
    .replace(/\bUNKNOWN\b/g, 'I PANJOHUR')
    .replace(/⚠️ SUGJERIM/g, STATUS_MARK.hint + ' **SUGJERIM**');
};

// ───────────────────────────────────────────────────────────────────────────
// MARKDOWN → PLAIN TEXT (për clipboard fallback)
// ───────────────────────────────────────────────────────────────────────────

export const stripInlineMarkdown = (text: string): string => {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
};

export const markdownToPlainText = (markdown: string): string => {
  if (!markdown) return '';
  const lines = markdown.split(/\r?\n/);
  const out: string[] = [];
  let consecutiveBlanks = 0;

  const pushBlank = () => {
    if (consecutiveBlanks < 1) { out.push(''); consecutiveBlanks++; }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { pushBlank(); continue; }
    consecutiveBlanks = 0;

    if (/^(---|---|\*\*\*|___)$/.test(line)) { out.push('─'.repeat(60)); continue; }

    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      const lvl = h[1].length;
      const text = stripInlineMarkdown(h[2]).trim();
      if (lvl === 1) {
        out.push(''); out.push(text.toUpperCase());
        out.push('═'.repeat(Math.min(60, Math.max(20, text.length))));
      } else if (lvl === 2) {
        out.push(''); out.push(text.toUpperCase());
        out.push('─'.repeat(Math.min(60, Math.max(20, text.length))));
      } else if (lvl === 3) {
        out.push(''); out.push(`◆ ${text}`);
      } else {
        out.push(''); out.push(`▸ ${text}`);
      }
      continue;
    }

    if (line.startsWith('>')) {
      out.push(`    "${stripInlineMarkdown(line.replace(/^>\s?/, ''))}"`);
      continue;
    }

    const bullet = line.match(/^([•\-\*])\s+(.+)$/);
    if (bullet) { out.push(`  • ${stripInlineMarkdown(bullet[2])}`); continue; }

    const num = line.match(/^(\d+)\.\s+(.+)$/);
    if (num) { out.push(`  ${num[1]}. ${stripInlineMarkdown(num[2])}`); continue; }

    out.push(stripInlineMarkdown(line));
  }

  while (out.length > 0 && out[0] === '') out.shift();
  while (out.length > 0 && out[out.length - 1] === '') out.pop();
  return out.join('\n');
};

// ───────────────────────────────────────────────────────────────────────────
// MARKDOWN → WORD HTML (për clipboard richtext + PDF export)
// ───────────────────────────────────────────────────────────────────────────

export const markdownToWordHtml = (markdown: string): string => {
  const lines = markdown.split(/\r?\n/);
  const htmlOutput: string[] = [];
  let inList: 'ul' | 'ol' | null = null;
  let inBlockquote = false;
  let blockquoteLines: string[] = [];

  const formatInline = (text: string): string => {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, `<code style="background-color: ${WORD_CODE_BG}; padding: 2px 4px; font-family: Consolas, monospace; font-size: 10pt;">$1</code>`);
  };

  const flushList = () => {
    if (inList) { htmlOutput.push(inList === 'ul' ? '</ul>' : '</ol>'); inList = null; }
  };

  const flushBlockquote = () => {
    if (inBlockquote) {
      htmlOutput.push(`<blockquote style="border-left: 3px solid ${WORD_BLOCKQUOTE_BORDER}; margin: 10px 0; padding: 8px 16px; background-color: ${WORD_BLOCKQUOTE_BG}; color: ${WORD_BLOCKQUOTE_TEXT}; font-style: italic; font-family: Georgia, serif;">${blockquoteLines.map(formatInline).join('<br>')}</blockquote>`);
      blockquoteLines = []; inBlockquote = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (/^(---|---|\*\*\*|___)$/.test(line)) {
      flushList(); flushBlockquote();
      htmlOutput.push(`<hr style="border: 0; border-top: 1px solid ${WORD_HR_COLOR}; margin: 16px 0;" />`);
      continue;
    }

    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushList(); flushBlockquote();
      const level = hMatch[1].length;
      const text = formatInline(hMatch[2]);
      const fontSize = level === 1 ? '16pt' : level === 2 ? '13pt' : '11.5pt';
      const fontFamily = level <= 2 ? 'Georgia, serif' : 'Georgia, serif';
      htmlOutput.push(`<h${level} style="font-size: ${fontSize}; font-family: ${fontFamily}; font-weight: bold; color: ${WORD_HEADING_COLOR}; margin-top: 14px; margin-bottom: 6px;">${text}</h${level}>`);
      continue;
    }

    if (line.startsWith('>')) { flushList(); inBlockquote = true; blockquoteLines.push(line.replace(/^>\s?/, '')); continue; }
    else if (inBlockquote) { flushBlockquote(); }

    const bulletMatch = line.match(/^([•\-\*])\s+(.+)$/);
    if (bulletMatch) {
      if (inList !== 'ul') { flushList(); htmlOutput.push('<ul style="margin: 6px 0 6px 24px; padding: 0; font-family: Georgia, serif;">'); inList = 'ul'; }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: ${WORD_BODY_COLOR}; font-size: 11pt;">${formatInline(bulletMatch[2])}</li>`);
      continue;
    }

    const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      if (inList !== 'ol') { flushList(); htmlOutput.push('<ol style="margin: 6px 6px 6px 24px; padding: 0; font-family: Georgia, serif;">'); inList = 'ol'; }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: ${WORD_BODY_COLOR}; font-size: 11pt;">${formatInline(numMatch[2])}</li>`);
      continue;
    }

    flushList();
    if (line.length === 0) continue;
    htmlOutput.push(`<p style="margin: 6px 0; font-family: Georgia, serif; font-size: 11pt; line-height: 1.55; color: ${WORD_BODY_COLOR};">${formatInline(line)}</p>`);
  }

  flushList(); flushBlockquote();

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Raport Verifikimi</title>
    <style>body { font-family: Georgia, serif; font-size: 11pt; line-height: 1.55; color: ${WORD_BODY_COLOR}; }</style>
    </head><body>${htmlOutput.join('\n')}</body></html>`.trim();
};