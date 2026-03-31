// FILE: src/drafting/templates/index.ts
import { TemplateConfig, TemplateType } from '../types';

import { genericTemplate } from './generic';
import { padiTemplate } from './litigation/padi';
import { pergjigjeTemplate } from './litigation/pergjigje';
import { kunderpadiTemplate } from './litigation/kunderpadi';
import { ankeseTemplate } from './litigation/ankese';
import { prapesimTemplate } from './litigation/prapësim';
import { ndaTemplate } from './corporate/nda';
import { mouTemplate } from './corporate/mou';
import { shareholdersTemplate } from './corporate/shareholders';
import { slaTemplate } from './corporate/sla';
import { employmentContractTemplate } from './employment/employment_contract';
import { terminationNoticeTemplate } from './employment/termination_notice';
import { warningLetterTemplate } from './employment/warning_letter';
import { leaseAgreementTemplate } from './real_estate/lease_agreement';
import { salesPurchaseTemplate } from './real_estate/sales_purchase';
import { powerOfAttorneyTemplate } from './real_estate/power_of_attorney';
import { termsConditionsTemplate } from './compliance/terms_conditions';
import { privacyPolicyTemplate } from './compliance/privacy_policy';

const withCompliance = (config: TemplateConfig, domain: 'FAMILY' | 'CORPORATE' | 'CIVIL' | 'LABOR'): TemplateConfig => ({
  ...config,
  structureInstructions: `
[STRICT LEGAL SCHEMA]
DOMAIN: ${domain}
MANDATORY CITATIONS: 
${domain === 'FAMILY' ? '- Ligji i Familjes së Kosovës (Nr. 2004/25)' : ''}
${domain === 'CORPORATE' ? '- Ligji Nr. 06/L-016 për Shoqëritë Tregtare' : ''}
${domain === 'LABOR' ? '- Ligji i Punës Nr. 03/L-212' : ''}
${domain === 'CIVIL' ? '- Kodi Civil i Republikës së Kosovës' : ''}

RULES:
1. NEVER cite laws from other domains.
2. If the user input is a family dispute, you are forbidden from mentioning commercial or corporate statutes.
3. If data (names, dates, IDs) is missing, use exactly this placeholder: [_____].

[INSTRUCTIONS]
${config.structureInstructions}
  `.trim()
});

export const templateConfigs: Record<TemplateType, TemplateConfig> = {
  generic: withCompliance(genericTemplate, 'CIVIL'),
  padi: withCompliance(padiTemplate, 'FAMILY'),
  pergjigje: withCompliance(pergjigjeTemplate, 'FAMILY'),
  kunderpadi: withCompliance(kunderpadiTemplate, 'FAMILY'),
  ankese: withCompliance(ankeseTemplate, 'CIVIL'),
  prapësim: withCompliance(prapesimTemplate, 'CIVIL'),
  nda: withCompliance(ndaTemplate, 'CORPORATE'),
  mou: withCompliance(mouTemplate, 'CORPORATE'),
  shareholders: withCompliance(shareholdersTemplate, 'CORPORATE'),
  sla: withCompliance(slaTemplate, 'CORPORATE'),
  employment_contract: withCompliance(employmentContractTemplate, 'LABOR'),
  termination_notice: withCompliance(terminationNoticeTemplate, 'LABOR'),
  warning_letter: withCompliance(warningLetterTemplate, 'LABOR'),
  lease_agreement: withCompliance(leaseAgreementTemplate, 'CIVIL'),
  sales_purchase: withCompliance(salesPurchaseTemplate, 'CIVIL'),
  power_of_attorney: withCompliance(powerOfAttorneyTemplate, 'CIVIL'),
  terms_conditions: withCompliance(termsConditionsTemplate, 'CIVIL'),
  privacy_policy: withCompliance(privacyPolicyTemplate, 'CIVIL'),
};