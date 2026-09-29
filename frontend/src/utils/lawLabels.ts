// FILE: src/utils/lawLabels.ts
// PHOENIX PROTOCOL - LAW LABELS TRANSLATOR V1.0
//
// Përkthen termat teknikë (match_type, confidence.level) në shqip.
// Përdoret nga: PrecedentCitationLink, LawCitationLink, LawArticleHeader.

import type { TFunction } from 'i18next';

// ═══════════════════════════════════════════════════════════════════════════
// MATCH TYPE
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Përkthen `source_info.match_type` / `title_match_type` në shqip.
 *
 * Vlerat e njohura:
 *   exact, case_number_exact, law_title_exact → "Përputhje e saktë"
 *   code                                       → "Përputhje me kod ligjor"
 *   substring, case_number_regex, law_title_regex → "Përputhje e pjesshme"
 *   word                                       → "Përputhje fjalësh"
 *   text_reference                             → "Vetëm referencë në tekst"
 *   unknown                                    → "I panjohur"
 */
export function getMatchTypeLabel(
  matchType: string | undefined | null,
  t: TFunction,
): string {
  if (!matchType) return t('lawLabels.matchUnknown', 'I panjohur');

  const mt = matchType.toLowerCase();

  if (
    mt === 'exact' ||
    mt === 'case_number_exact' ||
    mt === 'law_title_exact'
  ) {
    return t('lawLabels.matchExact', 'Përputhje e saktë');
  }

  if (mt === 'code') {
    return t('lawLabels.matchCode', 'Përputhje me kod ligjor');
  }

  if (
    mt === 'substring' ||
    mt === 'case_number_regex' ||
    mt === 'law_title_regex'
  ) {
    return t('lawLabels.matchSubstring', 'Përputhje e pjesshme');
  }

  if (mt === 'word') {
    return t('lawLabels.matchWord', 'Përputhje fjalësh');
  }

  if (mt === 'text_reference') {
    return t('lawLabels.matchTextReference', 'Vetëm referencë në tekst');
  }

  return t('lawLabels.matchUnknown', 'I panjohur');
}

// ═══════════════════════════════════════════════════════════════════════════
// CONFIDENCE LEVEL
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Përkthen `confidence.level` në shqip.
 *
 * Vlerat: HIGH | MEDIUM | LOW | NONE
 */
export function getConfidenceLevelLabel(
  level: string | undefined | null,
  t: TFunction,
): string {
  if (!level) return t('lawLabels.confidenceUnknown', 'I panjohur');

  switch (level.toUpperCase()) {
    case 'HIGH':
      return t('lawLabels.confidenceHigh', 'E lartë');
    case 'MEDIUM':
      return t('lawLabels.confidenceMedium', 'Mesatare');
    case 'LOW':
      return t('lawLabels.confidenceLow', 'E dobët');
    case 'NONE':
      return t('lawLabels.confidenceNone', 'Asnjë');
    default:
      return t('lawLabels.confidenceUnknown', 'I panjohur');
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// STATUS BADGES (për PrecedentCitationLink)
// ═══════════════════════════════════════════════════════════════════════════

export function getPrecedentBadgeLabel(
  status: string,
  t: TFunction,
): string {
  switch (status) {
    case 'idle':
      return t('precedentCitation.statusIdleShort', 'I PAVERIFIKUAR');
    case 'loading':
      return t('precedentCitation.statusLoadingShort', 'DUKE NGARKUAR');
    case 'verified_exact':
      return t('precedentCitation.statusVerifiedExactShort', 'VERIFIKUAR');
    case 'verified_regex':
      return t('precedentCitation.statusVerifiedRegexShort', 'VERIFIKUAR');
    case 'reference_only':
      return t('precedentCitation.statusReferenceOnlyShort', 'REFERENCË');
    case 'unverified':
      return t('precedentCitation.statusUnverifiedShort', 'I PAVERIFIKUAR');
    case 'error':
      return t('precedentCitation.statusErrorShort', 'GABIM');
    default:
      return t('precedentCitation.statusIdleShort', 'I PAVERIFIKUAR');
  }
}