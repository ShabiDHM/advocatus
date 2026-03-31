// FILE: src/drafting/utils/promptConstructor.ts
// ARCHITECTURE: ZERO-HALLUCINATION ROUTING & FACT EXTRACTION (ALBANIAN NATIVE)

import { TFunction } from 'i18next';
import { TemplateType } from '../types';
import { getDocumentStructureInstructions } from './templateHelpers';

export const constructSmartPrompt = (userText: string, template: TemplateType, _t: TFunction): string => {
  
  // 1. Map Templates to Accurate Kosovo Legal Domains
  // We removed the dangerous assumption that all lawsuits are Family Law.
  const getDomainInstruction = (tmpl: TemplateType) => {
    const mapping: Record<string, string> = {
      // Procedural Documents (Litigation)
      padi: "PROCEDURA KONTESTIMORE: Zbatoni 'Ligjin për Procedurën Kontestimore (LCP)'. Identifikoni natyrën e mosmarrëveshjes nga faktet e përdoruesit për të gjetur bazën e saktë materiale (psh. Detyrimore, Familjare, Pronësore).",
      pergjigje: "PROCEDURA KONTESTIMORE (MBROJTJA): Zbatoni 'Ligjin për Procedurën Kontestimore'. Përgatitni prapësimet procedurale dhe materiale bazuar në mbrojtjen e palës së paditur.",
      kunderpadi: "PROCEDURA KONTESTIMORE: Formoni kundërpadinë sipas kushteve të 'Ligjit për Procedurën Kontestimore', duke u lidhur me të njëjtin raport juridik.",
      ankese: "MJETET E RREGULLTA JURIDIKE: Zbatoni rregullat e ankesës sipas LCP-së (Shkelje thelbësore, vërtetim i gabuar i fakteve, zbatim i gabuar i ligjit material).",
      prapësim: "PROCEDURA PËRMBARIMORE / URDHËRESAT: Harto prapësimin sipas 'Ligjit për Procedurën Përmbarimore' ose procedurës përkatëse kundër urdhëresës.",
      
      // Corporate & Obligations
      nda: "E DREJTA KOMERCIALE: Zbatoni 'Ligjin për Shoqëritë Tregtare' dhe 'Ligjin për Marrëdhëniet e Detyrimeve (LMD)'. Fokus në mbrojtjen e sekretit afarist.",
      mou: "E DREJTA DETYRIMORE/KOMERCIALE: Draftoni si një marrëveshje paraparake/mirëkuptimi bazuar në parimin e lirisë së kontraktimit (LMD).",
      shareholders: "E DREJTA KOMERCIALE: Baza strikte në 'Ligjin për Shoqëritë Tregtare' (Rregullimi i raporteve mes ortakëve/aksionarëve, menaxhimi, transferimi i kuotave).",
      sla: "E DREJTA DETYRIMORE: Kontratë për ofrimin e shërbimeve sipas LMD-së. Thekso standardet e performancës dhe penalitetet.",
      
      // Employment Law
      employment_contract: "E DREJTA E PUNËS: Zbatim strikt i 'Ligjit të Punës së Kosovës'. Përfshi kushtet obligative: orari, paga, pushimi, dhe shkëputja.",
      termination_notice: "E DREJTA E PUNËS: Zbatim strikt i neneve për ndërprerjen e kontratës nga 'Ligji i Punës' (arsyetimi, paralajmërimi, koha e njoftimit).",
      warning_letter: "E DREJTA E PUNËS: Vërejtje disiplinore sipas 'Ligjit të Punës' me paralajmërim për pasojat juridike në rast të përsëritjes.",

      // Real Estate / Property
      lease_agreement: "E DREJTA DETYRIMORE / SENDORE: Zbatoni dispozitat për qiranë sipas 'Ligjit për Marrëdhëniet e Detyrimeve'.",
      sales_purchase: "E DREJTA DETYRIMORE: Kontratë Shitblerjeje. Siguro kalimin e pronësisë dhe mbrojtjen nga tëmetat juridike/fizike sipas LMD.",
      power_of_attorney: "E DREJTA DETYRIMORE: Përfaqësimi dhe Autorizimi sipas 'Ligjit për Marrëdhëniet e Detyrimeve'.",
    };

    return mapping[tmpl] || "KORNIZA E PËRGJITHSHME JURIDIKE: Zbatoni 'Ligjin për Marrëdhëniet e Detyrimeve' dhe parimet e përgjithshme të së drejtës në Kosovë.";
  };

  const domainInstruction = getDomainInstruction(template);

  // 2. Clear Role Alignment
  const roleInstruction = template === 'pergjigje' || template === 'ankese' || template === 'prapësim'
    ? "AVOKATI MBROJTËS (Përfaqësimi i të Paditurit / Debitorit)" 
    : "AVOKAT I SPECIALIZUAR (Hartuesi Kryesor)";

  // 3. Strict Structural and Placeholder Rules (Aligned with UI Regex)
  const structuralRules = `
UDHËZIME STRUKTURALE DHE KUNDËR HALUCINACIONEVE:
1. PËRSHTATJA E LIGJIT: Udhëzimi i mësipërm i fushës është baza juaj. Mos shpikni ligje të huaja.
2. PLACEHOLDERS (SHUMË E RËNDËSISHME): Nëse përdoruesi NUK ka dhënë një emër, datë, shumë, ose adresë specifike, mos e shpikni! Përdorni KLLAPA KATRORE ME TEKST PËRSHKRUES. 
   - E SAKTË: [EMRI_I_KOMPANISË], [DATA_E_NËNSHKRIMIT], [SHUMA_NË_EURO], [ADRESA_E_PALËS].
   - E GABUAR: [_____], _____ , N.N., Filan Fisteku.
3. NDALOJNË PARATHËNIET: Fillo direkt me dokumentin ligjor (psh. "GJYKATA THEMELORE NË..." ose "KONTRATË..."). Mos shkruaj "Këtu është dokumenti..." ose "Si model gjuhësor...".
4. SAKTESIA E NENEVE: Nëse nuk e dini numrin e saktë të nenit në ligjin e Kosovës, shkruani "në bazë të dispozitave përkatëse të [Emri i Ligjit]" në vend që të gënjeni numrin e nenit.
`;

  const structureInstructions = getDocumentStructureInstructions(template);

  return `
[UDHËZIMET E HARTIMIT PROCEDURAL]
ROLI: ${roleInstruction}
FUSHA LIGJORE: ${domainInstruction}

${structuralRules}

[STRUKTURA E KËRKUAR E DOKUMENTIT]
${structureInstructions}

[FAKTET DHE KONTEKSTI NGA KLIENTI / AVOKATI]
${userText}

Tani, harto dokumentin profesional ekskluzivisht në gjuhën shqipe (zyrtare, formale). Fillo direkt me titullin dhe strukturën e dokumentit.
`;
};