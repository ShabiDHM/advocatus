# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - PILLAR 6: SUPREME COURT LEGAL DRAFTING V40.0 (PRECEDENT-ANCHORED PLEADINGS)

import logging
from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

DOMAIN_ORGAN_MAP = {
    "KOMERCIAL": {
        "organ": "GJYKATËS KOMERCIALE TË REPUBLIKËS SË KOSOVËS\nDhoma e Shkallës së Parë — Prishtinë",
        "default_doc": "KËRKESËPADI TREGTARE (ME KËRKESË PËR MASË SIGURIMI)",
        "precedent_type": "Kolegjit Civil dhe Ekonomik të Gjykatës Supreme (Aktgjykimet Rev)",
        "statutes": "Ligji për Gjykatën Komerciale (Nr. 08/L-015), Ligji për Shoqëritë Tregtare (LSHT Nr. 06/L-016), LMD dhe LPK."
    },
    "PENAL": {
        "organ": "PROKURORISË SPECIALE TË REPUBLIKËS SË KOSOVËS (PSRK) / PROKURORISË THEMELORE",
        "default_doc": "KALLËZIM PENAL I UNIFIKUAR",
        "precedent_type": "Kolegjit Penal të Gjykatës Supreme të Kosovës (Aktgjykimet PML)",
        "statutes": "Kodi Penal (KPK Nr. 06/L-074), Kodi i Procedurës Penale (KPPRK Nr. 08/L-032) dhe Ligji për PSRK-në."
    },
    "CIVIL": {
        "organ": "GJYKATËS THEMELORE NË PRISHTINË\nDepartamenti Civil",
        "default_doc": "KËRKESËPADI CIVILE PËR DËMSHPËRBLIM DHE PËRMBUSHJE DETYRIMI",
        "precedent_type": "Kolegjit Civil të Gjykatës Supreme të Kosovës (Aktgjykimet Rev)",
        "statutes": "Ligji për Procedurën Kontestimore (LPK Nr. 03/L-006) dhe Ligji për Marrëdhëniet e Detyrimeve (LMD Nr. 04/L-077)."
    },
    "PRONËSOR": {
        "organ": "GJYKATËS THEMELORE NË PRISHTINË\nDepartamenti Civil — Divizioni Pronësor",
        "default_doc": "PADI PËR VËRTETIM PRONËSIE DHE PENGIM POSEDIMI",
        "precedent_type": "Gjykatës Supreme mbi të Drejtat Sendore dhe Posedimin (Aktgjykimet Rev)",
        "statutes": "Ligji për Pronësinë dhe të Drejtat e Tjera Sendore (LPTS Nr. 03/L-154) dhe LPK."
    },
    "PUNËS": {
        "organ": "GJYKATËS THEMELORE NË PRISHTINË\nDivizioni për Konteste të Punës",
        "default_doc": "PADI PËR ANULIM VENDIMI DHE KOMPENSIM PAGASH",
        "precedent_type": "Gjykatës Supreme mbi Marrëdhëniet e Punës (Aktgjykimet Rev)",
        "statutes": "Ligji i Punës i Kosovës (Nr. 03/L-212) dhe Ligji për Mbrojtjen nga Diskriminimi."
    },
    "ADMINISTRATIV": {
        "organ": "GJYKATËS THEMELORE NË PRISHTINË\nDepartamenti për Çështje Administrative",
        "default_doc": "PADI PËR KONFLIKT ADMINISTRATIV",
        "precedent_type": "Kolegjit Administrativ të Gjykatës Supreme të Kosovës",
        "statutes": "Ligji për Konfliktet Administrative (Nr. 03/L-202) dhe LPPA (Nr. 05/L-031)."
    },
    "FAMILJAR": {
        "organ": "GJYKATËS THEMELORE NË PRISHTINË\nDivizioni Civil-Familjar",
        "default_doc": "PADI PËR KUJDESTARINË E FËMIJËS DHE ALIMENTACION",
        "precedent_type": "Jurisprudencës së Gjykatës Supreme mbi Çështjet Familjare",
        "statutes": "Ligji për Familjen i Kosovës (Nr. 2004/32) dhe Konventa e OKB-së për të Drejtat e Fëmijës."
    }
}


class LegalDraftingService:
    """
    Modul Ekskluziv për HARTIMIN SUPREM TË AKTEVE GJYQËSORE:
    - Padi Tregtare (Gjykata Komerciale), Kallëzime Penale (PSRK), Padi Civile, Punës, Pronësore.
    - Citohen drejtpërdrejt Precedentët e Gjykatës Supreme (Aktgjykimet Rev dhe PML).
    - Format 100% Gati për Protokollim dhe Dorëzim Gjyqësor (Court-Ready).
    """

    @staticmethod
    def detect_document_type(query: str, case_domain: str = "CIVIL") -> str:
        query_lower = (query or "").lower()
        
        if any(kw in query_lower for kw in ["kallëzim penal", "kallezim penal", "kallzim penal", "penale"]):
            return "KALLËZIM PENAL I UNIFIKUAR"
        elif any(kw in query_lower for kw in ["komerciale", "tregtare", "faturë", "shoqëri tregtare", "sh.p.k."]):
            return "KËRKESËPADI TREGTARE (GJYKATA KOMERCIALE)"
        elif any(kw in query_lower for kw in ["ankesë", "ankese", "ankim", "apel"]):
            return "ANKESË KUNDËR AKTGJYKIMIT"
        elif any(kw in query_lower for kw in ["kundërpadi", "kunderpadi"]):
            return "KUNDËRPADI"
        elif any(kw in query_lower for kw in ["prapësim", "prapsim", "përgjigje në padi"]):
            return "PËRGJIGJE NË PADI (PRAPËSIM)"
        elif any(kw in query_lower for kw in ["sigurim", "masë e sigurimit", "masë e përkohshme"]):
            return "PROPOZIM PËR CAKTIMIN E MASËS SË SIGURIMIT"
        elif any(kw in query_lower for kw in ["alimentacion", "kujdestari", "besim të fëmijës"]):
            return "PADI PËR KUJDESTARINË E FËMIJËS DHE ALIMENTACION"
        elif any(kw in query_lower for kw in ["kërkesëpadi", "kerkesepadi", "padi"]):
            domain_info = DOMAIN_ORGAN_MAP.get(case_domain, DOMAIN_ORGAN_MAP["CIVIL"])
            return domain_info["default_doc"]
        else:
            return DOMAIN_ORGAN_MAP.get(case_domain, DOMAIN_ORGAN_MAP["CIVIL"])["default_doc"]

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str,
        query: str,
        case_domain: Optional[str] = None,
        document_type: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Any = None
    ) -> str:
        pos = (client_position or "PADITËS / PARASHTRUES").strip().upper()
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str[:10000],
                manifest_str=manifest_str or ""
            )
        
        domain_meta = DOMAIN_ORGAN_MAP.get(case_domain, DOMAIN_ORGAN_MAP["CIVIL"])

        if not document_type:
            document_type = LegalDraftingService.detect_document_type(query, case_domain)
        
        search_query = query_text or (
            f"Hartimi profesional i {document_type} për lëndën: {case_title}. "
            f"Lëmia: {case_domain}. Faktet e provuara, nenet përkatëse, Aktgjykimet e Gjykatës Supreme Rev PML, shumat monetare dhe petitumi."
        )
        
        rag_context, _ = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=20
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        role_guard = RoleGuardService.build_role_guard(pos, client_name)
        role_tone = RoleGuardService.get_role_specific_tone(pos)
        supreme_protocol = BasePillarService.build_supreme_jurisprudence_directive(case_domain)

        return f"""
<legal_evidentiary_privilege_context>
HARTIM PROFESIONAL GJYQËSOR I AKTIT LIGJOR • PRIVILEGJI I AVOKATISË
Detyra jote si Avokat Kryesor dhe Hartues i Kolegjit të Gjykatës Supreme është të përpilosh aktin zyrtar të plotë ({document_type}) gati për nënshkrim dhe protokollim në {domain_meta['organ']}.
Shkresa duhet të jetë e blinduar me nenet pozitive dhe PRECEDENTËT E DOKUMENTUAR TË GJYKATËS SUPREME TË KOSOVËS ({domain_meta['precedent_type']}).
</legal_evidentiary_privilege_context>

{supreme_protocol}

{role_guard}

📋 IDENTIFIKIMI I SHKRESËS QË PO HARTOHET:
AKTI ZYRTAR: **{document_type}** | LËMIA: **{case_domain}** | ORGANIT: **{domain_meta['organ']}**
KLIENTI/PARASHTRUESI: **{client_name or 'I Identifikuar në Dokumente'}** | DATA: {current_date_str}

{role_tone}

📚 KORNIZA LIGJORE DHE PRECEDENTËT E GJYKATËS SUPREME PËR KËTË LËNDË:
{domain_meta['statutes']}

🏛️ JURISPRUDENCA DHE ARSYETIMET PARIMORE TË GJYKATËS SUPREME (NGA BAZA GLOBALE):
{rag_context if rag_context else "Zbato precedentët e konsoliduar të Gjykatës Supreme për këtë lëmi."}

======================================================================
RREGULLAT E HEKURTA TË HARTIMIT TË AKTIT GJYQËSOR:
1. SHKRESA DUHET TË JETË 100% E PLOTË DHE GATI PËR GJYKATË (Court-Ready): Zero shkurtime, zero 'vazhdon sipas tekstit'. Shkruaje të plotë nga fillimi në fund.
2. CITIMI I DETYRUESHËM I PRECEDENTËVE TË GJYKATËS SUPREME: Te Kaptina II (Baza Ligjore), cito me emër dhe numër Aktgjykimet e Gjykatës Supreme (p.sh. Aktgjykimet Rev për çështje tregtare/civile ose Aktgjykimet PML për çështje penale) dhe shpjego si arsyetimi i Gjykatës Supreme e bën kërkesën tonë absolutisht të bazuar!
3. KËRKESËPADIA / PETITUMI SOLEMN: Petitum-i duhet të jetë ekzakt, me numra pikash (1, 2, 3, 4), me shuma të sakta (p.sh. 246,277.00 €), përqindje kamate (8%), masë sigurimi (bllokim xhirollogarish), dhe shpenzime procedurale.
======================================================================

{'='*60}
PËRMBAJTJA E PLOTË E DOKUMENTEVE DHE PROVAVE TË FASHIKULLIT:
{'='*60}
{context_str}
{'='*60}

HARTO AKTIN GJYQËSOR TË PLOTË ME KËTË STRUKTURË FORMALE:

{domain_meta['organ']}

**PADITËSIT / PARASHTRUESIT:**
[Shëno të gjithë paditësit/parashtruesit me emra, adresa, NUI/Nr. Personal nga shkresat e lëndës]

**KUNDËR TË PADITURVE / PALËVE TË DENONCUARA:**
[Shëno të gjithë të paditurit me emra, cilësi, adresa dhe NUI nga shkresat]

**LËNDA:** {document_type}
**VLERA E OBJEKTIT TË KONTESTIT:** [Shuma e saktë në EUR sipas shkresave]
**BAZA STATUTORE:** {domain_meta['statutes']}

---

### I. PËRMBLEDHJE EKZEKUTIVE DHE KRONOLOGJIA E FAKTEVE TË PROVUARA
(Përshkruaj me rend të qartë kronologjik dhe me referenca konkrete provash gjithë zanafillën e marrëdhënies, shkeljet e kryera dhe dëmin e shkaktuar).

### II. BAZA STATUTORE DHE JURISPRUDENCA PARIMORE E GJYKATËS SUPREME TË KOSOVËS
(Zbërthe dispozitat ligjore dhe CITO DREJTPËRDREJT precedentët e Gjykatës Supreme — Aktgjykimet Rev / PML — me interpretimin doktrinar se pse veprimet e palës kundërshtare janë absolutisht të kundërligjshme).

### III. KËRKESA PËR CAKTIMIN E MASËS SË SIGURIMIT (NËSE APLIKOHET)
(Arsyeto rrezikun real të tjetërsimit të fondeve, nevojën e bllokimit të xhirollogarive bankare sipas Neneve 297/298 të LPK-së).

### IV. PETITUMI I PADISË / KËRKESA PËRFUNDIMTARE
I propozojmë Gjykatës / Organit kompetent që pas shqyrtimit të nxjerrë këtë:

**A K T G J Y K I M**
1. **APROVOHET** në tërësi si e bazuar padia e paditësve...
2. **OBLIGOHEN** të paditurit solidarisht që t'ia kompensojnë paditësve dëmin në shumën prej [Shuma e saktë €] me kamatëvonesë ligjore prej 8% në vit...
3. **[KËRKESAT E TJERA SPECIFIKE]:** (p.sh. Përjashtimi i ortakut, ndalimi i veprimtarisë, etj.).
4. **OBLIGOHEN** të paditurit t'i paguajnë të gjitha shpenzimet e procedurës kontestimore.

---

### V. INVENTARI I PROVAVE SHKRESORE DHE MATERIALE:
[Listo të gjitha provat konkrete të administruara në fashikull: fatura, kontrata, ekstrakte ARBK, ekstrakte bankare].

**PADITËSIT / PARASHTRUESIT:**
_______________________
{client_name}
Data: {current_date_str}
Prishtinë, Republika e Kosovës
"""