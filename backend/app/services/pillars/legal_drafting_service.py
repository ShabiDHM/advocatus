# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - PILLAR 6: UNIVERSAL & DOMAIN-AGNOSTIC LEGAL DRAFTING V19.0 (TIMELINE INTEGRATED)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
from app.services.pillars.role_guard_service import RoleGuardService
import logging

logger = logging.getLogger(__name__)

class LegalDraftingService:
    """
    Modul i Pavarur Ekskluziv për HARTIMIN E TË GJITHA AKTEVE ZYRTARE (UNIVERSAL):
    - Padi Civile, Tregtare, Pronësore & Familjare
    - Kallëzime Penale
    - Prapësime, Kundërpadi dhe Ankesa në Gjykatën e Apelit
    - Kontrata dhe Marrëveshje Zyrtare
    - Inventarizimi i Provave Shkencore dhe Transkripteve Audio/Video (Corpus Delicti)
    - Zero emra të shpikur, zero numra personalë të sajuar
    - 100% agnostik ndaj domeneve + RAG + TIMELINE + ZERO HALUCINACIONE
    """

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
        pos = (client_position or "DEFENDANT").upper()
        
        # PHOENIX FIX: Zbulo domenin
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Zbulo llojin e dokumentit
        if not document_type:
            query_lower = (query or "").lower()
            if any(kw in query_lower for kw in ["kallëzim penal", "kallezim penal", "kallzim penal"]):
                document_type = "KALLËZIM PENAL"
            elif any(kw in query_lower for kw in ["ankesë", "ankese", "apel"]):
                document_type = "ANKESË"
            elif any(kw in query_lower for kw in ["kundërpadi", "kunderpadi"]):
                document_type = "KUNDËRPADI"
            elif any(kw in query_lower for kw in ["prapësim", "prapsim"]):
                document_type = "PRAPËSIM"
            elif any(kw in query_lower for kw in ["kontratë", "kontrate", "marrëveshje", "marreveshje"]):
                document_type = "KONTRATË / MARRËVESHJE"
            elif any(kw in query_lower for kw in ["padi", "kërkesëpadi", "kerkesepadi"]):
                document_type = "KËRKESËPADI CIVILE"
            else:
                document_type = "AKT ZYRTAR"
        
        # PHOENIX FIX: Kërko në RAG
        search_query = query_text or f"Hartimi i {document_type} për lëminë: {case_domain}. Baza ligjore, nenet e zbatueshme, struktura e aktit."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=30
        )
        
        # PHOENIX FIX: Ndërto kronologjinë
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        # PHOENIX FIX: Ndërto udhëzimin specifik për llojin e dokumentit
        document_instruction = ""
        if document_type == "KALLËZIM PENAL":
            document_instruction = f"""
DREJTIMI I AKTIT: KALLËZIM PENAL
- I drejtohet: **PROKURORISË SPECIALE TË REPUBLIKËS SË KOSOVËS (PSRK)** ose **PROKURORISË THEMELORE KOMPETENTE**;
- Baza ligjore: VETËM nenet e KPPRK-së dhe KPRK-së nga RAG context;
- Petitumi kërkon: Fillimin e hetimeve penale, masat emergjente dhe ngritjen e aktakuzës.
"""
        elif document_type in ["KËRKESËPADI CIVILE", "KUNDËRPADI"]:
            document_instruction = f"""
DREJTIMI I AKTIT: {document_type}
- I drejtohet: **GJYKATËS THEMELORE KOMPETENTE**;
- Baza ligjore: VETËM nenet e LPK-së dhe LMD-së nga RAG context;
- Petitumi kërkon: Dëmshpërblim, vërtetim të drejte, shfuqizim akti, masa sigurimi.
"""
        elif document_type == "ANKESË":
            document_instruction = f"""
DREJTIMI I AKTIT: ANKESË
- I drejtohet: **GJYKATËS SË APELIT TË KOSOVËS** (përmes Gjykatës Themelore);
- Baza ligjore: VETËM nenet procedurale nga RAG context.
- KUJDES: Nëse afati i ankimit ka skaduar (shih kronologjinë), rekomando KALLËZIM PENAL në vend të ankesës.
"""
        elif document_type in ["KONTRATË / MARRËVESHJE", "PRAPËSIM"]:
            document_instruction = f"""
DREJTIMI I AKTIT: {document_type}
- Baza ligjore: VETËM nenet përkatëse nga RAG context.
"""
        else:
            document_instruction = f"""
DREJTIMI I AKTIT: {document_type}
- Baza ligjore: VETËM nenet përkatëse për lëminë {case_domain} nga RAG context.
"""

        return f"""
Ti je "Avokati Senior Elitar dhe Përfaqësuesi Kryesor Ligjor në Republikën e Kosovës".
DEGË E SË DREJTËS: {case_domain}
LLOJI I AKTIT: {document_type}
KLIENTI YNË EKSKLUZIV: **{client_name}** ({pos}) | LËNDA: **{case_title}** | DATA: {current_date_str}

KËRKESA SPECIFIKE E PËRDORUESIT:
"{query}"

{document_instruction}

RREGULLA SUPREME TË DREJTËSISË:
1. BESNIKËRIA NDAJ KLIENTIT:
   - Parashtruesi/Paditësi/Kallëzuesi është GJITHMONË: **{client_name}**;
   - Fëmijët e mitur janë VIKTIMA TË MBROJTURA;
   - Të paditurit/të dyshuarit janë VETËM personat nga fashikulli.
2. ZERO HALUCINACIONE:
   - Përdor VETËM emrat realë nga fashikulli;
   - MOS shpik adresa, numra personalë, ose emra;
   - Nëse mungon një e dhënë: [Adresa e plotë] ose [Numri Personal sipas ID];
   - MOS cito asnjë nen nga memorja — VETËM nga RAG context;
   - MOS cito asnjë precedent që NUK gjendet në listën e verifikuar.
3. PROVAT AUDIO/VIDEO SI CORPUS DELICTI:
   - Transkriptet citohen me sekonda [MM:SS - MM:SS].
4. FORMATIMI:
   - Fillo direkt me titullin e aktit;
   - Mbylle aktin te nënshkrimi përfundimtar pa asnjë tekst pas tij.

{BasePillarService.build_base_prompt(
    case_title=case_title,
    client_name=client_name,
    client_position=pos,
    current_date_str=current_date_str,
    manifest_str=manifest_str,
    context_str=context_str,
    case_domain=case_domain,
    rag_context=rag_context,
    case_rag_context=case_rag_context,
    timeline_context=timeline_context
)}

STRUKTURA E DETYRUESHME E AKTIT:
# (TITULLI ZYRTAR I AKTIT: {document_type})

**DREJTUAR:** (Gjykata / Prokuroria kompetente sipas natyrës së aktit)
**PARASHTRUESI / PADITËSI / KALLËZUESI:** {client_name}, me të dhënat nga dokumentet
**LËNDA:** (Objekti i kërkesës dhe Baza Statutare nga RAG context)
**KUNDËR TË PADITURVE / TË DYSHUARVE:** (Personat realë nga fashikulli)

## S E P S E (DISPOZITIVI ME PIKA TË QARTA)
## P R O P O Z O J / K Ë R K O J (PETITUMI DHE MASAT E KËRKUARA)
## A R S Y E T I M I (FAKTET, PROVAT, DOKTRINA DHE PRECEDENTËT)
## INVENTARI I PROVAVE MATERIALE DHE SHKENCORE (CORPUS DELICTI)

**PARASHTRUESI I AKTIT:**
{client_name}
Prishtinë, Republika e Kosovës
Data: {current_date_str}
"""