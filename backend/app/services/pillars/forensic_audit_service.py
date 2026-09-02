# FILE: backend/app/services/pillars/forensic_audit_service.py
# PHOENIX PROTOCOL - SUPREME FORENSIC AUDIT SPECIALIST V60.0 (EXHAUSTIVE DEEP REASONING • ZERO SUPERFICIALITY)

import logging
import re
from typing import Dict, Any, Optional, Tuple
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

class ForensicAuditService:
    """
    Modul Ekskluziv për BUTONIN E FORENZIKËS LIGJORE (🔬):
    Auditimi i Thellë Kirurgjikal i Dokumentit:
    - Analizon çdo shkresë në mënyrë të shterruar (exhaustive) pa lënë asnjë të dyshuar, provë apo shkelje jashtë.
    - Zbardh falsifikimet, manipulimet me metadata/prapadatime dhe shkeljet 'Contra Legem'.
    - Auditon neni-për-nen të gjitha dispozitat e Kodit Penal (KPK), KPPRK, LPK dhe LMD.
    """

    @staticmethod
    def detect_document_category(
        document_text: str,
        file_name: str = ""
    ) -> Tuple[str, str]:
        combined = f"{file_name} {document_text[:8000]}".lower()
        
        categories = [
            ("KALLËZIM PENAL / AKTAKUZË", ["kallëzim penal", "kallezim penal", "kallzim penal", "aktakuzë", "aktakuze", "parashtruesi i kallëzimit", "denoncim penal"], 
             "Audito në thellësi maksimale bazueshmërinë ligjore, figurën e veprës penale për çdo të dyshuar, shkeljet e hetimeve, provat materiale dhe kompetencën e PSRK-së."),
            
            ("AKTGJYKIM / AKTVENDIM", ["aktgjykim", "aktvendim", "në emër të popullit", "ne emer te popullit", "gjykata themelore", "trupi gjykues"],
             "Audito ligjshmërinë e vendimit, shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), arsyetimin e mangët/kontradiktor dhe bazën e hekurt për ANKESË."),
            
            ("ANKESË / APEL", ["ankesë", "ankese", "drejtuar gjykatës së apelit", "kundër aktgjykimit", "pikat ankimore"],
             "Audito respektimin e afatit ligjor prekluziv, forcën e pikave ankimore dhe saktësinë e kërkesës ankimore (prishje/ndryshim)."),
            
            ("URDHËR MBROJTJE", ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "dhunë në familje", "dhune ne familje", "masat mbrojtëse"],
             "Audito proporcionalitetin e masave, afatet procedurale dhe bazueshmërinë sipas Ligjit Nr. 08/L-185 për Parandalimin dhe Mbrojtjen nga Dhuna në Familje."),
            
            ("PADI / KËRKESËPADI", ["kërkesëpadi", "kerkesepadi", "paditësi", "paditesi", "padia kundër", "petitum"],
             "Audito rregullsinë formale të padisë, kompetencën gjyqësore, qartësinë e Petitumit, legjitimimin e palëve dhe bazën statutore sipas LMD/LPK."),
            
            ("KUNDËRPADI / PRAPËSIM", ["kundërpadi", "kunderpadi", "prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
             "Audito forcën e prapësimeve procedurale (kompetenca, parashkrimi) dhe prapësimeve materiale kundërshtuese."),
            
            ("KONTRATË / MARRËVESHJE", ["kontratë", "kontrate", "marrëveshje", "marreveshje", "palët kontraktuese", "neni 1", "klauzolë"],
             "Audito ligjshmërinë e klauzolave sipas LMD-së, rreziqet e pavlefshmërisë absolute/relative dhe barrën e penaliteteve."),
            
            ("RAPORT SOCIAL / QPS", ["raport social", "qps", "qendra për punë sociale", "interesi më i mirë i fëmijës", "vlerësimi social"],
             "Audito objektivitetin metodologjik, mungesën e njëanshmërisë dhe përputhshmërinë me Ligjin për Familjen."),
            
            ("EKSPERTIZË FINANCIARE / MJEKËSORE", ["ekspertizë", "ekspertize", "raporti i ekspertit", "eksperti financiar", "super-ekspertizë"],
             "Audito metodologjinë llogaritëse/mjekësore, tejkalimin e kompetencave dhe përputhjen me provat laboratorike/shkresore."),
            
            ("DRAFT JURIDIK / PARASHTRESË", [], 
             "Audito shkresën për saktësi neni-për-nen, qartësi formulimi, respektim afatesh dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë.")
        ]
        
        for category, keywords, desc in categories:
            if not keywords:
                continue
            for kw in keywords:
                if kw in combined:
                    return category, desc
        
        return "DRAFT JURIDIK / PARASHTRESË", "Audito shkresën për saktësi neni-për-nen, qartësi formulimi, respektim afatesh dhe eliminimin e lapsuseve para dorëzimit në organet e drejtësisë."

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        context_str: str,
        case_domain: Optional[str] = None,
        document_text: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        manifest_str: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str or ""
            )
        
        audit_text = (document_text or context_str).strip()
        doc_category, category_description = ForensicAuditService.detect_document_category(audit_text)
        
        search_query = query_text or f"Auditimi forenzik i thellë i {doc_category}: {case_title}. Dispozitat e Kodit Penal, KPPRK, LPK, shkeljet contra legem, afatet."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=35
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        role_guard = RoleGuardService.build_role_guard(pos, client_name)

        base_prompt = BasePillarService.build_base_prompt(
            case_title=case_title,
            client_name=client_name,
            client_position=pos,
            current_date_str=current_date_str,
            manifest_str=manifest_str or "",
            context_str=context_str,
            case_domain=case_domain,
            rag_context=rag_context,
            case_rag_context=case_rag_context,
            timeline_context=timeline_context
        )

        return f"""
{base_prompt}

{role_guard}

📄 DOKUMENTI NË AUDITIMIN SUPREM FORENZIK: **{doc_category}**
🎯 OBJEKTIVI I KONTROLLIT: {category_description}

======================================================================
MANDATI RIGOROZ: ISH-GJYQTARI I GJYKATËS SUPREME (AUDITIM I SHKALLËS MË TË LARTË)
Përdoruesi ka sjellë këtë shkresë komplekse juridike dhe kërkon një AUDITIM TË SHKALLËS SUPREME DHE TË PLOTË.

⚠️ URDHËR I HEKURT KUNDËR SIPËRFAQËSISË DHE SHKURTIMEVE:
1. NDALOHET KATEGORIKISHT përmbledhja e shkurtër apo sipërfaqësore me pak pika.
2. NËSE DOKUMENTI KA TË DYSHUAR / AKTORË TË PËRFSHIRË: Zbërtheji ME EMRA DHE NENE SPECIFIKE të gjithë personat e denoncuar (Gjyqtarët, Mjekët, Zyrtarët e QPS-së, Prokurorinë, Personat Privatë).
3. NËSE DOKUMENTI KA PROVA SHKRESORE (nga A-1 te D-1): Analizo me imtësi çdo provë materiale (Testi Toksikologjik Koslabor, Raportet e QKUK-së, Procesverbalet e seancave me prapadatime, Audio-regjistrimet).
4. ZBËRTHE SHKELJET "CONTRA LEGEM": Thekso shkeljen e Nenit 93 të KPK-së (Rehabilitimi Ligjor), falsifikimet e dokumenteve zyrtare (Neni 427 KPK), keqpërdorimin e detyrës zyrtare (Neni 414 KPK) dhe nxjerrjen e vendimeve të kundërligjshme (Neni 425 KPK).
5. VLERËSO PETITUMIN DHE MASAT EMERGJENTE (Nenet 188 & 221 të KPPRK-së).
======================================================================

{'='*60}
TEKSTI I PLOTË I SHKRESËS QË AUDITOHET:
{'='*60}
{audit_text}

STRUKTURA E DETYRUESHME E RAPORTIT MASTER FORENZIK (THELLËSI MAKSIMALE):

### 1. 🔍 DIAGNOZA EKZEKUTIVE E SHKRESËS DHE STATUSI PROCEDURAL
* **Lloji i Aktit Juridik:** {doc_category}
* **Organi Kompetent & Jurisdiksioni:** (Pse kompetenca i takon PSRK-së / Departamentit Special sipas Ligjit Nr. 03/L-052 dhe Neni 9).
* **Konflikti i Interesit dhe Skualifikimi:** (Pse Prokuroria Themelore ka konflikt absolut interesi).
* **Urgjenca Procedurale & Rreziku Eminent (Periculum in mora):** Rreziku për dëmtimin e pariparueshëm psikofizik dhe asgjësimin e dëshmitarit kryesor të gjallë (*Testis principalis vivus*).

### 2. 👥 STRUKTURA E TË DYSHUARVE DHE KUALIFIKIMI PENAL NEN-PËR-NEN
(Zbërthe me emra dhe kualifikim të plotë të gjitha kategoritë e të dyshuarve të përfshirë në shkresë):
* 🏛️ **Zyrtarët e Lartë Ekzekutivë (MD):** Ushtrimi i ndikimit (Neni 424 KPK), Shtytja (Neni 32 KPK), Bashkëkryerja (Neni 31 KPK).
* ⚖️ **Gjyqtarët e Përfshirë (Themelore & Apel):** Nxjerrja e vendimeve të kundërligjshme (Neni 425 KPK), Shkelja e Rehabilitimit Ligjor (Neni 93 KPK), Prapadatimi i procesverbaleve (Neni 427 KPK), Dëbimi arbitrar nga salla.
* 🧠 **Mjekët dhe Ekspertët e QKUK-së:** Ekspertiza e rreme (Neni 387 KPK), Falsifikimi i dokumentit zyrtar (Neni 427 KPK), Moslajmërimi i kanosjes (Neni 385 KPK).
* 🏢 **Stafi i Qendrës për Punë Sociale (QPS):** Keqpërdorimi i detyrës (Neni 414 KPK), Kanosja e fëmijës (Nenet 250 & 386 KPK), Marrja e deklaratës nën presion (Neni 382 KPK).
* 👮 **Prokuroria & Hetuesit Policorë:** Fshehja e provave shfajësuese digjitale (Nenet 382 & 414 KPK), Cenimi i barazisë së armëve (Neni 193 KPK).

### 3. 🔬 TREKËNDËSHAT E PROVAVE MATERIALE DHE ANALIZA SHKENCORE (CORPUS DELICTI)
(Analizo ballafaqimin e provave konkrete):
* 🧪 **E Vërteta Shkencore vs. Falsifikimi Mjekësor:** Testi Toksikologjik i Koslaborit 100% Negativ (Prova A-1) kundrejt diagnozave gojore të porositura të QKUK-së.
* 📜 **Vetë-Kontradikta Gjyqësore (Dolus Directus):** Faqja 4 e Aktgjykimit C.nr. 5906/25 (fëmija nuk e refuzon babanë) kundrejt izolimit të kundërligjshëm në QPS.
* 💾 **Metadata dhe Prapadatimi (Antidatum):** Kryerreshtat e kthyer prapa më "19.01.2024" në procesverbalet e seancave të shkurtit (Shkresa Nr. 05210884).
* 🎙️ **Provat Audio & Mesazhet e Pakontestueshme:** Analiza e regjistrimit audio (Prova B-7) dhe mesazheve/vizatimit "ANDI DON BABI" (Prova B-6).

### 4. ⚠️ VERIFIKIMI NEN-PËR-NEN I DISPOZITAVE STATUTORE & GABIMET "CONTRA LEGEM"
(Ndërto tabelën e detajuar të të gjitha neneve):
| Dispozita & Ligji i Zbatueshëm | Statusi i Pajtueshmërisë | Analiza Forenzike & Efekti Procedural |
| :--- | :--- | :--- |
| *p.sh. Neni 93 i KPK Nr. 06/L-074* | *🔴 Shkelje Flagrante (Contra Legem)* | *Përdorimi i aktgjykimit të shlyer P.nr. 869/18 cenon rëndë ligjshmërinë e vendimit.* |
| *p.sh. Neni 257 i KPPRK Nr. 08/L-032* | *🔴 Provë e Papranueshme* | *Raportet mjekësore të bazuara në dëshmi gojore të paverifikuara shpallen të pavlefshme.* |
| *p.sh. Nenet 188 & 221 të KPPRK-së* | *🟢 Baza e Masave Emergjente* | *Detyrim ligjor i menjëhershëm i Prokurorit për largimin e fëmijës brenda 24 orëve.* |

### 5. 🏛️ OPINIONI DOKTRINAR I GJYQTARIT SUPREM (PROGNOZA E HETIMIT NË PSRK)
* **Qëndrueshmëria e Kallëzimit Penal:** Vlerësimi doktrinar mbi ekzistimin e dyshimit të bazuar mirë (*Fumus boni iuris*) për fillimin e hetimeve penale në PSRK.
* **Provat e Pathyeshme (Smoking Guns):** Cilat prova e vulosin përgjegjësinë penale të të dyshuarve.
* **Rreziqet Procedurale dhe Masat Mbrojtëse:** Mbrojtja e dëshmitarit të mitur nga presioni i vazhdueshëm psikologjik.

### 6. 🎯 KËRKESAT PËRFUNDIMTARE DHE MASTER PLANI I VEPRIMIT
* 🔴 **HAPI 1 (Urgjenca 24-Orëshe):** Lëshimi i Urdhëresës Emergjente të Mbrojtjes (Nenet 188 & 221 KPPRK) dhe ekzekutimi nga Policia e Kosovës.
* 🟡 **HAPI 2 (Ekspertiza e Pavarur & Sekuestrimi):** Caktimi i Komisionit të Pavarur të Ekspertëve (jashtë QKUK/QPS) dhe sekuestrimi i metadatave kompjuterike.
* 🟢 **HAPI 3 (Ngritja e Aktakuzës në Departamentin Special):** Procedimi i aktakuzës penale ndaj të gjithë bashkëkryerësve sipas Neneve 31 dhe 81 të KPK-së.
"""