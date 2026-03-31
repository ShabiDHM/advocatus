// FILE: src/drafting/templates/compliance/privacy_policy.ts
// ARCHITECTURE: KOSOVO COMPLIANCE STANDARD (AIP) & MARKDOWN ENFORCEMENT

import { TemplateConfig } from '../../types';

export const privacyPolicyTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Politika e Privatësisë për faqe interneti / aplikacion.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor saktësisht formatimin Markdown me '#' për titullin kryesor dhe '##' për nëntitujt):

# POLITIKA E PRIVATËSISË DHE MBROJTJA E TË DHËNAVE

## 1. Hyrje dhe Identifikimi i Kontrolluesit
- Përcakto qartë se kush i mbledh të dhënat (Përdor [EMRI_I_KOMPANISË] nëse nuk është dhënë).

## 2. Kategoritë e të Dhënave Personale që Mblidhen
- Listo qartë çfarë të dhënash mblidhen (psh. Emri, Emaili, IP Adresa, etj.).

## 3. Qëllimi dhe Baza Ligjore e Përpunimit
- Cito pëlqimin, detyrimin kontraktual, ose interesin legjitim sipas ligjit.

## 4. Ndarja e të Dhënave me Palët e Treta
- Specifiko nëse të dhënat ndahen me procesorë pagesash, shërbime postare, apo autoritete shtetërore.

## 5. Të Drejtat e Subjektit të të Dhënave
- Përfshi detyrimisht: E drejta për qasje, korrigjim, fshirje (E drejta për t'u harruar), dhe kufizim të përpunimit.

## 6. E Drejta e Ankesës në AIP
- KLAUZOLË E DETYRUESHME: Subjektet kanë të drejtë të paraqesin ankesë pranë Agjencisë për Informim dhe Privatësi (AIP) të Republikës së Kosovës, nëse vlerësojnë se u janë shkelur të drejtat.

## 7. Masat e Sigurisë dhe Kohëzgjatja e Ruajtjes
- Si mbrohen të dhënat dhe sa gjatë ruhen ato.

## 8. Të Dhënat e Kontaktit
- Emaili dhe adresa e Zyrtarit për Mbrojtjen e Të Dhënave (DPO) ose kompanisë.

BAZA LIGJORE E DETYRUESHME: Përmend shprehimisht "Ligjin për Mbrojtjen e të Dhënave Personale (Nr. 06/L-082) të Republikës së Kosovës".
  `,
  placeholder: "Shembull: Krijo një Politikë Privatësie për një platformë e-commerce (shitje rrobash online) me bazë në Prishtinë. Ne mbledhim emrin, emailin, numrin e telefonit dhe adresën për dërgesa. Përdorim bankat lokale për procesimin e pagesave dhe Postën e Kosovës për dërgesa...",
  label: "Politika e Privatësisë",
};