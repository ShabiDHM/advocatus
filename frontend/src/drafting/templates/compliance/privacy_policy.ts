// FILE: src/drafting/templates/compliance/privacy_policy.ts
// ARCHITECTURE: KOSOVO COMPLIANCE STANDARD (AIP) – DETERMINISTIC

import { TemplateConfig } from '../../types';

export const privacyPolicyTemplate: TemplateConfig = {
  structureInstructions: `
FORMATI: Politika e Privatësisë për faqe interneti / aplikacion, në përputhje me Ligjin për Mbrojtjen e të Dhënave Personale të Republikës së Kosovës.
GJUHA: Shqip (Formale, Juridike).

SEKSIONET E DETYRUESHME (Përdor formatimin Markdown '#' dhe '##'):

# POLITIKA E PRIVATËSISË DHE MBROJTJA E TË DHËNAVE

## 1. Hyrje dhe Identifikimi i Kontrolluesit
- Kjo politikë shpjegon se si [EMRI_I_KOMPANISË] (në tekstin e mëtejmë: “ne”, “na”, “jonë”) mbledh, përdor, ruan dhe mbron të dhënat personale të përdoruesve.
- Kontrolluesi i të dhënave: [EMRI_I_KOMPANISË], me seli në [ADRESA_E_KOMPANISË], email: [EMAIL_I_KOMPANISË], nr. telefonit: [NUMRI_TELEFONIT].

## 2. Kategoritë e të Dhënave Personale që Mblidhen
- Ne mbledhim këto kategori të dhënash:
  - **Të dhëna identifikuese**: [EMRI_DHE_MBIEMRI, NUMRI_PERSONAL, EMAIL, NUMRI_TELEFONIT]
  - **Të dhëna të llogarisë**: [EMRI_I_PËRDORUESIT, FJALËKALIMI_I_ENKRIPTUAR]
  - **Të dhëna teknike**: [ADRESA_IP, LLOJI_I_SHUFRUESIT, TË_DHËNAT_E_PËRDORIMIT]
  - **Të dhëna të tjera**: [LISTA_E_TJERA]

## 3. Qëllimi dhe Baza Ligjore e Përpunimit
- Të dhënat përpunohen për qëllimet e mëposhtme:
  - [QËLLIMI_1] (baza ligjore: pëlqimi / ekzekutimi i kontratës / detyrimi ligjor / interesi legjitim).
  - [QËLLIMI_2] (baza ligjore: …).
- Baza ligjore për përpunim është në përputhje me Ligjin për Mbrojtjen e të Dhënave Personale ([LIGJI_PËR_MBROJTJEN_E_TË_DHËNAVE]), neni [NENI_PËRKATËS].

## 4. Ndarja e të Dhënave me Palët e Treta
- Ne mund t’i ndajmë të dhënat me:
  - **Procesorë pagesash**: [EMRI_I_PROCESORIT_TË_PAGESAVE] për përpunimin e pagesave.
  - **Shërbime postare / transportuese**: [EMRI_I_TRANSPORTUESIT] për dërgimin e produkteve.
  - **Autoritetet shtetërore**: kur kërkohet me ligj.
- Të gjitha palët e treta janë të detyruara të respektojnë konfidencialitetin dhe të përdorin të dhënat vetëm për qëllimin e përcaktuar.

## 5. Të Drejtat e Subjektit të të Dhënave
- Në përputhje me Ligjin për Mbrojtjen e të Dhënave Personale ([LIGJI_PËR_MBROJTJEN_E_TË_DHËNAVE]), ju keni të drejtat e mëposhtme:
  1. **E drejta e qasjes** – të kërkoni konfirmim nëse përpunohen të dhënat tuaja dhe të merrni një kopje.
  2. **E drejta e korrigjimit** – të kërkoni korrigjimin e të dhënave të pasakta.
  3. **E drejta e fshirjes (e drejta për t’u harruar)** – të kërkoni fshirjen e të dhënave kur nuk janë më të nevojshme ose kur pëlqimi tërhiqet.
  4. **E drejta e kufizimit të përpunimit** – të kërkoni pezullimin e përpunimit në rrethana të caktuara.
  5. **E drejta e portabilitetit** – të merrni të dhënat në një format të strukturuar dhe t’i transferoni te një kontrollues tjetër.
  6. **E drejta e kundërshtimit** – të kundërshtoni përpunimin e bazuar në interes legjitim.

## 6. E Drejta e Ankesës në AIP
- **KLAUZOLË E DETYRUESHME:** Nëse besoni se të drejtat tuaja sipërcituara janë shkelur, keni të drejtë të paraqisni ankesë pranë **Agjencisë për Informim dhe Privatësi (AIP)** të Republikës së Kosovës:
  - Adresa: [ADRESA_E_AIP]
  - Faqja e internetit: [WEBSITE_I_AIP]
  - Email: [EMAIL_I_AIP]
- Ankesa mund të paraqitet brenda afateve të përcaktuara me ligj.

## 7. Masat e Sigurisë dhe Kohëzgjatja e Ruajtjes
- Ne zbatojmë masa teknike dhe organizative të përshtatshme (enkriptim, kontroll aksesi) për të mbrojtur të dhënat nga aksesi i paautorizuar, humbja ose shkatërrimi.
- Të dhënat ruhen vetëm për aq kohë sa është e nevojshme për përmbushjen e qëllimit ose për sa kërkohet me ligj. Pas kësaj, ato fshihen ose anonimizohen.

## 8. Të Dhënat e Kontaktit
- Për çdo pyetje në lidhje me këtë politikë ose për ushtrimin e të drejtave tuaja, na kontaktoni në:
  - Email: [EMAIL_I_ZYRTARIT_PËR_MBROJTJEN_E_TË_DHËNAVE]
  - Adresa: [ADRESA_E_KOMPANISË]
  - Telefoni: [NUMRI_TELEFONIT]

UDHËZIM SHTESË:
- Dokumenti fillon direkt me titullin "# POLITIKA E PRIVATËSISË DHE MBROJTJA E TË DHËNAVE" pa asnjë parathënie.
- Përdor gjithmonë emërtime të qarta brenda kllapave katrore për të dhënat që mungojnë (p.sh., [EMRI_I_KOMPANISË]). Mos përdor vija të zbrazëta apo formatin "[_____]".
- Referencat ligjore duhet të përdorin placeholderët: [LIGJI_PËR_MBROJTJEN_E_TË_DHËNAVE] dhe [NENI_PËRKATËS] për të shmangur numrat e vjetruar. Mos cito “Kodi Civil” ose ligje të tjera që nuk lidhen me mbrojtjen e të dhënave.
- Kjo politikë duhet të jetë në përputhje me udhëzimet e Agjencisë për Informim dhe Privatësi (AIP).
  `,
  placeholder: "Shembull: Krijo një Politikë Privatësie për një platformë e-commerce (shitje rrobash online) me bazë në Prishtinë. Ne mbledhim emrin, emailin, numrin e telefonit dhe adresën për dërgesa. Përdorim bankat lokale për procesimin e pagesave dhe Postën e Kosovës për dërgesa...",
  label: "Politika e Privatësisë",
};