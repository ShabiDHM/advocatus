// FILE: src/drafting/templates/corporate/nda.ts
// ARCHITECTURE: KOSOVO TRADE SECRET & COMMERCIAL LIABILITY PROTECTION – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const ndaTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Marrëveshje për Moszbulim të Informacionit (NDA - Non-Disclosure Agreement).
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# MARRËVESHJE PËR MOSZBULIMIN E INFORMACIONIT (NDA)

## 1. Palët e Marrëveshjes
- Pala Zbuluese ([EMRI_I_KOMPANISË_A]), me seli në [ADRESA_E_KOMPANISË_A], të regjistruar me nr. [NR_REGJISTRIMIT_A].
- Pala Pranuese ([EMRI_I_KOMPANISË_B]), me seli në [ADRESA_E_KOMPANISË_B], të regjistruar me nr. [NR_REGJISTRIMIT_B].

## 2. Përkufizimi i Informacionit Konfidencial
- Informacioni konfidencial përfshin çdo informacion teknik, financiar, komercial, strategjik ose tjetër që nuk është i njohur për publikun, duke përfshirë por pa u kufizuar: [LISTA_E_INFORMACIONEVE].
- Ky informacion mbron si "sekret tregtar" sipas Ligjit për Shoqëritë Tregtare (Ligji Nr. 06/L-016), neni 7 (Sekreti tregtar) dhe nenet e tjera përkatëse.

## 3. Detyrimet e Palës Pranuese
- Pala Pranuese nuk do të zbulojë, kopjojë, shpërndajë, përdorë për qëllime të tjera përveç atij të miratuar (qëllimi: [PËRSHKRIMI_I_QËLLIMIT]).
- Detyrimi zbatohet për periudhën e marrëveshjes dhe pas përfundimit të saj.

## 4. Standardi i Kujdesit
- Pala Pranuese duhet ta mbrojë informacionin me të njëjtin nivel kujdesi siç mbron informacionin e vet konfidencial, por jo më pak se një nivel i arsyeshëm profesional.

## 5. Përjashtimet (Informacionet Publike)
- Nuk konsiderohen konfidenciale informacionet që:
  a) ishin të njohura publikisht para zbulimit;
  b) bëhen publike pa faj të Palës Pranuese;
  c) i njiheshin Palës Pranuese para marrëveshjes, siç dëshmohet me shkrim;
  d) kërkohen me ligj nga autoritetet kompetente.

## 6. Kohëzgjatja (Termi)
- Detyrimet e kësaj marrëveshjeje zgjasin për [NUMRI_VJET] vjet pas përfundimit të bashkëpunimit, ose derisa informacioni të pushojë së qeni konfidencial.

## 7. Pasojat e Shkeljes dhe Dëmshpërblimi
- Në rast shkeljeje, Pala Pranuese është përgjegjëse për dëmin e shkaktuar sipas Ligjit për Detyrimet (Ligji Nr. 2004/31), neni 128 (Dëmshpërblimi) dhe nenet e tjera përkatëse.
- Pala Zbuluese ruan të drejtën të kërkojë masa të përkohshme dhe kompensim të plotë.

## 8. Ligji i Zbatueshëm dhe Gjykata Kompetente
- Marrëveshja interpretohet dhe zbatohet sipas ligjeve të Republikës së Kosovës.
- Çdo mosmarrëveshje do të zgjidhet në Gjykatën Themelore në Prishtinë, me rezervë të kompetencës së gjykatave të tjera sipas ligjit.

## 9. Nënshkrimet
- Për Palën Zbuluese: [EMRI_MBIEMRI_PËRFAQËSUES_A], [POZITA_A], nënshkrimi, data [DATA].
- Për Palën Pranuese: [EMRI_MBIEMRI_PËRFAQËSUES_B], [POZITA_B], nënshkrimi, data [DATA].

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "MARRËVESHJE PËR MOSZBULIMIN E INFORMACIONIT (NDA)" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_KOMPANISË_A]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Në këtë marrëveshje, baza ligjore përfshin Ligjin për Shoqëritë Tregtare (për sekretin tregtar) dhe Ligjin për Detyrimet (për dëmshpërblimin). Mos përfshi ligje që nuk lidhen me këtë fushë (p.sh., Ligji i Familjes ose LCP).
  `,
  placeholder: "Shembull: Kompania ime po ndan të dhëna teknike të një softueri të ri me një bashkëpunëtor të jashtëm. Dua të sigurohem që ata nuk do t'i kopjojnë kodin apo klientët tanë për 3 vitet e ardhshme.",
  label: "Marrëveshje Konfidencialiteti (NDA)",
};