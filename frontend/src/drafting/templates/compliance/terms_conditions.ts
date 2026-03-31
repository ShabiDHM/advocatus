// FILE: src/drafting/templates/compliance/terms_conditions.ts
// ARCHITECTURE: KOSOVO E-COMMERCE & CONSUMER PROTECTION COMPLIANCE

import { TemplateConfig } from '../../types';

export const termsConditionsTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Kushtet e Përdorimit (Terms and Conditions) për faqe interneti ose shërbime online.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor saktësisht formatimin Markdown me '#' dhe '##'):

# KUSHTET E PËRDORIMIT

## 1. Pranimit i Kushteve
- Deklarimi se duke përdorur faqen, përdoruesi pranon këto kushte.

## 2. Llogaritë e Përdoruesit
- Përgjegjësia për sigurinë e llogarisë dhe saktësinë e të dhënave.

## 3. Shitblerja dhe Pagesat (Nëse është e aplikueshme)
- Procesi i porosisë, mënyrat e pagesës, politikat e kthimit dhe zëvendësimit të produkteve.

## 4. Pronësia Intelektuale
- Mbrojtja e të drejtave të autorit mbi përmbajtjen, logot dhe dizajnin e faqes.

## 5. Kufizimi i Përgjegjësisë
- Mohimi i përgjegjësisë për dëme indirekte ose mosfunksionim të faqes.

## 6. Zbatimi i Ligjit dhe Zgjidhja e Mosmarrëveshjeve
- KLAUZOLË E DETYRUESHME: Këto kushte rregullohen nga ligjet e Republikës së Kosovës. Çdo mosmarrëveshje do të zgjidhet nga Gjykata Themelore në Prishtinë.

## 7. Referencat Ligjore (Detyruese)
- Cito shprehimisht: "Ligjin për Mbrojtjen e Konsumatorit (Nr. 06/L-034)" dhe "Ligjin për Tregtinë Elektronike (Nr. 08/L-038) të Republikës së Kosovës".

## 8. Kontakt
- Informacionet e kompanisë, adresa dhe kontakti i mbështetjes për klientë.
  `,
  placeholder: "Shembull: Kompania ime ofron shërbime të shitblerjes online (e-commerce). Përdoruesit mund të regjistrohen, të blejnë produkte me kartelë ose para në dorë dhe kanë 14 ditë afat për kthim...",
  label: "Kushtet e Përdorimit",
};