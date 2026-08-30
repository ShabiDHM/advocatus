# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - PILLAR 6: UNIVERSAL LEGAL DRAFTING V20.0 (COMPACT & STRICT)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class LegalDraftingService:
    """
    Modul i Pavarur Ekskluziv për HARTIMIN E TË GJITHA AKTEVE ZYRTARE (UNIVERSAL):
    - Padi Civile, Tregtare, Pronësore & Familjare
    - Kallëzime Penale
    - Prapësime, Kundërpadi dhe Ankesa
    - Kontrata dhe Marrëveshje
    - Inventarizimi i Provave (Corpus Delicti)
    - ZERO HALUCINACIONE + ZERO EMRA TË SHPIKUR
    """

    @staticmethod
    def detect_document_type(query: str) -> str:
        """
        Zbulon llojin e aktit nga kërkesa e përdoruesit.
        """
        query_lower = (query or "").lower()
        
        if any(kw in query_lower for kw in ["kallëzim penal", "kallezim penal", "kallzim penal"]):
            return "KALLËZIM PENAL"
        elif any(kw in query_lower for kw in ["ankesë", "ankese", "ankim", "apel"]):
            return "ANKESË"
        elif any(kw in query_lower for kw in ["kundërpadi", "kunderpadi"]):
            return "KUNDËRPADI"
        elif any(kw in query_lower for kw in ["prapësim", "prapsim"]):
            return "PRAPËSIM"
        elif any(kw in query_lower for kw in ["kontratë", "kontrate", "marrëveshje", "marreveshje"]):
            return "KONTRATË / MARRËVESHJE"
        elif any(kw in query_lower for kw in ["kërkesëpadi", "kerkesepadi", "padi"]):
            return "KËRKESËPADI CIVILE"
        else:
            return "AKT ZYRTAR"

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
        
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        if not document_type:
            document_type = LegalDraftingService.detect_document_type(query)
        
        search_query = query_text or f"Hartimi i {document_type} për lëminë: {case_domain}. Baza ligjore, nenet e zbatueshme."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=30
        )
        
        timeline_context = ""
        if db is not None and case_id:
            timeline_context = BasePillarService.get_timeline_context(
                db=db,
                case_id=case_id,
                user_id=user_id or ""
            )

        # Udhëzim specifik për llojin e dokumentit
        document_instruction = ""
        if document_type == "KALLËZIM PENAL":
            document_instruction = """
DREJTIMI: KALLËZIM PENAL
- I drejtohet: PROKURORISË SPECIALE (PSRK) ose PROKURORISË THEMELORE;
- Baza: KPPRK (Nr. 08/L-032) dhe KPRK (Nr. 06/L-074) — VETËM nga RAG context;
- Petitumi: Fillimi i hetimeve, masat emergjente, aktakuza.
"""
        elif document_type in ["KËRKESËPADI CIVILE", "KUNDËRPADI"]:
            document_instruction = f"""
DREJTIMI: {document_type}
- I drejtohet: GJYKATËS THEMELORE KOMPETENTE;
- Baza: LPK dhe LMD — VETËM nga RAG context;
- Petitumi: Dëmshpërblim, vërtetim të drejte, masa sigurimi.
"""
        elif document_type == "ANKESË":
            document_instruction = """
DREJTIMI: ANKESË
- I drejtohet: GJYKATËS SË APELIT (përmes Gjykatës Themelore);
- KUJDES: Nëse afati i ankimit ka skaduar (shih kronologjinë), rekomando KALLËZIM PENAL.
"""
        else:
            document_instruction = f"""
DREJTIMI: {document_type}
- Baza: VETËM nenet përkatëse nga RAG context.
"""

        base_prompt = BasePillarService.build_base_prompt(
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
        )

        return f"""
{base_prompt}

📝 KËRKESA SPECIFIKE E PËRDORUESIT:
"{query}"

📄 LLOJI I AKTIT: {document_type}

{document_instruction}

RREGULLA SUPREME TË HARTIMIT:
1. Parashtruesi/Paditësi/Kallëzuesi është GJITHMONË: **{client_name}**;
2. Fëmijët e mitur janë VIKTIMA TË MBROJTURA — asnjëherë te të dyshuarit;
3. MOS shpik asnjë emër, adresë, apo numër personal;
4. Nëse mungon një e dhënë: [Adresa e plotë] ose [Numri Personal sipas ID];
5. MOS cito asnjë nen nga memorja — VETËM nga RAG context;
6. MOS cito asnjë precedent që NUK gjendet në listën e verifikuar;
7. Provat audio/video citohen me sekonda [MM:SS - MM:SS];
8. Mbylle aktin te nënshkrimi përfundimtar — PA asnjë tekst pas tij.

STRUKTURA E DETYRUESHME E AKTIT:
# (TITULLI ZYRTAR: {document_type})

**DREJTUAR:** (Gjykata / Prokuroria kompetente)
**PARASHTRUESI:** {client_name}, me të dhënat nga dokumentet
**LËNDA:** (Objekti dhe Baza Statutare nga RAG context)
**KUNDËR TË PADITURVE / TË DYSHUARVE:** (Personat realë nga fashikulli)

## S E P S E (DISPOZITIVI ME PIKA TË QARTA)
## P R O P O Z O J / K Ë R K O J (PETITUMI)
## A R S Y E T I M I (FAKTET, PROVAT, DOKTRINA)
## INVENTARI I PROVAVE (CORPUS DELICTI)

**PARASHTRUESI I AKTIT:**
{client_name}
Prishtinë, Republika e Kosovës
Data: {current_date_str}
"""