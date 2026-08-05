// FILE: src/components/law/lawLibraryTypes.ts

export interface LawResult {
  law_title: string;
  article_number?: string;
  chunk_id: string;
  source?: string;
  text?: string;
}

export const DEFAULT_LAWS: string[] = [
  'LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS',
  'KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS',
  'KODI NR. 08/L-032 I PROCEDURËS PENALE',
  'LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE',
  'LIGJI NR. 03/L-212 I PUNËS',
  'LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE',
  'LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE',
  'LIGJI NR. 03/L-006 PËR CONTESTIN PROCEDURAL',
  'LIGJI NR. 04/L-139 PËR PROCEDURËN EKZEKUTIVE',
  'LIGJI NR. 05/L-031 PËR PROCEDURËN ADMINISTRATIVE',
];