// FILE: frontend/src/utils/albanianLegalTranslator.ts
// PHOENIX PROTOCOL - CLEAN ALBANIAN LEGAL TRANSLATION UTILITY V1.0

export const RELATION_ALBANIAN_MAP: Record<string, string> = {
  IMPLEMENTED_BY: 'ZBATUAR NGA',
  IMPLEMENTED: 'ZBATUAR NGA',
  CONTRACTED_BY: 'KONTRAKTUAR NGA',
  CONTRACTED: 'KONTRAKTUAR ME',
  CONTRACTED_WITH: 'KONTRAKTUAR ME',
  REPRESENTED_BY: 'PËRFAQËSOHET NGA',
  REPRESENTS: 'PËRFAQËSON',
  ASSOCIATED_WITH: 'LIDHUR ME',
  ASSOCIATED: 'LIDHUR ME',
  TRANSFERRED_FUNDS: 'TRANSAKSION FINANCIAR',
  TRANSFER_FUNDS: 'TRANSAKSION FINANCIAR',
  PAID_TO: 'PAGESË NDAJ',
  PAYMENT: 'PAGESË FINANCIARE',
  EMPLOYED_BY: 'I PUNËSUAR NË',
  WORKED_AT: 'I PUNËSUAR NË',
  EMPLOYEE: 'I PUNËSUAR NË',
  OWNED_BY: 'PRONËSI E',
  OWNS: 'PRONËSI E',
  OWNER: 'PRONAR NË',
  PRESENT_AT: 'PRANISHËM NË',
  LOCATED_AT: 'VENDNDODHJA',
  LOCATED_IN: 'VENDNDODHJA',
  CONTRADICTS: 'KUNDËRTHËNIE ME PROVËN',
  OWES_MONEY: 'DETYRIM FINANCIAR',
  SIGNED: 'NËNSHKRUAR NGA',
  SIGNED_BY: 'NËNSHKRUAR NGA',
  MENTIONED_IN: 'PËRMENDUR NË SHKRESË',
  HAS_ACCOUNT: 'LLOGARI BANKARE',
  PARTY_TO: 'PALË NË KONTRAKT',
  ISSUED_BY: 'LËSHUAR NGA',
  FINANCED_BY: 'FINANCUAR NGA',
  SUBMITTED_TO: 'DORËZUAR NË',
};

export const translateToAlbanian = (text?: string): string => {
  if (!text) return '';
  
  let translated = text;

  // Common German & English legal phrases translated to Shqip
  translated = translated
    .replace(/Dienstleistungsvertrag/gi, "Kontratë Shërbimi")
    .replace(/Vertrag/gi, "Kontratë")
    .replace(/Auftragnehmer/gi, "Kontraktuesi")
    .replace(/Auftraggeber/gi, "Porositësi / Punëdhënësi")
    .replace(/Durchführungspartner/gi, "Partner i Zbatimit")
    .replace(/Berater/gi, "Konsulent")
    .replace(/Rechnung/gi, "Faturë Financiale")
    .replace(/Überweisung/gi, "Transaksion Pagese")
    .replace(/Zahlung/gi, "Pagesë Financiale")
    .replace(/wird erwähnt als/gi, "përmendet si")
    .replace(/is mentioned as Consultant in the/gi, "përmendet si Konsulent në")
    .replace(/is mentioned as Consultant in/gi, "përmendet si Konsulent në")
    .replace(/is mentioned as/gi, "përmendet si")
    .replace(/is mentioned in the/gi, "përmendet në")
    .replace(/is mentioned in/gi, "përmendet në")
    .replace(/mentioned as/gi, "përmendet si")
    .replace(/mentioned in/gi, "përmendet në")
    .replace(/The direct local partner in the country of the assignment is the/gi, "Partneri direkt lokal në vendin e angazhimit është")
    .replace(/The direct local partner in the country of the assignment is/gi, "Partneri direkt lokal në vendin e angazhimit është")
    .replace(/The direct local partner/gi, "Partneri direkt lokal")
    .replace(/in the country of the assignment/gi, "në vendin e angazhimit")
    .replace(/Freelance Contract/gi, "Kontratë Shërbimi (Freelance)")
    .replace(/Service Contract/gi, "Kontratë Shërbimi")
    .replace(/Employment Contract/gi, "Kontratë Pune")
    .replace(/Indictment/gi, "Aktakuzë Gjyqësore")
    .replace(/Court Hearing/gi, "Seancë Gjyqësore")
    .replace(/Implemented by/gi, "Zbatuar nga")
    .replace(/Contracted by/gi, "Kontraktuar nga")
    .replace(/Signed by/gi, "Nënshkruar nga")
    .replace(/Submitted to/gi, "Dorëzuar në")
    .replace(/Issued by/gi, "Lëshuar nga")
    .replace(/Financed by/gi, "Financuar nga")
    .replace(/Bank Account/gi, "Llogari Bankare")
    .replace(/Payment transfer/gi, "Transaksion pagese")
    .replace(/According to article/gi, "Sipas nenit")
    .replace(/pursuant to/gi, "në bazë të")
    .replace(/in accordance with/gi, "në përputhje me")
    .replace(/on behalf of/gi, "në emër të")
    .replace(/in the amount of/gi, "në shumën prej")
    .replace(/amount of/gi, "shumën prej")
    .replace(/transfer of funds/gi, "transferimin e mjeteve financiare")
    .replace(/paid to/gi, "paguar ndaj")
    .replace(/contract signed between/gi, "kontratë e nënshkruar ndërmjet")
    .replace(/for the project/gi, "për projektin")
    .replace(/located in/gi, "me vendndodhje në")
    .replace(/registered in/gi, "i regjistruar në")
    .replace(/Defendant/gi, "I Padituri")
    .replace(/Plaintiff/gi, "Paditësi")
    .replace(/Witness/gi, "Dëshmitari");

  return translated;
};

export const formatRelationText = (rel: string): string => {
  if (!rel) return 'LIDHJE LIGJORE';
  
  let clean = rel.toUpperCase().trim().replace(/ /g, '_');
  
  if (RELATION_ALBANIAN_MAP[clean]) {
    return RELATION_ALBANIAN_MAP[clean];
  }

  return clean
    .replace(/_BY$/g, ' NGA')
    .replace(/_WITH$/g, ' ME')
    .replace(/_TO$/g, ' NDAJ')
    .replace(/_IN$/g, ' NË')
    .replace(/_AT$/g, ' NË')
    .replace(/_FOR$/g, ' PËR')
    .replace(/IMPLEMENTED/g, 'ZBATUAR')
    .replace(/CONTRACTED/g, 'KONTRAKTUAR')
    .replace(/TRANSFERRED/g, 'TRANSAKSION')
    .replace(/FUNDS/g, 'FINANCIAR')
    .replace(/ASSOCIATED/g, 'LIDHUR')
    .replace(/MENTIONED/g, 'PËRMENDUR')
    .replace(/SIGNED/g, 'NËNSHKRUAR')
    .replace(/BY$/g, 'NGA')
    .replace(/_/g, ' ');
};